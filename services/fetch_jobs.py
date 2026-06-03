import logging
import os
from typing import AsyncIterator

import aiofiles
import yaml

from core.config import settings
from services.llm_agent import invoke_agent
from services.prompt_config import build_fetch_system_prompt

logger = logging.getLogger("job-finder")


# ── Portal config ─────────────────────────────────────────────────────────────


async def _load_config() -> dict:
    path = os.path.join(settings.APP_PATH, "templates", "portals.yml")
    async with aiofiles.open(path) as f:
        content = await f.read()
    return yaml.safe_load(content)


async def _fetch_system_prompt() -> str:
    config = await _load_config()
    tf = config.get("title_filter", {})
    lf = config.get("location_filter")
    return build_fetch_system_prompt(
        positive=tf.get("positive"),
        negative=tf.get("negative"),
        location_filter=lf,
    )


async def get_enabled_queries() -> list[dict]:
    return [
        q
        for q in (await _load_config()).get("search_queries", [])
        if q.get("enabled", True)
    ]


async def get_enabled_companies() -> list[dict]:
    return [
        c
        for c in (await _load_config()).get("tracked_companies", [])
        if c.get("enabled", True)
    ]


# ── Per-item fetch ────────────────────────────────────────────────────────────


async def fetch_from_query(name: str, query: str, model: str | None = None) -> None:
    prompt = (
        f"Search for jobs using this exact query:\n{query}\n\n"
        f"For each result, extract the company name, job title, direct job URL, "
        f"and portal name (from the URL domain). Save each one with save_job_to_db."
    )
    logger.info(f"Fetching search query: {name}")
    await invoke_agent(prompt, await _fetch_system_prompt(), pipeline="fetch", model=model)


async def fetch_from_company(
    name: str, careers_url: str, scan_query: str | None, model: str | None = None
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
    await invoke_agent(prompt, await _fetch_system_prompt(), pipeline="fetch", model=model)


# ── Iterable steps (used by UI for progress) ─────────────────────────────────


async def iter_fetch_steps(
    companies: list[str] | None = None,
    queries: list[str] | None = None,
) -> AsyncIterator[tuple[str, str, dict]]:
    for q in await get_enabled_queries():
        if queries is None or q["name"] in queries:
            yield q["name"], "query", q

    for c in await get_enabled_companies():
        if companies is None or c["name"] in companies:
            yield c["name"], "company", c
