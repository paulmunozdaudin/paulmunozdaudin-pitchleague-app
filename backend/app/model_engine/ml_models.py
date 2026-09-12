"""Feature-based classifiers — a thin, common wrapper around scikit-learn
so `backtest.py` can treat them exactly like the Elo/Poisson models
(`.fit(...)` / `.match_probabilities_from_features(...)`).

Gradient boosting here is scikit-learn's `HistGradientBoostingClassifier`
rather than XGBoost/LightGBM: same algorithm family (histogram-based
gradient-boosted trees), no extra native-library dependency to get working
in a sandboxed build, and it's explicitly the option named as "cuando
proceda" in the brief. Swapping in XGBoost later is a drop-in change if a
production run wants it — same `.fit`/`.predict_proba` interface.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from app.model_engine.features import FEATURE_COLUMNS, build_features


class _SklearnMatchModel:
    name = "base"
    estimator_factory = None

    def __init__(self) -> None:
        self.model = self.estimator_factory()

    def fit(self, feature_frame: pd.DataFrame, labels: pd.Series) -> None:
        self.model.fit(feature_frame[FEATURE_COLUMNS].to_numpy(), labels.to_numpy())

    def predict_proba_row(self, feature_row: dict) -> tuple[float, float, float]:
        x = np.array([[feature_row[c] for c in FEATURE_COLUMNS]])
        proba = self.model.predict_proba(x)[0]
        # classes_ is sorted ascending for int labels {0,1,2} = H,D,A — but
        # guard explicitly rather than assume, in case a fold is missing a class.
        by_class = dict(zip(self.model.classes_, proba))
        return by_class.get(0, 0.0), by_class.get(1, 0.0), by_class.get(2, 0.0)


class LogisticRegressionModel(_SklearnMatchModel):
    name = "logistic_regression"
    estimator_factory = staticmethod(lambda: LogisticRegression(max_iter=1000, multi_class="multinomial"))


class GradientBoostingModel(_SklearnMatchModel):
    name = "gradient_boosting"
    estimator_factory = staticmethod(
        lambda: HistGradientBoostingClassifier(max_iter=150, max_depth=3, learning_rate=0.08)
    )


def features_for_match(home_elo: float, away_elo: float, form5_home: float, form5_away: float, form3_home: float, form3_away: float) -> dict:
    row = build_features(
        pd.DataFrame(
            [
                {
                    "home_elo_pre": home_elo,
                    "away_elo_pre": away_elo,
                    "Form5Home": form5_home,
                    "Form5Away": form5_away,
                    "Form3Home": form3_home,
                    "Form3Away": form3_away,
                }
            ]
        )
    ).iloc[0]
    return row.to_dict()
