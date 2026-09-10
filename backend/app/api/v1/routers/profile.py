import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.gamification import ProfileStats
from app.services.profile import compute_profile_stats

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me/stats", response_model=ProfileStats)
def get_my_stats(
    league_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileStats:
    return compute_profile_stats(db, user.id, league_id)
