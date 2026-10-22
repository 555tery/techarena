"""Prequential scoring and whole-stream uncertainty for the frozen protocol."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
from typing import Iterable

from model import (
    JointAssociation,
    MarginalHazard,
    PairOutcome,
    brier,
    log_loss,
)
from pipes_common import HORIZON, Pair, PipeFeatures, feature_map
from trace import Snapshot, extract_snapshots

BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 202610171337
Q_BINS = (0.0, 0.01, 0.025, 0.05, 0.10, 0.20, 0.40, 0.60, 1.0)


@dataclass(frozen=True)
class Prediction:
    snapshot_index: int
    command_index: int
    relation: int
    p_a: float
    p_b: float
    q_independent: float
    q_joint: float
    y_a: int
    y_b: int
    pair_weight: float


@dataclass(frozen=True)
class EndpointPending:
    pid: int
    features: PipeFeatures
    outcome: int
    weight: float


@dataclass(frozen=True)
class PairPending:
    relation: int
    p_a: float
    p_b: float
    y_a: int
    y_b: int
    weight: float


@dataclass(frozen=True)
class PendingSnapshot:
    endpoints: tuple[EndpointPending, ...]
    pairs: tuple[PairPending, ...]


@dataclass
class StreamResult:
    stream_name: str
    snapshot_count: int
    scored_snapshot_count: int
    empty_scored_snapshot_count: int
    predictions: list[Prediction]
    stream_metrics: dict[str, float]


def _pending_update(
    pending: PendingSnapshot,
    marginal: MarginalHazard,
    joint: JointAssociation,
    exposures: dict[int, int],
) -> None:
    for endpoint in pending.endpoints:
        marginal.update(endpoint.features, endpoint.outcome, endpoint.weight)
        exposures[endpoint.pid] = exposures.get(endpoint.pid, 0) + 1
    joint.update_checkpoint(
        [
            PairOutcome(
                relation=row.relation,
                p_a=row.p_a,
                p_b=row.p_b,
                y_a=row.y_a,
                y_b=row.y_b,
                weight=row.weight,
            )
            for row in pending.pairs
        ]
    )


def predict_stream(stream_name: str, snapshots: list[Snapshot]) -> StreamResult:
    """Forecast each snapshot before revealing its label window to the models."""
    marginal = MarginalHazard()
    joint = JointAssociation()
    exposures: dict[int, int] = {}
    pending: PendingSnapshot | None = None
    all_predictions: list[Prediction] = []
    warmup = len(snapshots) // 2
    scored_snapshot_count = 0
    empty_scored_snapshot_count = 0

    for snapshot_index, snapshot in enumerate(snapshots):
        if pending is not None:
            _pending_update(pending, marginal, joint, exposures)

        feature_by_pid = feature_map(snapshot.active, snapshot.command_index)
        endpoint_pending: list[EndpointPending] = []
        pair_pending: list[PairPending] = []
        predictions_this_snapshot: list[Prediction] = []
        for labeled in snapshot.pairs:
            pair = labeled.pair
            x_a = feature_by_pid[pair.left.pid]
            x_b = feature_by_pid[pair.right.pid]
            w_a = 1.0 / (1.0 + exposures.get(pair.left.pid, 0))
            w_b = 1.0 / (1.0 + exposures.get(pair.right.pid, 0))
            p_a = marginal.predict(x_a)
            p_b = marginal.predict(x_b)
            q0 = p_a * p_b
            q_joint = joint.predict(pair.relation, p_a, p_b)
            pair_weight = math.sqrt(w_a * w_b)
            y_both = int(labeled.y_left and labeled.y_right)
            if snapshot_index >= warmup:
                predictions_this_snapshot.append(
                    Prediction(
                        snapshot_index=snapshot_index,
                        command_index=snapshot.command_index,
                        relation=pair.relation,
                        p_a=p_a,
                        p_b=p_b,
                        q_independent=q0,
                        q_joint=q_joint,
                        y_a=labeled.y_left,
                        y_b=labeled.y_right,
                        pair_weight=pair_weight,
                    )
                )
            endpoint_pending.extend(
                (
                    EndpointPending(pair.left.pid, x_a, labeled.y_left, w_a),
                    EndpointPending(pair.right.pid, x_b, labeled.y_right, w_b),
                )
            )
            pair_pending.append(
                PairPending(
                    pair.relation,
                    p_a,
                    p_b,
                    labeled.y_left,
                    labeled.y_right,
                    pair_weight,
                )
            )
        if snapshot_index >= warmup:
            scored_snapshot_count += 1
            if not predictions_this_snapshot:
                empty_scored_snapshot_count += 1
            else:
                all_predictions.extend(predictions_this_snapshot)
        pending = PendingSnapshot(tuple(endpoint_pending), tuple(pair_pending))

    metrics = stream_metrics(all_predictions)
    return StreamResult(
        stream_name=stream_name,
        snapshot_count=len(snapshots),
        scored_snapshot_count=scored_snapshot_count,
        empty_scored_snapshot_count=empty_scored_snapshot_count,
        predictions=all_predictions,
        stream_metrics=metrics,
    )


def _snapshot_means(predictions: Iterable[Prediction]) -> dict[int, tuple[float, ...]]:
    groups: dict[int, list[Prediction]] = {}
    for row in predictions:
        groups.setdefault(row.snapshot_index, []).append(row)
    result: dict[int, tuple[float, ...]] = {}
    for snapshot_index, rows in groups.items():
        total_weight = sum(row.pair_weight for row in rows)
        if total_weight <= 0.0:
            continue
        metrics = [0.0] * 4
        for row in rows:
            y_both = int(row.y_a and row.y_b)
            weight = row.pair_weight / total_weight
            metrics[0] += weight * brier(row.q_independent, y_both)
            metrics[1] += weight * brier(row.q_joint, y_both)
            metrics[2] += weight * log_loss(row.q_independent, y_both)
            metrics[3] += weight * log_loss(row.q_joint, y_both)
        result[snapshot_index] = tuple(metrics)
    return result


def stream_metrics(predictions: list[Prediction]) -> dict[str, float]:
    by_snapshot = _snapshot_means(predictions)
    if not by_snapshot:
        return {}
    means = [sum(values[index] for values in by_snapshot.values()) / len(by_snapshot)
             for index in range(4)]
    return {
        "brier_independent": means[0],
        "brier_joint": means[1],
        "brier_improvement": means[0] - means[1],
        "logloss_independent": means[2],
        "logloss_joint": means[3],
        "logloss_improvement": means[2] - means[3],
    }


def calibration_rows(results: list[StreamResult]) -> list[dict[str, object]]:
    """Equal stream, then equal scored-snapshot, then exposure-weighted calibration."""
    stream_count = max(1, sum(bool(result.stream_metrics) for result in results))
    accum: dict[tuple[str, int, int], list[float]] = {}
    for result in results:
        snapshot_groups: dict[int, list[Prediction]] = {}
        for row in result.predictions:
            snapshot_groups.setdefault(row.snapshot_index, []).append(row)
        if not snapshot_groups:
            continue
        snapshot_mass = 1.0 / (stream_count * len(snapshot_groups))
        for rows in snapshot_groups.values():
            total_weight = sum(row.pair_weight for row in rows)
            if total_weight <= 0:
                continue
            for row in rows:
                weight = snapshot_mass * row.pair_weight / total_weight
                outcome = int(row.y_a and row.y_b)
                for name, q in (("independent", row.q_independent), ("joint", row.q_joint)):
                    bin_index = _bin_index(q)
                    key = (name, row.relation, bin_index)
                    values = accum.setdefault(key, [0.0, 0.0, 0.0])
                    values[0] += weight
                    values[1] += weight * q
                    values[2] += weight * outcome
    output: list[dict[str, object]] = []
    for model_name in ("independent", "joint"):
        for relation in (0, 1):
            for bin_index in range(len(Q_BINS) - 1):
                mass, predicted, observed = accum.get(
                    (model_name, relation, bin_index), [0.0, 0.0, 0.0]
                )
                if mass == 0.0:
                    continue
                output.append(
                    {
                        "model": model_name,
                        "relation": relation,
                        "q_bin": [Q_BINS[bin_index], Q_BINS[bin_index + 1]],
                        "weight": mass,
                        "mean_prediction": predicted / mass,
                        "observed_rate": observed / mass,
                        "observed_minus_predicted": (observed - predicted) / mass,
                    }
                )
    return output


def _bin_index(probability: float) -> int:
    for index, upper in enumerate(Q_BINS[1:]):
        if probability <= upper:
            return index
    return len(Q_BINS) - 2


def bootstrap_stream_metrics(
    results: list[StreamResult],
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, object]:
    usable = [result for result in results if result.stream_metrics]
    metric_names = ("brier_improvement", "logloss_improvement")
    if not usable:
        return {"usable_streams": 0, "intervals": {}}
    rng = random.Random(seed)
    draws = [
        [rng.randrange(len(usable)) for _ in range(len(usable))]
        for _ in range(replicates)
    ]
    intervals: dict[str, dict[str, float]] = {}
    for metric in metric_names:
        values = [float(result.stream_metrics[metric]) for result in usable]
        boot_means = sorted(
            sum(values[index] for index in draw) / len(draw)
            for draw in draws
        )
        intervals[metric] = {
            "mean": sum(values) / len(values),
            "ci95_low": boot_means[int(0.025 * replicates)],
            "ci95_high": boot_means[min(replicates - 1, int(0.975 * replicates))],
        }
    return {
        "usable_streams": len(usable),
        "streams_without_scored_pairs": len(results) - len(usable),
        "bootstrap_replicates": replicates,
        "bootstrap_seed": seed,
        "intervals": intervals,
    }


def summarize_dataset(dataset: str, results: list[StreamResult]) -> dict[str, object]:
    return {
        "dataset": dataset,
        "stream_count": len(results),
        "whole_stream_bootstrap": bootstrap_stream_metrics(results),
        "calibration": calibration_rows(results),
        "streams": [
            {
                "name": result.stream_name,
                "snapshots": result.snapshot_count,
                "scored_snapshots": result.scored_snapshot_count,
                "empty_scored_snapshots": result.empty_scored_snapshot_count,
                "metrics": result.stream_metrics,
            }
            for result in results
        ],
    }


def evaluate_trace_pair(
    stream_name: str,
    input_path: Path,
    reply_path: Path,
) -> StreamResult:
    snapshots = extract_snapshots(input_path, reply_path, horizon=HORIZON)
    return predict_stream(stream_name, snapshots)


def write_summary(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
