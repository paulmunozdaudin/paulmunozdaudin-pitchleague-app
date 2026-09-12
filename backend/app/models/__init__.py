"""All ORM models, imported here so Alembic's autogenerate and
`Base.metadata.create_all` (used by the test suite) see the full schema."""

from app.db.base import Base
from app.models.activity import LeagueActivity
from app.models.bet import Bet, BetLeg, Wallet
from app.models.gameweek import Gameweek, Match, OddsSnapshot
from app.models.gamification import Badge, Challenge, UserBadge, UserChallenge, UserStreak, UserXP
from app.models.league import League, LeagueMembership, Season
from app.models.model_registry import ModelVersion, TeamRating
from app.models.notification import Notification
from app.models.ops import FailedJob
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
    "Bet",
    "BetLeg",
    "Wallet",
    "Badge",
    "UserBadge",
    "UserStreak",
    "UserXP",
    "Challenge",
    "UserChallenge",
    "Notification",
    "ModelVersion",
    "TeamRating",
    "LeagueActivity",
    "FailedJob",
]
