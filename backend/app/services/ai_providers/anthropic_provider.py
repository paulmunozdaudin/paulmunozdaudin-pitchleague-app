from app.core.config import get_settings
from app.models.enums import Market
from app.models.gameweek import Match
from app.services.ai_providers.base import AIInsightProvider

SYSTEM_PROMPT = (
    "Eres un analista de datos deportivos. Con el contexto de un partido de fútbol y sus cuotas de "
    "mercado, escribe un único párrafo breve (máximo 3 frases) y neutral sobre forma, contexto y cuotas. "
    "Nunca recomiendes una selección ni digas qué apostar — solo aporta contexto objetivo. Responde en "
    "español, sin markdown."
)


class AnthropicInsightProvider(AIInsightProvider):
    name = "anthropic"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set — required when AI_INSIGHTS_PROVIDER=anthropic")

        import anthropic

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def generate_match_insight(self, match: Match) -> str:
        odds_lines = [
            f"{q.market.value}/{q.selection.value}{f' ({q.line})' if q.line else ''}: {q.price}"
            for q in match.current_odds()
        ]
        user_prompt = (
            f"Partido: {match.home_team} vs {match.away_team} ({match.competition}).\n"
            f"Cuotas actuales:\n" + "\n".join(odds_lines)
        )

        response = self._client.messages.create(
            model="claude-sonnet-5",
            max_tokens=220,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()
