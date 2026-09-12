import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.enums import MembershipRole
from app.models.league import League, LeagueMembership
from app.models.user import User


def get_league_or_404(league_id: uuid.UUID, db: Session = Depends(get_db)) -> League:
    league = db.get(League, league_id)
    if league is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="League not found")
    return league


def get_membership(
    league: League = Depends(get_league_or_404),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeagueMembership:
    membership = (
        db.query(LeagueMembership)
        .filter(
            LeagueMembership.league_id == league.id,
            LeagueMembership.user_id == user.id,
            LeagueMembership.is_active.is_(True),
        )
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this league")
    return membership


def require_admin(membership: LeagueMembership = Depends(get_membership)) -> LeagueMembership:
    if membership.role != MembershipRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return membership


def require_staff(user: User = Depends(get_current_user)) -> User:
    if not user.is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff only")
    return user
