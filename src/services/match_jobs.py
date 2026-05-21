import functools
import logging
from pathlib import Path

from database.models.jobs import Job
from services.llm_agent import invoke_agent
from services.prompt_config import build_match_system_prompt
from services.queries import get_todays_jobs

logger = logging.getLogger("job-finder")

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_BATCH_SIZE = 15


@functools.cache
def _load_templates() -> tuple[str, str]:
    profile = (_TEMPLATES_DIR / "profile.md").read_text()
    cv = (_TEMPLATES_DIR / "cv.md").read_text()
    return profile, cv


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


async def run_match_pipeline() -> int:
    jobs = await get_todays_jobs()
    if not jobs:
        logger.info("No jobs found for today — skipping match pipeline")
        return 0

    logger.info("Running match pipeline on %d job(s)", len(jobs))
    profile, cv = _load_templates()
    system_prompt = build_match_system_prompt(profile, cv)

    for i in range(0, len(jobs), _BATCH_SIZE):
        batch = jobs[i : i + _BATCH_SIZE]
        logger.info(
            "Matching batch %d/%d (%d jobs)",
            i // _BATCH_SIZE + 1,
            -(-len(jobs) // _BATCH_SIZE),
            len(batch),
        )
        await invoke_agent(_build_match_prompt(batch), system_prompt)

    return len(jobs)
