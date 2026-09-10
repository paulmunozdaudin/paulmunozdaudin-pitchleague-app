import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import GameweekStatus, Market, MatchOutcome, MatchStatus, Selection


class Gameweek(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "gameweeks"

    season_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seasons.id"))
    number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(60))
    opens_at: Mapped[datetime]
    locks_at: Mapped[datetime]
    budget: Mapped[int] = mapped_column(Integer)
    status: Mapped[GameweekStatus] = mapped_column(default=GameweekStatus.UPCOMING)

    season: Mapped["Season"] = relationship(back_populates="gameweeks")
    matches: Mapped[list["Match"]] = relationship(
        back_populates="gameweek", cascade="all, delete-orphan", order_by="Match.kickoff_at"
    )


class Match(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "matches"

    gameweek_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gameweeks.id"))
    external_id: Mapped[str] = mapped_column(String(120), index=True)
    competition: Mapped[str] = mapped_column(String(120))
    home_team: Mapped[str] = mapped_column(String(120))
    away_team: Mapped[str] = mapped_column(String(120))
    kickoff_at: Mapped[datetime]
    status: Mapped[MatchStatus] = mapped_column(default=MatchStatus.SCHEDULED)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[MatchOutcome | None] = mapped_column(nullable=True)

    gameweek: Mapped["Gameweek"] = relationship(back_populates="matches")
    odds_snapshots: Mapped[list["OddsSnapshot"]] = relationship(
        back_populates="match", cascade="all, delete-orphan", order_by="OddsSnapshot.fetched_at"
    )

    def current_odds(self) -> list["OddsSnapshot"]:
        """Latest snapshot per (market, selection, line) — what the UI shows."""
        latest: dict[tuple, "OddsSnapshot"] = {}
        for snap in self.odds_snapshots:
            key = (snap.market, snap.selection, snap.line)
            if key not in latest or snap.fetched_at > latest[key].fetched_at:
                latest[key] = snap
        return list(latest.values())


class OddsSnapshot(UUIDPKMixin, Base):
    """A timestamped price quote. We never overwrite odds — each fetch is
    appended so the exact price a prediction was placed against is always
    reconstructable, and price-movement history is preserved for free."""

    __tablename__ = "odds_snapshots"

    match_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matches.id"))
    market: Mapped[Market]
    selection: Mapped[Selection]
    # Over/under line, e.g. 2.5 goals. Null for markets without a line.
    line: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    fetched_at: Mapped[datetime] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(String(40))

    match: Mapped["Match"] = relationship(back_populates="odds_snapshots")
