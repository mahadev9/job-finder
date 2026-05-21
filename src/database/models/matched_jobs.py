import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("company", "role", name="uq_matched_jobs_company_role"),
    )
