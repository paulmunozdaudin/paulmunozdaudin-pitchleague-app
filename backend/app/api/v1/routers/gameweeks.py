import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.v1.deps import get_league_or_404, get_membership, require_admin
from app.db.base import utcnow
from app.db.session import get_db
from app.core.security import get_current_user
from app.models.bet import Bet, BetLeg
from app.models.gameweek import Gameweek
from app.models.league import League, LeagueMembership
from app.models.user import User
from app.schemas.bet import BetCreate, BetOut
from app.schemas.gameweek import GameweekOut, MatchLegSummary, MatchOut, OddsOut
from app.services import bets as bets_service
from app.services import gameweeks as gameweeks_service
from app.services import rankings as rankings_service
from app.services import settlement as settlement_service
from app.services.realtime import manager
from app.services.wallets import get_or_create_wallet

router = APIRouter(prefix="/leagues/{league_id}/gameweeks", tags=["gameweeks"])


def _to_gameweek_out(db: Session, gameweek: Gameweek, league: League, user: User) -> GameweekOut:
    legs_by_match: dict[uuid.UUID, list[MatchLegSummary]] = {}
    leg_rows = (
        db.query(BetLeg, Bet.id)
        .join(Bet, Bet.id == BetLeg.bet_id)
        .filter(Bet.gameweek_id == gameweek.id, Bet.user_id == user.id)
        .all()
    )
    for leg, bet_id in leg_rows:
        legs_by_match.setdefault(leg.match_id, []).append(
            MatchLegSummary(
                bet_id=bet_id,
                market=leg.market,
                selection=leg.selection,
                line=leg.line,
                odds_price_at_pick=leg.odds_price_at_pick,
                status=leg.status,
            )
        )

    now = utcnow()
    matches = []
    for match in gameweek.matches:
        match_out = MatchOut.model_validate(match)
        match_out.odds = [OddsOut.model_validate(quote) for quote in match.current_odds()]
        match_out.is_locked = now >= match.kickoff_at
        match_out.my_legs = legs_by_match.get(match.id, [])
        matches.append(match_out)

    wallet = get_or_create_wallet(db, user.id, league.id, gameweek)

    return GameweekOut(
        id=gameweek.id,
        number=gameweek.number,
        name=gameweek.name,
        opens_at=gameweek.opens_at,
        locks_at=gameweek.locks_at,
        budget=gameweek.budget,
        status=gameweek.status,
        matches=matches,
        my_wallet_balance=wallet.current_balance,
        my_wallet_starting=wallet.starting_balance,
    )


def _get_gameweek_or_404(db: Session, league: League, gameweek_id: uuid.UUID) -> Gameweek:
    gameweek = db.get(Gameweek, gameweek_id)
    if gameweek is None or gameweek.season.league_id != league.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gameweek not found")
    return gameweek


@router.get("/current", response_model=GameweekOut)
def get_current_gameweek(
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _membership: LeagueMembership = Depends(get_membership),
) -> GameweekOut:
    gameweeks_service.lock_expired_gameweeks(db)
    gameweek = gameweeks_service.get_current_gameweek(db, league)
    if gameweek is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No open gameweek yet")
    return _to_gameweek_out(db, gameweek, league, user)


@router.get("/{gameweek_id}", response_model=GameweekOut)
def get_gameweek(
    gameweek_id: uuid.UUID,
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _membership: LeagueMembership = Depends(get_membership),
) -> GameweekOut:
    gameweek = _get_gameweek_or_404(db, league, gameweek_id)
    return _to_gameweek_out(db, gameweek, league, user)


@router.post("/generate-next", response_model=GameweekOut, status_code=status.HTTP_201_CREATED)
def generate_next_gameweek(
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: LeagueMembership = Depends(require_admin),
) -> GameweekOut:
    gameweek = gameweeks_service.generate_next_gameweek(db, league)
    return _to_gameweek_out(db, gameweek, league, user)


@router.post("/{gameweek_id}/refresh-odds")
def refresh_odds(
    gameweek_id: uuid.UUID,
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    _admin: LeagueMembership = Depends(require_admin),
) -> dict:
    gameweek = _get_gameweek_or_404(db, league, gameweek_id)
    updated = gameweeks_service.refresh_odds(db, gameweek)
    return {"matches_updated": updated}


@router.post("/{gameweek_id}/bets", response_model=BetOut)
def place_bet(
    gameweek_id: uuid.UUID,
    payload: BetCreate,
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _membership: LeagueMembership = Depends(get_membership),
) -> BetOut:
    gameweek = _get_gameweek_or_404(db, league, gameweek_id)
    bet = bets_service.place_bet(db, user, league, gameweek, payload)
    return BetOut.model_validate(bet)


@router.delete("/{gameweek_id}/bets/{bet_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_bet(
    gameweek_id: uuid.UUID,
    bet_id: uuid.UUID,
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _membership: LeagueMembership = Depends(get_membership),
) -> None:
    bets_service.cancel_bet(db, user, league, bet_id)


@router.get("/{gameweek_id}/bets/me", response_model=list[BetOut])
def list_my_bets(
    gameweek_id: uuid.UUID,
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _membership: LeagueMembership = Depends(get_membership),
) -> list[BetOut]:
    gameweek = _get_gameweek_or_404(db, league, gameweek_id)
    return [BetOut.model_validate(b) for b in bets_service.list_my_bets(db, user, league, gameweek)]


@router.post("/{gameweek_id}/settle")
async def settle_gameweek(
    gameweek_id: uuid.UUID,
    league: League = Depends(get_league_or_404),
    db: Session = Depends(get_db),
    _admin: LeagueMembership = Depends(require_admin),
) -> dict:
    gameweek = _get_gameweek_or_404(db, league, gameweek_id)
    settled = await run_in_threadpool(settlement_service.settle_gameweek, db, gameweek)

    if settled:
        ranking = rankings_service.gameweek_ranking(db, league, gameweek)
        await manager.broadcast(
            league.id,
            {
                "type": "gameweek_settled",
                "gameweek_id": str(gameweek.id),
                "ranking": [
                    {"position": r.position, "user_id": str(r.user.id), "name": r.user.name, "balance": r.balance}
                    for r in ranking
                ],
            },
        )

    return {"settled": settled, "status": gameweek.status.value}
