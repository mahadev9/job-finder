import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select

from core.config import settings
from database.core import SessionLocal
from database.models.jobs import Job
from database.models.matched_jobs import JobStatus, MatchedJob

logger = logging.getLogger("job-finder")


async def get_matched_jobs(
    status_filter: str | None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[MatchedJob]:
    async with SessionLocal() as session:
        stmt = select(MatchedJob).order_by(MatchedJob.score.desc())
        if status_filter:
            stmt = stmt.where(MatchedJob.status == JobStatus(status_filter))
        if from_date:
            stmt = stmt.where(
                MatchedJob.created_at
                >= datetime.combine(from_date, datetime.min.time(), tzinfo=settings.tz)
            )
        if to_date:
            stmt = stmt.where(
                MatchedJob.created_at
                < datetime.combine(
                    to_date + timedelta(days=1),
                    datetime.min.time(),
                    tzinfo=settings.tz,
                )
            )
        return list((await session.execute(stmt)).scalars().all())


async def get_new_jobs_since(since: datetime) -> list[Job]:
    async with SessionLocal() as session:
        stmt = (
            select(Job).where(Job.created_at >= since).order_by(Job.created_at.desc())
        )
        return list((await session.execute(stmt)).scalars().all())


async def get_jobs_for_date(
    for_date: date, companies: list[str] | None = None
) -> list[Job]:
    day_start = datetime.combine(for_date, datetime.min.time(), tzinfo=settings.tz)
    day_end = datetime.combine(
        for_date + timedelta(days=1), datetime.min.time(), tzinfo=settings.tz
    )
    async with SessionLocal() as session:
        stmt = (
            select(Job)
            .where(
                Job.created_at >= day_start,
                Job.created_at < day_end,
                Job.pipeline_ran == False,  # noqa: E712
            )
            .order_by(Job.created_at.asc())
        )
        if companies:
            stmt = stmt.where(Job.company_name.in_(companies))
        return list((await session.execute(stmt)).scalars().all())


async def mark_jobs_matched(job_ids: list[int]) -> None:
    if not job_ids:
        return
    async with SessionLocal() as session:
        result = await session.execute(select(Job).where(Job.id.in_(job_ids)))
        for job in result.scalars().all():
            job.pipeline_ran = True
        await session.commit()


async def get_fetched_jobs(
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[Job]:
    async with SessionLocal() as session:
        stmt = select(Job).order_by(Job.created_at.desc())
        if from_date:
            stmt = stmt.where(
                Job.created_at
                >= datetime.combine(from_date, datetime.min.time(), tzinfo=settings.tz)
            )
        if to_date:
            stmt = stmt.where(
                Job.created_at
                < datetime.combine(
                    to_date + timedelta(days=1),
                    datetime.min.time(),
                    tzinfo=settings.tz,
                )
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
