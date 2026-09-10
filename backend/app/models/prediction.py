import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import Market, PredictionStatus, Selection


class Prediction(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "predictions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    league_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leagues.id"))
    gameweek_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gameweeks.id"))
    match_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matches.id"))

    market: Mapped[Market]
    selection: Mapped[Selection]
    line: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    odds_price_at_pick: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    stake: Mapped[int] = mapped_column(Integer)
    potential_payout: Mapped[int] = mapped_column(Integer)

    status: Mapped[PredictionStatus] = mapped_column(default=PredictionStatus.PENDING)
    payout: Mapped[int | None] = mapped_column(Integer, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        # One active pick per match per user per league — keeps the slip UX
        # simple (pick again = overwrite) and settlement math unambiguous.
        UniqueConstraint("user_id", "league_id", "match_id", name="uq_prediction_user_league_match"),
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
