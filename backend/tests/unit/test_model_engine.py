"""Correctness + leakage tests for the Model Engine. The leakage test is
the important one: it proves a later match's result cannot influence an
earlier match's pre-match rating, by checking that truncating the dataset
after any given match leaves every earlier prediction byte-for-byte
identical.
"""

import pandas as pd
import pytest

from app.model_engine.backtest import attach_walk_forward_elo
from app.model_engine.elo import EloRatingSystem
from app.model_engine.features import build_features


def _match_frame(rows: list[tuple[str, str, str, int, int]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"MatchDate": pd.Timestamp(date), "HomeTeam": home, "AwayTeam": away, "FTHome": hg, "FTAway": ag}
            for date, home, away, hg, ag in rows
        ]
    )


def test_elo_new_teams_start_at_default_rating():
    elo = EloRatingSystem()
    assert elo.get("Unknown FC") == 1500.0


def test_elo_winner_gains_rating_loser_loses_it():
    elo = EloRatingSystem()
    before_home, before_away = elo.get("A"), elo.get("B")
    elo.update("A", "B", home_goals=2, away_goals=0)
    assert elo.get("A") > before_home
    assert elo.get("B") < before_away


def test_elo_zero_sum():
    """Elo is a zero-sum system — one side's gain is exactly the other's loss."""
    elo = EloRatingSystem()
    elo.update("A", "B", home_goals=1, away_goals=0)
    assert (elo.get("A") - 1500.0) == pytest.approx(-(elo.get("B") - 1500.0))


def test_walk_forward_pre_match_rating_reflects_only_earlier_results():
    matches = _match_frame(
        [
            ("2020-01-01", "A", "B", 3, 0),  # A beats B big
            ("2020-01-08", "A", "C", 1, 1),  # A's rating pre-match should already reflect the win over B
            ("2020-01-15", "B", "C", 0, 0),
        ]
    )
    enriched, _final = attach_walk_forward_elo(matches)

    # Before any match, everyone is at the default.
    assert enriched.loc[0, "home_elo_pre"] == 1500.0
    assert enriched.loc[0, "away_elo_pre"] == 1500.0
    # A's rating going into match 2 must be ABOVE default — it already won match 1.
    assert enriched.loc[1, "home_elo_pre"] > 1500.0


def test_no_leakage_truncating_future_matches_does_not_change_past_predictions():
    full = _match_frame(
        [
            ("2020-01-01", "A", "B", 3, 0),
            ("2020-01-08", "A", "C", 1, 1),
            ("2020-01-15", "B", "C", 0, 4),
        ]
    )
    truncated = full.iloc[:2].copy()  # drop the last match entirely

    enriched_full, _ = attach_walk_forward_elo(full)
    enriched_truncated, _ = attach_walk_forward_elo(truncated)

    # The first two matches' pre-match ratings must be identical whether or
    # not a later match ever happened — that's the leakage guarantee.
    for col in ("home_elo_pre", "away_elo_pre", "elo_home_prob", "elo_draw_prob", "elo_away_prob"):
        assert list(enriched_full[col].iloc[:2]) == list(enriched_truncated[col])


def test_build_features_only_uses_pre_match_columns():
    frame = pd.DataFrame(
        [{"home_elo_pre": 1600.0, "away_elo_pre": 1500.0, "Form5Home": 10, "Form5Away": 5, "Form3Home": 6, "Form3Away": 3}]
    )
    features = build_features(frame)
    assert set(features.columns) == {"elo_diff", "form5_diff", "form3_diff"}
    assert features.iloc[0]["elo_diff"] > 0  # home team rated higher pre-match
