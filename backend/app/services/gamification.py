"""Badges, streaks and XP — awarded automatically right after a gameweek is
settled (called from `services.settlement.settle_gameweek`). Nothing here
is ever purchasable; the only inputs are what actually happened on the
slip, so progress can't be bought — only played for.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.bet import Bet, BetLeg
from app.models.enums import ActivityType, BetStatus, ChallengeStatus, Market, Selection, StreakType
from app.models.gameweek import Gameweek
from app.models.gamification import Badge, Challenge, UserBadge, UserChallenge, UserStreak, UserXP
from app.models.league import League, LeagueMembership, Season
from app.services import rankings
from app.services.activity import record_activity

XP_PER_CORRECT_PICK = 15
XP_PER_PICK_PLAYED = 3
XP_PER_LEVEL = 500

BADGE_CATALOG = [
    ("first_place", "Primer Puesto", "Termina 1.º en una jornada", "🏆"),
    ("hat_trick", "Hat Trick", "Acierta 3 o más predicciones en una jornada", "🎩"),
    ("comeback", "Comeback", "Sube 3 o más puestos en la liga en una jornada", "📈"),
    ("giant_killer", "Giant Killer", "Acierta una predicción con cuota 3.5 o superior", "🗡️"),
    ("perfect_week", "Perfect Week", "Acierta el 100% de tus predicciones en una jornada", "💯"),
    ("underdog", "Underdog", "Acierta una predicción con cuota entre 2.0 y 3.5", "🐺"),
    ("invencible", "Invencible", "5 jornadas seguidas en el Top 3", "🛡️"),
    ("sniper", "Sniper", "La cuota ganadora más alta de la liga en la jornada", "🎯"),
]


def seed_badges(db: Session) -> None:
    existing_codes = {b.code for b in db.query(Badge).all()}
    for code, name, description, icon in BADGE_CATALOG:
        if code not in existing_codes:
            db.add(Badge(code=code, name=name, description=description, icon=icon))
    db.commit()


def _award_badge(db: Session, user_id, league_id, gameweek_id, code: str) -> str | None:
    badge = db.query(Badge).filter(Badge.code == code).first()
    if badge is None:
        return None
    already = (
        db.query(UserBadge)
        .filter(
            UserBadge.user_id == user_id,
            UserBadge.league_id == league_id,
            UserBadge.badge_id == badge.id,
            UserBadge.gameweek_id == gameweek_id,
        )
        .first()
    )
    if already:
        return None
    db.add(UserBadge(user_id=user_id, league_id=league_id, badge_id=badge.id, gameweek_id=gameweek_id))
    record_activity(
        db,
        league_id=league_id,
        user_id=user_id,
        type=ActivityType.BADGE_EARNED,
        data={"code": badge.code, "name": badge.name, "icon": badge.icon},
    )
    return code


def _add_xp(db: Session, user_id, amount: int) -> None:
    record = db.query(UserXP).filter(UserXP.user_id == user_id).first()
    if record is None:
        record = UserXP(user_id=user_id, xp=0, level=1)
        db.add(record)
        db.flush()
    record.xp += amount
    record.level = 1 + record.xp // XP_PER_LEVEL


def _bump_streak(db: Session, user_id, league_id, streak_type: StreakType, hit: bool) -> int:
    streak = (
        db.query(UserStreak)
        .filter(UserStreak.user_id == user_id, UserStreak.league_id == league_id, UserStreak.streak_type == streak_type)
        .first()
    )
    if streak is None:
        streak = UserStreak(user_id=user_id, league_id=league_id, streak_type=streak_type, current_count=0, best_count=0)
        db.add(streak)
        db.flush()
    streak.current_count = streak.current_count + 1 if hit else 0
    streak.best_count = max(streak.best_count, streak.current_count)
    return streak.current_count


def apply_gameweek_results(db: Session, gameweek: Gameweek) -> None:
    seed_badges(db)
    season = db.get(Season, gameweek.season_id)
    league = db.get(League, season.league_id)

    ranking_rows = rankings.gameweek_ranking(db, league, gameweek)
    position_by_user = {row.user.id: row.position for row in ranking_rows}
    positions_before = rankings.season_positions(db, league, season, gameweek.number - 1)
    positions_after = rankings.season_positions(db, league, season, gameweek.number)

    member_ids = [m.user_id for m in db.query(LeagueMembership).filter(LeagueMembership.league_id == league.id).all()]
    legs_by_user: dict = {uid: [] for uid in member_ids}
    leg_rows = (
        db.query(BetLeg, Bet.user_id)
        .join(Bet, Bet.id == BetLeg.bet_id)
        .filter(Bet.gameweek_id == gameweek.id)
        .all()
    )
    for leg, user_id in leg_rows:
        legs_by_user.setdefault(user_id, []).append(leg)

    best_odds_user, best_odds_value = None, Decimal("0")

    for user_id in member_ids:
        picks = legs_by_user.get(user_id, [])
        correct = [p for p in picks if p.status == BetStatus.WON]
        total = len(picks)

        _add_xp(db, user_id, len(correct) * XP_PER_CORRECT_PICK + total * XP_PER_PICK_PLAYED)

        top3 = position_by_user.get(user_id, 999) <= 3
        _bump_streak(db, user_id, league.id, StreakType.TOP_3_FINISH, top3)
        perfect = total > 0 and len(correct) == total
        streak_count = _bump_streak(db, user_id, league.id, StreakType.CORRECT_PICKS, perfect)

        if position_by_user.get(user_id) == 1:
            _award_badge(db, user_id, league.id, gameweek.id, "first_place")
        if len(correct) >= 3:
            _award_badge(db, user_id, league.id, gameweek.id, "hat_trick")
        if perfect and total >= 3:
            _award_badge(db, user_id, league.id, gameweek.id, "perfect_week")
        if positions_after.get(user_id, 999) <= positions_before.get(user_id, 999) - 3:
            _award_badge(db, user_id, league.id, gameweek.id, "comeback")
        if streak_count >= 5:
            _award_badge(db, user_id, league.id, gameweek.id, "invencible")

        for leg in correct:
            price = leg.odds_price_at_pick
            if price >= Decimal("3.5"):
                _award_badge(db, user_id, league.id, gameweek.id, "giant_killer")
            elif price >= Decimal("2.0"):
                _award_badge(db, user_id, league.id, gameweek.id, "underdog")
            if price > best_odds_value:
                best_odds_user, best_odds_value = user_id, price

        _evaluate_challenges(db, user_id, gameweek, picks, correct)

    if best_odds_user is not None and best_odds_value >= Decimal("2.5"):
        _award_badge(db, best_odds_user, league.id, gameweek.id, "sniper")

    db.commit()


def _evaluate_challenges(db: Session, user_id, gameweek: Gameweek, picks: list[BetLeg], correct: list[BetLeg]) -> None:
    challenges = db.query(Challenge).filter(Challenge.gameweek_id == gameweek.id).all()
    for challenge in challenges:
        hit = False
        if challenge.code == "five_correct":
            hit = len(correct) >= 5
        elif challenge.code == "underdog_correct":
            hit = any(p.odds_price_at_pick >= Decimal("2.0") for p in correct)
        elif challenge.code == "three_overs_correct":
            hit = (
                sum(1 for p in correct if p.market == Market.OVER_UNDER and p.selection == Selection.OVER) >= 3
            )
        if not hit:
            continue

        user_challenge = (
            db.query(UserChallenge)
            .filter(UserChallenge.user_id == user_id, UserChallenge.challenge_id == challenge.id)
            .first()
        )
        if user_challenge is None:
            user_challenge = UserChallenge(user_id=user_id, challenge_id=challenge.id)
            db.add(user_challenge)
        if user_challenge.status != ChallengeStatus.COMPLETED:
            user_challenge.status = ChallengeStatus.COMPLETED
            user_challenge.completed_at = utcnow()
            _add_xp(db, user_id, challenge.xp_reward)
