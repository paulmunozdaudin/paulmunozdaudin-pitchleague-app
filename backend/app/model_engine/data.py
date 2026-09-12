"""Loads the historical dataset described in docs/DATA_SOURCES.md.

Every column here is either pre-match state (Elo, form) or the final
result — never an in-match/post-match statistic. That's not an
implementation detail, it's the leakage boundary; see
`tests/model_engine/test_no_leakage.py`.
"""

from pathlib import Path

import pandas as pd

DEFAULT_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "historical_matches.csv"

LEAGUES = {
    "E0": "premier_league",
    "SP1": "la_liga",
    "I1": "serie_a",
    "D1": "bundesliga",
    "F1": "ligue_1",
}

RESULT_CODES = {"H": 0, "D": 1, "A": 2}  # home win / draw / away win — a fixed, shared label order


def load_matches(path: Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Returns one row per match, sorted chronologically within each
    division. Columns: Division, MatchDate (datetime64), HomeTeam,
    AwayTeam, HomeElo, AwayElo, Form3Home, Form5Home, Form3Away, Form5Away,
    FTHome, FTAway, FTResult, result_code, OddHome, OddDraw, OddAway,
    Over25, Under25, market_home_prob, market_draw_prob, market_away_prob.
    """
    df = pd.read_csv(path)
    df["MatchDate"] = pd.to_datetime(df["MatchDate"])
    df["result_code"] = df["FTResult"].map(RESULT_CODES)
    df = df.dropna(subset=["result_code"]).copy()
    df["result_code"] = df["result_code"].astype(int)

    # De-vig the market's own odds (remove the bookmaker's overround) so
    # "the market" is a fair probability baseline to backtest our models
    # against, not one inflated by margin. Simple proportional method.
    inv_home, inv_draw, inv_away = 1 / df["OddHome"], 1 / df["OddDraw"], 1 / df["OddAway"]
    overround = inv_home + inv_draw + inv_away
    df["market_home_prob"] = inv_home / overround
    df["market_draw_prob"] = inv_draw / overround
    df["market_away_prob"] = inv_away / overround

    return df.sort_values(["Division", "MatchDate"]).reset_index(drop=True)


def matches_for_league(df: pd.DataFrame, division: str) -> pd.DataFrame:
    return df[df["Division"] == division].sort_values("MatchDate").reset_index(drop=True)
