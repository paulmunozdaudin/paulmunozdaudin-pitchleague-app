from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPKMixin


class ModelVersion(UUIDPKMixin, Base):
    """One row per (division, trained_at) — the Model Engine's own audit
    trail. `metrics` holds the full backtest summary (log loss, Brier
    score, accuracy, calibration) that justified shipping this version;
    see app/model_engine/backtest.py. Never edited by hand — only
    `app/model_engine/registry.py` writes these."""

    __tablename__ = "model_versions"

    division: Mapped[str] = mapped_column(String(10), index=True)
    model_name: Mapped[str] = mapped_column(String(40))
    trained_at: Mapped[datetime]
    artifact_path: Mapped[str] = mapped_column(String(255))
    metrics: Mapped[dict] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class TeamRating(UUIDPKMixin, Base):
    """Live, continuously-updating Elo state — seeded from the walk-forward
    backtest's final ratings, then advanced one real match at a time as
    this app's own gameweeks settle (`app/model_engine/live.py`). This is
    what keeps the Elo model "real" in production instead of frozen at
    whatever the training snapshot happened to end on."""

    __tablename__ = "team_ratings"

    division: Mapped[str] = mapped_column(String(10), index=True)
    team: Mapped[str] = mapped_column(String(120))
    rating: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime]

    __table_args__ = (UniqueConstraint("division", "team", name="uq_team_rating_division_team"),)
