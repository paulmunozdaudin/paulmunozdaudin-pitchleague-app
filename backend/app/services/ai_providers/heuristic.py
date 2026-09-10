"""Zero-config fallback: no API key needed, and it's what runs when the
Anthropic provider is unset or a call fails. Derives a plausible-sounding
but fully deterministic "form" narrative from the match's own odds skew and
a hash of the team names — same trick as the mock odds provider — so
insights are stable and don't require calling out to any real stats
source for the MVP.
"""

import hashlib
import random

from app.models.enums import Market, Selection
from app.models.gameweek import Match
from app.services.ai_providers.base import AIInsightProvider


def _rng(*parts: str) -> random.Random:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


FORM_PHRASES = ["en un gran momento de forma", "con altibajos en las últimas jornadas", "invicto en las últimas semanas", "recuperándose tras un tramo irregular"]
XG_PHRASES = ["un xG superior al de su rival", "números de xG muy parejos con el rival", "un xG algo por debajo de su rival"]
CONTEXT_PHRASES = ["Llega motivado tras una buena racha como local.", "El calendario reciente ha sido exigente.", "Sin bajas relevantes de cara a este partido.", "Recupera a una pieza importante para este encuentro."]


class HeuristicInsightProvider(AIInsightProvider):
    name = "heuristic"

    def generate_match_insight(self, match: Match) -> str:
        rng = _rng("insight", match.home_team, match.away_team, str(match.id))

        winner_odds = {q.selection: q.price for q in match.current_odds() if q.market == Market.WINNER}
        home_price, away_price = winner_odds.get(Selection.HOME), winner_odds.get(Selection.AWAY)

        favorite = None
        if home_price and away_price:
            favorite = match.home_team if home_price < away_price else match.away_team

        sentence = (
            f"{match.home_team} llega {rng.choice(FORM_PHRASES)} y con {rng.choice(XG_PHRASES)} "
            f"en las últimas jornadas frente al {match.away_team}. {rng.choice(CONTEXT_PHRASES)}"
        )
        if favorite:
            sentence += f" El mercado sitúa a {favorite} como ligero favorito."
        return sentence
