import asyncio
import logging

import streamlit as st
from sqlalchemy import select

from database.core import SessionLocal, init_db
from database.models.matched_jobs import JobStatus, MatchedJob
from logger import bootstrap_logging

bootstrap_logging()
logger = logging.getLogger("job-finder")

# ── Constants ─────────────────────────────────────────────────────────────────

STATUS_BADGE = {
    "pending": "🟡",
    "applied": "🔵",
    "rejected": "🔴",
}

COL_WIDTHS = [3, 3, 1, 1]

# ── DB ────────────────────────────────────────────────────────────────────────


@st.cache_resource
def init_database() -> None:
    asyncio.run(init_db())


# ── Data helpers ──────────────────────────────────────────────────────────────


async def _fetch_matched_jobs(status_filter: str | None) -> list[MatchedJob]:
    async with SessionLocal() as session:
        stmt = select(MatchedJob).order_by(MatchedJob.score.desc())
        if status_filter and status_filter != "All":
            stmt = stmt.where(MatchedJob.status == JobStatus(status_filter.lower()))
        return list((await session.execute(stmt)).scalars().all())


def get_matched_jobs(status_filter: str | None) -> list[MatchedJob]:
    return asyncio.run(_fetch_matched_jobs(status_filter))


# ── UI components ─────────────────────────────────────────────────────────────


def render_action_buttons() -> tuple[bool, bool]:
    col_fetch, col_match, _ = st.columns([1, 1, 4])
    with col_fetch:
        fetch = st.button(
            "🔍 Fetch New Jobs",
            use_container_width=True,
            help="Scan all enabled portals and save new job listings to the database.",
        )
    with col_match:
        match = st.button(
            "⚙️ Run Match Pipeline",
            use_container_width=True,
            help="Score all unmatched jobs against your profile and save results.",
        )
    return fetch, match


def render_jobs_table(jobs: list[MatchedJob]) -> None:
    if not jobs:
        st.info("No matched jobs found. Run the pipeline to populate results.")
        return

    st.caption(f"{len(jobs)} job(s) found")

    cols = st.columns(COL_WIDTHS)
    for col, label in zip(cols, ["**Company**", "**Role**", "**Score**", "**Status**"]):
        col.markdown(label)

    st.divider()

    for job in jobs:
        icon = STATUS_BADGE.get(job.status.value, "⚪")
        cols = st.columns(COL_WIDTHS)
        cols[0].write(job.company)
        cols[1].write(job.role)
        cols[2].write(f"{job.score:.2f}")
        cols[3].write(f"{icon} {job.status.value.capitalize()}")


# ── Page ──────────────────────────────────────────────────────────────────────


def main() -> None:
    st.set_page_config(page_title="Job Finder", page_icon="💼", layout="wide")
    init_database()

    st.title("💼 Job Finder")
    st.caption("Scan portals, run the match pipeline, and track your applications.")
    st.divider()

    fetch_clicked, match_clicked = render_action_buttons()

    if fetch_clicked:
        with st.spinner("Fetching new jobs from portals…"):
            pass  # TODO: fetch logic
        st.success("Fetched new jobs successfully.")

    if match_clicked:
        with st.spinner("Running match pipeline…"):
            pass  # TODO: match pipeline logic
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

    render_jobs_table(get_matched_jobs(status_filter))


main()
