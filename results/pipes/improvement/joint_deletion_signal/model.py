"""Causal individual-hazard and pair-association models for the preregistered study."""

from __future__ import annotations

from dataclasses import dataclass
import math

from pipes_common import PipeFeatures


def _shrink(success: float, weight: float, parent: float) -> float:
    return (success + 8.0 * parent) / (weight + 8.0)


class MarginalHazard:
    """Hierarchical Beta rate model; both compared predictors share this instance."""

    def __init__(self) -> None:
        self.success = 0.0
        self.weight = 0.0
        self.by_length: dict[int, tuple[float, float]] = {}
        self.by_length_age: dict[tuple[int, int], tuple[float, float]] = {}
        self.by_length_age_rank: dict[tuple[int, int, int], tuple[float, float]] = {}
        self.full: dict[tuple[int, int, int, int], tuple[float, float]] = {}

    @staticmethod
    def _add(
        table: dict[tuple[int, ...] | int, tuple[float, float]],
        key: tuple[int, ...] | int,
        outcome: int,
        sample_weight: float,
    ) -> None:
        success, weight = table.get(key, (0.0, 0.0))
        table[key] = (success + sample_weight * outcome, weight + sample_weight)

    def predict(self, x: PipeFeatures) -> float:
        global_rate = (1.0 + self.success) / (10.0 + self.weight)
        len_success, len_weight = self.by_length.get(x.length, (0.0, 0.0))
        len_rate = _shrink(len_success, len_weight, global_rate)
        la_key = (x.length, x.age_band)
        la_success, la_weight = self.by_length_age.get(la_key, (0.0, 0.0))
        la_rate = _shrink(la_success, la_weight, len_rate)
        lar_key = (x.length, x.age_band, x.newest_rank_quartile)
        lar_success, lar_weight = self.by_length_age_rank.get(lar_key, (0.0, 0.0))
        lar_rate = _shrink(lar_success, lar_weight, la_rate)
        full_key = (
            x.length,
            x.age_band,
            x.newest_rank_quartile,
            x.length_occurrence_parity,
        )
        full_success, full_weight = self.full.get(full_key, (0.0, 0.0))
        return min(1.0 - 1e-9, max(1e-9, _shrink(full_success, full_weight, lar_rate)))

    def update(self, x: PipeFeatures, outcome: int, sample_weight: float) -> None:
        if outcome not in (0, 1) or sample_weight <= 0.0:
            raise ValueError("invalid marginal-hazard observation")
        self.success += sample_weight * outcome
        self.weight += sample_weight
        self._add(self.by_length, x.length, outcome, sample_weight)
        self._add(
            self.by_length_age,
            (x.length, x.age_band),
            outcome,
            sample_weight,
        )
        self._add(
            self.by_length_age_rank,
            (x.length, x.age_band, x.newest_rank_quartile),
            outcome,
            sample_weight,
        )
        self._add(
            self.full,
            (x.length, x.age_band, x.newest_rank_quartile, x.length_occurrence_parity),
            outcome,
            sample_weight,
        )


def joint_probability(p_a: float, p_b: float, theta: float) -> float:
    """Return P(A=1,B=1) for fixed marginals and a prescribed log odds ratio."""
    if abs(theta) < 1e-12:
        return p_a * p_b
    odds_ratio = math.exp(theta)
    quadratic = odds_ratio - 1.0
    linear = 1.0 + quadratic * (p_a + p_b)
    constant = odds_ratio * p_a * p_b
    discriminant = max(0.0, linear * linear - 4.0 * quadratic * constant)
    denominator = linear + math.sqrt(discriminant)
    if abs(denominator) < 1e-15:
        # This branch is only a numerical fallback near an extreme boundary.
        low = max(0.0, p_a + p_b - 1.0)
        high = min(p_a, p_b)
        for _ in range(80):
            middle = (low + high) / 2.0
            lhs = middle * (1.0 - p_a - p_b + middle)
            rhs = odds_ratio * (p_a - middle) * (p_b - middle)
            if lhs < rhs:
                low = middle
            else:
                high = middle
        return (low + high) / 2.0
    value = 2.0 * constant / denominator
    low = max(0.0, p_a + p_b - 1.0)
    high = min(p_a, p_b)
    return min(high, max(low, value))


def _pair_cells(p_a: float, p_b: float, theta: float) -> tuple[float, float, float, float]:
    p11 = joint_probability(p_a, p_b, theta)
    return (
        p11,
        max(1e-15, p_a - p11),
        max(1e-15, p_b - p11),
        max(1e-15, 1.0 - p_a - p_b + p11),
    )


@dataclass(frozen=True)
class PairOutcome:
    relation: int
    p_a: float
    p_b: float
    y_a: int
    y_b: int
    weight: float


class JointAssociation:
    """Online Laplace/Newton update for a relation-specific log odds ratio."""

    def __init__(self) -> None:
        self.mean = [0.0, 0.0]
        self.precision = [1.0, 1.0]

    def predict(self, relation: int, p_a: float, p_b: float) -> float:
        if relation not in (0, 1):
            raise ValueError("relation must be binary")
        return joint_probability(p_a, p_b, self.mean[relation])

    def update_checkpoint(self, rows: list[PairOutcome]) -> None:
        """Update only from labels that have just matured at one checkpoint."""
        score = [0.0, 0.0]
        information = [0.0, 0.0]
        for row in rows:
            if row.relation not in (0, 1) or row.y_a not in (0, 1) or row.y_b not in (0, 1):
                raise ValueError("invalid joint observation")
            if row.weight <= 0.0:
                raise ValueError("joint observation weight must be positive")
            relation = row.relation
            theta = self.mean[relation]
            p11, p10, p01, p00 = _pair_cells(row.p_a, row.p_b, theta)
            q_prime = 1.0 / (1.0 / p11 + 1.0 / p10 + 1.0 / p01 + 1.0 / p00)
            if row.y_a and row.y_b:
                observed_cell = p11
                sign = 1.0
            elif not row.y_a and not row.y_b:
                observed_cell = p00
                sign = 1.0
            elif row.y_a:
                observed_cell = p10
                sign = -1.0
            else:
                observed_cell = p01
                sign = -1.0
            score[relation] += row.weight * sign * q_prime / observed_cell
            information[relation] += row.weight * q_prime * q_prime * (
                1.0 / p11 + 1.0 / p10 + 1.0 / p01 + 1.0 / p00
            )

        for relation in (0, 1):
            if information[relation] == 0.0 and score[relation] == 0.0:
                continue
            old_precision = self.precision[relation]
            step = score[relation] / (old_precision + information[relation])
            self.mean[relation] = min(3.0, max(-3.0, self.mean[relation] + step))
            self.precision[relation] = old_precision + information[relation]


def brier(probability: float, outcome: int) -> float:
    return (probability - outcome) ** 2


def log_loss(probability: float, outcome: int) -> float:
    bounded = min(1.0 - 1e-12, max(1e-12, probability))
    return -math.log(bounded if outcome else 1.0 - bounded)
