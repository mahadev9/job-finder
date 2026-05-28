from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.config import settings
from database.models.base import Base


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    pipeline: Mapped[str | None] = mapped_column(String, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reasoning_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(settings.tz),
    )

    __table_args__ = (
        Index("ix_token_usage_created_at", "created_at"),
        Index("ix_token_usage_pipeline", "pipeline"),
    )
