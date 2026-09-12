import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BetStatus, Market, Selection


class BetLegCreate(BaseModel):
    match_id: uuid.UUID
    market: Market
    selection: Selection
    line: Decimal | None = None
    # The price the client last saw for this selection — compared against
    # the current live price server-side so a moved market is caught and
    # surfaced ("La cuota ha cambiado de 2.10 a 2.05") instead of silently
    # honoring a stale number. See services/bets.py::_check_price.
    expected_price: Decimal


class BetCreate(BaseModel):
    stake: int = Field(gt=0)
    legs: list[BetLegCreate] = Field(min_length=1, max_length=12)


class BetLegOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    match_id: uuid.UUID
    market: Market
    selection: Selection
    line: Decimal | None
    odds_price_at_pick: Decimal
    status: BetStatus


class BetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stake: int
    combined_odds: Decimal
    potential_payout: int
    status: BetStatus
    payout: int | None
    created_at: datetime
    legs: list[BetLegOut] = []


class OddsChangedError(BaseModel):
    """Returned (HTTP 409) when a leg's price moved since the client last
    fetched it — the frontend re-shows the slip with updated prices and
    asks the user to confirm again rather than silently placing at a
    different price than what they saw."""

    match_id: uuid.UUID
    expected_price: Decimal
    current_price: Decimal
