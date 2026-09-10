from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.enums import GameweekStatus, PredictionStatus
from app.models.gameweek import Gameweek, Match
from app.models.league import League
from app.models.prediction import Prediction, Wallet
from app.models.user import User
from app.schemas.prediction import PredictionCreate
from app.services.wallets import get_or_create_wallet


def _find_quote(match: Match, payload: PredictionCreate):
    for quote in match.current_odds():
        if quote.market == payload.market and quote.selection == payload.selection and quote.line == payload.line:
            return quote
    return None


def place_prediction(
    db: Session, user: User, league: League, gameweek: Gameweek, payload: PredictionCreate
) -> Prediction:
    if gameweek.status != GameweekStatus.OPEN:
        raise HTTPException(status_code=400, detail="This gameweek is no longer accepting predictions")

    match = next((m for m in gameweek.matches if m.id == payload.match_id), None)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found in this gameweek")
    if utcnow() >= match.kickoff_at:
        raise HTTPException(status_code=400, detail="This match has already kicked off — selection is locked")

    quote = _find_quote(match, payload)
    if quote is None:
        raise HTTPException(status_code=400, detail="No current odds for that market/selection")

    wallet = get_or_create_wallet(db, user.id, league.id, gameweek)

    existing = (
        db.query(Prediction)
        .filter(Prediction.user_id == user.id, Prediction.league_id == league.id, Prediction.match_id == match.id)
        .first()
    )
    available = wallet.current_balance + (existing.stake if existing else 0)
    if payload.stake > available:
        raise HTTPException(
            status_code=400,
            detail=f"Stake exceeds available budget ({available} credits left)",
        )

    potential_payout = int((Decimal(payload.stake) * quote.price).to_integral_value(rounding=ROUND_HALF_UP))

    if existing:
        wallet.current_balance += existing.stake  # refund, then re-deduct below
        existing.market = payload.market
        existing.selection = payload.selection
        existing.line = payload.line
        existing.odds_price_at_pick = quote.price
        existing.stake = payload.stake
        existing.potential_payout = potential_payout
        existing.status = PredictionStatus.PENDING
        prediction = existing
    else:
        prediction = Prediction(
            user_id=user.id,
            league_id=league.id,
            gameweek_id=gameweek.id,
            match_id=match.id,
            market=payload.market,
            selection=payload.selection,
            line=payload.line,
            odds_price_at_pick=quote.price,
            stake=payload.stake,
            potential_payout=potential_payout,
        )
        db.add(prediction)

    wallet.current_balance -= payload.stake
    db.commit()
    db.refresh(prediction)
    return prediction


def cancel_prediction(db: Session, user: User, league: League, prediction_id) -> None:
    prediction = (
        db.query(Prediction)
        .filter(Prediction.id == prediction_id, Prediction.user_id == user.id, Prediction.league_id == league.id)
        .first()
    )
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")

    match = db.get(Match, prediction.match_id)
    if match and utcnow() >= match.kickoff_at:
        raise HTTPException(status_code=400, detail="Cannot cancel — the match has already kicked off")

    wallet = (
        db.query(Wallet)
        .filter(
            Wallet.user_id == user.id, Wallet.league_id == league.id, Wallet.gameweek_id == prediction.gameweek_id
        )
        .first()
    )
    if wallet:
        wallet.current_balance += prediction.stake

    db.delete(prediction)
    db.commit()


def list_my_predictions(db: Session, user: User, league: League, gameweek: Gameweek) -> list[Prediction]:
    return (
        db.query(Prediction)
        .filter(
            Prediction.user_id == user.id,
            Prediction.league_id == league.id,
            Prediction.gameweek_id == gameweek.id,
        )
        .all()
    )
