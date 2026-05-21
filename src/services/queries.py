import logging
from datetime import date, datetime, timezone

from sqlalchemy import select

from database.core import SessionLocal
from database.models.jobs import Job
from database.models.matched_jobs import JobStatus, MatchedJob

logger = logging.getLogger("job-finder")


async def get_matched_jobs(status_filter: str | None) -> list[MatchedJob]:
    async with SessionLocal() as session:
        stmt = select(MatchedJob).order_by(MatchedJob.score.desc())
        if status_filter:
            stmt = stmt.where(MatchedJob.status == JobStatus(status_filter))
        return list((await session.execute(stmt)).scalars().all())


async def get_new_jobs_since(since: datetime) -> list[Job]:
    async with SessionLocal() as session:
        stmt = (
            select(Job).where(Job.created_at >= since).order_by(Job.created_at.desc())
        )
        return list((await session.execute(stmt)).scalars().all())


async def get_todays_jobs() -> list[Job]:
    today_start = datetime.combine(
        date.today(), datetime.min.time(), tzinfo=timezone.utc
    )
    async with SessionLocal() as session:
        stmt = (
            select(Job)
            .where(Job.created_at >= today_start)
            .order_by(Job.created_at.asc())
        )
        return list((await session.execute(stmt)).scalars().all())


async def bulk_update_matched_job_status(updates: dict[int, JobStatus]) -> None:
    if not updates:
        return
    async with SessionLocal() as session:
        result = await session.execute(
            select(MatchedJob).where(MatchedJob.id.in_(updates))
        )
        jobs = result.scalars().all()
        if len(jobs) != len(updates):
            missing = set(updates) - {j.id for j in jobs}
            logger.warning(f"Status update skipped for unknown job IDs: {missing}")
        for job in jobs:
            job.status = updates[job.id]
        await session.commit()
        logger.info(f"Updated status for {len(jobs)} job(s)")
