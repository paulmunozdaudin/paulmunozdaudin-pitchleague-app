from app.core.config import get_settings
from app.services.ai_providers.base import AIInsightProvider, InsightContext

SYSTEM_PROMPT = (
    "Eres un analista de datos deportivos. Se te dan las probabilidades EXACTAS que un modelo "
    "estadístico calculó para un partido de fútbol, y opcionalmente las probabilidades implícitas del "
    "mercado de cuotas. Redacta un único párrafo breve (máximo 3 frases) en español, sin markdown, que "
    "explique esas cifras en lenguaje natural. "
    "REGLAS ESTRICTAS: (1) No inventes ni menciones estadísticas, forma, lesiones, xG ni ningún dato que "
    "no se te haya dado explícitamente — solo dispones de las probabilidades del modelo y del mercado. "
    "(2) No recomiendes ninguna selección ni digas qué apostar — solo describe lo que dicen las cifras. "
    "(3) Si mencionas un porcentaje, debe ser exactamente uno de los que se te ha dado, no lo redondees "
    "de forma que cambie su significado."
)


class AnthropicInsightProvider(AIInsightProvider):
    name = "anthropic"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set — required when AI_INSIGHTS_PROVIDER=anthropic")

        import anthropic

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def generate_match_insight(self, context: InsightContext) -> str:
        match = context.match
        lines = [
            f"Partido: {match.home_team} vs {match.away_team} ({match.competition}).",
            f"Probabilidades del modelo ({context.model_source}): "
            f"{match.home_team} {context.model_home_prob:.0%}, "
            f"Empate {context.model_draw_prob:.0%}, "
            f"{match.away_team} {context.model_away_prob:.0%}.",
        ]
        if context.market_home_prob is not None:
            lines.append(
                f"Probabilidades implícitas del mercado: "
                f"{match.home_team} {context.market_home_prob:.0%}, "
                f"Empate {context.market_draw_prob:.0%}, "
                f"{match.away_team} {context.market_away_prob:.0%}."
            )

        response = self._client.messages.create(
            model="claude-sonnet-5",
            max_tokens=220,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "\n".join(lines)}],
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()
