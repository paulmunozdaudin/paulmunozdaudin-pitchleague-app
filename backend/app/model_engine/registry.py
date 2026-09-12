"""Turns a backtest report into a shipped model: picks the best-performing
model per league (by log loss — a proper scoring rule, not a hunch), does
one final training pass on the full historical dataset, and persists both
the artifact and a `ModelVersion` audit row. Run via
`python -m scripts.train_models` — see docs/ARCHITECTURE.md#model-engine.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.model_engine.backtest import attach_walk_forward_elo
from app.model_engine.data import load_matches, matches_for_league
from app.model_engine.features import build_features
from app.model_engine.ml_models import GradientBoostingModel, LogisticRegressionModel
from app.model_engine.poisson_models import DixonColesModel, PoissonModel
from app.models.model_registry import ModelVersion, TeamRating

MODELS_DIR = Path(__file__).resolve().parents[2] / "data" / "models"
REPORT_PATH = MODELS_DIR / "backtest_report.json"

BATCH_MODEL_FACTORIES = {
    "poisson": PoissonModel,
    "dixon_coles": DixonColesModel,
    "logistic_regression": LogisticRegressionModel,
    "gradient_boosting": GradientBoostingModel,
}


def load_backtest_report() -> dict:
    return json.loads(REPORT_PATH.read_text())


def _pick_best_model(division_metrics: dict[str, dict]) -> str:
    """Best of OUR models by log loss. `market` is excluded — it's the
    benchmark we compare against, not something we could ship as ours."""
    candidates = {name: m for name, m in division_metrics.items() if name != "market"}
    return min(candidates, key=lambda name: candidates[name]["log_loss"])


def train_and_register_division(db: Session, division: str, division_metrics: dict[str, dict]) -> ModelVersion:
    df = load_matches()
    league_matches = matches_for_league(df, division)
    enriched, final_elo = attach_walk_forward_elo(league_matches)

    best_name = _pick_best_model(division_metrics)
    trained_at = utcnow()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # The final walk-forward Elo state is saved regardless of which model
    # wins: the ML models need it to compute elo_diff at inference time,
    # and it's also what seeds the live TeamRating table below.
    elo_path = MODELS_DIR / f"{division}_elo.json"
    elo_path.write_text(json.dumps(final_elo.ratings))

    if best_name == "elo":
        # No artifact to fit/serialize — `predict_match` reads live ratings
        # straight from TeamRating (seeded below), never from a file.
        artifact_path = elo_path
    elif best_name in ("poisson", "dixon_coles"):
        model = BATCH_MODEL_FACTORIES[best_name]()
        model.fit(enriched, as_of=enriched["MatchDate"].max())
        artifact_path = MODELS_DIR / f"{division}_{best_name}.joblib"
        joblib.dump(model, artifact_path)
    else:
        model = BATCH_MODEL_FACTORIES[best_name]()
        feats = build_features(enriched)
        model.fit(feats, enriched["result_code"])
        artifact_path = MODELS_DIR / f"{division}_{best_name}.joblib"
        joblib.dump(model, artifact_path)

    db.query(ModelVersion).filter(ModelVersion.division == division, ModelVersion.is_active.is_(True)).update(
        {"is_active": False}
    )
    version = ModelVersion(
        division=division,
        model_name=best_name,
        trained_at=trained_at,
        artifact_path=str(artifact_path.relative_to(MODELS_DIR.parents[1])),
        metrics=division_metrics,
        is_active=True,
    )
    db.add(version)

    # Seed (or refresh) live ratings from this training run's final state
    # — see app/model_engine/live.py for how these move forward afterwards.
    for team, rating in final_elo.ratings.items():
        existing = db.query(TeamRating).filter(TeamRating.division == division, TeamRating.team == team).first()
        if existing:
            existing.rating = rating
            existing.updated_at = trained_at
        else:
            db.add(TeamRating(division=division, team=team, rating=rating, updated_at=trained_at))

    db.commit()
    db.refresh(version)
    return version


def train_and_register_all(db: Session) -> list[ModelVersion]:
    report = load_backtest_report()
    return [train_and_register_division(db, division, metrics) for division, metrics in report.items()]
