"""Bridges the display names `services.odds_providers.mock` (and, for the
same clubs, a real odds API) uses to the exact spellings the historical
dataset uses — football-data.co.uk's convention abbreviates a lot of names
("Ath Madrid" for Atlético de Madrid, "Sociedad" for Real Sociedad). This
is a real data-integration problem, not a rounding error: without it the
Model Engine would silently treat "Real Sociedad" as a team it has never
seen and fall back to the no-history default for every single match.

Only the clubs the mock provider actually uses need an entry — anything
else already matches by construction (see the competition definitions in
`mock.py`, chosen from the dataset's own spellings for exactly this
reason).
"""

COMPETITION_TO_DIVISION = {
    "La Liga": "SP1",
    "Premier League": "E0",
    "Serie A": "I1",
    "Bundesliga": "D1",
    "Ligue 1": "F1",
}

TEAM_NAME_TO_DATASET_NAME = {
    "Atlético de Madrid": "Ath Madrid",
    "Real Sociedad": "Sociedad",
    "Athletic Club": "Ath Bilbao",
    "Real Betis": "Betis",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Tottenham Hotspur": "Tottenham",
    "Inter de Milán": "Inter",
    "AC Milan": "Milan",
}


def to_dataset_name(display_name: str) -> str:
    return TEAM_NAME_TO_DATASET_NAME.get(display_name, display_name)
