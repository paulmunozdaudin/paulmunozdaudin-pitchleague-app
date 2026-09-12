import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_league_or_404, get_membership, require_admin
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.enums import MembershipRole
from app.models.league import League, LeagueMembership
from app.models.user import User
from app.schemas.league import LeagueCreate, LeagueDetailOut, LeagueJoin, LeagueMemberOut, LeagueOut, LeagueUpdate
from app.services import leagues as leagues_service

router = APIRouter(prefix="/leagues", tags=["leagues"])


def _to_out(db: Session, league: League, user: User) -> LeagueOut:
    return LeagueOut(
        id=league.id,
        name=league.name,
        avatar_emoji=league.avatar_emoji,
        invite_code=league.invite_code,
        admin_user_id=league.admin_user_id,
        budget_per_gameweek=league.budget_per_gameweek,
        max_players=league.max_players,
        member_count=leagues_service.member_count(db, league.id),
        is_admin=league.admin_user_id == user.id,
    )


@router.post("", response_model=LeagueOut, status_code=status.HTTP_201_CREATED)
def create_league(
    payload: LeagueCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LeagueOut:
    league = leagues_service.create_league(
        db, user, payload.name, payload.avatar_emoji, payload.budget_per_gameweek, payload.max_players
    )
    return _to_out(db, league, user)


@router.post("/join", response_model=LeagueOut)
def join_league(
    payload: LeagueJoin, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LeagueOut:
    league = leagues_service.join_league(db, user, payload.invite_code)
    return _to_out(db, league, user)


@router.get("", response_model=list[LeagueOut])
def list_my_leagues(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[LeagueOut]:
    return [_to_out(db, league, user) for league in leagues_service.list_my_leagues(db, user)]


@router.get("/{league_id}", response_model=LeagueDetailOut)
def get_league(
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _membership: LeagueMembership = Depends(get_membership),
) -> LeagueDetailOut:
    memberships = (
        db.query(LeagueMembership)
        .filter(LeagueMembership.league_id == league.id, LeagueMembership.is_active.is_(True))
        .all()
    )
    members = [
        LeagueMemberOut(user=db.get(User, m.user_id), role=m.role.value, joined_at=str(m.joined_at))
        for m in memberships
    ]

    base = _to_out(db, league, user)
    return LeagueDetailOut(**base.model_dump(), members=members)


@router.patch("/{league_id}", response_model=LeagueOut)
def update_league(
    payload: LeagueUpdate,
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: LeagueMembership = Depends(require_admin),
) -> LeagueOut:
    league = leagues_service.update_league(
        db, league, payload.name, payload.budget_per_gameweek, payload.avatar_emoji, payload.max_players
    )
    return _to_out(db, league, user)


@router.delete("/{league_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def kick_member(
    user_id: uuid.UUID,
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    _admin: LeagueMembership = Depends(require_admin),
) -> None:
    leagues_service.kick_member(db, league, user_id)


@router.post("/{league_id}/reset-season", status_code=status.HTTP_201_CREATED)
def reset_season(
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    _admin: LeagueMembership = Depends(require_admin),
) -> dict:
    season = leagues_service.reset_season(db, league)
    return {"season_id": str(season.id), "name": season.name}
