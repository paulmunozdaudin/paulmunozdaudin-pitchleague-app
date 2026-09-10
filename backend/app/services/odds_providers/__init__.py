from app.core.config import get_settings
from app.services.odds_providers.base import MatchResult, OddsProvider, OddsQuote, UpcomingMatch
from app.services.odds_providers.mock import MockOddsProvider

__all__ = ["OddsProvider", "OddsQuote", "UpcomingMatch", "MatchResult", "get_odds_provider"]


def get_odds_provider() -> OddsProvider:
    settings = get_settings()
    if settings.odds_provider == "the_odds_api":
        from app.services.odds_providers.the_odds_api import TheOddsApiProvider

        return TheOddsApiProvider()
    return MockOddsProvider()
