from datetime import date, datetime, timezone

import reflex as rx
from pydantic import BaseModel


STATUS_COLORS: dict[str, str] = {
    "pending": "amber",
    "applied": "blue",
    "rejected": "red",
    "low_match": "gray",
}

STATUS_LABELS: dict[str, str] = {
    "pending": "Pending",
    "applied": "Applied",
    "rejected": "Rejected",
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


class FetchedJobRow(BaseModel):
    id: int
    company: str
    role: str
    link: str
    portal: str
    fetched_date: str


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
    )


def _to_fetched_row(j) -> FetchedJobRow:
    return FetchedJobRow(
        id=j.id,
        company=j.company_name,
        role=j.role,
        link=j.link,
        portal=j.portal,
        fetched_date=j.created_at.strftime("%b %d, %Y") if j.created_at else "",
    )


class AppState(rx.State):
    # Pipeline
    running: str = ""
    progress: float = 0.0
    status_text: str = ""
    result_message: str = ""
    result_kind: str = ""
    new_jobs: list[NewJob] = []

    # Matched jobs filters
    status_filter: str = "all"
    from_date: str = ""
    to_date: str = ""
    match_date: str = ""

    # Fetched jobs filters
    fetched_from_date: str = ""
    fetched_to_date: str = ""

    # Tables
    jobs: list[JobRow] = []
    fetched_jobs: list[FetchedJobRow] = []

    # Pagination
    jobs_page: int = 0
    fetched_page: int = 0
    page_size: int = 20

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
        n = len(self.jobs)
        return f"{n} job{'s' if n != 1 else ''}"

    @rx.var
    def has_fetched_jobs(self) -> bool:
        return len(self.fetched_jobs) > 0

    @rx.var
    def fetched_job_count_label(self) -> str:
        n = len(self.fetched_jobs)
        return f"{n} job{'s' if n != 1 else ''}"

    @rx.var
    def page_size_str(self) -> str:
        return str(self.page_size)

    @rx.var
    def jobs_page_items(self) -> list[JobRow]:
        start = self.jobs_page * self.page_size
        return self.jobs[start : start + self.page_size]

    @rx.var
    def jobs_page_count(self) -> int:
        return max(1, (len(self.jobs) + self.page_size - 1) // self.page_size)

    @rx.var
    def jobs_range_label(self) -> str:
        total = len(self.jobs)
        if total == 0:
            return "0 jobs"
        start = self.jobs_page * self.page_size + 1
        end = min((self.jobs_page + 1) * self.page_size, total)
        return f"{start}–{end} of {total}"

    @rx.var
    def fetched_page_items(self) -> list[FetchedJobRow]:
        start = self.fetched_page * self.page_size
        return self.fetched_jobs[start : start + self.page_size]

    @rx.var
    def fetched_page_count(self) -> int:
        return max(1, (len(self.fetched_jobs) + self.page_size - 1) // self.page_size)

    @rx.var
    def fetched_range_label(self) -> str:
        total = len(self.fetched_jobs)
        if total == 0:
            return "0 jobs"
        start = self.fetched_page * self.page_size + 1
        end = min((self.fetched_page + 1) * self.page_size, total)
        return f"{start}–{end} of {total}"

    # Lifecycle

    async def on_load(self):
        from core.logger import bootstrap_logging
        from database.core import init_db

        bootstrap_logging()
        await init_db()
        self.match_date = str(date.today())
        await self.load_jobs()
        await self.load_fetched_jobs()

    # Matched jobs data

    async def load_jobs(self):
        from datetime import date as _date

        from services.queries import get_matched_jobs

        status = self.status_filter if self.status_filter != "all" else None
        from_d = _date.fromisoformat(self.from_date) if self.from_date else None
        to_d = _date.fromisoformat(self.to_date) if self.to_date else None

        db_jobs = await get_matched_jobs(status, from_d, to_d)
        self.jobs = [_to_row(j) for j in db_jobs]
        self.jobs_page = 0

    async def set_status_filter(self, value: str):
        self.status_filter = value
        await self.load_jobs()

    async def set_from_date(self, value: str):
        self.from_date = value
        await self.load_jobs()

    async def set_to_date(self, value: str):
        self.to_date = value
        await self.load_jobs()

    def set_match_date(self, value: str):
        self.match_date = value

    async def update_job_status(self, job_id: int, status: str):
        from database.models.matched_jobs import JobStatus
        from services.queries import bulk_update_matched_job_status

        await bulk_update_matched_job_status({job_id: JobStatus(status)})
        self.jobs = [
            JobRow(
                id=j.id,
                company=j.company,
                role=j.role,
                role_link=j.role_link,
                score=j.score,
                score_label=j.score_label,
                score_color=j.score_color,
                status=status if j.id == job_id else j.status,
                status_label=STATUS_LABELS.get(status, status)
                if j.id == job_id
                else j.status_label,
                status_color=STATUS_COLORS.get(status, "gray")
                if j.id == job_id
                else j.status_color,
                reason=j.reason,
            )
            for j in self.jobs
        ]

    # Fetched jobs data

    async def load_fetched_jobs(self):
        from datetime import date as _date

        from services.queries import get_fetched_jobs

        from_d = (
            _date.fromisoformat(self.fetched_from_date)
            if self.fetched_from_date
            else None
        )
        to_d = (
            _date.fromisoformat(self.fetched_to_date) if self.fetched_to_date else None
        )

        jobs = await get_fetched_jobs(from_d, to_d)
        self.fetched_jobs = [_to_fetched_row(j) for j in jobs]
        self.fetched_page = 0

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

    def dismiss_result(self):
        self.result_message = ""
        self.result_kind = ""

    # Background pipelines

    @rx.event(background=True)
    async def run_fetch(self):
        import logging

        from services.fetch_jobs import (
            fetch_from_company,
            fetch_from_query,
            iter_fetch_steps,
        )
        from services.queries import get_fetched_jobs, get_new_jobs_since

        logger = logging.getLogger("job-finder")
        steps = [s async for s in iter_fetch_steps()]
        fetch_start = datetime.now(timezone.utc)

        async with self:
            self.running = "fetch"
            self.progress = 0.0
            self.status_text = "Starting fetch…"
            self.result_message = ""
            self.result_kind = ""
            self.new_jobs = []

        try:
            for i, (name, kind, data) in enumerate(steps):
                async with self:
                    self.progress = (i + 1) / (len(steps) + 1)
                    self.status_text = f"Fetching ({i + 1}/{len(steps)}): {name}…"

                if kind == "query":
                    await fetch_from_query(name, data["query"])
                else:
                    await fetch_from_company(
                        name, data["careers_url"], data.get("scan_query")
                    )

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

            async with self:
                self.running = ""
                self.progress = 1.0
                self.result_kind = "success"
                self.result_message = f"Fetched from {len(steps)} source(s)."

            fetched = await get_fetched_jobs()
            async with self:
                self.fetched_jobs = [_to_fetched_row(j) for j in fetched]

        except Exception as exc:
            logger.exception("Fetch pipeline failed")
            async with self:
                self.running = ""
                self.result_kind = "error"
                self.result_message = str(exc)

    @rx.event(background=True)
    async def run_match(self):
        import logging
        from datetime import date as _date

        from services.match_jobs import run_match_pipeline
        from services.queries import get_matched_jobs

        logger = logging.getLogger("job-finder")

        try:
            async with self:
                match_date_str = self.match_date
                status_filter = self.status_filter
                from_date_str = self.from_date
                to_date_str = self.to_date
                self.running = "match"
                self.progress = 0.05
                self.status_text = "Loading jobs for matching…"
                self.result_message = ""
                self.result_kind = ""

            _match_date = (
                _date.fromisoformat(match_date_str) if match_date_str else _date.today()
            )

            async def _on_batch(batch_num: int, total_batches: int) -> None:
                async with self:
                    self.progress = 0.1 + (batch_num / total_batches) * 0.85
                    self.status_text = f"Matching batch {batch_num}/{total_batches}…"

            count = await run_match_pipeline(
                progress_callback=_on_batch, for_date=_match_date
            )

            if count == 0:
                async with self:
                    self.running = ""
                    self.result_kind = "warning"
                    self.result_message = (
                        f"No jobs found for {_match_date}. Run 'Fetch New Jobs' first."
                    )
            else:
                async with self:
                    self.running = ""
                    self.progress = 1.0
                    self.result_kind = "success"
                    self.result_message = f"Match complete — evaluated {count} job(s)."

            status = status_filter if status_filter != "all" else None
            from_d = _date.fromisoformat(from_date_str) if from_date_str else None
            to_d = _date.fromisoformat(to_date_str) if to_date_str else None
            db_jobs = await get_matched_jobs(status, from_d, to_d)
            async with self:
                self.jobs = [_to_row(j) for j in db_jobs]

        except Exception as exc:
            logger.exception("Match pipeline failed")
            async with self:
                self.running = ""
                self.result_kind = "error"
                self.result_message = str(exc)
