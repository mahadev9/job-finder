import logging
from datetime import date
from pathlib import Path

import aiofiles

from database.models.jobs import Job
from services.llm_agent import invoke_agent
from services.prompt_config import build_match_system_prompt
from services.queries import get_jobs_for_date

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
    progress_callback=None, for_date: date | None = None
) -> int:
    jobs = await get_jobs_for_date(for_date or date.today())
    if not jobs:
        logger.info("No jobs found for today — skipping match pipeline")
        return 0

    logger.info(f"Running match pipeline on {len(jobs)} job(s)")
    profile, cv = await _load_templates()
    system_prompt = build_match_system_prompt(profile, cv)

    total_batches = -(-len(jobs) // _BATCH_SIZE)
    for i in range(0, len(jobs), _BATCH_SIZE):
        batch = jobs[i : i + _BATCH_SIZE]
        batch_num = i // _BATCH_SIZE + 1
        logger.info(f"Matching batch {batch_num}/{total_batches} ({len(batch)} jobs)")
        if progress_callback:
            await progress_callback(batch_num, total_batches)
        await invoke_agent(_build_match_prompt(batch), system_prompt)
        logger.info(f"Batch {batch_num}/{total_batches} complete")

    logger.info(f"Match pipeline complete: evaluated {len(jobs)} job(s)")
    return len(jobs)
