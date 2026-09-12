"""Bet placement — single selections and combinations are the same code
path (a "single" is just a one-leg Bet). This is where every check from
the brief's combinations section actually lives:

- duplicate match within one slip → rejected before touching the DB
- incompatible/suspended selection → "no current odds for that pick"
- stale odds → 409 with the old/new price, never silently honored
- match already started → checked per-leg, not just once for the whole slip
"""

import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.bet import Bet, BetLeg, Wallet
from app.models.enums import ActivityType, GameweekStatus
from app.models.gameweek import Gameweek, Match
from app.models.league import League
from app.models.user import User
from app.schemas.bet import BetCreate
from app.services.activity import record_activity
from app.services.wallets import get_or_create_wallet

ODDS_CHANGE_TOLERANCE = Decimal("0.01")  # rounding noise, not a real price move


def _match_by_id(gameweek: Gameweek, match_id: uuid.UUID) -> Match:
    match = next((m for m in gameweek.matches if m.id == match_id), None)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found in this gameweek")
    return match


def _current_quote(match: Match, market, selection, line):
    for quote in match.current_odds():
        if quote.market == market and quote.selection == selection and quote.line == line:
            return quote
    return None


def place_bet(db: Session, user: User, league: League, gameweek: Gameweek, payload: BetCreate) -> Bet:
    if gameweek.status != GameweekStatus.OPEN:
        raise HTTPException(status_code=400, detail="Esta jornada ya no acepta predicciones")

    match_ids = [leg.match_id for leg in payload.legs]
    if len(match_ids) != len(set(match_ids)):
        raise HTTPException(
            status_code=400, detail="No puedes incluir el mismo partido dos veces en una combinada"
        )

    now = utcnow()
    resolved_legs: list[tuple[Match, object]] = []  # (match, quote)

    for leg in payload.legs:
        match = _match_by_id(gameweek, leg.match_id)
        if now >= match.kickoff_at:
            raise HTTPException(
                status_code=400,
                detail=f"{match.home_team} vs {match.away_team} ya ha empezado — selección bloqueada",
            )

        quote = _current_quote(match, leg.market, leg.selection, leg.line)
        if quote is None:
            raise HTTPException(
                status_code=400,
                detail=f"Esa selección ya no está disponible para {match.home_team} vs {match.away_team}",
            )

        if abs(quote.price - leg.expected_price) > ODDS_CHANGE_TOLERANCE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": f"La cuota ha cambiado de {leg.expected_price} a {quote.price}",
                    "match_id": str(match.id),
                    "expected_price": str(leg.expected_price),
                    "current_price": str(quote.price),
                },
            )

        resolved_legs.append((match, quote))

    wallet = get_or_create_wallet(db, user.id, league.id, gameweek)
    if payload.stake > wallet.current_balance:
        raise HTTPException(
            status_code=400,
            detail=f"El importe supera tu presupuesto disponible ({wallet.current_balance} créditos)",
        )

    combined_odds = Decimal("1")
    for _, quote in resolved_legs:
        combined_odds *= quote.price
    combined_odds = combined_odds.quantize(Decimal("0.01"))
    potential_payout = int((Decimal(payload.stake) * combined_odds).to_integral_value(rounding=ROUND_HALF_UP))

    bet = Bet(
        user_id=user.id,
        league_id=league.id,
        gameweek_id=gameweek.id,
        stake=payload.stake,
        combined_odds=combined_odds,
        potential_payout=potential_payout,
    )
    db.add(bet)
    db.flush()

    for (match, quote), leg in zip(resolved_legs, payload.legs):
        db.add(
            BetLeg(
                bet_id=bet.id,
                match_id=match.id,
                market=leg.market,
                selection=leg.selection,
                line=leg.line,
                odds_price_at_pick=quote.price,
            )
        )

    wallet.current_balance -= payload.stake
    db.commit()
    db.refresh(bet)

    record_activity(
        db,
        league_id=league.id,
        user_id=user.id,
        type=ActivityType.BET_PLACED,
        data={
            "bet_id": str(bet.id),
            "stake": payload.stake,
            "leg_count": len(resolved_legs),
            "combined_odds": str(combined_odds),
            "matches": [f"{m.home_team} vs {m.away_team}" for m, _ in resolved_legs],
        },
    )
    db.commit()
    return bet


def cancel_bet(db: Session, user: User, league: League, bet_id: uuid.UUID) -> None:
    bet = (
        db.query(Bet)
        .filter(Bet.id == bet_id, Bet.user_id == user.id, Bet.league_id == league.id)
        .first()
    )
    if bet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Predicción no encontrada")

    now = utcnow()
    for leg in bet.legs:
        match = db.get(Match, leg.match_id)
        if match and now >= match.kickoff_at:
            raise HTTPException(
                status_code=400,
                detail="No se puede cancelar — al menos un partido de la combinada ya ha empezado",
            )

    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == user.id, Wallet.league_id == league.id, Wallet.gameweek_id == bet.gameweek_id)
        .first()
    )
    if wallet:
        wallet.current_balance += bet.stake

    db.delete(bet)
    db.commit()


def list_my_bets(db: Session, user: User, league: League, gameweek: Gameweek) -> list[Bet]:
    return (
        db.query(Bet)
        .filter(Bet.user_id == user.id, Bet.league_id == league.id, Bet.gameweek_id == gameweek.id)
        .order_by(Bet.created_at.desc())
        .all()
    )
