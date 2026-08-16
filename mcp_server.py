import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.logger import bootstrap_logging
from database.core import SessionLocal, init_db
from database.models.jobs import Job
from database.models.matched_jobs import JobStatus, MatchedJob

logger = logging.getLogger("job-finder.mcp")


@asynccontextmanager
async def lifespan(_: FastMCP) -> AsyncIterator[None]:
    bootstrap_logging()
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
            logger.info(
                f"Job already exists: '{existing.role}' at {existing.company_name} "
                f"(portal: {existing.portal}, link: {existing.link})"
            )
            return (
                f"exists: '{existing.role}' at {existing.company_name} "
                f"is already saved (portal: {existing.portal}, link: {link})"
            )

        job = Job(company_name=company_name, role=role, link=link, portal=portal)
        session.add(job)
        await session.commit()
        logger.info(f"Added job: '{role}' at {company_name} (portal: {portal})")
        return (
            f"added: '{role}' at {company_name} saved successfully (portal: {portal})"
        )


@mcp.tool(
    name="save_matched_job",
    description=(
        "Save a matched job to the pipeline. "
        "Deduplication is on company + role. "
        "score is 0-10. "
        "status defaults to 'pending'; accepted values: pending, applied, rejected, low_match."
    ),
)
async def save_matched_job(
    company: str,
    role: str,
    score: float,
    role_link: str,
    reason: str,
    status: str = "pending",
) -> str:

    try:
        job_status = JobStatus(status.lower())
    except ValueError:
        valid = ", ".join(s.value for s in JobStatus)
        return f"error: invalid status '{status}'. Valid values: {valid}"

    if not (0 <= score <= 10):
        return "error: score must be between 0 and 10"

    async with SessionLocal() as session:
        result = await session.execute(
            select(MatchedJob).where(
                MatchedJob.company == company,
                MatchedJob.role == role,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(
                f"Matched job already exists: '{existing.role}' at {existing.company} "
                f"(score: {existing.score}, status: {existing.status.value}, "
                f"role_link: {existing.role_link}, reason: {existing.reason})"
            )
            return (
                f"exists: '{existing.role}' at {existing.company} "
                f"already saved (score: {existing.score}, status: {existing.status.value}, "
                f"role_link: {existing.role_link}, reason: {existing.reason})"
            )

        job = MatchedJob(
            company=company,
            role=role,
            score=score,
            role_link=role_link,
            reason=reason,
            status=job_status,
        )
        session.add(job)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            logger.info(f"Matched job already exists (race): '{role}' at {company}")
            return f"exists: '{role}' at {company} already saved"
        logger.info(
            f"Added matched job: '{role}' at {company} (score: {score}, status: {job_status.value})"
        )
        return f"added: '{role}' at {company} saved (score: {score}, status: {job_status.value}, role_link: {role_link}, reason: {reason})"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8050, log_level="warning")
