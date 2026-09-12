"""Proper scoring rules for a 3-class probabilistic forecast — this is
what actually decides which model ships, not how "smart" one sounds.
"""

import numpy as np
from sklearn.metrics import log_loss


def brier_score(probs: np.ndarray, labels: np.ndarray) -> float:
    """Mean squared error between the predicted distribution and the
    one-hot actual outcome, summed over the 3 classes. Lower is better;
    0 is a perfect forecast, 2 is the worst possible."""
    onehot = np.eye(3)[labels]
    return float(np.mean(np.sum((probs - onehot) ** 2, axis=1)))


def log_loss_score(probs: np.ndarray, labels: np.ndarray) -> float:
    return float(log_loss(labels, probs, labels=[0, 1, 2]))


def accuracy(probs: np.ndarray, labels: np.ndarray) -> float:
    return float(np.mean(np.argmax(probs, axis=1) == labels))


def calibration_curve(probs: np.ndarray, labels: np.ndarray, outcome: int = 0, n_bins: int = 10) -> list[dict]:
    """Reliability diagram data for one outcome (default: home win): among
    matches where the model said "there's an X% chance," did it actually
    happen about X% of the time? A well-calibrated model's points sit near
    the diagonal predicted≈actual — this is what lets a probability be
    shown to a user as a real probability instead of a made-up number."""
    predicted = probs[:, outcome]
    actual = (labels == outcome).astype(float)
    bins = np.linspace(0, 1, n_bins + 1)
    bin_idx = np.clip(np.digitize(predicted, bins) - 1, 0, n_bins - 1)

    rows = []
    for b in range(n_bins):
        mask = bin_idx == b
        if not mask.any():
            continue
        rows.append(
            {
                "bin_low": round(float(bins[b]), 2),
                "bin_high": round(float(bins[b + 1]), 2),
                "predicted_mean": round(float(predicted[mask].mean()), 4),
                "actual_freq": round(float(actual[mask].mean()), 4),
                "count": int(mask.sum()),
            }
        )
    return rows


def summarize(probs: np.ndarray, labels: np.ndarray) -> dict:
    return {
        "n": int(len(labels)),
        "brier_score": round(brier_score(probs, labels), 4),
        "log_loss": round(log_loss_score(probs, labels), 4),
        "accuracy": round(accuracy(probs, labels), 4),
        "calibration_home_win": calibration_curve(probs, labels, outcome=0),
    }
