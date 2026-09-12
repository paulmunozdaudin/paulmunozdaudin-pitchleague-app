import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ActivityType
from app.schemas.user import UserOut


class LeagueActivityOut(BaseModel):
    id: uuid.UUID
    user: UserOut
    type: ActivityType
    data: dict
    created_at: datetime
