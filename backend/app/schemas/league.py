import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserOut


class LeagueCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    avatar_emoji: str = Field(default="⚽", max_length=10)
    budget_per_gameweek: int = Field(default=10_000, gt=0)
    max_players: int = Field(default=20, ge=2, le=100)


class LeagueJoin(BaseModel):
    invite_code: str = Field(min_length=4, max_length=10)


class LeagueUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    avatar_emoji: str | None = Field(default=None, max_length=10)
    budget_per_gameweek: int | None = Field(default=None, gt=0)
    max_players: int | None = Field(default=None, ge=2, le=100)


class LeagueMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserOut
    role: str
    joined_at: str | None = None


class LeagueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    avatar_emoji: str
    invite_code: str
    admin_user_id: uuid.UUID
    budget_per_gameweek: int
    max_players: int
    member_count: int = 0
    is_admin: bool = False


class LeagueDetailOut(LeagueOut):
    members: list[LeagueMemberOut] = []
