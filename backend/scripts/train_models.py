"""Trains and registers the production Model Engine from the latest
backtest report. Run `python -m scripts.run_backtest` first (it writes
data/models/backtest_report.json), then:

    python -m scripts.train_models
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.model_engine.registry import train_and_register_all  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        versions = train_and_register_all(db)
        for v in versions:
            print(f"{v.division}: shipped {v.model_name} (version {v.id}, trained {v.trained_at})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
