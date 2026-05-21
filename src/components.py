import streamlit as st

from database.models.jobs import Job
from database.models.matched_jobs import JobStatus, MatchedJob

STATUS_BADGE = {"pending": "🟡", "applied": "🔵", "rejected": "🔴", "low_match": "⚫"}
STATUS_OPTIONS = [s.value for s in JobStatus]
MATCH_COL_WIDTHS = [2, 3, 1, 2]


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


def render_live_jobs(
    container: st.delta_generator.DeltaGenerator, jobs: list[Job]
) -> None:
    with container:
        if not jobs:
            st.caption("No new jobs yet…")
            return
        st.caption(f"**{len(jobs)} new job(s) added**")
        for job in jobs:
            cols = st.columns([3, 3, 3, 2])
            cols[0].write(job.company_name)
            cols[1].write(job.role)
            cols[2].markdown(f"[link]({job.link})")
            cols[3].write(job.portal)


def _status_label(value: str) -> str:
    icon = STATUS_BADGE.get(value, "⚪")
    return f"{icon} {value.replace('_', ' ').capitalize()}"


def render_matched_jobs_table(jobs: list[MatchedJob]) -> None:
    if not jobs:
        st.info("No matched jobs found. Run the pipeline to populate results.")
        return

    st.caption(f"{len(jobs)} job(s) found")
    cols = st.columns(MATCH_COL_WIDTHS)
    for col, label in zip(
        cols, ["**Company**", "**Role**", "**Score /10**", "**Status**"]
    ):
        col.markdown(label)
    st.divider()

    for job in jobs:
        cols = st.columns(MATCH_COL_WIDTHS)
        cols[0].write(job.company)
        cols[1].markdown(f"[{job.role}]({job.role_link})")
        cols[2].write(f"{job.score:.1f}")
        cols[3].selectbox(
            "",
            options=STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(job.status.value),
            key=f"status_{job.id}",
            label_visibility="collapsed",
            format_func=_status_label,
        )
        if job.reason:
            st.caption(f"↳ {job.reason}")
