import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserOut


class LeagueCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class LeagueJoin(BaseModel):
    invite_code: str = Field(min_length=4, max_length=10)


class LeagueUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    budget_per_gameweek: int | None = Field(default=None, gt=0)


class LeagueMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserOut
    role: str
    joined_at: str | None = None


class LeagueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    invite_code: str
    admin_user_id: uuid.UUID
    budget_per_gameweek: int
    member_count: int = 0
    is_admin: bool = False


class LeagueDetailOut(LeagueOut):
    members: list[LeagueMemberOut] = []
