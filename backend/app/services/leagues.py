import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import MembershipRole
from app.models.league import League, LeagueMembership, Season
from app.models.user import User

# Excludes 0/O/1/I so a spoken/read-aloud code is never ambiguous.
INVITE_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _generate_invite_code(db: Session) -> str:
    for _ in range(20):
        code = "PL-" + "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(4))
        if db.query(League).filter(League.invite_code == code).first() is None:
            return code
    raise HTTPException(status_code=500, detail="Could not generate a unique invite code, try again")


def create_league(
    db: Session, owner: User, name: str, avatar_emoji: str = "⚽", budget_per_gameweek: int = 10_000, max_players: int = 20
) -> League:
    league = League(
        name=name,
        avatar_emoji=avatar_emoji,
        invite_code=_generate_invite_code(db),
        admin_user_id=owner.id,
        budget_per_gameweek=budget_per_gameweek,
        max_players=max_players,
    )
    db.add(league)
    db.flush()

    db.add(LeagueMembership(league_id=league.id, user_id=owner.id, role=MembershipRole.ADMIN))
    db.add(Season(league_id=league.id, name="Temporada 1", is_active=True))
    db.commit()
    db.refresh(league)
    return league


def join_league(db: Session, user: User, invite_code: str) -> League:
    league = db.query(League).filter(League.invite_code == invite_code.strip().upper()).first()
    if league is None or not league.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite code")

    existing = (
        db.query(LeagueMembership)
        .filter(LeagueMembership.league_id == league.id, LeagueMembership.user_id == user.id)
        .first()
    )
    if existing is not None:
        if not existing.is_active:
            if member_count(db, league.id) >= league.max_players:
                raise HTTPException(status_code=400, detail="Esta liga ya está completa")
            existing.is_active = True
            db.commit()
        return league

    if member_count(db, league.id) >= league.max_players:
        raise HTTPException(status_code=400, detail="Esta liga ya está completa")

    db.add(LeagueMembership(league_id=league.id, user_id=user.id, role=MembershipRole.MEMBER))
    db.commit()
    return league


def list_my_leagues(db: Session, user: User) -> list[League]:
    return (
        db.query(League)
        .join(LeagueMembership, LeagueMembership.league_id == League.id)
        .filter(LeagueMembership.user_id == user.id, LeagueMembership.is_active.is_(True))
        .all()
    )


def member_count(db: Session, league_id: uuid.UUID) -> int:
    return (
        db.query(func.count(LeagueMembership.id))
        .filter(LeagueMembership.league_id == league_id, LeagueMembership.is_active.is_(True))
        .scalar()
        or 0
    )


def update_league(
    db: Session,
    league: League,
    name: str | None,
    budget: int | None,
    avatar_emoji: str | None = None,
    max_players: int | None = None,
) -> League:
    if name:
        league.name = name
    if budget:
        league.budget_per_gameweek = budget
    if avatar_emoji:
        league.avatar_emoji = avatar_emoji
    if max_players:
        league.max_players = max_players
    db.commit()
    db.refresh(league)
    return league


def kick_member(db: Session, league: League, target_user_id: uuid.UUID) -> None:
    if target_user_id == league.admin_user_id:
        raise HTTPException(status_code=400, detail="Cannot remove the league admin")
    membership = (
        db.query(LeagueMembership)
        .filter(LeagueMembership.league_id == league.id, LeagueMembership.user_id == target_user_id)
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Member not found")
    membership.is_active = False
    db.commit()


def reset_season(db: Session, league: League) -> Season:
    db.query(Season).filter(Season.league_id == league.id, Season.is_active.is_(True)).update(
        {"is_active": False}
    )
    next_number = db.query(func.count(Season.id)).filter(Season.league_id == league.id).scalar() or 0
    season = Season(league_id=league.id, name=f"Temporada {next_number + 1}", is_active=True)
    db.add(season)
    db.commit()
    db.refresh(season)
    return season
