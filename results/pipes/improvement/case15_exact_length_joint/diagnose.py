#!/usr/bin/env python3
"""Prequential screen of exact-length co-deletion on the saved case15 trace.

This diagnostic uses a frozen source/reply/input triple. It does not invoke a
solver, change an allocator, or use future labels when forming predictions.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[4]
STUDY = ROOT / "results/pipes/improvement/joint_deletion_signal"
sys.path.insert(0, str(STUDY))

from model import JointAssociation, MarginalHazard, PairOutcome, brier, log_loss  # noqa: E402
from pipes_common import PipeFeatures, age_band  # noqa: E402


HORIZON = 128
PAIR_CAP = 256
WARMUP_FRACTION = 0.5
EXPECTED_SOURCE_SHA256 = "43bfbdadbae18ac180d1e59b6631342cfe1bef99190a449838f0470d6f220200"
EXPECTED_INPUT_SHA256 = "0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353"
SOURCE = ROOT / "results/pipes/improvement/case9_causal_profiles/source/champion_cohort_slabs.cpp"
INPUT = ROOT / "data/pipes/open/15.in"
REPLIES = ROOT / "results/pipes/improvement/case9_causal_profiles/runs/champion-cohort-slabs-open15/runs/15/judge_output.txt"
OUT = Path(__file__).with_name("hash_order_result.json")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Fenwick:
    def __init__(self, size: int) -> None:
        self.tree = [0] * (size + 1)

    def add(self, index: int, delta: int) -> None:
        while index < len(self.tree):
            self.tree[index] += delta
            index += index & -index

    def prefix(self, index: int) -> int:
        total = 0
        while index:
            total += self.tree[index]
            index -= index & -index
        return total


def systematic_indices(count: int, cap: int) -> list[int]:
    if count <= cap:
        return list(range(count))
    return [((2 * slot + 1) * count) // (2 * cap) for slot in range(cap)]


def main() -> int:
    source_bytes = SOURCE.read_bytes()
    input_bytes = INPUT.read_bytes()
    reply_bytes = REPLIES.read_bytes()
    source_hash = sha256(source_bytes)
    input_hash = sha256(input_bytes)
    if source_hash != EXPECTED_SOURCE_SHA256:
        raise SystemExit(f"unexpected candidate source SHA-256: {source_hash}")
    if input_hash != EXPECTED_INPUT_SHA256:
        raise SystemExit(f"unexpected case15 input SHA-256: {input_hash}")

    lines = input_bytes.decode("ascii").splitlines()
    header = lines[0].split()
    if len(header) != 2:
        raise ValueError("expected Pipes header with weight and command count")
    command_count = int(header[1])
    commands = [int(token) for line in lines[1:] for token in line.split()]
    if len(commands) != command_count + 1 or commands[-1] != 0:
        raise ValueError("input command count/terminator mismatch")
    commands.pop()
    reply_lines = reply_bytes.decode("ascii").splitlines()
    if len(reply_lines) != command_count:
        raise ValueError("reply count does not match input")

    lengths = [0]
    starts = [0]
    placed_at = [0]
    removed_at = [0]
    active_by_length: list[dict[int, None]] = [dict() for _ in range(41)]
    active = bytearray(command_count + 2)
    fenwick = Fenwick(command_count + 1)
    active_count = 0
    next_pid = 1
    trench = 0
    for step, (command, reply_line) in enumerate(zip(commands, reply_lines), start=1):
        fields = tuple(map(int, reply_line.split()))
        if command > 0:
            if not 1 <= command <= 40 or len(fields) != 2:
                raise ValueError(f"bad placement reply at command {step}")
            digs, start = fields
            if digs < 0 or start < 0:
                raise ValueError(f"negative placement output at command {step}")
            trench += 20 * digs
            lengths.append(command)
            starts.append(start)
            placed_at.append(step)
            removed_at.append(0)
            active[next_pid] = 1
            active_by_length[command][next_pid] = None
            fenwick.add(next_pid, 1)
            active_count += 1
            next_pid += 1
        elif command < 0:
            if len(fields) != 1:
                raise ValueError(f"bad removal reply at command {step}")
            pid = -command
            if pid <= 0 or pid >= next_pid or not active[pid]:
                raise ValueError(f"invalid removal at command {step}: pid={pid}")
            if fields[0] != starts[pid]:
                raise ValueError(f"removal coordinate mismatch at command {step}")
            active[pid] = 0
            removed_at[pid] = step
            active_by_length[lengths[pid]].pop(pid)
            fenwick.add(pid, -1)
            active_count -= 1
        else:
            raise ValueError("zero terminator found before command_count")
    placements = next_pid - 1
    snapshots: list[tuple[int, list[tuple[int, int, int, PipeFeatures, PipeFeatures, int, int]]]] = []
    # Replay active membership from the command stream; each snapshot uses only
    # state through its command boundary. Future removal times label outcomes.
    active_by_length = [dict() for _ in range(41)]
    active = bytearray(placements + 1)
    fenwick = Fenwick(placements)
    active_count = 0
    next_pid = 1
    pair_counts: list[int] = []
    adjacent_excluded = 0

    for step, command in enumerate(commands, start=1):
        if command > 0:
            pid = next_pid
            next_pid += 1
            active[pid] = 1
            active_by_length[command][pid] = None
            fenwick.add(pid, 1)
            active_count += 1
        elif command < 0:
            pid = -command
            active[pid] = 0
            active_by_length[lengths[pid]].pop(pid)
            fenwick.add(pid, -1)
            active_count -= 1

        if step % HORIZON != 0 or step + HORIZON > command_count:
            continue

        candidate_pairs: list[tuple[int, int]] = []
        for length in range(1, 41):
            pids = list(active_by_length[length])
            # Pair by a deterministic affine permutation of current active
            # PIDs. This remains a state-only diagnostic, but avoids always
            # pairing creation-adjacent items as in the first screen.
            size = len(pids)
            if size < 2:
                continue
            multiplier = (2 * step + 3 * length + 1) % size
            if multiplier == 0:
                multiplier = 1
            while math.gcd(multiplier, size) != 1:
                multiplier = (multiplier + 1) % size
                if multiplier == 0:
                    multiplier = 1
            offset = (17 * step + 13 * length) % size
            permuted = [pids[(multiplier * index + offset) % size] for index in range(size)]
            for index in range(0, size - 1, 2):
                a, b = permuted[index], permuted[index + 1]
                # Exclude physical contact: this tests same-size cohort
                # association beyond the prior touching-neighbor relation.
                if abs(starts[a] - starts[b]) == length:
                    adjacent_excluded += 1
                    continue
                candidate_pairs.append((a, b))

        selected = [candidate_pairs[index] for index in systematic_indices(
            len(candidate_pairs), PAIR_CAP
        )]
        labeled: list[tuple[int, int, int, PipeFeatures, PipeFeatures, int, int]] = []
        for a, b in selected:
            def make_features(pid: int) -> PipeFeatures:
                newer = active_count - fenwick.prefix(pid)
                rank_quartile = 0 if active_count <= 1 else min(
                    3, (4 * newer) // (active_count - 1)
                )
                return PipeFeatures(
                    length=lengths[pid],
                    age_band=age_band(step - placed_at[pid]),
                    newest_rank_quartile=rank_quartile,
                    length_occurrence_parity=0,  # deliberately excluded
                )

            end = step + HORIZON
            y_a = int(removed_at[a] != 0 and step < removed_at[a] <= end)
            y_b = int(removed_at[b] != 0 and step < removed_at[b] <= end)
            labeled.append((a, b, lengths[a], make_features(a), make_features(b), y_a, y_b))
        snapshots.append((step, labeled))
        pair_counts.append(len(labeled))

    if not snapshots:
        raise ValueError("no snapshots available")

    marginal = MarginalHazard()
    joint = JointAssociation()
    exposures: dict[int, int] = {}
    pending_endpoints: list[tuple[int, PipeFeatures, int, float]] = []
    pending_pairs: list[PairOutcome] = []
    scored_snapshot_metrics: list[dict[str, float]] = []
    outcome_counts = Counter()
    scored_pair_count = 0
    warmup = int(len(snapshots) * WARMUP_FRACTION)

    for snapshot_index, (step, rows) in enumerate(snapshots):
        if pending_endpoints:
            for pid, features, outcome, weight in pending_endpoints:
                marginal.update(features, outcome, weight)
                exposures[pid] = exposures.get(pid, 0) + 1
            joint.update_checkpoint(pending_pairs)
            pending_endpoints = []
            pending_pairs = []

        predictions: list[tuple[float, float, int, float, int, int]] = []
        for pid_a, pid_b, _length, feat_a, feat_b, y_a, y_b in rows:
            weight_a = 1.0 / (1.0 + exposures.get(pid_a, 0))
            weight_b = 1.0 / (1.0 + exposures.get(pid_b, 0))
            pair_weight = math.sqrt(weight_a * weight_b)
            p_a = marginal.predict(feat_a)
            p_b = marginal.predict(feat_b)
            q_independent = p_a * p_b
            q_joint = joint.predict(1, p_a, p_b)
            predictions.append((q_independent, q_joint, int(y_a and y_b), pair_weight, y_a, y_b))
            pending_endpoints.extend(((pid_a, feat_a, y_a, weight_a), (pid_b, feat_b, y_b, weight_b)))
            pending_pairs.append(PairOutcome(1, p_a, p_b, y_a, y_b, pair_weight))

        if snapshot_index < warmup or not predictions:
            continue
        scored_pair_count += len(predictions)
        outcome_counts["left_deleted"] += sum(row[4] for row in predictions)
        outcome_counts["right_deleted"] += sum(row[5] for row in predictions)
        outcome_counts["both_deleted"] += sum(row[2] for row in predictions)
        outcome_counts["one_deleted"] += sum(int(row[4] != row[5]) for row in predictions)
        total_weight = sum(row[3] for row in predictions)
        losses = [0.0, 0.0, 0.0, 0.0]
        for q0, q1, both, weight, _ya, _yb in predictions:
            normalized = weight / total_weight
            losses[0] += normalized * brier(q0, both)
            losses[1] += normalized * brier(q1, both)
            losses[2] += normalized * log_loss(q0, both)
            losses[3] += normalized * log_loss(q1, both)
        scored_snapshot_metrics.append({
            "brier_independent": losses[0],
            "brier_joint": losses[1],
            "logloss_independent": losses[2],
            "logloss_joint": losses[3],
            "pair_count": float(len(predictions)),
            "command_index": float(step),
        })

    # Finish learning from the final matured scoring window for a descriptive
    # posterior only; this cannot affect any reported prequential prediction.
    if pending_endpoints:
        for pid, features, outcome, weight in pending_endpoints:
            marginal.update(features, outcome, weight)
            exposures[pid] = exposures.get(pid, 0) + 1
        joint.update_checkpoint(pending_pairs)

    means = {
        key: sum(row[key] for row in scored_snapshot_metrics) / len(scored_snapshot_metrics)
        for key in (
            "brier_independent", "brier_joint", "logloss_independent", "logloss_joint"
        )
    }
    result = {
        "scope": "Open case15 only; exact-length active-PID pairs, independent of geometry; touching equal-length pairs excluded",
        "source_sha256": source_hash,
        "input_sha256": input_hash,
        "reply_sha256": sha256(reply_bytes),
        "diagnostic_sha256": sha256(Path(__file__).read_bytes()),
        "command_count": command_count,
        "placements": placements,
        "deletions": command_count - placements,
        "horizon_commands": HORIZON,
        "snapshot_count": len(snapshots),
        "warmup_snapshots": warmup,
        "scored_snapshots": len(scored_snapshot_metrics),
        "pair_cap_per_snapshot": PAIR_CAP,
        "selected_pairs_per_snapshot_min": min(pair_counts),
        "selected_pairs_per_snapshot_median": sorted(pair_counts)[len(pair_counts) // 2],
        "selected_pairs_per_snapshot_max": max(pair_counts),
        "scored_pair_count": scored_pair_count,
        "pair_outcomes": dict(outcome_counts),
        "metrics_mean_over_scored_snapshots": {
            **means,
            "brier_improvement": means["brier_independent"] - means["brier_joint"],
            "logloss_improvement": means["logloss_independent"] - means["logloss_joint"],
        },
        "joint_log_odds_ratio_parameter_after_all_matured_windows": joint.mean[1],
        "joint_parameter_precision": joint.precision[1],
        "pair_definition": "Within each exact length, pair consecutive active PIDs after deterministic affine permutation (coprime multiplier and state-derived offset); exclude physically touching pairs; systematically select at most 256 across length groups.",
        "marginal_controls": "length, age band, newest-rank quartile; length-occurrence parity fixed to 0 and unused as signal",
        "limitations": [
            "single Open15 stream; descriptive screening only, no stream-level uncertainty estimate",
            "the result tests same-length non-touching pairs and does not establish a causal placement-policy gain",
            "A deterministic affine permutation defines disjoint pair sampling only; its inputs are current step, length, and active PIDs, and are not used as predictors",
            "future deletions label outcomes only after the prediction horizon and are never features",
        ],
        "scored_snapshot_metrics": scored_snapshot_metrics,
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "scored_snapshot_metrics"}, indent=2))
    print(f"saved {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
