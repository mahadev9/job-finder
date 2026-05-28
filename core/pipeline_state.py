import logging
import threading
from typing import Literal

logger = logging.getLogger("job-finder")

PipelineKind = Literal["fetch", "match"]


class _PipelineState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self.running: PipelineKind | None = None
        self.progress: float = 0.0
        self.status_text: str = ""
        self.result_message: str = ""
        self.result_kind: Literal["success", "warning", "error"] | None = None
        self.new_jobs: list = []

    def start(self, kind: PipelineKind) -> None:
        with self._lock:
            self.running = kind
            self.progress = 0.0
            self.status_text = f"Starting {kind}…"
            self.result_message = ""
            self.result_kind = None
            self.new_jobs = []
        self._stop_event.clear()
        logger.info(f"Pipeline started: {kind}")

    def request_stop(self) -> None:
        self._stop_event.set()
        logger.info("Pipeline stop requested")

    def is_stop_requested(self) -> bool:
        return self._stop_event.is_set()

    def update(self, progress: float, text: str) -> None:
        with self._lock:
            self.progress = progress
            self.status_text = text

    def add_jobs(self, jobs: list) -> None:
        with self._lock:
            self.new_jobs = list(jobs)

    def finish(
        self, message: str, kind: Literal["success", "warning"] = "success"
    ) -> None:
        with self._lock:
            logger.info(f"Pipeline [{self.running}] finished: {message}")
            self.running = None
            self.progress = 1.0
            self.result_message = message
            self.result_kind = kind

    def fail(self, error: str) -> None:
        with self._lock:
            logger.error(f"Pipeline [{self.running}] failed: {error}")
            self.running = None
            self.result_message = error
            self.result_kind = "error"

    @property
    def snapshot(self) -> dict:
        with self._lock:
            return {
                "running": self.running,
                "progress": self.progress,
                "status_text": self.status_text,
                "result_message": self.result_message,
                "result_kind": self.result_kind,
                "new_jobs": list(self.new_jobs),
            }


pipeline_state = _PipelineState()
