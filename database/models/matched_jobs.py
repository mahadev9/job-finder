import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    LOW_MATCH = "low_match"


class MatchedJob(Base):
    __tablename__ = "matched_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company: Mapped[str] = mapped_column(String, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(
            JobStatus, name="job_status", values_callable=lambda e: [m.value for m in e]
        ),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )
    role_link: Mapped[str] = mapped_column(String, nullable=False, default="")
    reason: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("company", "role", name="uq_matched_jobs_company_role"),
        Index("ix_matched_jobs_created_at", "created_at"),
        Index("ix_matched_jobs_status_created_at", "status", "created_at"),
        Index("ix_matched_jobs_score_desc", "score"),
    )
