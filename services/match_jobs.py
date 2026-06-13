import logging
from datetime import date, datetime
from pathlib import Path

import aiofiles

from core.config import settings
from database.models.jobs import Job
from services.llm_agent import invoke_agent
from services.prompt_config import build_match_system_prompt
from services.queries import get_recent_matched_jobs, get_unmatched_jobs, mark_jobs_matched

logger = logging.getLogger("job-finder")

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_BATCH_SIZE = 15

_templates_cache: tuple[str, str] | None = None


async def _load_templates() -> tuple[str, str]:
    global _templates_cache
    if _templates_cache is not None:
        return _templates_cache
    async with aiofiles.open(_TEMPLATES_DIR / "profile.md") as f:
        profile = await f.read()
    async with aiofiles.open(_TEMPLATES_DIR / "cv.md") as f:
        cv = await f.read()
    _templates_cache = (profile, cv)
    return _templates_cache


def _build_match_prompt(jobs: list[Job]) -> str:
    lines = [
        "Evaluate and score each of the following job listings against the candidate profile.\n"
    ]
    for i, job in enumerate(jobs, 1):
        lines.append(
            f"{i}. Company: {job.company_name} | Role: {job.role} | "
            f"Link: {job.link} | Portal: {job.portal}"
        )
    lines.append(
        "\nFor every job with score >= 0.50, call save_matched_job with: "
        "company, role, score, role_link (use the Link URL exactly as given), and reason. "
        "Process all jobs — do not stop early."
    )
    return "\n".join(lines)


async def run_match_pipeline(
    progress_callback=None,
    for_date: date | None = None,
    batch_size: int = _BATCH_SIZE,
    companies: list[str] | None = None,
    created_by: str | None = None,
    model: str | None = None,
    should_stop=None,
) -> tuple[int, bool]:
    jobs = await get_unmatched_jobs(for_date=for_date, companies=companies, created_by=created_by)
    if not jobs:
        logger.info("No jobs found for today — skipping match pipeline")
        return 0, False

    logger.info(f"Running match pipeline on {len(jobs)} job(s)")
    profile, cv = await _load_templates()
    today = (for_date or datetime.now(settings.tz).date()).strftime("%B %d, %Y")
    recent_matches = await get_recent_matched_jobs(companies=companies, limit=5)
    system_prompt = build_match_system_prompt(profile, cv, today, recent_matches)

    total_batches = -(-len(jobs) // batch_size)
    processed = 0
    for i in range(0, len(jobs), batch_size):
        if should_stop and should_stop():
            logger.info("Match pipeline stopped by request")
            return processed, True
        batch = jobs[i : i + batch_size]
        batch_num = i // batch_size + 1
        logger.info(f"Matching batch {batch_num}/{total_batches} ({len(batch)} jobs)")
        if progress_callback:
            await progress_callback(batch_num, total_batches)
        await invoke_agent(_build_match_prompt(batch), system_prompt, pipeline="match", model=model)
        await mark_jobs_matched([j.id for j in batch])
        processed += len(batch)
        logger.info(f"Batch {batch_num}/{total_batches} complete")

    logger.info(f"Match pipeline complete: evaluated {len(jobs)} job(s)")
    return processed, False
