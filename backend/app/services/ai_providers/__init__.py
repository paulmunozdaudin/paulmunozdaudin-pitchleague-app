import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.model_engine.engine import ModelPrediction, predict_match
from app.models.enums import Market, Selection
from app.models.gameweek import Match
from app.services.ai_providers.base import AIInsightProvider, InsightContext
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


def _market_probabilities(match: Match) -> tuple[float, float, float] | None:
    """De-vigged 1X2 market probabilities from the match's own current
    odds — the same "remove the bookmaker's margin" method used to build
    the training data (see docs/DATA_SOURCES.md), so it's directly
    comparable to the model's output."""
    winner_odds = {q.selection: q.price for q in match.current_odds() if q.market == Market.WINNER}
    home, draw, away = winner_odds.get(Selection.HOME), winner_odds.get(Selection.DRAW), winner_odds.get(Selection.AWAY)
    if not (home and draw and away):
        return None
    inv_home, inv_draw, inv_away = Decimal(1) / home, Decimal(1) / draw, Decimal(1) / away
    total = inv_home + inv_draw + inv_away
    return float(inv_home / total), float(inv_draw / total), float(inv_away / total)


def get_model_prediction(db: Session, match: Match) -> ModelPrediction:
    market_probs = _market_probabilities(match)
    return predict_match(db, match.competition, match.home_team, match.away_team, market_probs)


def generate_match_insight(db: Session, match: Match) -> tuple[str, str, ModelPrediction]:
    """Returns (text, text_provider_name, prediction). `prediction` is the
    Model Engine's real output; the provider (heuristic or LLM) only ever
    turns those numbers into prose, so it structurally cannot invent a
    statistic that isn't in `prediction`."""
    prediction = get_model_prediction(db, match)
    market_probs = _market_probabilities(match)
    context = InsightContext(
        match=match,
        model_home_prob=prediction.home_prob,
        model_draw_prob=prediction.draw_prob,
        model_away_prob=prediction.away_prob,
        model_source=prediction.source,
        market_home_prob=market_probs[0] if market_probs else None,
        market_draw_prob=market_probs[1] if market_probs else None,
        market_away_prob=market_probs[2] if market_probs else None,
    )

    try:
        provider = _get_provider()
        return provider.generate_match_insight(context), provider.name, prediction
    except Exception:  # noqa: BLE001 — any provider failure falls back
        logger.exception("AI insight provider failed, falling back to heuristic")
        return _heuristic.generate_match_insight(context), "heuristic_fallback", prediction
