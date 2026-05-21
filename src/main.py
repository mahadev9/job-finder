import asyncio
import logging
from datetime import datetime, timezone

import streamlit as st

from components import render_action_buttons, render_live_jobs, render_matched_jobs_table
from database.core import init_db
from logger import bootstrap_logging
from services.fetch_jobs import fetch_from_company, fetch_from_query, iter_fetch_steps
from services.queries import get_matched_jobs, get_new_jobs_since

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
                await fetch_from_company(name, data["careers_url"], data.get("scan_query"))
            render_live_jobs(live_container, await get_new_jobs_since(fetch_start))

        progress.progress(1.0, text="Done")
        st.success(f"Fetched from {len(steps)} sources.")

    if match_clicked:
        with st.spinner("Running match pipeline…"):
            pass
        st.success("Match pipeline complete.")

    st.divider()
    st.subheader("Matched Jobs")

    filter_col, _ = st.columns([2, 6])
    with filter_col:
        status_filter = st.selectbox(
            "Filter by status",
            options=["All", "Pending", "Applied", "Rejected"],
            label_visibility="collapsed",
        )

    render_matched_jobs_table(await get_matched_jobs(status_filter))


asyncio.run(main())