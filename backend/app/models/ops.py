from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPKMixin


class FailedJob(UUIDPKMixin, Base):
    """A worker tick (odds refresh, settlement) that raised — written by
    `app/workers/scheduler.py` so admins can see real operational failures
    instead of them only existing in a log file nobody is tailing."""

    __tablename__ = "failed_jobs"

    job_name: Mapped[str] = mapped_column(String(80), index=True)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime]
