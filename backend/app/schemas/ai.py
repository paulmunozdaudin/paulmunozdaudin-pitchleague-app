import uuid

from pydantic import BaseModel


class ModelProbabilities(BaseModel):
    home: float
    draw: float
    away: float
    source: str


class MatchInsightOut(BaseModel):
    match_id: uuid.UUID
    summary: str
    provider: str
    model: ModelProbabilities
