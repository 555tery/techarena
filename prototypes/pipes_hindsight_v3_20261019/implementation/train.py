#!/usr/bin/env python3
"""Fixed pairwise logistic recipe. Run on training labels only; no split tuning."""
import argparse
import hashlib
import json
import math
from pathlib import Path

RECIPE = {
    "estimator": "pairwise_logistic_linear_no_intercept",
    "features": 128,
    "feature_schema": "causal_cross128_v1",
    "minimum_cost_gap": 20,
    "l2": 0.05,
    "max_newton_iterations": 40,
    "gradient_tolerance": 1e-8,
    "line_search": "at most 20 fixed halvings, Armijo 1e-4",
    "pair_weighting": "each informative state has equal total weight; all pairs with gap>=20",
    "selection": "higher linear score; deterministic BF-first tie order",
    "feature_scaling": "fixed causal_cross128_v1; no fitted scaling",
    "hyperparameter_sweep": False,
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(out, weights, trained, fit, files):
    out.mkdir(parents=True, exist_ok=True)
    values = ",\n    ".join(format(float(w), ".17g") for w in weights)
    header = ("#pragma once\n#include <array>\nnamespace hindsight_v3 {\n"
              f"inline constexpr bool ModelTrained={'true' if trained else 'false'};\n"
              "inline constexpr std::array<double,128> ModelWeights{{\n    " + values +
              "\n}};\n} // namespace hindsight_v3\n")
    (out / "model.hpp").write_text(header)
    fit.update(recipe=RECIPE, trained=trained, weights=list(map(float, weights)))
    (out / "fit.json").write_text(json.dumps(fit, indent=2, allow_nan=False) + "\n")
    sources = {p.name: sha(p) for p in sorted(Path(__file__).parent.iterdir())
               if p.is_file() and p.suffix in {".hpp", ".cpp", ".py", ".md"}}
    manifest = {
        "schema": "pipes-hindsight-v3-artifacts",
        "source_hashes_sha256": sources,
        "labels_sha256": {str(p.resolve()): sha(p) for p in files},
        "model_sha256": sha(out / "model.hpp"),
        "fit_sha256": sha(out / "fit.json"),
        "recipe": RECIPE,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if not args.labels_dir.is_dir():
        ap.error("--labels-dir must exist")
    files = sorted(args.labels_dir.rglob("*.jsonl"))
    differences, weights = [], []
    states = action_count = informative = 0
    pair_gaps = []
    for file in files:
        for line_number, line in enumerate(file.read_text().splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("schema") != "pipes-hindsight-v3":
                raise ValueError(f"unknown schema: {file}:{line_number}")
            if row.get("feature_schema") != RECIPE["feature_schema"]:
                raise ValueError(f"incompatible feature schema: {file}:{line_number}")
            states += 1
            actions = row["actions"]
            action_count += len(actions)
            pairs = []
            for a in actions:
                if len(a["features"]) != 128 or not all(math.isfinite(x) for x in a["features"]):
                    raise ValueError("expected 128 finite features")
                if a["cost"] > a["bf_suffix_cost"]:
                    raise ValueError("teacher label violates complete BF upper bound")
            for i, a in enumerate(actions):
                for b in actions[i + 1:]:
                    gap = abs(a["cost"] - b["cost"])
                    if gap < RECIPE["minimum_cost_gap"]:
                        continue
                    better, worse = (a, b) if a["cost"] < b["cost"] else (b, a)
                    pairs.append([x - y for x, y in zip(better["features"], worse["features"])])
                    pair_gaps.append(gap)
            if pairs:
                informative += 1
                differences.extend(pairs)
                weights.extend([1.0 / len(pairs)] * len(pairs))
    fit = {"status": "pending", "label_files": len(files), "label_states": states,
           "actions": action_count, "informative_states": informative, "pairs": len(differences),
           "cost_gap_min": min(pair_gaps, default=None), "cost_gap_max": max(pair_gaps, default=None)}
    if not differences:
        fit.update(status="fail_no_informative_labels", reason="No cost-gap>=20 pairs; emitted BF-identical model")
        emit(args.out, [0.0] * 128, False, fit, files)
        print(json.dumps({k: v for k, v in fit.items() if k != "weights"}))
        return 3
    import numpy as np
    x = np.asarray(differences, dtype=np.float64)
    sample_weight = np.asarray(weights, dtype=np.float64)
    sample_weight /= sample_weight.sum()
    w = np.zeros(128, dtype=np.float64)
    l2 = RECIPE["l2"]

    def objective(v):
        return float(sample_weight @ np.logaddexp(0.0, -(x @ v)) + 0.5 * l2 * (v @ v))

    iterations = 0
    for step in range(RECIPE["max_newton_iterations"]):
        margin = x @ w
        q = 0.5 * (1.0 - np.tanh(margin / 2.0))
        grad = -(x.T @ (sample_weight * q)) + l2 * w
        if float(np.max(np.abs(grad))) < RECIPE["gradient_tolerance"]:
            break
        curvature = sample_weight * q * (1.0 - q)
        hessian = x.T @ (curvature[:, None] * x) + l2 * np.eye(128)
        delta = np.linalg.solve(hessian, grad)
        old = objective(w)
        rate = 1.0
        for _ in range(20):
            proposed = w - rate * delta
            if objective(proposed) <= old - 1e-4 * rate * float(grad @ delta):
                w = proposed
                break
            rate *= 0.5
        else:
            break
        iterations = step + 1
    if not np.all(np.isfinite(w)):
        raise ValueError("nonfinite fit")
    margin = x @ w
    fit.update(status="fit_complete", iterations=iterations, objective=objective(w),
               training_pair_accuracy=float(np.mean(margin > 0)),
               training_weighted_pair_accuracy=float(sample_weight @ (margin > 0)),
               note="Training diagnostics only; no rollout or generalization claim")
    emit(args.out, w, True, fit, files)
    print(json.dumps({k: v for k, v in fit.items() if k not in {"weights", "recipe"}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
