import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPKMixin, utcnow
from app.models.enums import ActivityType


class LeagueActivity(UUIDPKMixin, Base):
    """Feed rows for "La Liga" (the social tab) — a lightweight event log,
    not derived live from other tables, so the feed stays fast and stable
    even as bets/streaks change state later. Written by the same services
    that cause the event (bets.py, gamification.py, settlement.py)."""

    __tablename__ = "league_activity"

    league_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leagues.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    type: Mapped[ActivityType]
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
