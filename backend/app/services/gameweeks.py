from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.bet import Bet
from app.models.enums import GameweekStatus
from app.models.gameweek import Gameweek, Match, OddsSnapshot
from app.models.gamification import Challenge
from app.models.league import League, LeagueMembership, Season
from app.services import notifications
from app.services.odds_providers import get_odds_provider

DEADLINE_REMINDER_WINDOW = timedelta(hours=2)

DEFAULT_CHALLENGES = [
    ("five_correct", "Racha de 5", "Acierta 5 predicciones en esta jornada", 80),
    ("underdog_correct", "Caza-underdogs", "Acierta una predicción con cuota 2.0 o superior", 40),
    ("three_overs_correct", "Ofensiva total", "Acierta 3 predicciones de Over en esta jornada", 50),
]


def get_active_season(db: Session, league: League) -> Season:
    season = db.query(Season).filter(Season.league_id == league.id, Season.is_active.is_(True)).first()
    if season is None:
        raise HTTPException(status_code=500, detail="League has no active season")
    return season


def get_current_gameweek(db: Session, league: League) -> Gameweek | None:
    season = get_active_season(db, league)
    return (
        db.query(Gameweek)
        .filter(Gameweek.season_id == season.id, Gameweek.status != GameweekStatus.SETTLED)
        .order_by(Gameweek.number.desc())
        .first()
    )


def generate_next_gameweek(db: Session, league: League, match_count: int = 6) -> Gameweek:
    """Pulls fixtures + odds from the active odds provider and opens a new
    gameweek. Locking time is the earliest kickoff, matching the spec: once
    the first match of the gameweek starts, the whole slip is frozen."""
    season = get_active_season(db, league)
    existing_open = get_current_gameweek(db, league)
    if existing_open is not None:
        raise HTTPException(status_code=400, detail="There is already an open gameweek")

    provider = get_odds_provider()
    upcoming = provider.fetch_upcoming_matches(limit=match_count)
    if not upcoming:
        raise HTTPException(status_code=502, detail="Odds provider returned no upcoming matches")

    next_number = (db.query(func.max(Gameweek.number)).filter(Gameweek.season_id == season.id).scalar() or 0) + 1
    locks_at = min(m.kickoff_at for m in upcoming)

    gameweek = Gameweek(
        season_id=season.id,
        number=next_number,
        name=f"Jornada {next_number}",
        opens_at=utcnow(),
        locks_at=locks_at,
        budget=league.budget_per_gameweek,
        status=GameweekStatus.OPEN,
    )
    db.add(gameweek)
    db.flush()

    for upcoming_match in upcoming:
        match = Match(
            gameweek_id=gameweek.id,
            external_id=upcoming_match.external_id,
            competition=upcoming_match.competition,
            home_team=upcoming_match.home_team,
            away_team=upcoming_match.away_team,
            kickoff_at=upcoming_match.kickoff_at,
        )
        db.add(match)
        db.flush()
        fetched_at = utcnow()
        for quote in upcoming_match.odds:
            db.add(
                OddsSnapshot(
                    match_id=match.id,
                    market=quote.market,
                    selection=quote.selection,
                    line=quote.line,
                    price=quote.price,
                    fetched_at=fetched_at,
                    source=provider.name,
                )
            )

    for code, name, description, xp_reward in DEFAULT_CHALLENGES:
        db.add(
            Challenge(
                gameweek_id=gameweek.id, code=code, name=name, description=description, xp_reward=xp_reward
            )
        )

    db.commit()
    db.refresh(gameweek)
    return gameweek


def refresh_odds(db: Session, gameweek: Gameweek) -> int:
    """Re-fetches current prices for every not-yet-locked match and appends
    new OddsSnapshot rows (old ones are kept for history)."""
    if gameweek.status != GameweekStatus.OPEN:
        return 0

    provider = get_odds_provider()
    upcoming_by_id = {m.external_id: m for m in provider.fetch_upcoming_matches(limit=50)}

    updated = 0
    for match in gameweek.matches:
        if utcnow() >= match.kickoff_at:
            continue
        fresh = upcoming_by_id.get(match.external_id)
        if fresh is None:
            continue
        fetched_at = utcnow()
        for quote in fresh.odds:
            db.add(
                OddsSnapshot(
                    match_id=match.id,
                    market=quote.market,
                    selection=quote.selection,
                    line=quote.line,
                    price=quote.price,
                    fetched_at=fetched_at,
                    source=provider.name,
                )
            )
        updated += 1
    db.commit()
    return updated


def lock_expired_gameweeks(db: Session) -> None:
    db.query(Gameweek).filter(Gameweek.status == GameweekStatus.OPEN, Gameweek.locks_at <= utcnow()).update(
        {"status": GameweekStatus.LOCKED}
    )
    db.commit()


def send_deadline_reminders(db: Session) -> int:
    """One reminder per gameweek, to members who haven't predicted yet —
    fired once (deadline_reminder_sent) so the countdown never turns into
    spam, per the brief's "notificaciones sin spam" requirement."""
    now = utcnow()
    due = (
        db.query(Gameweek)
        .filter(
            Gameweek.status == GameweekStatus.OPEN,
            Gameweek.deadline_reminder_sent.is_(False),
            Gameweek.locks_at <= now + DEADLINE_REMINDER_WINDOW,
            Gameweek.locks_at > now,
        )
        .all()
    )
    sent = 0
    for gameweek in due:
        season = db.get(Season, gameweek.season_id)
        league = db.get(League, season.league_id)
        member_ids = {m.user_id for m in db.query(LeagueMembership).filter(LeagueMembership.league_id == league.id).all()}
        already_picked = {
            b.user_id for b in db.query(Bet).filter(Bet.gameweek_id == gameweek.id).all()
        }
        hours_left = round((gameweek.locks_at - now).total_seconds() / 3600)
        for user_id in member_ids - already_picked:
            notifications.create_notification(
                db,
                user_id=user_id,
                league_id=league.id,
                type="deadline_reminder",
                title=f"{gameweek.name} se bloquea pronto",
                body=f"Quedan {max(hours_left, 1)}h para que se bloqueen las predicciones en {league.name}. ¡Todavía no has predicho!",
                data={"league_id": str(league.id), "gameweek_id": str(gameweek.id)},
            )
            sent += 1
        gameweek.deadline_reminder_sent = True
        db.commit()
    return sent
