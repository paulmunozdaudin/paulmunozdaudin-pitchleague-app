from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_league_or_404, get_membership
from app.db.session import get_db
from app.models.league import League, LeagueMembership
from app.models.user import User
from app.schemas.activity import LeagueActivityOut
from app.services.activity import list_recent_activity

router = APIRouter(prefix="/leagues/{league_id}/activity", tags=["activity"])


@router.get("", response_model=list[LeagueActivityOut])
def get_league_activity(
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    _membership: LeagueMembership = Depends(get_membership),
) -> list[LeagueActivityOut]:
    """Powers "La Liga" — the social feed. Rivalry and conversation, not a
    full chat (see the brief: the feed matters more than chat for the MVP)."""
    rows = list_recent_activity(db, league.id)
    users = {u.id: u for u in db.query(User).filter(User.id.in_([r.user_id for r in rows])).all()}
    return [
        LeagueActivityOut(id=r.id, user=users[r.user_id], type=r.type, data=r.data, created_at=r.created_at)
        for r in rows
        if r.user_id in users
    ]
