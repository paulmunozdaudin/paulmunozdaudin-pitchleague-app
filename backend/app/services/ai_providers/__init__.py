import logging

from app.core.config import get_settings
from app.models.gameweek import Match
from app.services.ai_providers.base import AIInsightProvider
from app.services.ai_providers.heuristic import HeuristicInsightProvider

logger = logging.getLogger(__name__)

__all__ = ["AIInsightProvider", "generate_match_insight"]

_heuristic = HeuristicInsightProvider()


def _get_provider() -> AIInsightProvider:
    settings = get_settings()
    if settings.ai_insights_provider == "anthropic":
        from app.services.ai_providers.anthropic_provider import AnthropicInsightProvider

        return AnthropicInsightProvider()
    return _heuristic


def generate_match_insight(match: Match) -> tuple[str, str]:
    """Returns (text, provider_name_used). Always falls back to the
    heuristic provider on any error so a flaky/misconfigured LLM never
    breaks the match screen."""
    try:
        provider = _get_provider()
        return provider.generate_match_insight(match), provider.name
    except Exception:  # noqa: BLE001 — any provider failure falls back
        logger.exception("AI insight provider failed, falling back to heuristic")
        return _heuristic.generate_match_insight(match), "heuristic_fallback"
