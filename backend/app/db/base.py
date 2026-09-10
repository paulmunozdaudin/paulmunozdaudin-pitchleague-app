import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Naive UTC on purpose: SQLite's DATETIME type doesn't reliably round-trip
    offsets (it happily accepts `DateTime(timezone=True)` but silently hands
    back naive datetimes on read), which breaks `aware >= naive` comparisons
    the moment a row is reloaded. Every datetime column in this app is UTC by
    convention instead — naive everywhere, consistently, across SQLite,
    Postgres and the mock/real odds providers."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
