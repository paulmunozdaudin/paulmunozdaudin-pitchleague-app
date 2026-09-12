from decimal import Decimal
from types import SimpleNamespace

from app.models.enums import BetStatus, Market, MatchOutcome, MatchStatus, Selection
from app.services.settlement import _leg_outcome, _settle_bet


def _match(home=2, away=1, status=MatchStatus.FINISHED, result=MatchOutcome.HOME):
    return SimpleNamespace(status=status, home_score=home, away_score=away, result=result)


def _leg(market, selection, line=None, status=BetStatus.PENDING, odds="2.00"):
    return SimpleNamespace(market=market, selection=selection, line=line, status=status, odds_price_at_pick=Decimal(odds))


def test_winner_home_win():
    match = _match(2, 1, result=MatchOutcome.HOME)
    leg = _leg(Market.WINNER, Selection.HOME)
    assert _leg_outcome(leg, match) == BetStatus.WON


def test_winner_wrong_pick_loses():
    match = _match(2, 1, result=MatchOutcome.HOME)
    leg = _leg(Market.WINNER, Selection.AWAY)
    assert _leg_outcome(leg, match) == BetStatus.LOST


def test_double_chance_home_or_draw_wins_on_draw():
    match = _match(1, 1, result=MatchOutcome.DRAW)
    leg = _leg(Market.DOUBLE_CHANCE, Selection.HOME_OR_DRAW)
    assert _leg_outcome(leg, match) == BetStatus.WON


def test_double_chance_home_or_away_loses_on_draw():
    match = _match(1, 1, result=MatchOutcome.DRAW)
    leg = _leg(Market.DOUBLE_CHANCE, Selection.HOME_OR_AWAY)
    assert _leg_outcome(leg, match) == BetStatus.LOST


def test_over_under_over_wins():
    match = _match(2, 2, result=MatchOutcome.DRAW)  # 4 total goals
    leg = _leg(Market.OVER_UNDER, Selection.OVER, Decimal("2.5"))
    assert _leg_outcome(leg, match) == BetStatus.WON


def test_over_under_under_wins():
    match = _match(1, 0, result=MatchOutcome.HOME)  # 1 total goal
    leg = _leg(Market.OVER_UNDER, Selection.UNDER, Decimal("2.5"))
    assert _leg_outcome(leg, match) == BetStatus.WON


def test_over_under_push_is_void():
    match = _match(2, 1, result=MatchOutcome.HOME)  # 3 total goals
    leg = _leg(Market.OVER_UNDER, Selection.OVER, Decimal("3"))
    assert _leg_outcome(leg, match) == BetStatus.VOID


def test_btts_yes_wins_when_both_score():
    match = _match(1, 1, result=MatchOutcome.DRAW)
    leg = _leg(Market.BOTH_TEAMS_TO_SCORE, Selection.YES)
    assert _leg_outcome(leg, match) == BetStatus.WON


def test_btts_no_wins_when_one_team_blanks():
    match = _match(2, 0, result=MatchOutcome.HOME)
    leg = _leg(Market.BOTH_TEAMS_TO_SCORE, Selection.NO)
    assert _leg_outcome(leg, match) == BetStatus.WON


def test_unfinished_match_is_void():
    match = _match(status=MatchStatus.SCHEDULED, result=None)
    leg = _leg(Market.WINNER, Selection.HOME)
    assert _leg_outcome(leg, match) == BetStatus.VOID


# --- Combination (multi-leg) settlement ---


def _bet(stake, legs):
    return SimpleNamespace(stake=stake, legs=legs, status=None, payout=None, settled_at=None)


def test_combo_wins_only_if_every_leg_wins():
    match_a = _match(2, 0, result=MatchOutcome.HOME)
    match_b = _match(1, 1, result=MatchOutcome.DRAW)
    leg_a = _leg(Market.WINNER, Selection.HOME, odds="2.00")  # wins
    leg_a.match_id = "a"
    leg_b = _leg(Market.WINNER, Selection.HOME, odds="1.50")  # loses (real result is a draw)
    leg_b.match_id = "b"
    bet = _bet(1000, [leg_a, leg_b])

    _settle_bet(bet, {"a": match_a, "b": match_b})

    assert leg_a.status == BetStatus.WON
    assert leg_b.status == BetStatus.LOST
    assert bet.status == BetStatus.LOST
    assert bet.payout == 0


def test_combo_all_legs_win_pays_combined_odds():
    match_a = _match(2, 0, result=MatchOutcome.HOME)
    match_b = _match(0, 1, result=MatchOutcome.AWAY)
    leg_a = _leg(Market.WINNER, Selection.HOME, odds="2.00")
    leg_a.match_id = "a"
    leg_b = _leg(Market.WINNER, Selection.AWAY, odds="1.50")
    leg_b.match_id = "b"
    bet = _bet(1000, [leg_a, leg_b])

    _settle_bet(bet, {"a": match_a, "b": match_b})

    assert leg_a.status == BetStatus.WON and leg_b.status == BetStatus.WON
    assert bet.status == BetStatus.WON
    assert bet.payout == 3000  # 1000 * 2.00 * 1.50


def test_combo_void_leg_is_excluded_from_price_not_the_whole_bet():
    match_a = _match(2, 0, result=MatchOutcome.HOME)
    match_b = _match(status=MatchStatus.SCHEDULED, result=None)  # unresolved -> void
    leg_a = _leg(Market.WINNER, Selection.HOME, odds="2.00")
    leg_a.match_id = "a"
    leg_b = _leg(Market.WINNER, Selection.AWAY, odds="1.80")
    leg_b.match_id = "b"
    bet = _bet(1000, [leg_a, leg_b])

    _settle_bet(bet, {"a": match_a, "b": match_b})

    assert leg_a.status == BetStatus.WON
    assert leg_b.status == BetStatus.VOID
    assert bet.status == BetStatus.WON
    assert bet.payout == 2000  # void leg's odds excluded — just 1000 * 2.00


def test_combo_all_legs_void_refunds_stake():
    match_a = _match(status=MatchStatus.SCHEDULED, result=None)
    match_b = _match(status=MatchStatus.SCHEDULED, result=None)
    leg_a = _leg(Market.WINNER, Selection.HOME)
    leg_a.match_id = "a"
    leg_b = _leg(Market.WINNER, Selection.AWAY)
    leg_b.match_id = "b"
    bet = _bet(1000, [leg_a, leg_b])

    _settle_bet(bet, {"a": match_a, "b": match_b})

    assert bet.status == BetStatus.VOID
    assert bet.payout == 1000
