"""Standalone worker process — the thing that makes settlement "automatic"
in production instead of requiring an admin to click "Liquidar jornada".

Run it as a separate process/container alongside the API:

    python -m app.workers.scheduler

Every tick it:
  1. Locks any OPEN gameweek whose first kickoff has passed.
  2. Refreshes odds for still-OPEN gameweeks (price movement before lock).
  3. Attempts to settle every LOCKED gameweek — settlement itself only
     completes once every match in it has a final result, so this is safe
     to call repeatedly; it's a no-op until the last match finishes.

No new business logic lives here — it only calls the same services the API
routers call, on a timer instead of a button press.
"""

import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.models.enums import GameweekStatus
from app.models.gameweek import Gameweek
from app.services import gameweeks as gameweeks_service
from app.services import settlement as settlement_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pitchleague.worker")


def tick() -> None:
    db = SessionLocal()
    try:
        gameweeks_service.lock_expired_gameweeks(db)

        for gameweek in db.query(Gameweek).filter(Gameweek.status == GameweekStatus.OPEN).all():
            try:
                gameweeks_service.refresh_odds(db, gameweek)
            except Exception:  # noqa: BLE001 — one league's odds failure shouldn't stop the tick
                logger.exception("Failed to refresh odds for gameweek %s", gameweek.id)

        for gameweek in db.query(Gameweek).filter(Gameweek.status == GameweekStatus.LOCKED).all():
            try:
                settled = settlement_service.settle_gameweek(db, gameweek)
                if settled:
                    logger.info("Settled gameweek %s", gameweek.id)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to settle gameweek %s", gameweek.id)
    finally:
        db.close()


def main() -> None:
    scheduler = BackgroundScheduler()
    scheduler.add_job(tick, "interval", minutes=5, next_run_time=None)
    scheduler.start()
    logger.info("PitchLeague worker started — ticking every 5 minutes")
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    main()
