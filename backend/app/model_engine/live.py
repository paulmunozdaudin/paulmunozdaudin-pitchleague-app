"""Keeps `TeamRating` moving forward as this app's own gameweeks settle —
without this, the Elo model (and the elo_diff feature every other model
uses) would be frozen at whatever the last training run happened to see,
which drifts further from reality every week. Only Elo updates online like
this; the batch models (Poisson, Dixon-Coles, logistic regression,
gradient boosting) need a full refit to incorporate new results — that's
`scripts/train_models.py`, meant to be re-run periodically (see
docs/DATA_SOURCES.md#refresh-strategy), not on every settlement.
"""

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.model_engine.elo import EloRatingSystem
from app.model_engine.team_aliases import COMPETITION_TO_DIVISION, to_dataset_name
from app.models.enums import MatchStatus
from app.models.gameweek import Gameweek
from app.models.model_registry import TeamRating


def update_ratings_for_gameweek(db: Session, gameweek: Gameweek) -> int:
    updated = 0
    now = utcnow()

    for match in gameweek.matches:
        if match.status != MatchStatus.FINISHED or match.home_score is None:
            continue
        division = COMPETITION_TO_DIVISION.get(match.competition)
        if division is None:
            continue

        home_ds, away_ds = to_dataset_name(match.home_team), to_dataset_name(match.away_team)
        home_row = db.query(TeamRating).filter(TeamRating.division == division, TeamRating.team == home_ds).first()
        away_row = db.query(TeamRating).filter(TeamRating.division == division, TeamRating.team == away_ds).first()

        elo = EloRatingSystem(
            ratings={
                home_ds: home_row.rating if home_row else 1500.0,
                away_ds: away_row.rating if away_row else 1500.0,
            }
        )
        elo.update(home_ds, away_ds, match.home_score, match.away_score)

        if home_row:
            home_row.rating, home_row.updated_at = elo.get(home_ds), now
        else:
            db.add(TeamRating(division=division, team=home_ds, rating=elo.get(home_ds), updated_at=now))
        if away_row:
            away_row.rating, away_row.updated_at = elo.get(away_ds), now
        else:
            db.add(TeamRating(division=division, team=away_ds, rating=elo.get(away_ds), updated_at=now))
        updated += 1

    db.commit()
    return updated
