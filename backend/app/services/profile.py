import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.bet import Bet, BetLeg, Wallet
from app.models.enums import BetStatus, GameweekStatus
from app.models.gameweek import Gameweek
from app.models.gamification import Badge, UserBadge, UserStreak, UserXP
from app.schemas.gamification import BadgeOut, ProfileStats
from app.services.gamification import XP_PER_LEVEL


def compute_profile_stats(db: Session, user_id: uuid.UUID, league_id: uuid.UUID | None = None) -> ProfileStats:
    bet_q = db.query(Bet).filter(Bet.user_id == user_id)
    leg_q = db.query(BetLeg).join(Bet, Bet.id == BetLeg.bet_id).filter(Bet.user_id == user_id)
    # Only gameweeks that have actually finished count towards "weeks
    # played" / "best week" — an in-progress wallet's balance is just money
    # currently at risk, not a result yet.
    wallet_q = (
        db.query(Wallet)
        .join(Gameweek, Gameweek.id == Wallet.gameweek_id)
        .filter(Wallet.user_id == user_id, Gameweek.status == GameweekStatus.SETTLED)
    )
    if league_id:
        bet_q = bet_q.filter(Bet.league_id == league_id)
        leg_q = leg_q.filter(Bet.league_id == league_id)
        wallet_q = wallet_q.filter(Wallet.league_id == league_id)

    # Accuracy and "highest multiplier" are per-pick concepts — a combo's
    # four legs are four picks, not one — so they're computed over legs.
    settled_legs = leg_q.filter(BetLeg.status.in_([BetStatus.WON, BetStatus.LOST])).all()
    won_legs = [leg for leg in settled_legs if leg.status == BetStatus.WON]
    accuracy = (len(won_legs) / len(settled_legs) * 100) if settled_legs else 0.0
    highest_multiplier = max((float(leg.odds_price_at_pick) for leg in won_legs), default=0.0)

    # ROI is a money-flow concept — computed over bets (one stake, one
    # payout per slip), not legs.
    settled_bets = bet_q.filter(Bet.status.in_([BetStatus.WON, BetStatus.LOST, BetStatus.VOID])).all()
    total_staked = sum(b.stake for b in settled_bets) or 0
    total_returned = sum((b.payout or 0) for b in settled_bets)
    roi = ((total_returned - total_staked) / total_staked * 100) if total_staked else 0.0

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
