import logging
from datetime import date, datetime

import reflex as rx
from pydantic import BaseModel

from core.config import settings
from core.logger import bootstrap_logging
from core.pipeline_state import pipeline_state
from database.core import init_db
from database.models.matched_jobs import JobStatus
from services.fetch_jobs import (
    fetch_from_company,
    fetch_from_query,
    get_enabled_companies,
    get_enabled_queries,
    iter_fetch_steps,
)
from services.match_jobs import run_match_pipeline
from services.queries import (
    bulk_update_matched_job_status,
    get_distinct_token_usage_models,
    get_fetched_jobs,
    get_matched_jobs,
    get_new_jobs_since,
    get_token_usage_page,
    insert_job_manual,
)

STATUS_COLORS: dict[str, str] = {
    "pending": "amber",
    "interested": "violet",
    "applied": "blue",
    "rejected": "red",
    "not_interested": "orange",
    "low_match": "gray",
}

STATUS_LABELS: dict[str, str] = {
    "pending": "Pending",
    "interested": "Interested",
    "applied": "Applied",
    "rejected": "Rejected",
    "not_interested": "Not Interested",
    "low_match": "Low Match",
}


class NewJob(BaseModel):
    company: str
    role: str
    link: str
    portal: str


class JobRow(BaseModel):
    id: int
    company: str
    role: str
    role_link: str
    score: float
    score_label: str
    score_color: str
    status: str
    status_label: str
    status_color: str
    reason: str
    status_changed_at: str = ""


class FetchedJobRow(BaseModel):
    id: int
    company: str
    role: str
    link: str
    portal: str
    fetched_date: str
    fetched_ts: float = 0.0
    pipeline_ran: bool = False
    created_by: str = "system"


def _detect_portal(link: str) -> str:
    l = link.lower()
    for domain, name in [
        ("greenhouse.io", "greenhouse"),
        ("ashbyhq.com", "ashby"),
        ("jobs.lever.co", "lever"),
        ("myworkdayjobs.com", "workday"),
        ("linkedin.com", "linkedin"),
        ("workable.com", "workable"),
        ("wellfound.com", "wellfound"),
        ("indeed.com", "indeed"),
    ]:
        if domain in l:
            return name
    return "manual"


def _score_color(score: float) -> str:
    if score >= 8:
        return "green"
    if score >= 6:
        return "amber"
    return "red"


def _to_row(j) -> JobRow:
    return JobRow(
        id=j.id,
        company=j.company,
        role=j.role,
        role_link=j.role_link,
        score=j.score,
        score_label=f"{j.score:.1f}",
        score_color=_score_color(j.score),
        status=j.status.value,
        status_label=STATUS_LABELS.get(j.status.value, j.status.value),
        status_color=STATUS_COLORS.get(j.status.value, "gray"),
        reason=j.reason or "",
        status_changed_at=(
            j.status_changed_at.strftime("%b %d, %Y") if j.status_changed_at else ""
        ),
    )


def _to_fetched_row(j) -> FetchedJobRow:
    return FetchedJobRow(
        id=j.id,
        company=j.company_name,
        role=j.role,
        link=j.link,
        portal=j.portal,
        fetched_date=j.created_at.strftime("%b %d, %Y") if j.created_at else "",
        fetched_ts=j.created_at.timestamp() if j.created_at else 0.0,
        pipeline_ran=j.pipeline_ran,
        created_by=j.created_by,
    )


class AppState(rx.State):
    # Model selection
    selected_model: str = ""
    available_models: list[str] = []

    # Pipeline
    running: str = ""
    stop_requested: bool = False
    progress: float = 0.0
    status_text: str = ""
    result_message: str = ""
    result_kind: str = ""
    new_jobs: list[NewJob] = []

    # Matched jobs filters
    status_filter: str = "all"
    company_filter: list[str] = []
    company_filter_search: str = ""
    from_date: str = ""
    to_date: str = ""
    score_range: list[int] = [0, 10]
    match_date: str = ""
    match_batch_size: int = 2

    # Match pipeline options
    match_companies: list[str] = []
    match_companies_search: str = ""
    match_created_by: str = "all"

    # Fetch pipeline options
    fetch_available_companies: list[str] = []
    fetch_available_queries: list[str] = []
    fetch_companies: list[str] = []
    fetch_queries: list[str] = []
    fetch_companies_search: str = ""
    fetch_queries_search: str = ""

    # Matched jobs sort
    jobs_sort_col: str = "score"
    jobs_sort_asc: bool = False

    # Fetched jobs filters
    fetched_company_filter: list[str] = []
    fetched_company_filter_search: str = ""
    fetched_from_date: str = ""
    fetched_to_date: str = ""
    fetched_pipeline_ran_filter: str = "all"

    # Fetched jobs sort
    fetched_sort_col: str = "fetched_ts"
    fetched_sort_asc: bool = False

    # Manual job dialog
    manual_job_open: bool = False
    manual_job_company: str = ""
    manual_job_role: str = ""
    manual_job_portal: str = ""
    manual_job_link: str = ""
    manual_job_error: str = ""

    # Tables
    jobs: list[JobRow] = []
    fetched_jobs: list[FetchedJobRow] = []

    # Pagination
    jobs_page: int = 0
    fetched_page: int = 0
    page_size: int = 10

    # Computed vars

    @rx.var
    def is_running(self) -> bool:
        return self.running != ""

    @rx.var
    def has_new_jobs(self) -> bool:
        return len(self.new_jobs) > 0

    @rx.var
    def new_job_count(self) -> int:
        return len(self.new_jobs)

    @rx.var
    def has_result(self) -> bool:
        return self.result_kind != ""

    @rx.var
    def progress_pct(self) -> int:
        return int(self.progress * 100)

    @rx.var
    def has_jobs(self) -> bool:
        return len(self.jobs) > 0

    @rx.var
    def job_count_label(self) -> str:
        n = len(self.display_jobs)
        return f"{n} job{'s' if n != 1 else ''}"

    @rx.var
    def has_fetched_jobs(self) -> bool:
        return len(self.fetched_jobs) > 0

    @rx.var
    def fetched_job_count_label(self) -> str:
        n = len(self.display_fetched_jobs)
        return f"{n} job{'s' if n != 1 else ''}"

    @rx.var
    def page_size_str(self) -> str:
        return str(self.page_size)

    @rx.var
    def match_batch_size_str(self) -> str:
        return str(self.match_batch_size)

    @rx.var
    def match_companies_label(self) -> str:
        n = len(self.match_companies)
        total = len(self.distinct_fetched_companies)
        if n == total:
            return "All Companies"
        if n == 0:
            return "None selected"
        if n == 1:
            return self.match_companies[0]
        return f"{n} companies"

    @rx.var
    def fetch_companies_label(self) -> str:
        n = len(self.fetch_companies)
        total = len(self.fetch_available_companies)
        if n == 0:
            return "None selected"
        if n == total:
            return "All Companies"
        if n == 1:
            return self.fetch_companies[0]
        return f"{n} companies"

    @rx.var
    def fetch_queries_label(self) -> str:
        n = len(self.fetch_queries)
        total = len(self.fetch_available_queries)
        if n == 0:
            return "None selected"
        if n == total:
            return "All Queries"
        if n == 1:
            return self.fetch_queries[0]
        return f"{n} queries"

    @rx.var
    def filtered_fetch_companies(self) -> list[str]:
        q = self.fetch_companies_search.lower()
        if not q:
            return self.fetch_available_companies
        return [c for c in self.fetch_available_companies if q in c.lower()]

    @rx.var
    def filtered_fetch_queries(self) -> list[str]:
        q = self.fetch_queries_search.lower()
        if not q:
            return self.fetch_available_queries
        return [c for c in self.fetch_available_queries if q in c.lower()]

    @rx.var
    def filtered_match_companies(self) -> list[str]:
        q = self.match_companies_search.lower()
        if not q:
            return self.distinct_fetched_companies
        return [c for c in self.distinct_fetched_companies if q in c.lower()]

    @rx.var
    def distinct_companies(self) -> list[str]:
        return sorted({j.company for j in self.jobs})

    @rx.var
    def company_filter_label(self) -> str:
        n = len(self.company_filter)
        total = len(self.distinct_companies)
        if n == total:
            return "All Companies"
        if n == 0:
            return "None selected"
        if n == 1:
            return self.company_filter[0]
        return f"{n} companies"

    @rx.var
    def filtered_distinct_companies(self) -> list[str]:
        q = self.company_filter_search.lower()
        if not q:
            return self.distinct_companies
        return [c for c in self.distinct_companies if q in c.lower()]

    @rx.var
    def score_range_label(self) -> str:
        lo, hi = self.score_range[0], self.score_range[1]
        if lo == 0 and hi == 10:
            return "Score: All"
        return f"Score: {lo}–{hi}"

    @rx.var
    def display_jobs(self) -> list[JobRow]:
        lo, hi = self.score_range[0], self.score_range[1]
        jobs = [j for j in self.jobs if j.company in self.company_filter]
        if lo > 0 or hi < 10:
            jobs = [j for j in jobs if lo <= j.score <= hi]
        return jobs

    @rx.var
    def jobs_page_items(self) -> list[JobRow]:
        col, asc = self.jobs_sort_col, self.jobs_sort_asc
        jobs = sorted(self.display_jobs, key=lambda j: getattr(j, col), reverse=not asc)
        start = self.jobs_page * self.page_size
        return jobs[start : start + self.page_size]

    @rx.var
    def jobs_page_count(self) -> int:
        return max(1, (len(self.display_jobs) + self.page_size - 1) // self.page_size)

    @rx.var
    def jobs_range_label(self) -> str:
        total = len(self.display_jobs)
        if total == 0:
            return "0 jobs"
        start = self.jobs_page * self.page_size + 1
        end = min((self.jobs_page + 1) * self.page_size, total)
        return f"{start}–{end} of {total}"

    @rx.var
    def distinct_fetched_companies(self) -> list[str]:
        return sorted({j.company for j in self.fetched_jobs})

    @rx.var
    def fetched_company_filter_label(self) -> str:
        n = len(self.fetched_company_filter)
        total = len(self.distinct_fetched_companies)
        if n == total:
            return "All Companies"
        if n == 0:
            return "None selected"
        if n == 1:
            return self.fetched_company_filter[0]
        return f"{n} companies"

    @rx.var
    def filtered_distinct_fetched_companies(self) -> list[str]:
        q = self.fetched_company_filter_search.lower()
        if not q:
            return self.distinct_fetched_companies
        return [c for c in self.distinct_fetched_companies if q in c.lower()]

    @rx.var
    def display_fetched_jobs(self) -> list[FetchedJobRow]:
        jobs = [j for j in self.fetched_jobs if j.company in self.fetched_company_filter]
        if self.fetched_pipeline_ran_filter == "ran":
            jobs = [j for j in jobs if j.pipeline_ran]
        elif self.fetched_pipeline_ran_filter == "pending":
            jobs = [j for j in jobs if not j.pipeline_ran]
        return jobs

    @rx.var
    def fetched_page_items(self) -> list[FetchedJobRow]:
        col, asc = self.fetched_sort_col, self.fetched_sort_asc
        jobs = sorted(
            self.display_fetched_jobs, key=lambda j: getattr(j, col), reverse=not asc
        )
        start = self.fetched_page * self.page_size
        return jobs[start : start + self.page_size]

    @rx.var
    def fetched_page_count(self) -> int:
        return max(
            1, (len(self.display_fetched_jobs) + self.page_size - 1) // self.page_size
        )

    @rx.var
    def fetched_range_label(self) -> str:
        total = len(self.display_fetched_jobs)
        if total == 0:
            return "0 jobs"
        start = self.fetched_page * self.page_size + 1
        end = min((self.fetched_page + 1) * self.page_size, total)
        return f"{start}–{end} of {total}"

    # Lifecycle

    async def on_load(self):
        bootstrap_logging()
        await init_db()
        self.selected_model = settings.LLM_MODEL
        self.available_models = settings.all_available_models
        self.match_date = str(datetime.now(settings.tz).date())
        enabled_companies = await get_enabled_companies()
        enabled_queries = await get_enabled_queries()
        self.fetch_available_companies = [c["name"] for c in enabled_companies]
        self.fetch_available_queries = [q["name"] for q in enabled_queries]
        self.fetch_companies = list(self.fetch_available_companies)
        self.fetch_queries = list(self.fetch_available_queries)
        await self.load_jobs()
        await self.load_fetched_jobs()
        self.match_companies = list(self.distinct_fetched_companies)

    # Matched jobs data

    async def load_jobs(self):
        status = self.status_filter if self.status_filter != "all" else None
        from_d = date.fromisoformat(self.from_date) if self.from_date else None
        to_d = date.fromisoformat(self.to_date) if self.to_date else None

        db_jobs = await get_matched_jobs(status, from_d, to_d)
        self.jobs = [_to_row(j) for j in db_jobs]
        self.company_filter = sorted({j.company for j in self.jobs})
        self.jobs_page = 0

    async def set_status_filter(self, value: str):
        self.status_filter = value
        await self.load_jobs()

    def toggle_company_filter(self, company: str, checked: bool):
        if checked and company not in self.company_filter:
            self.company_filter = [*self.company_filter, company]
        elif not checked:
            self.company_filter = [c for c in self.company_filter if c != company]
        self.jobs_page = 0

    def clear_company_filter(self):
        self.company_filter = []
        self.jobs_page = 0

    def set_company_filter_search(self, value: str):
        self.company_filter_search = value

    async def set_from_date(self, value: str):
        self.from_date = value
        await self.load_jobs()

    async def set_to_date(self, value: str):
        self.to_date = value
        await self.load_jobs()

    def set_score_range(self, value: list[float]):
        self.score_range = [int(v) for v in value]
        self.jobs_page = 0

    def set_selected_model(self, value: str):
        self.selected_model = value

    def set_match_date(self, value: str):
        self.match_date = value

    def set_match_batch_size(self, value: str):
        self.match_batch_size = int(value)

    def toggle_match_company(self, company: str, checked: bool):
        if checked and company not in self.match_companies:
            self.match_companies = [*self.match_companies, company]
        elif not checked:
            self.match_companies = [c for c in self.match_companies if c != company]

    def set_match_companies(self, value: list[str]):
        self.match_companies = value

    def set_match_companies_search(self, value: str):
        self.match_companies_search = value

    def set_match_created_by(self, value: str):
        self.match_created_by = value

    def toggle_fetch_company(self, company: str, checked: bool):
        if checked and company not in self.fetch_companies:
            self.fetch_companies = [*self.fetch_companies, company]
        elif not checked:
            self.fetch_companies = [c for c in self.fetch_companies if c != company]

    def toggle_fetch_query(self, query: str, checked: bool):
        if checked and query not in self.fetch_queries:
            self.fetch_queries = [*self.fetch_queries, query]
        elif not checked:
            self.fetch_queries = [q for q in self.fetch_queries if q != query]

    def set_fetch_companies_search(self, value: str):
        self.fetch_companies_search = value

    def set_fetch_queries_search(self, value: str):
        self.fetch_queries_search = value

    def clear_fetch_companies(self):
        self.fetch_companies = []

    def select_all_fetch_companies(self):
        self.fetch_companies = list(self.fetch_available_companies)

    def clear_fetch_queries(self):
        self.fetch_queries = []

    def select_all_fetch_queries(self):
        self.fetch_queries = list(self.fetch_available_queries)

    def clear_match_companies(self):
        self.match_companies = []

    def select_all_match_companies(self):
        self.match_companies = list(self.distinct_fetched_companies)

    def select_all_company_filter(self):
        self.company_filter = list(self.distinct_companies)
        self.jobs_page = 0

    def select_all_fetched_company_filter(self):
        self.fetched_company_filter = list(self.distinct_fetched_companies)
        self.fetched_page = 0

    async def update_job_status(self, job_id: int, status: str):
        await bulk_update_matched_job_status({job_id: JobStatus(status)})
        now_str = datetime.now(settings.tz).strftime("%b %d, %Y")
        for i, j in enumerate(self.jobs):
            if j.id == job_id:
                self.jobs[i] = JobRow(
                    id=j.id,
                    company=j.company,
                    role=j.role,
                    role_link=j.role_link,
                    score=j.score,
                    score_label=j.score_label,
                    score_color=j.score_color,
                    status=status,
                    status_label=STATUS_LABELS.get(status, status),
                    status_color=STATUS_COLORS.get(status, "gray"),
                    reason=j.reason,
                    status_changed_at="" if status == "pending" else now_str,
                )
                break

    # Fetched jobs data

    async def load_fetched_jobs(self):
        from_d = (
            date.fromisoformat(self.fetched_from_date)
            if self.fetched_from_date
            else None
        )
        to_d = (
            date.fromisoformat(self.fetched_to_date) if self.fetched_to_date else None
        )

        jobs = await get_fetched_jobs(from_d, to_d)
        self.fetched_jobs = [_to_fetched_row(j) for j in jobs]
        self.fetched_company_filter = sorted({j.company for j in self.fetched_jobs})
        self.fetched_page = 0

    def toggle_fetched_company_filter(self, company: str, checked: bool):
        if checked and company not in self.fetched_company_filter:
            self.fetched_company_filter = [*self.fetched_company_filter, company]
        elif not checked:
            self.fetched_company_filter = [
                c for c in self.fetched_company_filter if c != company
            ]
        self.fetched_page = 0

    def clear_fetched_company_filter(self):
        self.fetched_company_filter = []
        self.fetched_page = 0

    def set_fetched_pipeline_ran_filter(self, value: str):
        self.fetched_pipeline_ran_filter = value
        self.fetched_page = 0

    def set_fetched_company_filter_search(self, value: str):
        self.fetched_company_filter_search = value

    async def set_fetched_from_date(self, value: str):
        self.fetched_from_date = value
        await self.load_fetched_jobs()

    async def set_fetched_to_date(self, value: str):
        self.fetched_to_date = value
        await self.load_fetched_jobs()

    def jobs_prev_page(self):
        self.jobs_page = max(0, self.jobs_page - 1)

    def jobs_next_page(self):
        self.jobs_page = min(self.jobs_page_count - 1, self.jobs_page + 1)

    def fetched_prev_page(self):
        self.fetched_page = max(0, self.fetched_page - 1)

    def fetched_next_page(self):
        self.fetched_page = min(self.fetched_page_count - 1, self.fetched_page + 1)

    def set_page_size(self, value: str):
        self.page_size = int(value)
        self.jobs_page = 0
        self.fetched_page = 0

    def sort_jobs(self, col: str):
        if self.jobs_sort_col == col:
            self.jobs_sort_asc = not self.jobs_sort_asc
        else:
            self.jobs_sort_col = col
            self.jobs_sort_asc = col == "company" or col == "status"
        self.jobs_page = 0

    def sort_fetched(self, col: str):
        if self.fetched_sort_col == col:
            self.fetched_sort_asc = not self.fetched_sort_asc
        else:
            self.fetched_sort_col = col
            self.fetched_sort_asc = col == "company"
        self.fetched_page = 0

    def set_manual_job_open(self, value: bool):
        self.manual_job_open = value

    def set_manual_job_company(self, value: str):
        self.manual_job_company = value

    def set_manual_job_role(self, value: str):
        self.manual_job_role = value

    def set_manual_job_portal(self, value: str):
        self.manual_job_portal = value

    def set_manual_job_link(self, value: str):
        self.manual_job_link = value

    def open_manual_job_dialog(self):
        self.manual_job_company = ""
        self.manual_job_role = ""
        self.manual_job_portal = ""
        self.manual_job_link = ""
        self.manual_job_error = ""
        self.manual_job_open = True

    async def submit_manual_job(self):
        company = self.manual_job_company.strip()
        role = self.manual_job_role.strip()
        link = self.manual_job_link.strip()
        portal = self.manual_job_portal.strip() or _detect_portal(self.manual_job_link)

        if not company:
            self.manual_job_error = "Company is required."
            return
        if not role:
            self.manual_job_error = "Role is required."
            return
        if not link:
            self.manual_job_error = "Link is required."
            return

        ok, err = await insert_job_manual(company, role, link, portal)
        if not ok:
            self.manual_job_error = err
            return

        jobs = await get_fetched_jobs()
        self.fetched_jobs = [_to_fetched_row(j) for j in jobs]
        self.fetched_company_filter = sorted({j.company for j in self.fetched_jobs})
        self.fetched_page = 0
        self.manual_job_open = False

    def dismiss_result(self):
        self.result_message = ""
        self.result_kind = ""

    def stop_pipeline(self):
        pipeline_state.request_stop()
        self.stop_requested = True

    # Background pipelines

    @rx.event(background=True)
    async def run_fetch(self):
        logger = logging.getLogger("job-finder")
        async with self:
            fetch_companies = list(self.fetch_companies)
            fetch_queries = list(self.fetch_queries)
            selected_model = self.selected_model or None
        steps = [
            s
            async for s in iter_fetch_steps(
                companies=fetch_companies, queries=fetch_queries
            )
        ]
        fetch_start = datetime.now(settings.tz)

        pipeline_state.start("fetch")
        async with self:
            self.running = "fetch"
            self.progress = 0.0
            self.status_text = "Starting fetch…"
            self.result_message = ""
            self.result_kind = ""
            self.new_jobs = []

        try:
            completed = 0
            for i, (name, kind, data) in enumerate(steps):
                if pipeline_state.is_stop_requested():
                    break

                async with self:
                    self.progress = (i + 1) / (len(steps) + 1)
                    self.status_text = f"Fetching ({i + 1}/{len(steps)}): {name}…"

                if kind == "query":
                    await fetch_from_query(name, data["query"], model=selected_model)
                else:
                    await fetch_from_company(
                        name,
                        data["careers_url"],
                        data.get("scan_query"),
                        model=selected_model,
                    )

                completed += 1
                new = await get_new_jobs_since(fetch_start)
                async with self:
                    self.new_jobs = [
                        NewJob(
                            company=j.company_name,
                            role=j.role,
                            link=j.link,
                            portal=j.portal,
                        )
                        for j in new
                    ]
                    self.status_text = (
                        f"Fetching ({i + 1}/{len(steps)}): {name}…"
                        f" ({len(new)} new job(s) so far)"
                    )

            was_stopped = pipeline_state.is_stop_requested()
            async with self:
                self.running = ""
                self.stop_requested = False
                self.progress = 1.0
                if was_stopped:
                    self.result_kind = "warning"
                    self.result_message = (
                        f"Stopped after {completed}/{len(steps)} source(s)."
                    )
                else:
                    self.result_kind = "success"
                    self.result_message = f"Fetched from {len(steps)} source(s)."

            fetched = await get_fetched_jobs()
            async with self:
                self.fetched_jobs = [_to_fetched_row(j) for j in fetched]
                self.fetched_company_filter = sorted({j.company for j in self.fetched_jobs})

        except Exception as exc:
            logger.exception("Fetch pipeline failed")
            async with self:
                self.running = ""
                self.stop_requested = False
                self.result_kind = "error"
                self.result_message = str(exc)

    @rx.event(background=True)
    async def run_match(self):
        logger = logging.getLogger("job-finder")

        try:
            async with self:
                match_date_str = self.match_date
                match_batch_size = self.match_batch_size
                match_companies = list(self.match_companies)
                all_fetched_companies = sorted({j.company for j in self.fetched_jobs})
                match_created_by = self.match_created_by
                status_filter = self.status_filter
                from_date_str = self.from_date
                to_date_str = self.to_date
                fetched_from_date_str = self.fetched_from_date
                fetched_to_date_str = self.fetched_to_date
                selected_model = self.selected_model or None
                self.running = "match"
                self.progress = 0.05
                self.status_text = "Loading jobs for matching…"
                self.result_message = ""
                self.result_kind = ""

            pipeline_state.start("match")

            _match_date = (
                date.fromisoformat(match_date_str)
                if match_date_str
                else datetime.now(settings.tz).date()
            )

            async def _on_batch(batch_num: int, total_batches: int) -> None:
                async with self:
                    self.progress = 0.1 + (batch_num / total_batches) * 0.85
                    self.status_text = f"Matching batch {batch_num}/{total_batches}…"

            companies_param = (
                match_companies
                if len(match_companies) < len(all_fetched_companies)
                else None
            )
            count, was_stopped = await run_match_pipeline(
                progress_callback=_on_batch,
                for_date=_match_date,
                batch_size=match_batch_size,
                companies=companies_param,
                created_by=match_created_by if match_created_by != "all" else None,
                model=selected_model,
                should_stop=pipeline_state.is_stop_requested,
            )

            if was_stopped:
                async with self:
                    self.running = ""
                    self.stop_requested = False
                    self.result_kind = "warning"
                    self.result_message = f"Stopped after evaluating {count} job(s)."
            elif count == 0:
                async with self:
                    self.running = ""
                    self.stop_requested = False
                    self.result_kind = "warning"
                    self.result_message = (
                        f"No jobs found for {_match_date}. Run 'Fetch New Jobs' first."
                    )
            else:
                async with self:
                    self.running = ""
                    self.stop_requested = False
                    self.progress = 1.0
                    self.result_kind = "success"
                    self.result_message = f"Match complete — evaluated {count} job(s)."

            status = status_filter if status_filter != "all" else None
            from_d = date.fromisoformat(from_date_str) if from_date_str else None
            to_d = date.fromisoformat(to_date_str) if to_date_str else None
            fetched_from_d = (
                date.fromisoformat(fetched_from_date_str)
                if fetched_from_date_str
                else None
            )
            fetched_to_d = (
                date.fromisoformat(fetched_to_date_str) if fetched_to_date_str else None
            )
            db_jobs = await get_matched_jobs(status, from_d, to_d)
            fetched = await get_fetched_jobs(fetched_from_d, fetched_to_d)
            async with self:
                self.jobs = [_to_row(j) for j in db_jobs]
                self.company_filter = sorted({j.company for j in self.jobs})
                self.fetched_jobs = [_to_fetched_row(j) for j in fetched]
                self.fetched_company_filter = sorted({j.company for j in self.fetched_jobs})
                self.fetched_page = 0

        except Exception as exc:
            logger.exception("Match pipeline failed")
            async with self:
                self.running = ""
                self.stop_requested = False
                self.result_kind = "error"
                self.result_message = str(exc)


# ── Token usage page ──────────────────────────────────────────────────────────


class UsageRow(BaseModel):
    id: int
    request_id: str
    model: str
    pipeline: str
    input_tokens: str
    output_tokens: str
    reasoning_tokens: str
    total_tokens: str
    created_at: str


class UsageState(rx.State):
    usage_rows: list[UsageRow] = []
    usage_page: int = 0
    usage_page_size: int = 20
    usage_total_count: int = 0
    usage_total_input: int = 0
    usage_total_output: int = 0
    usage_total_tokens: int = 0
    usage_total_reasoning: int = 0
    usage_pipeline_filter: str = "all"
    usage_model_filter: str = "all"
    usage_available_models: list[str] = []
    usage_from_date: str = ""
    usage_to_date: str = ""

    @rx.var
    def usage_total_input_fmt(self) -> str:
        return f"{self.usage_total_input:,}"

    @rx.var
    def usage_total_output_fmt(self) -> str:
        return f"{self.usage_total_output:,}"

    @rx.var
    def usage_total_tokens_fmt(self) -> str:
        return f"{self.usage_total_tokens:,}"

    @rx.var
    def usage_total_reasoning_fmt(self) -> str:
        return f"{self.usage_total_reasoning:,}"

    @rx.var
    def usage_page_count(self) -> int:
        return max(1, -(-self.usage_total_count // self.usage_page_size))

    @rx.var
    def usage_range_label(self) -> str:
        if not self.usage_total_count:
            return "0 records"
        start = self.usage_page * self.usage_page_size + 1
        end = min((self.usage_page + 1) * self.usage_page_size, self.usage_total_count)
        return f"{start}–{end} of {self.usage_total_count}"

    async def _load(self) -> None:
        pipeline = (
            self.usage_pipeline_filter if self.usage_pipeline_filter != "all" else None
        )
        model = self.usage_model_filter if self.usage_model_filter != "all" else None
        from_d = (
            date.fromisoformat(self.usage_from_date) if self.usage_from_date else None
        )
        to_d = date.fromisoformat(self.usage_to_date) if self.usage_to_date else None
        rows, total, agg = await get_token_usage_page(
            pipeline=pipeline,
            model=model,
            from_date=from_d,
            to_date=to_d,
            offset=self.usage_page * self.usage_page_size,
            limit=self.usage_page_size,
        )
        self.usage_rows = [
            UsageRow(
                id=r.id,
                request_id=(r.request_id or "")[:8],
                model=r.model,
                pipeline=r.pipeline or "—",
                input_tokens=f"{r.input_tokens:,}",
                output_tokens=f"{r.output_tokens:,}",
                reasoning_tokens=f"{r.reasoning_tokens:,}",
                total_tokens=f"{r.total_tokens:,}",
                created_at=r.created_at.astimezone(settings.tz).strftime(
                    "%b %d, %H:%M"
                ),
            )
            for r in rows
        ]
        self.usage_total_count = total
        self.usage_total_input = agg["input_tokens"]
        self.usage_total_output = agg["output_tokens"]
        self.usage_total_tokens = agg["total_tokens"]
        self.usage_total_reasoning = agg["reasoning_tokens"]

    async def on_load(self) -> None:
        self.usage_page = 0
        self.usage_available_models = await get_distinct_token_usage_models()
        await self._load()

    async def set_usage_pipeline_filter(self, value: str) -> None:
        self.usage_pipeline_filter = value
        self.usage_page = 0
        await self._load()

    async def set_usage_model_filter(self, value: str) -> None:
        self.usage_model_filter = value
        self.usage_page = 0
        await self._load()

    async def set_usage_from_date(self, value: str) -> None:
        self.usage_from_date = value
        self.usage_page = 0
        await self._load()

    async def set_usage_to_date(self, value: str) -> None:
        self.usage_to_date = value
        self.usage_page = 0
        await self._load()

    async def usage_prev_page(self) -> None:
        if self.usage_page > 0:
            self.usage_page -= 1
            await self._load()

    async def usage_next_page(self) -> None:
        if self.usage_page < self.usage_page_count - 1:
            self.usage_page += 1
            await self._load()
