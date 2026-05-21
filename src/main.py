import asyncio
import logging
from datetime import datetime, timezone

import streamlit as st

from components import (
    render_action_buttons,
    render_live_jobs,
    render_matched_jobs_table,
)
from database.core import init_db
from database.models.matched_jobs import JobStatus
from logger import bootstrap_logging
from services.fetch_jobs import fetch_from_company, fetch_from_query, iter_fetch_steps
from services.match_jobs import run_match_pipeline
from services.queries import (
    bulk_update_matched_job_status,
    get_matched_jobs,
    get_new_jobs_since,
)

bootstrap_logging()
logger = logging.getLogger("job-finder")


async def main() -> None:
    st.set_page_config(page_title="Job Finder", page_icon="💼", layout="wide")
    await init_db()

    st.title("💼 Job Finder")
    st.caption("Scan portals, run the match pipeline, and track your applications.")
    st.divider()

    fetch_clicked, match_clicked = render_action_buttons()

    if fetch_clicked:
        steps = list(iter_fetch_steps())
        fetch_start = datetime.now(timezone.utc)
        progress = st.progress(0, text="Starting fetch…")
        st.subheader("Newly Added Jobs")
        live_container = st.container()

        for i, (name, kind, data) in enumerate(steps):
            progress.progress(i / len(steps), text=f"Fetching: {name}")
            if kind == "query":
                await fetch_from_query(name, data["query"])
            else:
                await fetch_from_company(
                    name, data["careers_url"], data.get("scan_query")
                )
            render_live_jobs(live_container, await get_new_jobs_since(fetch_start))

        progress.progress(1.0, text="Done")
        st.success(f"Fetched from {len(steps)} sources.")

    if match_clicked:
        with st.spinner("Running match pipeline…"):
            count = await run_match_pipeline()
        if count == 0:
            st.warning("No jobs found for today. Run 'Fetch New Jobs' first.")
        else:
            st.success(f"Match pipeline complete — evaluated {count} job(s).")

    st.divider()
    st.subheader("Matched Jobs")

    filter_col, _ = st.columns([2, 6])
    with filter_col:
        status_filter = st.selectbox(
            "Filter by status",
            options=["All"] + [s.value.replace("_", " ").title() for s in JobStatus],
            label_visibility="collapsed",
        )

    _filter = (
        status_filter.lower().replace(" ", "_") if status_filter != "All" else None
    )
    jobs = await get_matched_jobs(_filter)

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
