import uuid

from sqlalchemy.orm import Session

from app.models.gameweek import Gameweek
from app.models.prediction import Wallet


def get_or_create_wallet(db: Session, user_id: uuid.UUID, league_id: uuid.UUID, gameweek: Gameweek) -> Wallet:
    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == user_id, Wallet.league_id == league_id, Wallet.gameweek_id == gameweek.id)
        .first()
    )
    if wallet is None:
        wallet = Wallet(
            user_id=user_id,
            league_id=league_id,
            gameweek_id=gameweek.id,
            starting_balance=gameweek.budget,
            current_balance=gameweek.budget,
        )
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet
