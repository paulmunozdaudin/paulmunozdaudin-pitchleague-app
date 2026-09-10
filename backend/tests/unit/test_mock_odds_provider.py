from app.models.enums import Market, MatchStatus, Selection
from app.services.odds_providers.mock import MockOddsProvider


def test_fetch_upcoming_matches_is_deterministic():
    a = MockOddsProvider(day_bucket="2025-06-01").fetch_upcoming_matches(limit=5)
    b = MockOddsProvider(day_bucket="2025-06-01").fetch_upcoming_matches(limit=5)

    assert [m.external_id for m in a] == [m.external_id for m in b]
    for match_a, match_b in zip(a, b):
        prices_a = {(q.market, q.selection): q.price for q in match_a.odds}
        prices_b = {(q.market, q.selection): q.price for q in match_b.odds}
        assert prices_a == prices_b


def test_upcoming_matches_carry_all_mvp_markets():
    matches = MockOddsProvider(day_bucket="2025-06-01").fetch_upcoming_matches(limit=1)
    markets = {q.market for q in matches[0].odds}
    assert markets == {Market.WINNER, Market.DOUBLE_CHANCE, Market.OVER_UNDER, Market.BOTH_TEAMS_TO_SCORE}


def test_winner_prices_have_bookmaker_overround():
    matches = MockOddsProvider(day_bucket="2025-06-01").fetch_upcoming_matches(limit=1)
    winner_quotes = [q for q in matches[0].odds if q.market == Market.WINNER]
    implied_sum = sum(1 / q.price for q in winner_quotes)
    assert implied_sum > 1  # overround: the book always shaves a margin


def test_fetch_results_is_deterministic_and_reproducible():
    provider = MockOddsProvider(day_bucket="2025-06-01")
    matches = provider.fetch_upcoming_matches(limit=3)
    external_ids = [m.external_id for m in matches]

    results_a = provider.fetch_results(external_ids)
    results_b = MockOddsProvider(day_bucket="2025-06-01").fetch_results(external_ids)

    assert [(r.external_id, r.home_score, r.away_score) for r in results_a] == [
        (r.external_id, r.home_score, r.away_score) for r in results_b
    ]
    assert all(r.status == MatchStatus.FINISHED for r in results_a)


def test_fetch_results_unknown_id_is_postponed():
    provider = MockOddsProvider(day_bucket="2025-06-01")
    [result] = provider.fetch_results(["not-a-real-id"])
    assert result.status == MatchStatus.POSTPONED
