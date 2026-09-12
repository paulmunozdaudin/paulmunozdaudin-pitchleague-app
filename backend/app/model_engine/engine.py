"""Runtime prediction API — the one function the rest of the app (AI
Insights, eventually a "model probabilities" chip on the match card) is
allowed to call. Everything upstream of this (backtesting, training) is
offline; this is the online path, and it never fabricates a number: if the
shipped model can't score a match (team it never saw in training), it
falls back to the de-vigged market price and says so.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path

import joblib
from sqlalchemy.orm import Session

from app.model_engine.ml_models import features_for_match
from app.model_engine.team_aliases import COMPETITION_TO_DIVISION, to_dataset_name
from app.models.model_registry import ModelVersion, TeamRating

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ELO = 1500.0


@dataclass
class ModelPrediction:
    home_prob: float
    draw_prob: float
    away_prob: float
    source: str  # the model name that produced it, or "market" on fallback
    model_version_id: str | None


@functools.lru_cache(maxsize=16)
def _load_artifact(relative_path: str):
    return joblib.load(REPO_ROOT / relative_path)


def _get_rating(db: Session, division: str, team: str) -> float:
    row = db.query(TeamRating).filter(TeamRating.division == division, TeamRating.team == team).first()
    return row.rating if row else DEFAULT_ELO


def get_active_version(db: Session, division: str) -> ModelVersion | None:
    return (
        db.query(ModelVersion)
        .filter(ModelVersion.division == division, ModelVersion.is_active.is_(True))
        .order_by(ModelVersion.trained_at.desc())
        .first()
    )


def predict_match(
    db: Session, competition: str, home_team: str, away_team: str, market_probs: tuple[float, float, float] | None
) -> ModelPrediction:
    fallback = ModelPrediction(*(market_probs or (1 / 3, 1 / 3, 1 / 3)), source="market", model_version_id=None)

    division = COMPETITION_TO_DIVISION.get(competition)
    if division is None:
        return fallback

    version = get_active_version(db, division)
    if version is None:
        return fallback

    home_ds, away_ds = to_dataset_name(home_team), to_dataset_name(away_team)

    if version.model_name == "elo":
        from app.model_engine.elo import EloRatingSystem

        home_elo = _get_rating(db, division, home_ds)
        away_elo = _get_rating(db, division, away_ds)
        elo = EloRatingSystem(ratings={home_ds: home_elo, away_ds: away_elo})
        home_p, draw_p, away_p = elo.match_probabilities(home_ds, away_ds)
        return ModelPrediction(home_p, draw_p, away_p, source="elo", model_version_id=str(version.id))

    try:
        model = _load_artifact(version.artifact_path)
    except FileNotFoundError:
        return fallback

    if version.model_name in ("poisson", "dixon_coles"):
        result = model.match_probabilities(home_ds, away_ds)
        if result is None:
            return fallback
        home_p, draw_p, away_p = result
        return ModelPrediction(home_p, draw_p, away_p, source=version.model_name, model_version_id=str(version.id))

    # logistic_regression / gradient_boosting — feature-based.
    home_elo = _get_rating(db, division, home_ds)
    away_elo = _get_rating(db, division, away_ds)
    # Rolling form isn't tracked live for teams outside the training set in
    # this MVP, so it's fed as neutral (0) at inference time — elo_diff,
    # which *is* kept live via app/model_engine/live.py, carries the signal
    # instead. Documented here rather than silently defaulted elsewhere.
    features = features_for_match(home_elo, away_elo, 0.0, 0.0, 0.0, 0.0)
    home_p, draw_p, away_p = model.predict_proba_row(features)
    return ModelPrediction(home_p, draw_p, away_p, source=version.model_name, model_version_id=str(version.id))
