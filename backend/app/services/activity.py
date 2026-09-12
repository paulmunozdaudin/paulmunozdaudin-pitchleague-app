import uuid

from sqlalchemy.orm import Session

from app.models.activity import LeagueActivity
from app.models.enums import ActivityType


def record_activity(db: Session, league_id: uuid.UUID, user_id: uuid.UUID, type: ActivityType, data: dict) -> None:
    db.add(LeagueActivity(league_id=league_id, user_id=user_id, type=type, data=data))


def list_recent_activity(db: Session, league_id: uuid.UUID, limit: int = 50) -> list[LeagueActivity]:
    return (
        db.query(LeagueActivity)
        .filter(LeagueActivity.league_id == league_id)
        .order_by(LeagueActivity.created_at.desc())
        .limit(limit)
        .all()
    )
