import asyncio
import logging
import threading
import time
from datetime import date, datetime, timezone

import streamlit as st

from ui.components import (
    render_action_buttons,
    render_live_jobs,
    render_matched_jobs_table,
)
from database.core import init_db
from database.models.matched_jobs import JobStatus
from core.logger import bootstrap_logging
from core.pipeline_state import pipeline_state
from services.fetch_jobs import fetch_from_company, fetch_from_query, iter_fetch_steps
from services.match_jobs import run_match_pipeline
from services.queries import (
    bulk_update_matched_job_status,
    get_matched_jobs,
    get_new_jobs_since,
)

bootstrap_logging()
logger = logging.getLogger("job-finder")


async def _run_fetch() -> None:
    steps = list(iter_fetch_steps())
    fetch_start = datetime.now(timezone.utc)
    pipeline_state.start("fetch")
    try:
        for i, (name, kind, data) in enumerate(steps):
            pipeline_state.update((i + 1) / (len(steps) + 1), f"Fetching ({i + 1}/{len(steps)}): {name}…")
            if kind == "query":
                await fetch_from_query(name, data["query"])
            else:
                await fetch_from_company(
                    name, data["careers_url"], data.get("scan_query")
                )
            new_jobs = await get_new_jobs_since(fetch_start)
            pipeline_state.add_jobs(new_jobs)
            pipeline_state.update(
                (i + 1) / (len(steps) + 1),
                f"Fetching ({i + 1}/{len(steps)}): {name}… ({len(new_jobs)} new job(s) so far)",
            )
        pipeline_state.finish(f"Fetched from {len(steps)} sources.")
    except Exception as exc:
        logger.exception("Fetch pipeline failed")
        pipeline_state.fail(str(exc))


async def _run_match(for_date: date) -> None:
    pipeline_state.start("match")
    try:
        pipeline_state.update(0.05, f"Loading jobs for {for_date}…")

        def _on_batch(batch_num: int, total_batches: int) -> None:
            progress = 0.1 + (batch_num / total_batches) * 0.85
            pipeline_state.update(progress, f"Matching batch {batch_num}/{total_batches}…")

        count = await run_match_pipeline(progress_callback=_on_batch, for_date=for_date)
        if count == 0:
            pipeline_state.finish(
                f"No jobs found for {for_date}. Run 'Fetch New Jobs' first.", "warning"
            )
        else:
            pipeline_state.finish(f"Match pipeline complete — evaluated {count} job(s).")
    except Exception as exc:
        logger.exception("Match pipeline failed")
        pipeline_state.fail(str(exc))


def _start_in_thread(coro_fn) -> None:
    threading.Thread(target=lambda: asyncio.run(coro_fn()), daemon=True).start()


async def main() -> None:
    st.set_page_config(page_title="Job Finder", page_icon="💼", layout="wide")
    await init_db()

    st.title("💼 Job Finder")
    st.caption("Scan portals, run the match pipeline, and track your applications.")
    st.divider()

    state = pipeline_state.snapshot
    is_running = state["running"] is not None

    fetch_clicked, match_clicked, match_date = render_action_buttons(
        fetch_disabled=is_running,
        match_disabled=is_running,
    )

    if fetch_clicked and not is_running:
        logger.info("Fetch pipeline triggered from UI")
        _start_in_thread(_run_fetch)
        st.rerun()

    if match_clicked and not is_running:
        logger.info("Match pipeline triggered from UI for %s", match_date)
        _d = match_date
        _start_in_thread(lambda: _run_match(_d))
        st.rerun()

    if is_running:
        st.progress(state["progress"], text=state["status_text"])
        if state["running"] == "fetch" and state["new_jobs"]:
            st.subheader("Newly Added Jobs")
            render_live_jobs(st.container(), state["new_jobs"])
        time.sleep(1)
        st.rerun()

    if state["result_kind"] == "success":
        st.success(state["result_message"])
    elif state["result_kind"] == "warning":
        st.warning(state["result_message"])
    elif state["result_kind"] == "error":
        st.error(state["result_message"])

    st.divider()
    st.subheader("Matched Jobs")

    filter_col, from_col, to_col, _ = st.columns([2, 2, 2, 2])
    with filter_col:
        status_filter = st.selectbox(
            "Filter by status",
            options=["All"] + [s.value.replace("_", " ").title() for s in JobStatus],
            label_visibility="collapsed",
        )
    with from_col:
        from_date = st.date_input("From", value=None, label_visibility="collapsed")
    with to_col:
        to_date = st.date_input("To", value=None, label_visibility="collapsed")

    _filter = (
        status_filter.lower().replace(" ", "_") if status_filter != "All" else None
    )
    jobs = await get_matched_jobs(_filter, from_date or None, to_date or None)

    pending_updates = {
        job.id: JobStatus(st.session_state[f"status_{job.id}"])
        for job in jobs
        if f"status_{job.id}" in st.session_state
        and st.session_state[f"status_{job.id}"] != job.status.value
    }
    if pending_updates:
        await bulk_update_matched_job_status(pending_updates)
        for job in jobs:
            if job.id in pending_updates:
                job.status = pending_updates[job.id]

    render_matched_jobs_table(jobs)


asyncio.run(main())