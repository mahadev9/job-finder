import asyncio
import logging

import streamlit as st
from sqlalchemy import select

from database.core import SessionLocal, init_db
from database.models.matched_jobs import JobStatus, MatchedJob
from logger import bootstrap_logging

bootstrap_logging()
logger = logging.getLogger("job-finder")

st.set_page_config(
    page_title="Job Finder",
    page_icon="💼",
    layout="wide",
)


@st.cache_resource
def init_database():
    asyncio.run(init_db())


init_database()


async def _load_matched_jobs(status_filter: str | None) -> list[MatchedJob]:
    async with SessionLocal() as session:
        stmt = select(MatchedJob).order_by(MatchedJob.score.desc())
        if status_filter and status_filter != "All":
            stmt = stmt.where(MatchedJob.status == JobStatus(status_filter.lower()))
        result = await session.execute(stmt)
        return list(result.scalars().all())


def load_matched_jobs(status_filter: str | None) -> list[MatchedJob]:
    return asyncio.run(_load_matched_jobs(status_filter))


STATUS_BADGE = {
    "pending": "🟡",
    "applied": "🔵",
    "rejected": "🔴",
}


st.title("💼 Job Finder")
st.caption("Scan portals, run the match pipeline, and track your applications.")

st.divider()

col_fetch, col_match, _ = st.columns([1, 1, 4])

with col_fetch:
    fetch_clicked = st.button(
        "🔍 Fetch New Jobs",
        use_container_width=True,
        help="Scan all enabled portals and save new job listings to the database.",
    )

with col_match:
    match_clicked = st.button(
        "⚙️ Run Match Pipeline",
        use_container_width=True,
        help="Score all unmatched jobs against your profile and save results.",
    )

if fetch_clicked:
    with st.spinner("Fetching new jobs from portals…"):
        # TODO: call fetch logic
        pass
    st.success("Fetched new jobs successfully.")

if match_clicked:
    with st.spinner("Running match pipeline…"):
        # TODO: call match pipeline logic
        pass
    st.success("Match pipeline complete.")

st.divider()

st.subheader("Matched Jobs")

filter_col, _ = st.columns([2, 6])
with filter_col:
    status_filter = st.selectbox(
        "Filter by status",
        options=["All", "Pending", "Applied", "Rejected"],
        index=0,
        label_visibility="collapsed",
    )

jobs = load_matched_jobs(status_filter)

if not jobs:
    st.info("No matched jobs found. Run the pipeline to populate results.")
else:
    st.caption(f"{len(jobs)} job(s) found")

    header = st.columns([3, 3, 1, 1])
    header[0].markdown("**Company**")
    header[1].markdown("**Role**")
    header[2].markdown("**Score**")
    header[3].markdown("**Status**")

    st.divider()

    for job in jobs:
        icon = STATUS_BADGE.get(job.status.value, "⚪")
        row = st.columns([3, 3, 1, 1])
        row[0].write(job.company)
        row[1].write(job.role)
        row[2].write(f"{job.score:.2f}")
        row[3].write(f"{icon} {job.status.value.capitalize()}")
