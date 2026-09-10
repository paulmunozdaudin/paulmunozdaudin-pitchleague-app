from pydantic import BaseModel, ConfigDict


class BadgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str
    icon: str
    earned_at: str | None = None


class ProfileStats(BaseModel):
    gameweeks_played: int
    accuracy: float
    best_week_net: int
    longest_streak: int
    highest_multiplier: float
    roi_percent: float
    xp: int
    level: int
    xp_to_next_level: int
    badges: list[BadgeOut] = []
