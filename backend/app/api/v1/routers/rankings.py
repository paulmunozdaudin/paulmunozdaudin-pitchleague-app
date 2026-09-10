import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_league_or_404, get_membership
from app.db.session import get_db
from app.models.enums import PredictionStatus, StreakType
from app.models.gameweek import Gameweek
from app.models.gamification import Badge, UserBadge, UserStreak
from app.models.league import League, LeagueMembership
from app.models.prediction import Prediction, Wallet
from app.models.user import User
from app.schemas.ranking import GameweekResultSummary, RankingRow
from app.services import gameweeks as gameweeks_service
from app.services import rankings as rankings_service

router = APIRouter(prefix="/leagues/{league_id}/rankings", tags=["rankings"])


@router.get("/season", response_model=list[RankingRow])
def get_season_ranking(
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    _membership: LeagueMembership = Depends(get_membership),
) -> list[RankingRow]:
    season = gameweeks_service.get_active_season(db, league)
    return rankings_service.season_ranking(db, league, season)


@router.get("/{gameweek_id}", response_model=list[RankingRow])
def get_gameweek_ranking(
    gameweek_id: uuid.UUID,
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    _membership: LeagueMembership = Depends(get_membership),
) -> list[RankingRow]:
    gameweek = db.get(Gameweek, gameweek_id)
    if gameweek is None or gameweek.season.league_id != league.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gameweek not found")
    return rankings_service.gameweek_ranking(db, league, gameweek)


@router.get("/{gameweek_id}/result-summary", response_model=GameweekResultSummary)
def get_result_summary(
    gameweek_id: uuid.UUID,
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    membership: LeagueMembership = Depends(get_membership),
) -> GameweekResultSummary:
    gameweek = db.get(Gameweek, gameweek_id)
    if gameweek is None or gameweek.season.league_id != league.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gameweek not found")
    if gameweek.status.value != "settled":
        raise HTTPException(status_code=400, detail="Gameweek not settled yet")

    season = gameweek.season
    user_id = membership.user_id

    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == user_id, Wallet.league_id == league.id, Wallet.gameweek_id == gameweek.id)
        .first()
    )
    net_change = (wallet.current_balance - wallet.starting_balance) if wallet else 0

    positions_before = rankings_service.season_positions(db, league, season, gameweek.number - 1)
    positions_after = rankings_service.season_positions(db, league, season, gameweek.number)
    position = positions_after.get(user_id, 0)
    previous_position = positions_before.get(user_id)
    positions_gained = (previous_position - position) if previous_position else 0

    picks = db.query(Prediction).filter(Prediction.gameweek_id == gameweek.id, Prediction.user_id == user_id).all()
    correct_picks = sum(1 for p in picks if p.status == PredictionStatus.WON)

    streak = (
        db.query(UserStreak)
        .filter(
            UserStreak.user_id == user_id,
            UserStreak.league_id == league.id,
            UserStreak.streak_type == StreakType.TOP_3_FINISH,
        )
        .first()
    )

    new_badges = [
        code
        for (code,) in db.query(Badge.code)
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .filter(UserBadge.user_id == user_id, UserBadge.league_id == league.id, UserBadge.gameweek_id == gameweek.id)
        .all()
    ]

    rival_overtaken = None
    if previous_position:
        for other_id, prev_pos in positions_before.items():
            if other_id == user_id or prev_pos >= previous_position:
                continue
            new_pos = positions_after.get(other_id)
            if new_pos and position and new_pos > position:
                rival = db.get(User, other_id)
                if rival:
                    rival_overtaken = rival.name
                break

    return GameweekResultSummary(
        gameweek_id=gameweek.id,
        net_change=net_change,
        position=position,
        previous_position=previous_position,
        positions_gained=positions_gained,
        correct_picks=correct_picks,
        total_picks=len(picks),
        current_streak=streak.current_count if streak else 0,
        new_badges=new_badges,
        rival_overtaken=rival_overtaken,
    )
