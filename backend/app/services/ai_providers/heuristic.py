"""Zero-config fallback: no API key needed, and it's what runs when the
Anthropic provider is unset or a call fails. Unlike the product's first
draft, this does NOT invent form/xG narrative — it only phrases the real
numbers handed to it in `InsightContext` (the Model Engine's own
probabilities, and the market's for comparison). If those numbers all a
provider has, that's a feature: it structurally can't say anything that
didn't come from real data.
"""

from app.services.ai_providers.base import AIInsightProvider, InsightContext

FAVORITE_TEMPLATES = [
    "Nuestro modelo ({source}) da a {favorite} un {prob}% de opciones de ganar este partido.",
]
CLOSE_TEMPLATE = "Nuestro modelo ({source}) ve este partido muy igualado: {home}% / {draw}% / {away}%."
AGREEMENT_TEMPLATE = " El mercado opina lo mismo — cuotas alineadas con el modelo."
DISAGREEMENT_TEMPLATE = " El mercado difiere algo: le da a {favorite} un {market_prob}%."


class HeuristicInsightProvider(AIInsightProvider):
    name = "heuristic"

    def generate_match_insight(self, context: InsightContext) -> str:
        home_pct = round(context.model_home_prob * 100)
        draw_pct = round(context.model_draw_prob * 100)
        away_pct = round(context.model_away_prob * 100)

        probs = {"home": home_pct, "draw": draw_pct, "away": away_pct}
        top_side = max(probs, key=probs.get)

        if probs[top_side] - draw_pct < 8:
            sentence = CLOSE_TEMPLATE.format(source=context.model_source, home=home_pct, draw=draw_pct, away=away_pct)
        else:
            favorite = context.match.home_team if top_side == "home" else context.match.away_team
            sentence = FAVORITE_TEMPLATES[0].format(source=context.model_source, favorite=favorite, prob=probs[top_side])

        if context.market_home_prob is not None:
            market_probs = {
                "home": round(context.market_home_prob * 100),
                "draw": round(context.market_draw_prob * 100),
                "away": round(context.market_away_prob * 100),
            }
            if abs(market_probs[top_side] - probs[top_side]) <= 5:
                sentence += AGREEMENT_TEMPLATE
            else:
                market_favorite_side = max(market_probs, key=market_probs.get)
                market_favorite = (
                    context.match.home_team if market_favorite_side == "home" else context.match.away_team
                )
                sentence += DISAGREEMENT_TEMPLATE.format(
                    favorite=market_favorite, market_prob=market_probs[market_favorite_side]
                )

        return sentence
