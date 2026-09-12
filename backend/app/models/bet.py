import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import BetStatus, Market, Selection


class Bet(UUIDPKMixin, TimestampMixin, Base):
    """A single confirmed slip — one stake, one-or-more legs. A plain
    single-selection pick is simply a Bet with exactly one leg; a
    combination ("combinada") is the same row with several. Users can hold
    several Bets in the same gameweek (each its own stake against the
    shared weekly wallet), matching how a real bet slip works — unlike the
    old one-pick-per-match model this replaces."""

    __tablename__ = "bets"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    league_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leagues.id"))
    gameweek_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gameweeks.id"))

    stake: Mapped[int] = mapped_column(Integer)
    combined_odds: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    potential_payout: Mapped[int] = mapped_column(Integer)

    status: Mapped[BetStatus] = mapped_column(default=BetStatus.PENDING)
    payout: Mapped[int | None] = mapped_column(Integer, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(nullable=True)

    legs: Mapped[list["BetLeg"]] = relationship(
        back_populates="bet", cascade="all, delete-orphan", order_by="BetLeg.created_at"
    )


class BetLeg(UUIDPKMixin, TimestampMixin, Base):
    """One selection within a Bet. `line` carries the over/under threshold
    when the market needs one (null otherwise)."""

    __tablename__ = "bet_legs"

    bet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bets.id"))
    match_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matches.id"))

    market: Mapped[Market]
    selection: Mapped[Selection]
    line: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    odds_price_at_pick: Mapped[Decimal] = mapped_column(Numeric(6, 2))

    status: Mapped[BetStatus] = mapped_column(default=BetStatus.PENDING)

    bet: Mapped["Bet"] = relationship(back_populates="legs")

    __table_args__ = (
        # The one hard rule from the brief's combination-checks list that's
        # enforced at the schema level: a single slip can't reference the
        # same match twice (see services/bets.py for the rest — stale
        # odds, kickoff-started, incompatible markets).
        UniqueConstraint("bet_id", "match_id", name="uq_bet_leg_bet_match"),
    )


class Wallet(UUIDPKMixin, TimestampMixin, Base):
    """A user's virtual credit balance for one league, one gameweek. Reset
    every gameweek by design (see docs/ARCHITECTURE.md#budget) so a bad week
    never eliminates anyone."""

    __tablename__ = "wallets"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    league_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leagues.id"))
    gameweek_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gameweeks.id"))

    starting_balance: Mapped[int] = mapped_column(Integer)
    current_balance: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("user_id", "league_id", "gameweek_id", name="uq_wallet_user_league_gameweek"),
    )
