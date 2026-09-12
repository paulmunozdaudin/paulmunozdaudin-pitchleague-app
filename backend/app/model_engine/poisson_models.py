"""Maher's (1982) independent-Poisson goals model, and Dixon & Coles'
(1997) extension of it. Both are fit by maximum likelihood on real
historical goals — nothing here is a hand-tuned heuristic.

Maher: each team has an attack and a defense strength; the home team's
expected goals is exp(base_rate + home_advantage + attack_home -
defense_away), and symmetrically for the away team. Goals are then
independent Poisson draws — good enough to already beat naive baselines,
but it structurally over-predicts high/low-scoring draws because it
assumes home and away goals are independent, which real football data
mildly contradicts at low scores.

Dixon-Coles: same attack/defense/goal-rate model, plus (a) a small
correction factor `rho` applied to the four low-score outcomes (0-0, 1-0,
0-1, 1-1) to fix that independence assumption, and (b) exponential
time-decay weighting so a match from last month counts for more than one
from five seasons ago when fitting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

DEFAULT_TIME_DECAY_XI = 0.0018  # Dixon & Coles (1997)'s own fitted value; not re-tuned here


class PoissonModel:
    name = "poisson"

    def __init__(self) -> None:
        self.teams: list[str] = []
        self.team_index: dict[str, int] = {}
        self.attack: np.ndarray | None = None
        self.defense: np.ndarray | None = None
        self.home_adv: float = 0.0
        self.base_rate: float = 0.0

    def _weights(self, dates: pd.Series, as_of) -> np.ndarray:
        return np.ones(len(dates))

    def fit(self, matches: pd.DataFrame, as_of=None) -> None:
        teams = sorted(set(matches["HomeTeam"]) | set(matches["AwayTeam"]))
        n = len(teams)
        index = {t: i for i, t in enumerate(teams)}
        home_idx = matches["HomeTeam"].map(index).to_numpy()
        away_idx = matches["AwayTeam"].map(index).to_numpy()
        home_goals = matches["FTHome"].to_numpy(dtype=float)
        away_goals = matches["FTAway"].to_numpy(dtype=float)
        weights = self._weights(matches["MatchDate"], as_of or matches["MatchDate"].max())

        def unpack(params: np.ndarray):
            return params[:n], params[n : 2 * n], params[2 * n], params[2 * n + 1]

        def neg_log_likelihood(params: np.ndarray) -> float:
            attack, defense, home_adv, base_rate = unpack(params)
            lam_home = np.exp(base_rate + home_adv + attack[home_idx] - defense[away_idx])
            lam_away = np.exp(base_rate + attack[away_idx] - defense[home_idx])
            ll = weights * (
                home_goals * np.log(lam_home) - lam_home + away_goals * np.log(lam_away) - lam_away
            )
            # Soft identifiability constraint (attack/defense are only
            # identified up to an additive constant otherwise).
            penalty = 200.0 * (attack.mean() ** 2 + defense.mean() ** 2)
            return -ll.sum() + penalty

        x0 = np.zeros(2 * n + 2)
        x0[2 * n + 1] = float(np.log(max((home_goals.mean() + away_goals.mean()) / 2, 0.1)))
        result = minimize(neg_log_likelihood, x0, method="L-BFGS-B", options={"maxiter": 400})

        self.teams = teams
        self.team_index = index
        self.attack, self.defense, self.home_adv, self.base_rate = unpack(result.x)
        self.converged = bool(result.success)

    def expected_goals(self, home: str, away: str) -> tuple[float, float] | None:
        i, j = self.team_index.get(home), self.team_index.get(away)
        if i is None or j is None or self.attack is None:
            return None
        lam_home = float(np.exp(self.base_rate + self.home_adv + self.attack[i] - self.defense[j]))
        lam_away = float(np.exp(self.base_rate + self.attack[j] - self.defense[i]))
        return lam_home, lam_away

    def _score_grid(self, lam_home: float, lam_away: float, max_goals: int = 10) -> np.ndarray:
        home_probs = poisson.pmf(np.arange(max_goals + 1), lam_home)
        away_probs = poisson.pmf(np.arange(max_goals + 1), lam_away)
        return np.outer(home_probs, away_probs)

    def match_probabilities(self, home: str, away: str) -> tuple[float, float, float] | None:
        expected = self.expected_goals(home, away)
        if expected is None:
            return None
        grid = self._score_grid(*expected)
        return _outcome_probs_from_grid(grid)


def _outcome_probs_from_grid(grid: np.ndarray) -> tuple[float, float, float]:
    home_win = float(np.tril(grid, -1).sum())
    draw = float(np.trace(grid))
    away_win = float(np.triu(grid, 1).sum())
    total = home_win + draw + away_win
    return home_win / total, draw / total, away_win / total


def _tau(x: int, y: int, lam_home: float, lam_away: float, rho: float) -> float:
    """Dixon-Coles' low-score correction factor."""
    if x == 0 and y == 0:
        return 1 - lam_home * lam_away * rho
    if x == 0 and y == 1:
        return 1 + lam_home * rho
    if x == 1 and y == 0:
        return 1 + lam_away * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0


class DixonColesModel(PoissonModel):
    name = "dixon_coles"

    def __init__(self, xi: float = DEFAULT_TIME_DECAY_XI) -> None:
        super().__init__()
        self.xi = xi
        self.rho = 0.0

    def _weights(self, dates: pd.Series, as_of) -> np.ndarray:
        days_ago = (pd.Timestamp(as_of) - dates).dt.days.clip(lower=0).to_numpy(dtype=float)
        return np.exp(-self.xi * days_ago)

    def fit(self, matches: pd.DataFrame, as_of=None) -> None:
        teams = sorted(set(matches["HomeTeam"]) | set(matches["AwayTeam"]))
        n = len(teams)
        index = {t: i for i, t in enumerate(teams)}
        home_idx = matches["HomeTeam"].map(index).to_numpy()
        away_idx = matches["AwayTeam"].map(index).to_numpy()
        home_goals = matches["FTHome"].to_numpy(dtype=float)
        away_goals = matches["FTAway"].to_numpy(dtype=float)
        weights = self._weights(matches["MatchDate"], as_of or matches["MatchDate"].max())

        is_00 = (home_goals == 0) & (away_goals == 0)
        is_01 = (home_goals == 0) & (away_goals == 1)
        is_10 = (home_goals == 1) & (away_goals == 0)
        is_11 = (home_goals == 1) & (away_goals == 1)

        def unpack(params: np.ndarray):
            return params[:n], params[n : 2 * n], params[2 * n], params[2 * n + 1], params[2 * n + 2]

        def neg_log_likelihood(params: np.ndarray) -> float:
            attack, defense, home_adv, base_rate, rho = unpack(params)
            lam_home = np.exp(base_rate + home_adv + attack[home_idx] - defense[away_idx])
            lam_away = np.exp(base_rate + attack[away_idx] - defense[home_idx])

            # Vectorized Dixon-Coles tau — the same four cases as `_tau`,
            # applied across the whole training set at once instead of a
            # Python loop (this function is called dozens of times per
            # optimizer step, so the loop version dominated fit time).
            tau_vals = np.ones_like(lam_home)
            tau_vals = np.where(is_00, np.clip(1 - lam_home * lam_away * rho, 1e-6, None), tau_vals)
            tau_vals = np.where(is_01, np.clip(1 + lam_home * rho, 1e-6, None), tau_vals)
            tau_vals = np.where(is_10, np.clip(1 + lam_away * rho, 1e-6, None), tau_vals)
            tau_vals = np.where(is_11, np.clip(1 - rho, 1e-6, None), tau_vals)

            ll = weights * (
                np.log(tau_vals)
                + home_goals * np.log(lam_home)
                - lam_home
                + away_goals * np.log(lam_away)
                - lam_away
            )
            penalty = 200.0 * (attack.mean() ** 2 + defense.mean() ** 2)
            return -ll.sum() + penalty

        x0 = np.zeros(2 * n + 3)
        x0[2 * n + 1] = float(np.log(max((home_goals.mean() + away_goals.mean()) / 2, 0.1)))
        result = minimize(neg_log_likelihood, x0, method="L-BFGS-B", options={"maxiter": 400})

        self.teams = teams
        self.team_index = index
        self.attack, self.defense, self.home_adv, self.base_rate, self.rho = unpack(result.x)
        self.converged = bool(result.success)

    def match_probabilities(self, home: str, away: str) -> tuple[float, float, float] | None:
        expected = self.expected_goals(home, away)
        if expected is None:
            return None
        lam_home, lam_away = expected
        grid = self._score_grid(lam_home, lam_away)
        for x in range(2):
            for y in range(2):
                grid[x, y] *= max(_tau(x, y, lam_home, lam_away, self.rho), 1e-6)
        return _outcome_probs_from_grid(grid)
