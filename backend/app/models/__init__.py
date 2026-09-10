"""All ORM models, imported here so Alembic's autogenerate and
`Base.metadata.create_all` (used by the test suite) see the full schema."""

from app.db.base import Base
from app.models.gameweek import Gameweek, Match, OddsSnapshot
from app.models.gamification import Badge, Challenge, UserBadge, UserChallenge, UserStreak, UserXP
from app.models.league import League, LeagueMembership, Season
from app.models.notification import Notification
from app.models.prediction import Prediction, Wallet
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "League",
    "LeagueMembership",
    "Season",
    "Gameweek",
    "Match",
    "OddsSnapshot",
    "Prediction",
    "Wallet",
    "Badge",
    "UserBadge",
    "UserStreak",
    "UserXP",
    "Challenge",
    "UserChallenge",
    "Notification",
]
