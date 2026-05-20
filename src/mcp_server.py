import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastmcp import FastMCP
from sqlalchemy import select

from src.database.core import Job, SessionLocal, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastMCP) -> AsyncIterator[None]:
    await init_db()
    yield


mcp = FastMCP(
    name="Job Finder MCP",
    instructions="Tools for saving and querying job listings.",
    version="1.0.0",
    lifespan=lifespan,
)


@mcp.tool()
async def save_job_to_db(
    company_name: str,
    role: str,
    link: str,
    portal: str,
) -> str:
    """Save a job listing to the database.

    Returns a message indicating whether the job was added or already exists.
    Deduplication is performed on the job link.
    """
    async with SessionLocal() as session:
        result = await session.execute(select(Job).where(Job.link == link))
        existing = result.scalar_one_or_none()

        if existing:
            return (
                f"exists: '{existing.role}' at {existing.company_name} "
                f"is already saved (portal: {existing.portal}, link: {link})"
            )

        job = Job(company_name=company_name, role=role, link=link, portal=portal)
        session.add(job)
        await session.commit()
        return (
            f"added: '{role}' at {company_name} saved successfully (portal: {portal})"
        )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8050)
