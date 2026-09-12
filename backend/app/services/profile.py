import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import GameweekStatus, PredictionStatus
from app.models.gameweek import Gameweek
from app.models.gamification import Badge, UserBadge, UserStreak, UserXP
from app.models.prediction import Prediction, Wallet
from app.schemas.gamification import BadgeOut, ProfileStats
from app.services.gamification import XP_PER_LEVEL


def compute_profile_stats(db: Session, user_id: uuid.UUID, league_id: uuid.UUID | None = None) -> ProfileStats:
    prediction_q = db.query(Prediction).filter(Prediction.user_id == user_id)
    # Only gameweeks that have actually finished count towards "weeks
    # played" / "best week" — an in-progress wallet's balance is just money
    # currently at risk, not a result yet.
    wallet_q = (
        db.query(Wallet)
        .join(Gameweek, Gameweek.id == Wallet.gameweek_id)
        .filter(Wallet.user_id == user_id, Gameweek.status == GameweekStatus.SETTLED)
    )
    if league_id:
        prediction_q = prediction_q.filter(Prediction.league_id == league_id)
        wallet_q = wallet_q.filter(Wallet.league_id == league_id)

    settled = prediction_q.filter(Prediction.status.in_([PredictionStatus.WON, PredictionStatus.LOST])).all()
    won = [p for p in settled if p.status == PredictionStatus.WON]

    accuracy = (len(won) / len(settled) * 100) if settled else 0.0
    total_staked = sum(p.stake for p in settled) or 0
    total_returned = sum((p.payout or 0) for p in settled)
    roi = ((total_returned - total_staked) / total_staked * 100) if total_staked else 0.0
    highest_multiplier = max((float(p.odds_price_at_pick) for p in won), default=0.0)

    wallets = wallet_q.all()
    weekly_nets = [w.current_balance - w.starting_balance for w in wallets]
    gameweeks_played = len(wallets)
    best_week_net = max(weekly_nets, default=0)

    streak_q = db.query(UserStreak).filter(UserStreak.user_id == user_id)
    if league_id:
        streak_q = streak_q.filter(UserStreak.league_id == league_id)
    longest_streak = max((s.best_count for s in streak_q.all()), default=0)

    xp_record = db.query(UserXP).filter(UserXP.user_id == user_id).first()
    xp = xp_record.xp if xp_record else 0
    level = xp_record.level if xp_record else 1
    xp_to_next_level = XP_PER_LEVEL - (xp % XP_PER_LEVEL)

    badge_rows_q = (
        db.query(Badge, func.max(UserBadge.earned_at))
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .filter(UserBadge.user_id == user_id)
    )
    if league_id:
        badge_rows_q = badge_rows_q.filter(UserBadge.league_id == league_id)
    badge_rows = badge_rows_q.group_by(Badge.id).all()
    badges = [
        BadgeOut(code=b.code, name=b.name, description=b.description, icon=b.icon, earned_at=str(earned_at))
        for b, earned_at in badge_rows
    ]

    return ProfileStats(
        gameweeks_played=gameweeks_played,
        accuracy=round(accuracy, 1),
        best_week_net=best_week_net,
        longest_streak=longest_streak,
        highest_multiplier=round(highest_multiplier, 2),
        roi_percent=round(roi, 1),
        xp=xp,
        level=level,
        xp_to_next_level=xp_to_next_level,
        badges=badges,
    )
