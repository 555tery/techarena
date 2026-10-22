#!/usr/bin/env python3
"""Fit and validate an offline regression forest for causal gap selection.

Training labels use a fixed synthetic command horizon. Future commands never
enter feature extraction and are not available to the compiled solver.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
GENERATOR = ROOT / "tools/generate_pipes_synthetic.py"
BASELINE = ROOT / "results/pipes/final/solution.cpp"
SIM_PATH = ROOT / "results/pipes/improvement/joint_gap_portfolio_probe/probe.py"
HORIZON = 512
TRAIN_CADENCE = 240
VALIDATION_CADENCE_SHORT = 240
VALIDATION_CADENCE_LONG = 1_200
MIN_COMMAND = 360
TREES = 24
TREE_DEPTH = 5
MIN_LEAF = 24
FEATURES_PER_NODE = 18
THRESHOLD_QUANTILES = 20
TRAIN_SEED = 2026101717

spec = importlib.util.spec_from_file_location("joint_gap_probe", SIM_PATH)
assert spec is not None and spec.loader is not None
joint = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = joint
spec.loader.exec_module(joint)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_commands(path: Path) -> list[int]:
    values = path.read_text(encoding="ascii").split()
    n = int(values[1])
    commands = [int(x) for x in values[2:]]
    if len(commands) != n + 1 or commands[-1] != 0:
        raise RuntimeError(f"bad command count in {path}")
    return commands


def run_solver(binary: Path, commands: list[int]) -> list[list[int]]:
    p = subprocess.run([str(binary)], input="\n".join(map(str, commands)) + "\n",
                       text=True, capture_output=True, check=True)
    lines = [line.split() for line in p.stdout.splitlines()]
    expected = sum(x != 0 for x in commands)
    if len(lines) != expected:
        raise RuntimeError(f"reply count mismatch for {binary}")
    return [[int(x) for x in row] for row in lines]


def candidates(sim, length: int):
    actions, baseline = joint.baseline_action_list(sim, length)
    ranked = [a for a in actions if a.label in ("ranked-gap", "baseline")]
    result = []
    seen = set()
    for action in ranked:
        key = (action.start, action.high_side)
        if key not in seen:
            result.append(action)
            seen.add(key)
        if len(result) == 3:
            break
    return result, baseline


def bin_gap(length: int) -> int:
    if length <= 80:
        return length - 1
    if length <= 100:
        return 80
    if length <= 140:
        return 81
    if length <= 200:
        return 82
    if length <= 400:
        return 83
    return 84


FEATURE_NAMES = (
    [f"post_gap_count_{i}" for i in range(1, 81)]
    + ["post_gap_81_100", "post_gap_101_140", "post_gap_141_200",
       "post_gap_201_400", "post_gap_401_plus"]
    + [f"recent_length_share_{i}" for i in range(1, 41)]
    + [f"request_length_{i}" for i in range(1, 41)]
    + ["active_log", "gap_count_log", "trench_scaled", "occupancy_ratio",
       "tail_length_scaled", "candidate_start_ratio", "candidate_gap_scaled",
       "candidate_slack_scaled", "candidate_is_tail", "candidate_high_side",
       "candidate_gap_cohort", "size_cohort", "parity_mode", "alternating_mode",
       "candidate_rank_scaled"]
)


def features(sim, length: int, action, rank: int) -> list[float]:
    before = sim
    original_gap_end, original_cohort = before.gaps[action.start]
    original_gap_length = original_gap_end - action.start
    is_tail = before.tail_start() == action.start
    after = before.clone()
    after.place_candidate(length, action)

    result = [0.0] * len(FEATURE_NAMES)
    for start, (end, _cohort) in after.gaps.items():
        result[bin_gap(end - start)] += 1.0
    hist_end = 85
    history_count = max(1, len(before.length_history))
    for request, frequency in enumerate(before.length_freq):
        if request > 0:
            result[hist_end + request - 1] = frequency / history_count
    req_start = hist_end + 40
    result[req_start + length - 1] = 1.0

    summary_start = req_start + 40
    active_count = len(before.active)
    occupied = sum(pipe.length for pipe in before.active)
    tail_start = after.tail_start()
    tail_length = 0 if tail_start is None else after.trench - tail_start
    trench_denominator = max(1, before.trench)
    values = [
        math.log1p(active_count) / 10.0,
        math.log1p(len(after.gaps)) / 10.0,
        before.trench / 1_000_000.0,
        occupied / trench_denominator,
        min(tail_length, 400) / 400.0,
        action.start / trench_denominator,
        min(original_gap_length, 400) / 400.0,
        (original_gap_length - length) / 40.0,
        float(is_tail),
        float(action.high_side),
        float(original_cohort),
        float(before.length_occurrences[length] % 2),
        float(before.parity_cohort_mode),
        float(before.alternating_delete_mode),
        rank / 2.0,
    ]
    result[summary_start:] = values
    return result


def future_growth(sim, length: int, action, commands: list[int], start: int) -> int:
    rolled = sim.clone()
    initial = rolled.trench
    rolled.place_candidate(length, action)
    end = min(len(commands), start + HORIZON)
    for command in commands[start:end]:
        if command == 0:
            break
        if command > 0:
            rolled.place(command)
        else:
            rolled.remove_pid(-command)
    return int(rolled.trench - initial)


def collect_stream(path: Path, binary: Path, split: str):
    commands = parse_commands(path)
    outputs = run_solver(binary, commands)
    sim = joint.Sim()
    rows = []
    reply_index = 0
    cadence = TRAIN_CADENCE if split == "train" else (
        VALIDATION_CADENCE_LONG if len(commands) > 50_000 else VALIDATION_CADENCE_SHORT
    )
    for index, command in enumerate(commands):
        if command == 0:
            break
        actual = outputs[reply_index]
        reply_index += 1
        if command > 0:
            if (index >= MIN_COMMAND and index % cadence == 0
                    and index + HORIZON < len(commands)):
                options, baseline = candidates(sim, command)
                if len(options) >= 2 and (options[0].start, options[0].high_side) == (
                    baseline.start, baseline.high_side
                ):
                    state_id = f"{path.stem}:{index}"
                    targets = []
                    for rank, action in enumerate(options):
                        x = features(sim, command, action, rank)
                        y = future_growth(sim, command, action, commands, index + 1)
                        targets.append(y)
                        rows.append({
                            "state_id": state_id,
                            "stream": path.stem,
                            "command_index": index,
                            "candidate_rank": rank,
                            "baseline_action": int((action.start, action.high_side) ==
                                                   (baseline.start, baseline.high_side)),
                            "target_growth_m": y,
                            "features": x,
                        })
            reply = sim.place(command)
            if list(reply) != actual:
                raise RuntimeError(f"Python sim diverged from C++ at {path.name}:{index}: {reply} vs {actual}")
        else:
            reply = [sim.remove_pid(-command)]
            if reply != actual:
                raise RuntimeError(f"Python delete diverged at {path.name}:{index}: {reply} vs {actual}")
    return rows


def train_tree(X, y, rows, rng: random.Random):
    node_features = []
    node_thresholds = []
    node_left = []
    node_right = []
    node_values = []
    node_feature = []

    def build(indices: list[int], depth: int) -> int:
        node = len(node_values)
        mean = sum(y[i] for i in indices) / len(indices)
        node_values.append(mean)
        node_features.append(-1)
        node_thresholds.append(0.0)
        node_left.append(-1)
        node_right.append(-1)
        node_feature.append(-1)
        if depth >= TREE_DEPTH or len(indices) < MIN_LEAF * 2:
            return node

        features_to_try = rng.sample(range(len(X[0])), min(FEATURES_PER_NODE, len(X[0])))
        parent_sse = sum((y[i] - mean) ** 2 for i in indices)
        best_gain = 0.0
        best = None
        for feature in features_to_try:
            ordered = sorted(indices, key=lambda i: X[i][feature])
            n = len(ordered)
            total_sum = sum(y[i] for i in ordered)
            total_sq = sum(y[i] * y[i] for i in ordered)
            left_sum = 0.0
            left_sq = 0.0
            left_n = 0
            probe_positions = set(
                max(MIN_LEAF, min(n - MIN_LEAF, round(n * q / THRESHOLD_QUANTILES)))
                for q in range(1, THRESHOLD_QUANTILES)
            )
            for pos, idx in enumerate(ordered[:-1], start=1):
                left_sum += y[idx]
                left_sq += y[idx] * y[idx]
                left_n = pos
                if pos not in probe_positions or X[idx][feature] >= X[ordered[pos]][feature]:
                    continue
                right_n = n - pos
                right_sum = total_sum - left_sum
                right_sq = total_sq - left_sq
                gain = parent_sse - (left_sq - left_sum * left_sum / left_n) - (
                    right_sq - right_sum * right_sum / right_n
                )
                if gain > best_gain:
                    threshold = (X[idx][feature] + X[ordered[pos]][feature]) * 0.5
                    best_gain = gain
                    best = (feature, threshold, ordered[:pos], ordered[pos:])
        if best is None:
            return node
        feature, threshold, left_rows, right_rows = best
        node_feature[node] = feature
        node_features[node] = feature
        node_thresholds[node] = threshold
        node_left[node] = build(left_rows, depth + 1)
        node_right[node] = build(right_rows, depth + 1)
        return node

    root = build(rows, 0)
    return {
        "root": root,
        "feature": node_features,
        "threshold": node_thresholds,
        "left": node_left,
        "right": node_right,
        "value": node_values,
    }


def predict_tree(tree, x) -> float:
    node = tree["root"]
    while tree["feature"][node] >= 0:
        feature = tree["feature"][node]
        node = tree["left"][node] if x[feature] <= tree["threshold"][node] else tree["right"][node]
    return tree["value"][node]


def predict_forest(forest, x) -> float:
    return sum(predict_tree(tree, x) for tree in forest) / len(forest)


def fit_forest(rows):
    X = [row["features"] for row in rows]
    y = [float(row["target_growth_m"]) for row in rows]
    rng = random.Random(TRAIN_SEED)
    forest = []
    n = len(rows)
    for _ in range(TREES):
        bootstrap = [rng.randrange(n) for _ in range(n)]
        forest.append(train_tree(X, y, bootstrap, rng))
    return forest


def evaluate_model(rows, forest):
    states: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        row["prediction_m"] = predict_forest(forest, row["features"])
        states[row["state_id"]].append(row)
    stream_state: dict[str, list[dict]] = defaultdict(list)
    for state_rows in states.values():
        state_rows.sort(key=lambda row: row["candidate_rank"])
        if len(state_rows) < 2:
            continue
        baseline = next((row for row in state_rows if row["baseline_action"]), state_rows[0])
        chosen = min(state_rows, key=lambda row: (row["prediction_m"], row["candidate_rank"]))
        best_target = min(row["target_growth_m"] for row in state_rows)
        informative = [
            (a, b) for i, a in enumerate(state_rows) for b in state_rows[i + 1:]
            if a["target_growth_m"] != b["target_growth_m"]
        ]
        pair_correct = 0.0
        for a, b in informative:
            pred_a_better = a["prediction_m"] < b["prediction_m"]
            true_a_better = a["target_growth_m"] < b["target_growth_m"]
            pair_correct += 0.5 if a["prediction_m"] == b["prediction_m"] else float(pred_a_better == true_a_better)
        stream = state_rows[0]["stream"]
        stream_state[stream].append({
            "regret_baseline_m": baseline["target_growth_m"] - best_target,
            "regret_model_m": chosen["target_growth_m"] - best_target,
            "model_minus_baseline_m": chosen["target_growth_m"] - baseline["target_growth_m"],
            "pair_accuracy": pair_correct / len(informative) if informative else None,
            "informative_pairs": len(informative),
        })
    per_stream = {}
    for stream, vals in sorted(stream_state.items()):
        informative = [v for v in vals if v["pair_accuracy"] is not None]
        per_stream[stream] = {
            "states": len(vals),
            "baseline_regret_m": sum(v["regret_baseline_m"] for v in vals) / len(vals),
            "model_regret_m": sum(v["regret_model_m"] for v in vals) / len(vals),
            "model_minus_baseline_m": sum(v["model_minus_baseline_m"] for v in vals) / len(vals),
            "pair_accuracy": sum(v["pair_accuracy"] for v in informative) / len(informative) if informative else None,
        }
    deltas = [x["model_minus_baseline_m"] for x in per_stream.values()]
    rng = random.Random(20261017)
    boot = []
    if deltas:
        for _ in range(20_000):
            boot.append(sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas))
    boot.sort()
    return {
        "states": len(states),
        "stream_count": len(per_stream),
        "mean_model_minus_baseline_growth_m": sum(deltas) / len(deltas) if deltas else None,
        "stream_bootstrap_95_ci_m": [boot[int(0.025 * len(boot))], boot[min(len(boot)-1, int(0.975 * len(boot)))]] if boot else None,
        "streams_improved": sum(x < 0 for x in deltas),
        "streams_worsened": sum(x > 0 for x in deltas),
        "streams_tied": sum(x == 0 for x in deltas),
        "per_stream": per_stream,
    }


def write_cpp_header(forest, path: Path) -> None:
    nodes = []
    roots = []
    for tree in forest:
        offset = len(nodes)
        roots.append(offset + tree["root"])
        for i in range(len(tree["feature"])):
            nodes.append((tree["feature"][i], tree["threshold"][i],
                          -1 if tree["left"][i] < 0 else offset + tree["left"][i],
                          -1 if tree["right"][i] < 0 else offset + tree["right"][i],
                          tree["value"][i]))
    with path.open("w", encoding="ascii") as out:
        out.write("#pragma once\n#include <array>\n#include <cstddef>\n\nnamespace learned_gap_value {\n")
        out.write("struct Node { int feature; double threshold; int left; int right; double value; };\n")
        out.write(f"inline constexpr std::array<Node, {len(nodes)}> kNodes = {{{{\n")
        for f, threshold, left, right, value in nodes:
            out.write(f"    Node{{{f}, {threshold:.17g}, {left}, {right}, {value:.17g}}},\n")
        out.write("}};\n")
        out.write(f"inline constexpr std::array<int, {len(roots)}> kRoots = {{{{")
        out.write(", ".join(map(str, roots)))
        out.write("}};\n")
        out.write(f"inline constexpr std::size_t kFeatureCount = {len(FEATURE_NAMES)};\n")
        out.write("inline double predict(const std::array<double, kFeatureCount>& x) {\n")
        out.write("    double total = 0.0;\n")
        out.write("    for (int root : kRoots) { int node = root; while (kNodes[static_cast<std::size_t>(node)].feature >= 0) { const Node& n = kNodes[static_cast<std::size_t>(node)]; node = x[static_cast<std::size_t>(n.feature)] <= n.threshold ? n.left : n.right; } total += kNodes[static_cast<std::size_t>(node)].value; }\n")
        out.write("    return total / static_cast<double>(kRoots.size());\n}\n}\n")


def main() -> None:
    baseline = HERE / "bin" / "frozen_nomc"
    labeler = HERE / "bin" / "label_runner"
    if not baseline.exists():
        raise RuntimeError("compile frozen_nomc first")
    subprocess.run([sys.executable, str(HERE / "build_labeler.py")], cwd=ROOT, check=True)
    subprocess.run([
        "clang++", "-O2", "-std=c++20", "-Wall", "-Wextra", "-Wconversion",
        "-Wshadow", "-pedantic", "-Werror", str(HERE / "src" / "label_runner.cpp"),
        "-o", str(labeler),
    ], cwd=ROOT, check=True)

    label_root = HERE / "training" / "labels"
    reply_root = HERE / "training" / "baseline_replies"
    label_root.mkdir(parents=True, exist_ok=True)
    reply_root.mkdir(parents=True, exist_ok=True)
    label_files = {"train": [], "validation": []}
    input_hashes = {"train": {}, "validation": {}}
    reply_hashes = {"train": {}, "validation": {}}
    for split in ("train", "validation"):
        inputs = sorted((HERE / "inputs" / split).glob("*.in"))
        for path in inputs:
            print(f"label {split}/{path.name}", flush=True)
            tokens = path.read_text(encoding="ascii").split()
            commands = [int(value) for value in tokens[2:]]
            replies = run_solver(baseline, commands)
            reply_path = reply_root / f"{split}_{path.stem}.txt"
            reply_path.write_text("".join(" ".join(map(str, row)) + "\n" for row in replies), encoding="ascii")
            label_path = label_root / f"{split}_{path.stem}.csv"
            cadence = TRAIN_CADENCE if split == "train" else (
                VALIDATION_CADENCE_LONG if len(commands) > 50_000 else VALIDATION_CADENCE_SHORT
            )
            subprocess.run([
                str(labeler), str(path), str(reply_path), split, path.stem,
                str(cadence), str(label_path),
            ], cwd=ROOT, check=True, capture_output=True, text=True)
            label_files[split].append(label_path)
            input_hashes[split][str(path.relative_to(ROOT))] = sha256(path)
            reply_hashes[split][str(reply_path.relative_to(ROOT))] = sha256(reply_path)

    def load_rows(paths):
        rows = []
        for path in paths:
            with path.open(newline="", encoding="ascii") as handle:
                for record in csv.DictReader(handle):
                    rows.append({
                        "stream": record["stream"],
                        "state_id": record["state_id"],
                        "command_index": int(record["command_index"]),
                        "candidate_rank": int(record["candidate_rank"]),
                        "baseline_action": int(record["baseline_action"]),
                        "target_growth_m": int(record["target_growth_m"]),
                        "features": [float(record[f"f{i}"]) for i in range(len(FEATURE_NAMES))],
                    })
        return rows

    training_rows = load_rows(label_files["train"])
    validation_rows = load_rows(label_files["validation"])
    if len(training_rows) < 300:
        raise RuntimeError(f"too few training candidates: {len(training_rows)}")
    forest = fit_forest(training_rows)
    metrics = evaluate_model(validation_rows, forest)

    out_dir = HERE / "training"
    out_dir.mkdir(exist_ok=True)
    model_json = out_dir / "forest.json"
    model_json.write_text(json.dumps(forest, separators=(",", ":")) + "\n", encoding="utf-8")
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (out_dir / "feature_names.json").write_text(json.dumps(FEATURE_NAMES, indent=2) + "\n", encoding="utf-8")
    write_cpp_header(forest, HERE / "src" / "learned_model.hpp")
    with (out_dir / "validation_predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["stream", "state_id", "command_index", "candidate_rank", "baseline_action",
                  "target_growth_m", "prediction_m"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in validation_rows:
            writer.writerow({key: row.get(key) for key in fields})
    dataset_manifest = {
        "baseline_sha256": sha256(BASELINE),
        "simulation_reference_sha256": sha256(BASELINE),
        "labeler_source_sha256": sha256(HERE / "src" / "label_runner.cpp"),
        "labeler_binary_sha256": sha256(labeler),
        "labeler_build": "clang++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror",
        "input_hashes": input_hashes,
        "baseline_reply_hashes": reply_hashes,
        "training_candidate_rows": len(training_rows),
        "training_states": len({row["state_id"] for row in training_rows}),
        "validation_candidate_rows": len(validation_rows),
        "validation_states": len({row["state_id"] for row in validation_rows}),
        "label_horizon_commands": HORIZON,
        "training_sampling_cadence": TRAIN_CADENCE,
        "validation_cadence_short": VALIDATION_CADENCE_SHORT,
        "validation_cadence_long": None,
        "forest": {"trees": TREES, "max_depth": TREE_DEPTH,
                   "min_leaf_rows": MIN_LEAF, "features_per_node": FEATURES_PER_NODE,
                   "threshold_quantiles": THRESHOLD_QUANTILES, "seed": TRAIN_SEED},
        "features": FEATURE_NAMES,
        "files": {},
    }
    for path in [model_json, out_dir / "metrics.json", out_dir / "feature_names.json",
                 out_dir / "validation_predictions.csv", HERE / "src" / "learned_model.hpp"]:
        dataset_manifest["files"][str(path.relative_to(ROOT))] = sha256(path)
    (out_dir / "manifest.json").write_text(json.dumps(dataset_manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics.items() if k != "per_stream"}, indent=2))
    print(f"train_rows={len(training_rows)} validation_rows={len(validation_rows)} features={len(FEATURE_NAMES)}")


if __name__ == "__main__":
    main()
