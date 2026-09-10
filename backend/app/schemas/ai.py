import uuid

from pydantic import BaseModel


class MatchInsightOut(BaseModel):
    match_id: uuid.UUID
    summary: str
    provider: str
