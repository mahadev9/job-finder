import logging
import os
from typing import Iterator

import yaml

from core.config import settings
from services.llm_agent import invoke_agent
from services.prompt_config import build_fetch_system_prompt

logger = logging.getLogger("job-finder")


# ── Portal config ─────────────────────────────────────────────────────────────


def _load_config() -> dict:
    with open(os.path.join(settings.APP_PATH, "src", "templates", "portals.yml")) as f:
        return yaml.safe_load(f)


def _fetch_system_prompt() -> str:
    tf = _load_config().get("title_filter", {})
    return build_fetch_system_prompt(
        positive=tf.get("positive"),
        negative=tf.get("negative"),
    )


def get_enabled_queries() -> list[dict]:
    return [
        q for q in _load_config().get("search_queries", []) if q.get("enabled", True)
    ]


def get_enabled_companies() -> list[dict]:
    return [
        c for c in _load_config().get("tracked_companies", []) if c.get("enabled", True)
    ]


# ── Per-item fetch ────────────────────────────────────────────────────────────


async def fetch_from_query(name: str, query: str) -> None:
    prompt = (
        f"Search for jobs using this exact query:\n{query}\n\n"
        f"For each result, extract the company name, job title, direct job URL, "
        f"and portal name (from the URL domain). Save each one with save_job_to_db."
    )
    logger.info(f"Fetching search query: {name}")
    await invoke_agent(prompt, _fetch_system_prompt())


async def fetch_from_company(
    name: str, careers_url: str, scan_query: str | None
) -> None:
    if scan_query:
        prompt = (
            f"Search for jobs at {name} using this query:\n{scan_query}\n\n"
            f"For each result, extract the job title, direct job URL, and portal name. "
            f"Save each one with save_job_to_db using company_name='{name}'."
        )
    else:
        prompt = (
            f"Visit the careers page for {name} at: {careers_url}\n\n"
            f"Extract all relevant AI / ML / engineering job listings. "
            f"For each one, save it with save_job_to_db using company_name='{name}' "
            f"and the portal name derived from the URL domain."
        )
    logger.info(f"Fetching company: {name}")
    await invoke_agent(prompt, _fetch_system_prompt())


# ── Iterable steps (used by UI for progress) ─────────────────────────────────


def iter_fetch_steps() -> Iterator[tuple[str, str, dict]]:
    """Yield (label, kind, data) for every enabled portal entry."""
    for q in get_enabled_queries():
        yield q["name"], "query", q

    for c in get_enabled_companies():
        yield c["name"], "company", c
