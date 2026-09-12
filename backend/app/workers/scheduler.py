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

from app.db.base import utcnow
from app.db.session import SessionLocal
from app.models.enums import GameweekStatus
from app.models.gameweek import Gameweek
from app.models.ops import FailedJob
from app.services import gameweeks as gameweeks_service
from app.services import settlement as settlement_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pitchleague.worker")


def _record_failure(db, job_name: str, reference: str | None, error: Exception) -> None:
    logger.exception("%s failed", job_name)
    try:
        db.rollback()  # the failed job may have left the session in a bad transaction state
        db.add(FailedJob(job_name=job_name, reference=reference, error_message=str(error), occurred_at=utcnow()))
        db.commit()
    except Exception:  # noqa: BLE001 — recording the failure must never itself crash the tick
        logger.exception("Additionally failed to record the failure for %s", job_name)
        db.rollback()


def tick() -> None:
    db = SessionLocal()
    try:
        gameweeks_service.lock_expired_gameweeks(db)

        try:
            gameweeks_service.send_deadline_reminders(db)
        except Exception as exc:  # noqa: BLE001 — a reminder failure shouldn't stop the tick
            _record_failure(db, "send_deadline_reminders", None, exc)

        for gameweek in db.query(Gameweek).filter(Gameweek.status == GameweekStatus.OPEN).all():
            try:
                gameweeks_service.refresh_odds(db, gameweek)
            except Exception as exc:  # noqa: BLE001 — one league's odds failure shouldn't stop the tick
                _record_failure(db, "refresh_odds", str(gameweek.id), exc)

        for gameweek in db.query(Gameweek).filter(Gameweek.status == GameweekStatus.LOCKED).all():
            try:
                settled = settlement_service.settle_gameweek(db, gameweek)
                if settled:
                    logger.info("Settled gameweek %s", gameweek.id)
            except Exception as exc:  # noqa: BLE001
                _record_failure(db, "settle_gameweek", str(gameweek.id), exc)
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
