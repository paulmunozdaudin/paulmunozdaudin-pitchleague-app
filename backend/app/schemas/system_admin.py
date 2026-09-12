import uuid
from datetime import datetime

from pydantic import BaseModel


class SystemOverviewOut(BaseModel):
    users_count: int
    leagues_count: int
    matches_count: int
    open_gameweeks_count: int
    odds_provider: str
    ai_insights_provider: str


class ModelVersionOut(BaseModel):
    id: uuid.UUID
    division: str
    model_name: str
    trained_at: datetime
    is_active: bool
    metrics: dict


class OddsHealthRow(BaseModel):
    competition: str
    matches_open: int
    stale_matches: int
    last_fetched_at: datetime | None


class FailedJobOut(BaseModel):
    id: uuid.UUID
    job_name: str
    reference: str | None
    error_message: str
    occurred_at: datetime
