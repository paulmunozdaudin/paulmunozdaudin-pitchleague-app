from abc import ABC, abstractmethod

from app.models.gameweek import Match


class AIInsightProvider(ABC):
    name: str

    @abstractmethod
    def generate_match_insight(self, match: Match) -> str:
        """A short, neutral paragraph of context (form, odds skew) — never
        a pick or a recommendation. The user always decides alone."""
