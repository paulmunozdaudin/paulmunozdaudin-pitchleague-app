"""Deterministic, zero-config odds provider used in local dev and tests.

Nothing here is random in the "changes every call" sense — every price and
every simulated result is a pure function of (team names, day bucket), so
running the sync job twice on the same day reproduces the same fixtures and
settling a gameweek is fully reproducible in tests. That determinism is the
whole point: it lets the rest of the app (settlement, gamification, the
frontend demo) be exercised end-to-end with no API key and no flakiness.
"""

import hashlib
import math
import random
from datetime import timedelta
from decimal import Decimal

from app.db.base import utcnow
from app.models.enums import Market, MatchStatus, Selection
from app.services.odds_providers.base import MatchResult, OddsProvider, OddsQuote, UpcomingMatch

COMPETITIONS: dict[str, list[str]] = {
    "La Liga": [
        "Real Madrid", "Barcelona", "Atlético de Madrid", "Real Sociedad",
        "Athletic Club", "Real Betis", "Villarreal", "Sevilla",
    ],
    "Premier League": [
        "Manchester City", "Arsenal", "Liverpool", "Chelsea",
        "Manchester United", "Tottenham Hotspur",
    ],
    "Serie A": ["Inter de Milán", "Juventus", "AC Milan", "Napoli"],
    "Bundesliga": ["Bayern Munich", "Dortmund", "RB Leipzig", "Leverkusen"],
    "Ligue 1": ["Paris SG", "Marseille", "Lyon", "Monaco"],
}

_SLUG_TO_NAME = {name.lower().replace(" ", "-"): name for names in COMPETITIONS.values() for name in names}

WINNER_MARGIN = Decimal("1.07")
SECONDARY_MARGIN = Decimal("1.12")


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def _rng(*parts: str) -> random.Random:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _team_strength(name: str) -> float:
    return _rng("strength", name).uniform(0.8, 1.5)


def _match_probabilities(home: str, away: str) -> tuple[float, float, float, float, float]:
    """Returns (p_home, p_draw, p_away, xg_home, xg_away)."""
    home_strength = _team_strength(home) * 1.15  # home advantage
    away_strength = _team_strength(away)
    total = home_strength + away_strength

    p_home_raw = home_strength / total
    p_away_raw = away_strength / total
    closeness = 1 - abs(p_home_raw - p_away_raw)
    p_draw = 0.20 + 0.15 * closeness
    remaining = 1 - p_draw
    p_home = p_home_raw * remaining
    p_away = p_away_raw * remaining

    xg_home = home_strength * 1.3
    xg_away = away_strength * 1.1
    return p_home, p_draw, p_away, xg_home, xg_away


def _price(prob: float, margin: Decimal = WINNER_MARGIN) -> Decimal:
    prob = min(max(prob, 0.02), 0.97)
    raw = Decimal(str(1 / prob)) / margin
    return max(raw.quantize(Decimal("0.01")), Decimal("1.01"))


def _build_odds(home: str, away: str) -> list[OddsQuote]:
    p_home, p_draw, p_away, xg_home, xg_away = _match_probabilities(home, away)

    quotes = [
        OddsQuote(Market.WINNER, Selection.HOME, _price(p_home)),
        OddsQuote(Market.WINNER, Selection.DRAW, _price(p_draw)),
        OddsQuote(Market.WINNER, Selection.AWAY, _price(p_away)),
        OddsQuote(Market.DOUBLE_CHANCE, Selection.HOME_OR_DRAW, _price(p_home + p_draw, SECONDARY_MARGIN)),
        OddsQuote(Market.DOUBLE_CHANCE, Selection.AWAY_OR_DRAW, _price(p_away + p_draw, SECONDARY_MARGIN)),
        OddsQuote(Market.DOUBLE_CHANCE, Selection.HOME_OR_AWAY, _price(p_home + p_away, SECONDARY_MARGIN)),
    ]

    total_xg = xg_home + xg_away
    p_over = 1 / (1 + math.exp(-(total_xg - 2.5) * 1.3))
    p_over = min(max(p_over, 0.25), 0.85)
    quotes.append(OddsQuote(Market.OVER_UNDER, Selection.OVER, _price(p_over, SECONDARY_MARGIN), Decimal("2.5")))
    quotes.append(
        OddsQuote(Market.OVER_UNDER, Selection.UNDER, _price(1 - p_over, SECONDARY_MARGIN), Decimal("2.5"))
    )

    p_btts = min(max(0.30 + 0.25 * min(xg_home, xg_away), 0.35), 0.75)
    quotes.append(OddsQuote(Market.BOTH_TEAMS_TO_SCORE, Selection.YES, _price(p_btts, SECONDARY_MARGIN)))
    quotes.append(OddsQuote(Market.BOTH_TEAMS_TO_SCORE, Selection.NO, _price(1 - p_btts, SECONDARY_MARGIN)))

    return quotes


def _poisson(rng: random.Random, lam: float) -> int:
    limit = math.exp(-lam)
    k, p = 0, 1.0
    while p > limit:
        k += 1
        p *= rng.random()
    return min(k - 1, 6)


class MockOddsProvider(OddsProvider):
    name = "mock"

    def __init__(self, day_bucket: str | None = None):
        # Overridable for tests; defaults to "today" so the same fixtures
        # keep coming back across a single day's requests.
        self.day_bucket = day_bucket or utcnow().strftime("%Y-%m-%d")

    def fetch_upcoming_matches(self, limit: int = 10) -> list[UpcomingMatch]:
        pairings: list[tuple[str, str, str]] = []
        for competition, teams in COMPETITIONS.items():
            shuffled = teams[:]
            _rng("shuffle", competition, self.day_bucket).shuffle(shuffled)
            for i in range(0, len(shuffled) - 1, 2):
                pairings.append((competition, shuffled[i], shuffled[i + 1]))

        pairings = pairings[:limit]
        now = utcnow()
        kickoff_base = now.replace(minute=0, second=0, microsecond=0) + timedelta(
            days=2, hours=(14 - now.hour) % 24
        )

        matches = []
        for idx, (competition, home, away) in enumerate(pairings):
            kickoff_at = kickoff_base + timedelta(hours=2.5 * idx)
            external_id = f"mock:{_slug(home)}:{_slug(away)}:{self.day_bucket}"
            matches.append(
                UpcomingMatch(
                    external_id=external_id,
                    competition=competition,
                    home_team=home,
                    away_team=away,
                    kickoff_at=kickoff_at,
                    odds=_build_odds(home, away),
                )
            )
        return matches

    def fetch_results(self, external_ids: list[str]) -> list[MatchResult]:
        results = []
        for external_id in external_ids:
            try:
                _, home_slug, away_slug, day_bucket = external_id.split(":")
                home, away = _SLUG_TO_NAME[home_slug], _SLUG_TO_NAME[away_slug]
            except (ValueError, KeyError):
                results.append(MatchResult(external_id=external_id, status=MatchStatus.POSTPONED))
                continue

            _, _, _, xg_home, xg_away = _match_probabilities(home, away)
            rng = _rng("result", home, away, day_bucket)
            home_score = _poisson(rng, xg_home)
            away_score = _poisson(rng, xg_away)
            results.append(
                MatchResult(
                    external_id=external_id,
                    status=MatchStatus.FINISHED,
                    home_score=home_score,
                    away_score=away_score,
                )
            )
        return results
