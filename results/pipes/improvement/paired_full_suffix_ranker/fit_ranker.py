#!/usr/bin/env python3
"""Fit the fixed pairwise ranker using train-only counterfactual labels."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
FEATURE_COUNT = 180
TEMPERATURE_M = 20.0
L2 = 0.01
STEPS = 1_000
LEARNING_RATE = 0.03
SEED = 20261018
EPS = 1e-12


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rows(paths: list[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in paths:
        with path.open(newline="", encoding="ascii") as stream:
            reader = csv.DictReader(stream)
            required = {"stream", "state_id", "command_index", "candidate_rank",
                        "baseline_action", "target_growth_m"}
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                raise RuntimeError(f"bad label CSV header: {path}")
            for record in reader:
                rows.append({
                    "stream": record["stream"], "state_id": record["state_id"],
                    "command_index": int(record["command_index"]),
                    "candidate_rank": int(record["candidate_rank"]),
                    "baseline_action": int(record["baseline_action"]),
                    "target": float(record["target_growth_m"]),
                    "x": [float(record[f"f{i}"]) for i in range(FEATURE_COUNT)],
                })
    return rows


def sigmoid(x: float) -> float:
    if x >= 40.0:
        return 1.0
    if x <= -40.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", nargs="+", required=True, type=Path)
    parser.add_argument("--header", type=Path, default=HERE / "src/ranker_model.hpp")
    parser.add_argument("--model-json", type=Path, required=True)
    args = parser.parse_args()
    paths = [path.resolve() for path in args.labels]
    rows = load_rows(paths)
    if not rows:
        raise RuntimeError("no training label rows")

    by_state: dict[str, list[dict[str, object]]] = defaultdict(list)
    states_per_stream: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        state_id = str(row["state_id"])
        by_state[state_id].append(row)
        states_per_stream[str(row["stream"])].add(state_id)
    for state_id, state_rows in by_state.items():
        state_rows.sort(key=lambda row: int(row["candidate_rank"]))
        if len(state_rows) < 2 or sum(int(row["baseline_action"]) for row in state_rows) != 1:
            raise RuntimeError(f"invalid candidate group {state_id}")

    streams = sorted(states_per_stream)
    if len(streams) < 10:
        raise RuntimeError(f"too few train streams: {len(streams)}")

    x_rows = [row["x"] for row in rows]
    means = [sum(float(x[j]) for x in x_rows) / len(x_rows) for j in range(FEATURE_COUNT)]
    scales: list[float] = []
    for j in range(FEATURE_COUNT):
        variance = sum((float(x[j]) - means[j]) ** 2 for x in x_rows) / len(x_rows)
        scale = math.sqrt(variance)
        scales.append(scale if scale > 1e-8 else 1.0)

    # Each training stream has equal total weight; within it, each sampled
    # trajectory state and then each candidate pair share that weight.
    pairs: list[tuple[list[float], float, float]] = []
    for state_id in sorted(by_state):
        group = by_state[state_id]
        stream = str(group[0]["stream"])
        pair_weight = 1.0 / len(streams) / len(states_per_stream[stream])
        pair_weight /= len(group) * (len(group) - 1) / 2
        for i in range(len(group)):
            xi = group[i]["x"]
            yi = float(group[i]["target"])
            for j in range(i + 1, len(group)):
                xj = group[j]["x"]
                yj = float(group[j]["target"])
                delta = [(float(xj[k]) - float(xi[k])) / scales[k]
                         for k in range(FEATURE_COUNT)]
                target = sigmoid((yj - yi) / TEMPERATURE_M)
                # `delta` is x_j - x_i. The desired probability that i is
                # better is sigmoid(score_j - score_i) = sigmoid(w dot delta).
                pairs.append((delta, target, pair_weight))

    weights = [0.0] * FEATURE_COUNT
    first = [0.0] * FEATURE_COUNT
    second = [0.0] * FEATURE_COUNT
    beta1, beta2 = 0.9, 0.999
    rng = random.Random(SEED)
    order = list(range(len(pairs)))
    total_pair_weight = sum(pair[2] for pair in pairs)
    losses: list[float] = []
    for step in range(1, STEPS + 1):
        rng.shuffle(order)
        gradient = [0.0] * FEATURE_COUNT
        epoch_loss = 0.0
        for pair_index in order:
            delta, target, pair_weight = pairs[pair_index]
            margin = sum(weights[k] * delta[k] for k in range(FEATURE_COUNT))
            predicted = sigmoid(margin)
            clipped = min(1.0 - EPS, max(EPS, predicted))
            epoch_loss += pair_weight * (
                -target * math.log(clipped) - (1.0 - target) * math.log(1.0 - clipped)
            )
            multiplier = pair_weight * (predicted - target) / total_pair_weight
            for k in range(FEATURE_COUNT):
                gradient[k] += multiplier * delta[k]
        for k in range(FEATURE_COUNT):
            gradient[k] += L2 * weights[k]
            first[k] = beta1 * first[k] + (1.0 - beta1) * gradient[k]
            second[k] = beta2 * second[k] + (1.0 - beta2) * gradient[k] * gradient[k]
            corrected_first = first[k] / (1.0 - beta1 ** step)
            corrected_second = second[k] / (1.0 - beta2 ** step)
            weights[k] -= LEARNING_RATE * corrected_first / (math.sqrt(corrected_second) + 1e-8)
        if step in (1, 10, 100, STEPS):
            regularized = epoch_loss + 0.5 * L2 * sum(w * w for w in weights)
            losses.append(regularized)

    def write_array(out, name: str, values: list[float]) -> None:
        out.write(f"inline constexpr std::array<double, {FEATURE_COUNT}> {name} = {{{{\n    ")
        out.write(", ".join(f"{value:.17g}" for value in values))
        out.write("\n}};\n")

    args.header.parent.mkdir(parents=True, exist_ok=True)
    with args.header.open("w", encoding="ascii") as out:
        out.write("#pragma once\n#include <array>\n#include <cstddef>\n\n")
        out.write("namespace learned_gap_value {\n")
        out.write(f"inline constexpr std::size_t kFeatureCount = {FEATURE_COUNT};\n")
        write_array(out, "kMean", means)
        write_array(out, "kScale", scales)
        write_array(out, "kWeight", weights)
        out.write("inline double predict(const std::array<double, kFeatureCount>& x) {\n")
        out.write("    double result = 0.0;\n")
        out.write("    for (std::size_t i = 0; i < kFeatureCount; ++i)\n")
        out.write("        result += kWeight[i] * (x[i] - kMean[i]) / kScale[i];\n")
        out.write("    return result;\n}\n}\n")

    stream_state_counts = {stream: len(states) for stream, states in sorted(states_per_stream.items())}
    model = {
        "objective": "paired_soft_ranknet_final_trench_growth",
        "feature_count": FEATURE_COUNT,
        "temperature_m": TEMPERATURE_M,
        "l2": L2,
        "steps": STEPS,
        "learning_rate": LEARNING_RATE,
        "seed": SEED,
        "rows": len(rows),
        "states": len(by_state),
        "streams": streams,
        "states_per_stream": stream_state_counts,
        "pairs": len(pairs),
        "regularized_loss_checkpoints": losses,
        "header_sha256": sha256(args.header),
        "label_csvs": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
    }
    args.model_json.parent.mkdir(parents=True, exist_ok=True)
    args.model_json.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: model[k] for k in ("rows", "states", "pairs", "regularized_loss_checkpoints",
                                            "header_sha256")}, indent=2))


if __name__ == "__main__":
    main()
