from datetime import datetime

from sqlalchemy import select

from database.core import SessionLocal
from database.models.jobs import Job
from database.models.matched_jobs import JobStatus, MatchedJob


async def get_matched_jobs(status_filter: str | None) -> list[MatchedJob]:
    async with SessionLocal() as session:
        stmt = select(MatchedJob).order_by(MatchedJob.score.desc())
        if status_filter and status_filter != "All":
            stmt = stmt.where(MatchedJob.status == JobStatus(status_filter.lower()))
        return list((await session.execute(stmt)).scalars().all())


async def get_new_jobs_since(since: datetime) -> list[Job]:
    async with SessionLocal() as session:
        stmt = select(Job).where(Job.created_at >= since).order_by(Job.created_at.desc())
        return list((await session.execute(stmt)).scalars().all())