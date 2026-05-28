import logging
from datetime import date, datetime, timedelta

from sqlalchemy import func, select

from core.config import settings
from database.core import SessionLocal
from database.models.jobs import Job
from database.models.matched_jobs import JobStatus, MatchedJob
from database.models.token_usage import TokenUsage

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


async def get_unmatched_jobs(
    for_date: date | None = None,
    companies: list[str] | None = None,
) -> list[Job]:
    async with SessionLocal() as session:
        stmt = (
            select(Job)
            .where(Job.pipeline_ran == False)  # noqa: E712
            .order_by(Job.created_at.asc())
        )
        if for_date:
            day_start = datetime.combine(for_date, datetime.min.time(), tzinfo=settings.tz)
            day_end = datetime.combine(
                for_date + timedelta(days=1), datetime.min.time(), tzinfo=settings.tz
            )
            stmt = stmt.where(Job.created_at >= day_start, Job.created_at < day_end)
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


async def get_distinct_token_usage_models() -> list[str]:
    async with SessionLocal() as session:
        stmt = select(TokenUsage.model).distinct().order_by(TokenUsage.model)
        result = await session.execute(stmt)
        return [row[0] for row in result.all() if row[0]]


async def get_token_usage_page(
    pipeline: str | None = None,
    model: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[TokenUsage], int, dict]:
    async with SessionLocal() as session:
        conditions = []
        if pipeline:
            conditions.append(TokenUsage.pipeline == pipeline)
        if model:
            conditions.append(TokenUsage.model == model)
        if from_date:
            conditions.append(
                TokenUsage.created_at
                >= datetime.combine(from_date, datetime.min.time(), tzinfo=settings.tz)
            )
        if to_date:
            conditions.append(
                TokenUsage.created_at
                < datetime.combine(
                    to_date + timedelta(days=1), datetime.min.time(), tzinfo=settings.tz
                )
            )

        count_stmt = select(func.count()).select_from(TokenUsage)
        agg_stmt = select(
            func.coalesce(func.sum(TokenUsage.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(TokenUsage.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(TokenUsage.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(TokenUsage.reasoning_tokens), 0).label("reasoning_tokens"),
        )
        page_stmt = select(TokenUsage).order_by(TokenUsage.created_at.desc())

        if conditions:
            count_stmt = count_stmt.where(*conditions)
            agg_stmt = agg_stmt.where(*conditions)
            page_stmt = page_stmt.where(*conditions)

        total = (await session.execute(count_stmt)).scalar() or 0
        agg = (await session.execute(agg_stmt)).one()
        rows = list(
            (await session.execute(page_stmt.offset(offset).limit(limit))).scalars().all()
        )

        return rows, total, {
            "input_tokens": agg.input_tokens,
            "output_tokens": agg.output_tokens,
            "total_tokens": agg.total_tokens,
            "reasoning_tokens": agg.reasoning_tokens,
        }


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
        now = datetime.now(settings.tz)
        for job in jobs:
            new_status = updates[job.id]
            job.status = new_status
            if new_status == JobStatus.PENDING:
                job.status_changed_at = None
            else:
                job.status_changed_at = now
        await session.commit()
        logger.info(f"Updated status for {len(jobs)} job(s)")
