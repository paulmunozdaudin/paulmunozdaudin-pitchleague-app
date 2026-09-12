from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.gameweek import Match


@dataclass
class InsightContext:
    """Everything an insight provider is allowed to talk about — all of it
    computed upstream by the Model Engine / odds data, never by the
    provider itself. This is the enforcement point for "la IA no debe
    inventar información": a provider (heuristic or LLM) only ever
    receives real numbers and turns them into words."""

    match: Match
    model_home_prob: float
    model_draw_prob: float
    model_away_prob: float
    model_source: str
    market_home_prob: float | None
    market_draw_prob: float | None
    market_away_prob: float | None


class AIInsightProvider(ABC):
    name: str

    @abstractmethod
    def generate_match_insight(self, context: InsightContext) -> str:
        """A short, neutral paragraph phrasing `context`'s real numbers —
        never a pick or a recommendation, and never a number that isn't in
        `context`. The user always decides alone."""
