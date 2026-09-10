import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.models.enums import ChallengeStatus, StreakType


class Badge(UUIDPKMixin, Base):
    """Catalog of badge definitions (seeded, not user-created)."""

    __tablename__ = "badges"

    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(240))
    icon: Mapped[str] = mapped_column(String(10))  # emoji, keeps the frontend dependency-free


class UserBadge(UUIDPKMixin, Base):
    __tablename__ = "user_badges"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    league_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leagues.id"))
    badge_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("badges.id"))
    gameweek_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("gameweeks.id"), nullable=True)
    earned_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "league_id", "badge_id", "gameweek_id", name="uq_user_badge"),
    )


class UserStreak(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "user_streaks"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    league_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leagues.id"))
    streak_type: Mapped[StreakType]
    current_count: Mapped[int] = mapped_column(Integer, default=0)
    best_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "league_id", "streak_type", name="uq_user_streak"),
    )


class UserXP(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "user_xp"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)


class Challenge(UUIDPKMixin, Base):
    __tablename__ = "challenges"

    gameweek_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gameweeks.id"))
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(240))
    xp_reward: Mapped[int] = mapped_column(Integer, default=50)


class UserChallenge(UUIDPKMixin, Base):
    __tablename__ = "user_challenges"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    challenge_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("challenges.id"))
    status: Mapped[ChallengeStatus] = mapped_column(default=ChallengeStatus.PENDING)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", name="uq_user_challenge"),
    )
