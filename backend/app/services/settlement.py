"""Turns raw match results into settled predictions, updated wallets, and
(via `services.gamification`) badges/streaks/XP. This is the one place in
the app where "did this pick win" is decided — see `_prediction_outcome`.
"""

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.enums import GameweekStatus, Market, MatchOutcome, MatchStatus, PredictionStatus, Selection
from app.models.gameweek import Gameweek, Match
from app.models.league import League, Season
from app.models.prediction import Prediction, Wallet
from app.services import gamification, notifications, rankings
from app.services.odds_providers import get_odds_provider


def _prediction_outcome(prediction: Prediction, match: Match) -> PredictionStatus:
    """Returns WON, LOST or VOID for one settled (FINISHED) match."""
    if match.status != MatchStatus.FINISHED or match.result is None:
        return PredictionStatus.VOID

    home, away, result = match.home_score, match.away_score, match.result

    if prediction.market == Market.WINNER:
        won = (
            (prediction.selection == Selection.HOME and result == MatchOutcome.HOME)
            or (prediction.selection == Selection.DRAW and result == MatchOutcome.DRAW)
            or (prediction.selection == Selection.AWAY and result == MatchOutcome.AWAY)
        )
        return PredictionStatus.WON if won else PredictionStatus.LOST

    if prediction.market == Market.DOUBLE_CHANCE:
        won = (
            (prediction.selection == Selection.HOME_OR_DRAW and result in (MatchOutcome.HOME, MatchOutcome.DRAW))
            or (prediction.selection == Selection.AWAY_OR_DRAW and result in (MatchOutcome.AWAY, MatchOutcome.DRAW))
            or (prediction.selection == Selection.HOME_OR_AWAY and result != MatchOutcome.DRAW)
        )
        return PredictionStatus.WON if won else PredictionStatus.LOST

    if prediction.market == Market.OVER_UNDER:
        total_goals = home + away
        line = float(prediction.line) if prediction.line is not None else 2.5
        if total_goals == line:
            return PredictionStatus.VOID
        won = (prediction.selection == Selection.OVER and total_goals > line) or (
            prediction.selection == Selection.UNDER and total_goals < line
        )
        return PredictionStatus.WON if won else PredictionStatus.LOST

    if prediction.market == Market.BOTH_TEAMS_TO_SCORE:
        both_scored = home > 0 and away > 0
        won = (prediction.selection == Selection.YES and both_scored) or (
            prediction.selection == Selection.NO and not both_scored
        )
        return PredictionStatus.WON if won else PredictionStatus.LOST

    return PredictionStatus.VOID


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

    predictions = db.query(Prediction).filter(Prediction.gameweek_id == gameweek.id).all()
    matches_by_id = {m.id: m for m in gameweek.matches}
    wallets = {
        w.user_id: w for w in db.query(Wallet).filter(Wallet.gameweek_id == gameweek.id).all()
    }

    for prediction in predictions:
        if prediction.status != PredictionStatus.PENDING:
            continue
        match = matches_by_id[prediction.match_id]
        outcome = _prediction_outcome(prediction, match)
        prediction.status = outcome
        prediction.settled_at = utcnow()

        wallet = wallets.get(prediction.user_id)
        if outcome == PredictionStatus.WON:
            prediction.payout = prediction.potential_payout
            if wallet:
                wallet.current_balance += prediction.payout
        elif outcome == PredictionStatus.VOID:
            prediction.payout = prediction.stake
            if wallet:
                wallet.current_balance += prediction.stake
        else:
            prediction.payout = 0

    gameweek.status = GameweekStatus.SETTLED
    db.commit()

    gamification.apply_gameweek_results(db, gameweek)
    _notify_members(db, gameweek)
    return True


def _notify_members(db: Session, gameweek: Gameweek) -> None:
    season = db.get(Season, gameweek.season_id)
    league = db.get(League, season.league_id)
    ranking = rankings.gameweek_ranking(db, league, gameweek)

    for row in ranking:
        sign = "+" if row.net_change >= 0 else ""
        notifications.create_notification(
            db,
            user_id=row.user.id,
            league_id=league.id,
            type="gameweek_settled",
            title=f"{gameweek.name} terminada",
            body=f"Terminaste #{row.position} con {sign}{row.net_change} créditos.",
            data={"gameweek_id": str(gameweek.id), "position": row.position, "net_change": row.net_change},
        )
