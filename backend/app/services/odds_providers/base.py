from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.models.enums import Market, MatchStatus, Selection


@dataclass
class OddsQuote:
    market: Market
    selection: Selection
    price: Decimal
    line: Decimal | None = None


@dataclass
class UpcomingMatch:
    external_id: str
    competition: str
    home_team: str
    away_team: str
    kickoff_at: datetime
    odds: list[OddsQuote] = field(default_factory=list)


@dataclass
class MatchResult:
    external_id: str
    status: MatchStatus
    home_score: int | None = None
    away_score: int | None = None


class OddsProvider(ABC):
    """Every odds source (mock or real) implements this. Nothing above this
    layer — the sync job, settlement engine, API routers — knows or cares
    which one is active. See docs/ARCHITECTURE.md#adr-001-odds-provider."""

    name: str

    @abstractmethod
    def fetch_upcoming_matches(self, limit: int = 10) -> list[UpcomingMatch]:
        """Matches for the next gameweek, each already carrying a full set
        of market quotes (winner, double chance, over/under, BTTS)."""

    @abstractmethod
    def fetch_results(self, external_ids: list[str]) -> list[MatchResult]:
        """Final scores for matches that should have finished by now."""
