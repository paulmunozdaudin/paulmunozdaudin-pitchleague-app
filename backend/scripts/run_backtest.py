"""Runs the full walk-forward backtest for every league and prints/saves a
report. Usage: python -m scripts.run_backtest [DIVISION_CODE]
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.model_engine.backtest import run_league_backtest  # noqa: E402
from app.model_engine.data import LEAGUES, load_matches, matches_for_league  # noqa: E402

REPORT_PATH = Path(__file__).resolve().parents[1] / "data" / "models" / "backtest_report.json"


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    df = load_matches()
    report = {}

    for division in LEAGUES if only is None else [only]:
        league_matches = matches_for_league(df, division)
        print(f"== {division} ({LEAGUES[division]}) — {len(league_matches)} matches ==", flush=True)
        start = time.time()
        results, _ = run_league_backtest(league_matches, division)
        elapsed = time.time() - start
        print(f"   done in {elapsed:.1f}s, {len(results)} models scored")

        report[division] = {}
        for r in sorted(results, key=lambda x: x.metrics.get("log_loss", 99)):
            print(
                f"   {r.model_name:20s} n={r.n_matches_evaluated:5d}  "
                f"log_loss={r.metrics['log_loss']:.4f}  brier={r.metrics['brier_score']:.4f}  "
                f"acc={r.metrics['accuracy']:.4f}"
            )
            report[division][r.model_name] = r.metrics

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"\nSaved report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
