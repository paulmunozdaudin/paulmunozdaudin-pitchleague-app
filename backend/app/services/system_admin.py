"""Read-only queries backing the platform system-admin panel — deliberately
separate from `services/leagues.py`'s per-league admin actions, since this
is the operator's cross-league view (health of the whole system), not
something a league admin can reach."""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import utcnow
from app.models.enums import GameweekStatus
from app.models.gameweek import Gameweek, Match, OddsSnapshot
from app.models.league import League
from app.models.model_registry import ModelVersion
from app.models.ops import FailedJob
from app.models.user import User
from app.services.odds_providers import get_odds_provider

ODDS_STALE_AFTER = timedelta(hours=6)


def get_overview(db: Session) -> dict:
    settings = get_settings()
    return {
        "users_count": db.query(User).count(),
        "leagues_count": db.query(League).count(),
        "matches_count": db.query(Match).count(),
        "open_gameweeks_count": db.query(Gameweek).filter(Gameweek.status == GameweekStatus.OPEN).count(),
        "odds_provider": get_odds_provider().name,
        "ai_insights_provider": settings.ai_insights_provider,
    }


def list_model_versions(db: Session) -> list[ModelVersion]:
    return db.query(ModelVersion).order_by(ModelVersion.division, ModelVersion.trained_at.desc()).all()


def odds_health(db: Session) -> list[dict]:
    now = utcnow()
    open_matches = (
        db.query(Match)
        .join(Gameweek, Gameweek.id == Match.gameweek_id)
        .filter(Gameweek.status == GameweekStatus.OPEN)
        .all()
    )

    by_competition: dict[str, list[Match]] = {}
    for match in open_matches:
        by_competition.setdefault(match.competition, []).append(match)

    rows = []
    for competition, matches in sorted(by_competition.items()):
        last_fetches = []
        stale = 0
        for match in matches:
            latest = (
                db.query(OddsSnapshot)
                .filter(OddsSnapshot.match_id == match.id)
                .order_by(OddsSnapshot.fetched_at.desc())
                .first()
            )
            if latest is None:
                stale += 1
                continue
            last_fetches.append(latest.fetched_at)
            if now - latest.fetched_at > ODDS_STALE_AFTER:
                stale += 1
        rows.append(
            {
                "competition": competition,
                "matches_open": len(matches),
                "stale_matches": stale,
                "last_fetched_at": max(last_fetches) if last_fetches else None,
            }
        )
    return rows


def list_failed_jobs(db: Session, limit: int = 50) -> list[FailedJob]:
    return db.query(FailedJob).order_by(FailedJob.occurred_at.desc()).limit(limit).all()
