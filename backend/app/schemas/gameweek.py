import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import GameweekStatus, Market, MatchOutcome, MatchStatus, Selection


class OddsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    market: Market
    selection: Selection
    line: Decimal | None
    price: Decimal
    fetched_at: datetime


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
    my_prediction: "PredictionOut | None" = None


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


from app.schemas.prediction import PredictionOut  # noqa: E402

MatchOut.model_rebuild()
