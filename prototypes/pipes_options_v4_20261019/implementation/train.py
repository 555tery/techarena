#!/usr/bin/env python3
"""Fixed multioutput tree. Training diagnostics do not establish rollout gains."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

RECIPE = {
    "estimator": "sklearn.tree.DecisionTreeRegressor", "max_depth": 5,
    "min_samples_leaf": 8, "random_state": 20261019,
    "feature_schema": "causal_state128_bf_v1", "features": 128,
    "target": "gain_i=(cost_option0-cost_option_i)/20", "outputs": 4,
    "all_ties_included": True, "sample_weight": "1/count(complete observable_key)",
    "selection": "lowest index maximizing gain, unless max gain <0.25 then BF",
    "gain_threshold": 0.25, "hyperparameter_selection": False,
    "features_dtype": "float32", "wave_count": 3, "final_checkpoint": "M3",
    "options": ["BFleft", "BFright", "FFleft", "anchored_BFleft_then_BFright"],
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")

def select(values):
    best = max(range(4), key=lambda i: values[i])
    return best if values[best] >= .25 else 0

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    files = sorted(args.labels_dir.rglob("*.jsonl"))
    if not args.labels_dir.is_dir() or not files:
        ap.error("labels directory must contain jsonl files")
    rows = []
    for file in files:
        for line_no, line in enumerate(file.read_text().splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("schema") != "pipes-options-v4" or row.get("feature_schema") != RECIPE["feature_schema"]:
                raise ValueError(f"incompatible schema: {file}:{line_no}")
            features = row["features"]
            if len(features) != 128 or not all(math.isfinite(v) for v in features):
                raise ValueError("expected 128 finite causal features")
            options = row["options"]
            if len(options) != 4 or [v["index"] for v in options] != list(range(4)):
                raise ValueError("expected four ordered options")
            if any(o["cost"] > o["reference_cost"] for o in options):
                raise ValueError("teacher cost exceeds complete BF reference")
            target = [(options[0]["cost"] - o["cost"]) / 20. for o in options]
            if len(row["gains"])!=4 or any(not math.isfinite(v) for v in target) or any(abs(a-b)>1e-12 for a,b in zip(target,row["gains"])):
                raise ValueError("gain target mismatch")
            if not isinstance(row["observable_key"], str) or not row["observable_key"]:
                raise ValueError("complete observable key is required")
            rows.append((row["observable_key"], features, target))
    if not rows:
        raise ValueError("no labeled states")
    import numpy as np
    import sklearn
    from sklearn.tree import DecisionTreeRegressor
    counts = Counter(r[0] for r in rows)
    x = np.asarray([r[1] for r in rows], dtype=np.float32)
    y = np.asarray([r[2] for r in rows], dtype=np.float64)
    weights = np.asarray([1. / counts[r[0]] for r in rows], dtype=np.float64)
    estimator = DecisionTreeRegressor(max_depth=5, min_samples_leaf=8, random_state=20261019)
    estimator.fit(x, y, sample_weight=weights)
    tree = estimator.tree_
    arrays = {
        "feature": tree.feature.tolist(), "threshold": tree.threshold.tolist(),
        "left": tree.children_left.tolist(), "right": tree.children_right.tolist(),
        "value": tree.value[:, :, 0].tolist(),
    }
    labels_hashes = {str(p.resolve()): sha(p) for p in files}
    provenance = hashlib.sha256(json.dumps({"labels":labels_hashes,"recipe":RECIPE},sort_keys=True).encode()).hexdigest()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    header = ["#pragma once", "#include <array>", "namespace options_v4 {",
              "inline constexpr bool ModelTrained=true;",
              f'inline constexpr const char* ModelProvenance="sha256:{provenance}";']
    for name, ctype in [("feature", "int"), ("threshold", "double"), ("left", "int"), ("right", "int")]:
        values = ",".join(format(v, ".17g") if ctype == "double" else str(v) for v in arrays[name])
        header.append(f"inline constexpr {ctype} Tree_{name}[] = {{{values}}};")
    values = ",\n".join("{" + ",".join(format(float(v), ".17g") for v in row) + "}" for row in arrays["value"])
    header.extend(["inline constexpr double Tree_value[][4] = {" + values + "};",
      "inline std::array<double,4> predict(const std::array<float,128>& x) {",
      "  int node=0; while(Tree_left[node]>=0) node=(static_cast<double>(x[Tree_feature[node]])<=Tree_threshold[node])?Tree_left[node]:Tree_right[node];",
      "  return {{Tree_value[node][0],Tree_value[node][1],Tree_value[node][2],Tree_value[node][3]}};", "}", "}"])
    (out / "model.hpp").write_text("\n".join(header) + "\n")
    dump(out / "tree.json", {"schema":"pipes-options-v4-tree", "recipe":RECIPE, "arrays":arrays})
    predictions = estimator.predict(x)
    fixtures = [{"features":row.tolist(),"gains":pred.tolist(),"option":select(pred)} for row,pred in zip(x,predictions)]
    dump(out / "parity_fixtures.json", {"schema":"pipes-options-v4-parity", "fixtures":fixtures})
    fit = {"status":"fit_complete", "recipe":RECIPE, "label_files":len(files), "label_states":len(rows),
           "observable_groups":len(counts), "ties":int(np.sum(np.all(y == 0,axis=1))),
           "node_count":tree.node_count, "depth":tree.max_depth, "sklearn_version":sklearn.__version__,
           "weighted_training_mse":float(np.average(np.mean((predictions-y)**2,axis=1),weights=weights)),
           "provenance":provenance, "note":"Training diagnostics only; no rollout or transfer claim"}
    dump(out / "fit.json", fit)
    sources = {p.name:sha(p) for p in sorted(Path(__file__).parent.iterdir()) if p.is_file() and (p.suffix in {".cpp",".hpp",".py",".md"} or p.name=="Makefile")}
    dump(out / "manifest.json", {"schema":"pipes-options-v4-model-manifest", "recipe":RECIPE,
         "source_hashes_sha256":sources,"labels_sha256":labels_hashes,
         "artifacts_sha256":{name:sha(out/name) for name in ["model.hpp","tree.json","fit.json","parity_fixtures.json"]}})
    print(json.dumps(fit,allow_nan=False))

if __name__ == "__main__":
    main()
