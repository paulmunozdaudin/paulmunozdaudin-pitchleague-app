"""Real odds via The Odds API (https://the-odds-api.com).

See docs/ARCHITECTURE.md#adr-001-odds-provider for why this provider was
chosen over Betfair Exchange, Pinnacle, OddsAPI.io and sportsdataio: it's
the best fit for an MVP — a plain REST JSON API (no FIX/exchange protocol
to integrate), a free tier (500 requests/month) that's enough for a handful
of private leagues syncing once or twice a day, per-request pricing beyond
that with no minimum commit, and it already aggregates dozens of
bookmakers across soccer's major leagues so we're not tied to one book.

Requires THE_ODDS_API_KEY. Two market caveats worth knowing:
- "Double chance" isn't a market this API sells directly, so we derive it
  from the 1X2 (h2h) probabilities ourselves (see `_derive_double_chance`)
  — same technique the mock provider uses, just fed real prices.
- "Both teams to score" (`btts`) coverage varies by competition/bookmaker;
  when no bookmaker offers it for a given match we simply omit that market
  rather than fabricate a price.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

import httpx

from app.core.config import get_settings
from app.models.enums import Market, MatchStatus, Selection
from app.services.odds_providers.base import MatchResult, OddsProvider, OddsQuote, UpcomingMatch

DEFAULT_SPORT_KEYS = [
    "soccer_spain_la_liga",
    "soccer_epl",
    "soccer_uefa_champs_league",
    "soccer_italy_serie_a",
]

_H2H_TO_SELECTION = {"home": Selection.HOME, "draw": Selection.DRAW, "away": Selection.AWAY}


def _avg_price(prices: list[Decimal]) -> Decimal | None:
    if not prices:
        return None
    return (sum(prices) / len(prices)).quantize(Decimal("0.01"))


def _derive_double_chance(home_price: Decimal, draw_price: Decimal, away_price: Decimal) -> list[OddsQuote]:
    """1/price ≈ implied probability; combine two outcomes' probabilities
    and re-price, carrying the market's own overround through instead of
    inventing a new margin."""
    p_home, p_draw, p_away = 1 / home_price, 1 / draw_price, 1 / away_price
    quotes = []
    for selection, combined in (
        (Selection.HOME_OR_DRAW, p_home + p_draw),
        (Selection.AWAY_OR_DRAW, p_away + p_draw),
        (Selection.HOME_OR_AWAY, p_home + p_away),
    ):
        if combined > 0:
            quotes.append(OddsQuote(Market.DOUBLE_CHANCE, selection, (1 / combined).quantize(Decimal("0.01"))))
    return quotes


class TheOddsApiProvider(OddsProvider):
    name = "the_odds_api"

    def __init__(self, sport_keys: list[str] | None = None):
        settings = get_settings()
        if not settings.the_odds_api_key:
            raise RuntimeError("THE_ODDS_API_KEY is not set — required when ODDS_PROVIDER=the_odds_api")
        self.api_key = settings.the_odds_api_key
        self.base_url = settings.the_odds_api_base_url.rstrip("/")
        self.sport_keys = sport_keys or DEFAULT_SPORT_KEYS

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=10.0)

    def fetch_upcoming_matches(self, limit: int = 10) -> list[UpcomingMatch]:
        matches: list[UpcomingMatch] = []
        with self._client() as client:
            for sport_key in self.sport_keys:
                if len(matches) >= limit:
                    break
                resp = client.get(
                    f"/sports/{sport_key}/odds",
                    params={
                        "apiKey": self.api_key,
                        "regions": "eu,uk",
                        "markets": "h2h,totals,btts",
                        "oddsFormat": "decimal",
                    },
                )
                resp.raise_for_status()
                for event in resp.json():
                    matches.append(self._parse_event(event, sport_key))
        return matches[:limit]

    def _parse_event(self, event: dict, sport_key: str) -> UpcomingMatch:
        h2h_prices: dict[Selection, list[Decimal]] = {s: [] for s in _H2H_TO_SELECTION.values()}
        totals_prices: dict[tuple[Selection, Decimal], list[Decimal]] = {}
        btts_prices: dict[Selection, list[Decimal]] = {Selection.YES: [], Selection.NO: []}

        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    try:
                        price = Decimal(str(outcome["price"]))
                    except (InvalidOperation, KeyError):
                        continue

                    if market["key"] == "h2h":
                        name = outcome["name"]
                        if name == event["home_team"]:
                            h2h_prices[Selection.HOME].append(price)
                        elif name == event["away_team"]:
                            h2h_prices[Selection.AWAY].append(price)
                        elif name.lower() == "draw":
                            h2h_prices[Selection.DRAW].append(price)
                    elif market["key"] == "totals" and "point" in outcome:
                        line = Decimal(str(outcome["point"]))
                        selection = Selection.OVER if outcome["name"].lower() == "over" else Selection.UNDER
                        totals_prices.setdefault((selection, line), []).append(price)
                    elif market["key"] == "btts":
                        selection = Selection.YES if outcome["name"].lower() == "yes" else Selection.NO
                        btts_prices[selection].append(price)

        odds: list[OddsQuote] = []
        home_avg, draw_avg, away_avg = (
            _avg_price(h2h_prices[Selection.HOME]),
            _avg_price(h2h_prices[Selection.DRAW]),
            _avg_price(h2h_prices[Selection.AWAY]),
        )
        if home_avg and draw_avg and away_avg:
            odds += [
                OddsQuote(Market.WINNER, Selection.HOME, home_avg),
                OddsQuote(Market.WINNER, Selection.DRAW, draw_avg),
                OddsQuote(Market.WINNER, Selection.AWAY, away_avg),
            ]
            odds += _derive_double_chance(home_avg, draw_avg, away_avg)

        for (selection, line), prices in totals_prices.items():
            avg = _avg_price(prices)
            if avg:
                odds.append(OddsQuote(Market.OVER_UNDER, selection, avg, line))

        yes_avg, no_avg = _avg_price(btts_prices[Selection.YES]), _avg_price(btts_prices[Selection.NO])
        if yes_avg and no_avg:
            odds += [
                OddsQuote(Market.BOTH_TEAMS_TO_SCORE, Selection.YES, yes_avg),
                OddsQuote(Market.BOTH_TEAMS_TO_SCORE, Selection.NO, no_avg),
            ]

        return UpcomingMatch(
            external_id=event["id"],
            competition=sport_key,
            home_team=event["home_team"],
            away_team=event["away_team"],
            # Stored naive-UTC, consistent with every other datetime in the
            # app (see app.db.base.utcnow).
            kickoff_at=datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00")).replace(tzinfo=None),
            odds=odds,
        )

    def fetch_results(self, external_ids: list[str]) -> list[MatchResult]:
        if not external_ids:
            return []
        results: dict[str, MatchResult] = {}
        with self._client() as client:
            for sport_key in self.sport_keys:
                resp = client.get(
                    f"/sports/{sport_key}/scores",
                    params={"apiKey": self.api_key, "daysFrom": 3},
                )
                resp.raise_for_status()
                for event in resp.json():
                    if event["id"] not in external_ids or event["id"] in results:
                        continue
                    if not event.get("completed"):
                        continue
                    scores = {s["name"]: s["score"] for s in event.get("scores") or []}
                    home_score, away_score = scores.get(event["home_team"]), scores.get(event["away_team"])
                    if home_score is None or away_score is None:
                        continue
                    results[event["id"]] = MatchResult(
                        external_id=event["id"],
                        status=MatchStatus.FINISHED,
                        home_score=int(home_score),
                        away_score=int(away_score),
                    )
        return list(results.values())
