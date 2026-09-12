"""Feature engineering — every feature here is a value known strictly
before kickoff. `elo_diff` comes from our own walk-forward Elo state
(computed match-by-match in `backtest.py`/`registry.py`, never refit on
future data); `form*_diff` comes straight from the dataset's own rolling
pre-match form columns (see docs/DATA_SOURCES.md for why those are safe).
"""

import numpy as np
import pandas as pd

FEATURE_COLUMNS = ["elo_diff", "form5_diff", "form3_diff"]


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    """`frame` must already carry home_elo_pre/away_elo_pre (attached
    walk-forward by the caller) plus the dataset's Form3/Form5 columns."""
    out = pd.DataFrame(index=frame.index)
    out["elo_diff"] = (frame["home_elo_pre"] - frame["away_elo_pre"]) / 400.0
    out["form5_diff"] = (frame["Form5Home"] - frame["Form5Away"]) / 15.0
    out["form3_diff"] = (frame["Form3Home"] - frame["Form3Away"]) / 9.0
    return out.replace([np.inf, -np.inf], 0.0).fillna(0.0)
