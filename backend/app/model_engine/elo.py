"""Our own Elo rating system — not the `HomeElo`/`AwayElo` columns already
in the dataset (those are ClubElo's, kept only as a reference feature).
This is a from-scratch, online-updating implementation: ratings only ever
use results *before* the match being rated, which is what makes it safe to
run in production as new real gameweeks settle (see
`update_ratings_from_settlement` wiring in `app/services/settlement.py`).

Method: standard logistic Elo (the same family used by FIDE chess and
eloratings.net's World Football Elo), with a home-advantage offset and a
goal-difference multiplier on the K-factor — a well-established refinement
(bigger wins move ratings more than 1-0 squeakers).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

INITIAL_RATING = 1500.0
HOME_ADVANTAGE = 65.0  # rating points added to the home side's effective strength
BASE_K = 24.0


def _goal_diff_multiplier(goal_diff: int) -> float:
    """Bigger wins shift ratings more, but with diminishing returns —
    Elo World Football's well-known adjustment."""
    diff = abs(goal_diff)
    if diff <= 1:
        return 1.0
    if diff == 2:
        return 1.5
    return (11 + diff) / 8


@dataclass
class EloRatingSystem:
    ratings: dict[str, float] = field(default_factory=dict)
    k: float = BASE_K
    home_advantage: float = HOME_ADVANTAGE

    def get(self, team: str) -> float:
        return self.ratings.get(team, INITIAL_RATING)

    def expected_home_score(self, home: str, away: str) -> float:
        """Elo's expected-score function — a value in (0, 1), NOT a 1X2
        probability (there's no draw in classic Elo). `match_probabilities`
        below turns this into a real 3-way distribution."""
        diff = (self.get(home) + self.home_advantage) - self.get(away)
        return 1.0 / (1.0 + 10 ** (-diff / 400))

    def match_probabilities(self, home: str, away: str) -> tuple[float, float, float]:
        """Maps the Elo expected-score onto (home, draw, away) using a
        draw band calibrated on the training set (see `fit_draw_width`) —
        the closer the two expected scores, the likelier a draw."""
        expected = self.expected_home_score(home, away)
        draw_prob = self._draw_probability(expected)
        remaining = 1.0 - draw_prob
        home_prob = remaining * expected
        away_prob = remaining * (1.0 - expected)
        return home_prob, draw_prob, away_prob

    def _draw_probability(self, expected_home: float) -> float:
        # Draws are most likely at 50/50 and taper off towards the
        # extremes — a symmetric peak, width set by `draw_peak`/`draw_width`
        # (fit once on training data in `calibrate_draw_curve`, not a
        # hand-picked constant).
        centered = expected_home - 0.5
        return max(0.05, self.draw_peak - self.draw_width * (centered**2))

    draw_peak: float = 0.28
    draw_width: float = 0.6

    def update(self, home: str, away: str, home_goals: int, away_goals: int) -> None:
        """Call once, after the match is known, in chronological order."""
        expected = self.expected_home_score(home, away)
        actual = 1.0 if home_goals > away_goals else 0.0 if home_goals < away_goals else 0.5
        shift = self.k * _goal_diff_multiplier(home_goals - away_goals) * (actual - expected)
        self.ratings[home] = self.get(home) + shift
        self.ratings[away] = self.get(away) - shift

    def clone(self) -> "EloRatingSystem":
        return EloRatingSystem(
            ratings=dict(self.ratings), k=self.k, home_advantage=self.home_advantage,
            draw_peak=self.draw_peak, draw_width=self.draw_width,
        )
