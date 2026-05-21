import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastmcp import FastMCP
from sqlalchemy import select

from src.database.core import SessionLocal, init_db
from src.database.models.jobs import Job
from src.database.models.matched_jobs import JobStatus, MatchedJob

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


@mcp.tool(
    name="save_job_to_db",
    description=(
        "Save a job listing to the database. "
        "Returns a message indicating whether the job was added or already exists. "
        "Deduplication is performed on the job link."
    ),
)
async def save_job_to_db(
    company_name: str,
    role: str,
    link: str,
    portal: str,
) -> str:
    """
    Save a job listing to the database.

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


@mcp.tool(
    name="save_matched_job",
    description=(
        "Save a matched job to the pipeline. "
        "Deduplication is on company + role. "
        "Status defaults to 'pending'; accepted values: pending, applied, rejected."
    ),
)
async def save_matched_job(
    company: str,
    role: str,
    score: float,
    status: str = "pending",
) -> str:
    try:
        job_status = JobStatus(status.lower())
    except ValueError:
        valid = ", ".join(s.value for s in JobStatus)
        return f"error: invalid status '{status}'. Valid values: {valid}"

    async with SessionLocal() as session:
        result = await session.execute(
            select(MatchedJob).where(
                MatchedJob.company == company,
                MatchedJob.role == role,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return (
                f"exists: '{existing.role}' at {existing.company} "
                f"already saved (score: {existing.score}, status: {existing.status.value})"
            )

        job = MatchedJob(company=company, role=role, score=score, status=job_status)
        session.add(job)
        await session.commit()
        return f"added: '{role}' at {company} saved (score: {score}, status: {job_status.value})"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8050)
