import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin, utcnow
from app.models.enums import MembershipRole


class League(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "leagues"

    name: Mapped[str] = mapped_column(String(80))
    invite_code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    admin_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    budget_per_gameweek: Mapped[int] = mapped_column(Integer, default=10_000)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    seasons: Mapped[list["Season"]] = relationship(back_populates="league", cascade="all, delete-orphan")
    memberships: Mapped[list["LeagueMembership"]] = relationship(
        back_populates="league", cascade="all, delete-orphan"
    )


class LeagueMembership(UUIDPKMixin, Base):
    __tablename__ = "league_memberships"

    league_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leagues.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    role: Mapped[MembershipRole] = mapped_column(default=MembershipRole.MEMBER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(default=utcnow)

    league: Mapped["League"] = relationship(back_populates="memberships")


class Season(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "seasons"

    league_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leagues.id"))
    name: Mapped[str] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    champion_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    league: Mapped["League"] = relationship(back_populates="seasons")
    gameweeks: Mapped[list["Gameweek"]] = relationship(
        back_populates="season", cascade="all, delete-orphan", order_by="Gameweek.number"
    )
