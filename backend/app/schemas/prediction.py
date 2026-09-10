import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Market, PredictionStatus, Selection


class PredictionCreate(BaseModel):
    match_id: uuid.UUID
    market: Market
    selection: Selection
    line: Decimal | None = None
    stake: int = Field(gt=0)


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    match_id: uuid.UUID
    market: Market
    selection: Selection
    line: Decimal | None
    odds_price_at_pick: Decimal
    stake: int
    potential_payout: int
    status: PredictionStatus
    payout: int | None
