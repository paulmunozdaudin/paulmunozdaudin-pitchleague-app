import uuid

from pydantic import BaseModel

from app.schemas.user import UserOut


class RankingRow(BaseModel):
    position: int
    previous_position: int | None
    user: UserOut
    balance: int
    net_change: int
    streak: int = 0
    is_you: bool = False


class GameweekResultSummary(BaseModel):
    """Powers the videogame-style end-of-gameweek screen."""

    gameweek_id: uuid.UUID
    net_change: int
    position: int
    previous_position: int | None
    positions_gained: int
    correct_picks: int
    total_picks: int
    current_streak: int
    new_badges: list[str] = []
    rival_overtaken: str | None = None
