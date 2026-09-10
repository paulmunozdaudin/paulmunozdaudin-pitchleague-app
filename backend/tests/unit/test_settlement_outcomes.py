from decimal import Decimal
from types import SimpleNamespace

from app.models.enums import Market, MatchOutcome, MatchStatus, PredictionStatus, Selection
from app.services.settlement import _prediction_outcome


def _match(home=2, away=1, status=MatchStatus.FINISHED, result=MatchOutcome.HOME):
    return SimpleNamespace(status=status, home_score=home, away_score=away, result=result)


def _prediction(market, selection, line=None):
    return SimpleNamespace(market=market, selection=selection, line=line)


def test_winner_home_win():
    match = _match(2, 1, result=MatchOutcome.HOME)
    prediction = _prediction(Market.WINNER, Selection.HOME)
    assert _prediction_outcome(prediction, match) == PredictionStatus.WON


def test_winner_wrong_pick_loses():
    match = _match(2, 1, result=MatchOutcome.HOME)
    prediction = _prediction(Market.WINNER, Selection.AWAY)
    assert _prediction_outcome(prediction, match) == PredictionStatus.LOST


def test_double_chance_home_or_draw_wins_on_draw():
    match = _match(1, 1, result=MatchOutcome.DRAW)
    prediction = _prediction(Market.DOUBLE_CHANCE, Selection.HOME_OR_DRAW)
    assert _prediction_outcome(prediction, match) == PredictionStatus.WON


def test_double_chance_home_or_away_loses_on_draw():
    match = _match(1, 1, result=MatchOutcome.DRAW)
    prediction = _prediction(Market.DOUBLE_CHANCE, Selection.HOME_OR_AWAY)
    assert _prediction_outcome(prediction, match) == PredictionStatus.LOST


def test_over_under_over_wins():
    match = _match(2, 2, result=MatchOutcome.DRAW)  # 4 total goals
    prediction = _prediction(Market.OVER_UNDER, Selection.OVER, Decimal("2.5"))
    assert _prediction_outcome(prediction, match) == PredictionStatus.WON


def test_over_under_under_wins():
    match = _match(1, 0, result=MatchOutcome.HOME)  # 1 total goal
    prediction = _prediction(Market.OVER_UNDER, Selection.UNDER, Decimal("2.5"))
    assert _prediction_outcome(prediction, match) == PredictionStatus.WON


def test_over_under_push_is_void():
    match = _match(2, 1, result=MatchOutcome.HOME)  # 3 total goals
    prediction = _prediction(Market.OVER_UNDER, Selection.OVER, Decimal("3"))
    assert _prediction_outcome(prediction, match) == PredictionStatus.VOID


def test_btts_yes_wins_when_both_score():
    match = _match(1, 1, result=MatchOutcome.DRAW)
    prediction = _prediction(Market.BOTH_TEAMS_TO_SCORE, Selection.YES)
    assert _prediction_outcome(prediction, match) == PredictionStatus.WON


def test_btts_no_wins_when_one_team_blanks():
    match = _match(2, 0, result=MatchOutcome.HOME)
    prediction = _prediction(Market.BOTH_TEAMS_TO_SCORE, Selection.NO)
    assert _prediction_outcome(prediction, match) == PredictionStatus.WON


def test_unfinished_match_is_void():
    match = _match(status=MatchStatus.SCHEDULED, result=None)
    prediction = _prediction(Market.WINNER, Selection.HOME)
    assert _prediction_outcome(prediction, match) == PredictionStatus.VOID
