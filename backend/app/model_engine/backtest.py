"""Walk-forward validation — the only way a model earns a place in
production here (see docs/ARCHITECTURE.md#model-engine). Every prediction
scored below was made using *only* data strictly before that match's
date: Elo updates one match at a time in chronological order, and the
batch models (Poisson, Dixon-Coles, logistic regression, gradient
boosting) are refit periodically on an expanding window that never
includes the matches they're about to be scored on.

`docs/DATA_SOURCES.md` explains the data; `docs/ARCHITECTURE.md` explains
why this file's output (not intuition) is what picks the shipped model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.model_engine.elo import EloRatingSystem
from app.model_engine.features import build_features
from app.model_engine.metrics import summarize
from app.model_engine.ml_models import GradientBoostingModel, LogisticRegressionModel
from app.model_engine.poisson_models import DixonColesModel, PoissonModel

REFIT_EVERY_DAYS = 120
BURN_IN_MATCHES = 400  # roughly a season+ of the smallest leagues, before anything is scored


@dataclass
class BacktestResult:
    league: str
    model_name: str
    metrics: dict
    n_matches_evaluated: int


def attach_walk_forward_elo(matches: pd.DataFrame) -> tuple[pd.DataFrame, EloRatingSystem]:
    """Runs Elo across the whole league history once, recording each
    match's PRE-match ratings — this is the shared, leak-free feature both
    the Elo model and the ML models are scored/trained against. Returns
    the enriched frame AND the final rating system (its end state is what
    seeds the live, continuously-updating ratings — see
    `app/model_engine/live.py` and `scripts/train_models.py`)."""
    elo = EloRatingSystem()
    home_pre, away_pre, elo_home_probs, elo_draw_probs, elo_away_probs = [], [], [], [], []

    for row in matches.itertuples():
        home_pre.append(elo.get(row.HomeTeam))
        away_pre.append(elo.get(row.AwayTeam))
        h, d, a = elo.match_probabilities(row.HomeTeam, row.AwayTeam)
        elo_home_probs.append(h)
        elo_draw_probs.append(d)
        elo_away_probs.append(a)
        elo.update(row.HomeTeam, row.AwayTeam, row.FTHome, row.FTAway)

    out = matches.copy()
    out["home_elo_pre"] = home_pre
    out["away_elo_pre"] = away_pre
    out["elo_home_prob"] = elo_home_probs
    out["elo_draw_prob"] = elo_draw_probs
    out["elo_away_prob"] = elo_away_probs
    return out, elo


def _refit_points(dates: pd.Series, start_date) -> list:
    points = []
    current = start_date
    end = dates.max()
    while current <= end:
        points.append(current)
        current = current + pd.Timedelta(days=REFIT_EVERY_DAYS)
    return points


def _predict_batch_model(model, rows: pd.DataFrame) -> np.ndarray:
    probs = []
    for row in rows.itertuples():
        result = model.match_probabilities(row.HomeTeam, row.AwayTeam)
        probs.append(result if result is not None else (1 / 3, 1 / 3, 1 / 3))
    return np.array(probs)


def _predict_ml_model(model, rows: pd.DataFrame) -> np.ndarray:
    feats = build_features(rows)
    probs = [model.predict_proba_row(feats.iloc[i].to_dict()) for i in range(len(rows))]
    return np.array(probs)


def run_league_backtest(matches: pd.DataFrame, league: str) -> tuple[list[BacktestResult], pd.DataFrame]:
    """Returns (results per model incl. the market baseline, the enriched
    per-match frame used — handy for debugging/inspection)."""
    enriched, _final_elo = attach_walk_forward_elo(matches)
    if len(enriched) <= BURN_IN_MATCHES:
        return [], enriched

    eval_frame = enriched.iloc[BURN_IN_MATCHES:].reset_index(drop=True)
    labels = eval_frame["result_code"].to_numpy()

    results: list[BacktestResult] = []

    # --- Elo: already walk-forward by construction, just read it off ---
    elo_probs = eval_frame[["elo_home_prob", "elo_draw_prob", "elo_away_prob"]].to_numpy()
    results.append(BacktestResult(league, "elo", summarize(elo_probs, labels), len(labels)))

    # --- Market baseline (de-vigged bookmaker odds) — not a model we
    # ship, but the benchmark every model is judged against ---
    market_probs = eval_frame[["market_home_prob", "market_draw_prob", "market_away_prob"]].to_numpy()
    results.append(BacktestResult(league, "market", summarize(market_probs, labels), len(labels)))

    # --- Periodically-refit models ---
    refit_dates = _refit_points(enriched["MatchDate"], enriched["MatchDate"].iloc[BURN_IN_MATCHES])

    model_specs = {
        "poisson": PoissonModel,
        "dixon_coles": DixonColesModel,
        "logistic_regression": LogisticRegressionModel,
        "gradient_boosting": GradientBoostingModel,
    }
    predictions_by_model: dict[str, list[np.ndarray]] = {name: [] for name in model_specs}
    covered_mask = np.zeros(len(eval_frame), dtype=bool)

    for i, refit_date in enumerate(refit_dates):
        window_end = refit_dates[i + 1] if i + 1 < len(refit_dates) else enriched["MatchDate"].max() + pd.Timedelta(
            days=1
        )
        train_df = enriched[enriched["MatchDate"] < refit_date]
        window_mask = (eval_frame["MatchDate"] >= refit_date) & (eval_frame["MatchDate"] < window_end)
        window_rows = eval_frame[window_mask]
        if window_rows.empty or len(train_df) < 40:
            continue
        covered_mask |= window_mask.to_numpy()

        for name, factory in model_specs.items():
            model = factory()
            if name in ("poisson", "dixon_coles"):
                model.fit(train_df, as_of=refit_date)
                preds = _predict_batch_model(model, window_rows)
            else:
                feats = build_features(train_df)
                model.fit(feats, train_df["result_code"])
                preds = _predict_ml_model(model, window_rows)
            predictions_by_model[name].append((window_rows.index.to_numpy(), preds))

    for name, chunks in predictions_by_model.items():
        if not chunks:
            continue
        all_idx = np.concatenate([idx for idx, _ in chunks])
        all_preds = np.concatenate([p for _, p in chunks], axis=0)
        order = np.argsort(all_idx)
        aligned_preds = all_preds[order]
        aligned_labels = eval_frame.loc[all_idx[order], "result_code"].to_numpy()
        results.append(BacktestResult(league, name, summarize(aligned_preds, aligned_labels), len(aligned_labels)))

    return results, enriched
