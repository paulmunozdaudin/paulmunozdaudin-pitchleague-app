"""Turns raw match results into settled bets, updated wallets, and (via
`services.gamification`) badges/streaks/XP. `_leg_outcome` is the one place
in the app where "did this leg win" is decided; `_settle_bet` is where a
combination's per-leg outcomes turn into one payout.
"""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.bet import Bet, BetLeg, Wallet
from app.models.enums import ActivityType, BetStatus, GameweekStatus, Market, MatchOutcome, MatchStatus, Selection
from app.models.gameweek import Gameweek, Match
from app.models.league import League, Season
from app.services import gamification, notifications, rankings
from app.services.activity import record_activity
from app.services.odds_providers import get_odds_provider


def _leg_outcome(leg: BetLeg, match: Match) -> BetStatus:
    """Returns WON, LOST or VOID for one leg of a (possibly single-leg)
    bet, judged strictly against the match's actual final score — never
    against the odds it was placed at."""
    if match.status != MatchStatus.FINISHED or match.result is None:
        return BetStatus.VOID

    home, away, result = match.home_score, match.away_score, match.result

    if leg.market == Market.WINNER:
        won = (
            (leg.selection == Selection.HOME and result == MatchOutcome.HOME)
            or (leg.selection == Selection.DRAW and result == MatchOutcome.DRAW)
            or (leg.selection == Selection.AWAY and result == MatchOutcome.AWAY)
        )
        return BetStatus.WON if won else BetStatus.LOST

    if leg.market == Market.DOUBLE_CHANCE:
        won = (
            (leg.selection == Selection.HOME_OR_DRAW and result in (MatchOutcome.HOME, MatchOutcome.DRAW))
            or (leg.selection == Selection.AWAY_OR_DRAW and result in (MatchOutcome.AWAY, MatchOutcome.DRAW))
            or (leg.selection == Selection.HOME_OR_AWAY and result != MatchOutcome.DRAW)
        )
        return BetStatus.WON if won else BetStatus.LOST

    if leg.market == Market.OVER_UNDER:
        total_goals = home + away
        line = float(leg.line) if leg.line is not None else 2.5
        if total_goals == line:
            return BetStatus.VOID
        won = (leg.selection == Selection.OVER and total_goals > line) or (
            leg.selection == Selection.UNDER and total_goals < line
        )
        return BetStatus.WON if won else BetStatus.LOST

    if leg.market == Market.BOTH_TEAMS_TO_SCORE:
        both_scored = home > 0 and away > 0
        won = (leg.selection == Selection.YES and both_scored) or (
            leg.selection == Selection.NO and not both_scored
        )
        return BetStatus.WON if won else BetStatus.LOST

    return BetStatus.VOID


def _settle_bet(bet: Bet, matches_by_id: dict) -> None:
    """A combination wins only if every leg wins. A void leg (its match
    was postponed/unresolved) is dropped from the price rather than
    failing the whole bet — the same "void leg, resettle the rest"
    convention real bookmakers use for accumulators."""
    effective_odds = Decimal("1")
    any_lost = False
    any_won = False

    for leg in bet.legs:
        outcome = _leg_outcome(leg, matches_by_id[leg.match_id])
        leg.status = outcome
        if outcome == BetStatus.LOST:
            any_lost = True
        elif outcome == BetStatus.WON:
            any_won = True
            effective_odds *= leg.odds_price_at_pick

    bet.settled_at = utcnow()
    if any_lost:
        bet.status = BetStatus.LOST
        bet.payout = 0
    elif any_won:
        bet.status = BetStatus.WON
        bet.payout = int((Decimal(bet.stake) * effective_odds).to_integral_value(rounding=ROUND_HALF_UP))
    else:
        # every leg void (e.g. the whole gameweek's matches were postponed)
        bet.status = BetStatus.VOID
        bet.payout = bet.stake


def sync_match_results(db: Session, gameweek: Gameweek) -> int:
    """Fetches results for matches that have kicked off but aren't marked
    FINISHED yet. Safe to call repeatedly (e.g. every few minutes)."""
    pending_matches = [
        m for m in gameweek.matches if m.status != MatchStatus.FINISHED and utcnow() >= m.kickoff_at
    ]
    if not pending_matches:
        return 0

    provider = get_odds_provider()
    results_by_id = {r.external_id: r for r in provider.fetch_results([m.external_id for m in pending_matches])}

    updated = 0
    for match in pending_matches:
        result = results_by_id.get(match.external_id)
        if result is None or result.status != MatchStatus.FINISHED:
            continue
        match.status = MatchStatus.FINISHED
        match.home_score = result.home_score
        match.away_score = result.away_score
        match.result = (
            MatchOutcome.HOME
            if result.home_score > result.away_score
            else MatchOutcome.AWAY
            if result.away_score > result.home_score
            else MatchOutcome.DRAW
        )
        updated += 1
    db.commit()
    return updated


def settle_gameweek(db: Session, gameweek: Gameweek) -> bool:
    """Returns True if the gameweek was fully settled, False if some
    matches still haven't finished (call again later)."""
    if gameweek.status == GameweekStatus.SETTLED:
        return True

    sync_match_results(db, gameweek)
    db.refresh(gameweek)

    if any(m.status != MatchStatus.FINISHED for m in gameweek.matches):
        return False

    bets = db.query(Bet).filter(Bet.gameweek_id == gameweek.id, Bet.status == BetStatus.PENDING).all()
    matches_by_id = {m.id: m for m in gameweek.matches}
    wallets = {w.user_id: w for w in db.query(Wallet).filter(Wallet.gameweek_id == gameweek.id).all()}

    for bet in bets:
        _settle_bet(bet, matches_by_id)
        wallet = wallets.get(bet.user_id)
        if wallet and bet.payout:
            wallet.current_balance += bet.payout

    gameweek.status = GameweekStatus.SETTLED
    db.commit()

    gamification.apply_gameweek_results(db, gameweek)
    from app.model_engine.live import update_ratings_for_gameweek

    update_ratings_for_gameweek(db, gameweek)
    _notify_members(db, gameweek)
    return True


def _notify_members(db: Session, gameweek: Gameweek) -> None:
    season = db.get(Season, gameweek.season_id)
    league = db.get(League, season.league_id)
    ranking = rankings.gameweek_ranking(db, league, gameweek)

    if ranking:
        winner = ranking[0]
        record_activity(
            db,
            league_id=league.id,
            user_id=winner.user.id,
            type=ActivityType.GAMEWEEK_SETTLED,
            data={
                "gameweek_id": str(gameweek.id),
                "gameweek_name": gameweek.name,
                "net_change": winner.net_change,
                "top3": [
                    {"name": row.user.name, "net_change": row.net_change} for row in ranking[:3]
                ],
            },
        )
        db.commit()

    for row in ranking:
        sign = "+" if row.net_change >= 0 else ""
        notifications.create_notification(
            db,
            user_id=row.user.id,
            league_id=league.id,
            type="gameweek_settled",
            title=f"{gameweek.name} terminada",
            body=f"Terminaste #{row.position} con {sign}{row.net_change} créditos.",
            data={
                "league_id": str(league.id),
                "gameweek_id": str(gameweek.id),
                "position": row.position,
                "net_change": row.net_change,
            },
        )
