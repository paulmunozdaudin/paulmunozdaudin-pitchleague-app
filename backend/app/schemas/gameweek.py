import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import BetStatus, GameweekStatus, Market, MatchOutcome, MatchStatus, Selection


class OddsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    market: Market
    selection: Selection
    line: Decimal | None
    price: Decimal
    fetched_at: datetime


class MatchLegSummary(BaseModel):
    """One of the caller's own picks on this match — a match can appear in
    several of the caller's bets (a standalone pick and, separately, one
    leg of a combo), so this is a list on MatchOut, not a single field."""

    model_config = ConfigDict(from_attributes=True)

    bet_id: uuid.UUID
    market: Market
    selection: Selection
    line: Decimal | None
    odds_price_at_pick: Decimal
    status: BetStatus


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competition: str
    home_team: str
    away_team: str
    kickoff_at: datetime
    status: MatchStatus
    home_score: int | None
    away_score: int | None
    result: MatchOutcome | None
    odds: list[OddsOut] = []
    is_locked: bool = False
    my_legs: list[MatchLegSummary] = []


class GameweekOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: int
    name: str
    opens_at: datetime
    locks_at: datetime
    budget: int
    status: GameweekStatus
    matches: list[MatchOut] = []
    my_wallet_balance: int | None = None
    my_wallet_starting: int | None = None
