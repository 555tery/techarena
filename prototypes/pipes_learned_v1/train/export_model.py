#!/usr/bin/env python3
"""Atomically export a saved MLP model.json and optionally check C++ score parity."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import random
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


INPUTS = 128
DEFAULT_SAMPLE_COUNT = 128
DEFAULT_TOLERANCE = 5.0e-5


def load_trainer():
    trainer_path = Path(__file__).with_name("train_mlp.py")
    spec = importlib.util.spec_from_file_location("pipes_learned_train_mlp", trainer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load trainer helpers from {trainer_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_model(model_path: Path) -> tuple[dict[str, Any], np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    record = json.loads(model_path.read_text(encoding="utf-8"))
    if record.get("format") != "pipes_learned_mlp_v1":
        raise ValueError(f"unsupported model format in {model_path}")
    if record.get("architecture") != [128, 32, 1]:
        raise ValueError(f"unsupported architecture: {record.get('architecture')}")
    mean = np.asarray(record["normalization"]["mean"], dtype=np.float32)
    scale = np.asarray(record["normalization"]["scale"], dtype=np.float32)
    weights = record["weights"]
    params = {
        "w1": np.asarray(weights["w1_row_major_128x32"], dtype=np.float32).reshape(128, 32),
        "b1": np.asarray(weights["b1"], dtype=np.float32),
        "w2": np.asarray(weights["w2"], dtype=np.float32),
        "b2": np.asarray([weights["b2"]], dtype=np.float32),
    }
    if mean.shape != (INPUTS,) or scale.shape != (INPUTS,):
        raise ValueError("normalization tensors must have 128 entries")
    if params["b1"].shape != (32,) or params["w2"].shape != (32,):
        raise ValueError("hidden-layer tensors must have 32 entries")
    if not all(np.all(np.isfinite(array)) for array in (mean, scale, *params.values())):
        raise ValueError("model contains non-finite inference values")
    return record, mean, scale, params


def read_parity_features(
    path: Path,
    sample_count: int,
) -> tuple[np.ndarray, list[tuple[str, str, int, int]], int]:
    fields = [f"f{i}" for i in range(INPUTS)]
    metadata_fields = ("stream", "state", "action", "is_base")
    reservoir: list[list[float]] = []
    metadata: list[tuple[str, str, int, int]] = []
    rng = random.Random(20261017)
    seen = 0
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or any(
            field not in reader.fieldnames for field in (*metadata_fields, *fields)
        ):
            raise ValueError(f"{path}: expected stream/state/action/is_base and f0..f127 columns")
        for line_no, row in enumerate(reader, start=2):
            try:
                features = [float(row[field]) for field in fields]
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{path}: invalid features on line {line_no}: {exc}") from exc
            if not all(np.isfinite(features)):
                raise ValueError(f"{path}: non-finite feature on line {line_no}")
            stream = (row["stream"] or "").strip()
            state = (row["state"] or "").strip()
            try:
                action = int(row["action"])
                is_base = int(row["is_base"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{path}: invalid action metadata on line {line_no}") from exc
            if not stream or not state or action < 0 or is_base not in (0, 1):
                raise ValueError(f"{path}: invalid action metadata on line {line_no}")
            metadata.append((stream, state, action, is_base))
            seen += 1
            if len(reservoir) < sample_count:
                reservoir.append(features)
            else:
                replacement = rng.randrange(seen)
                if replacement < sample_count:
                    reservoir[replacement] = features
    if not reservoir:
        raise ValueError(f"no feature rows found in {path}")
    return np.asarray(reservoir, dtype=np.float32), metadata, seen


def scalar_cpp_order_score(
    features: np.ndarray,
    mean: np.ndarray,
    scale: np.ndarray,
    params: dict[str, np.ndarray],
) -> float:
    """Emulate the exported C++ loop using ordered float32 operations."""
    hidden = params["b1"].copy()
    for i in range(INPUTS):
        normalized = np.float32(np.float32(features[i] - mean[i]) * scale[i])
        normalized = np.float32(min(8.0, max(-8.0, float(normalized))))
        hidden += np.float32(normalized * params["w1"][i])
    result = np.float32(params["b2"][0])
    for j in range(32):
        activation = np.float32(max(0.0, float(hidden[j])))
        result = np.float32(result + np.float32(activation * params["w2"][j]))
    return float(result)


def cpp_order_scores(
    features: np.ndarray,
    mean: np.ndarray,
    scale: np.ndarray,
    params: dict[str, np.ndarray],
) -> np.ndarray:
    """Vectorize across examples while preserving C++ float32 accumulation order."""
    count = len(features)
    hidden = np.broadcast_to(params["b1"], (count, 32)).copy()
    for i in range(INPUTS):
        normalized = np.float32((features[:, i] - mean[i]) * scale[i])
        np.clip(normalized, -8.0, 8.0, out=normalized)
        hidden += normalized[:, None] * params["w1"][i][None, :]
    activations = np.maximum(np.float32(0.0), hidden)
    result = np.full(count, params["b2"][0], dtype=np.float32)
    for j in range(32):
        result += activations[:, j] * params["w2"][j]
    return result


def compile_and_check(
    header_path: Path,
    features: np.ndarray,
    mean: np.ndarray,
    scale: np.ndarray,
    params: dict[str, np.ndarray],
    compiler: str,
    tolerance: float,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    include_path = json.dumps(str(header_path.resolve()))
    source = f'''#include <array>
#include <iomanip>
#include <iostream>
#include {include_path}

int main() {{
    std::array<float, 128> features{{}};
    std::cout << std::setprecision(10);
    while (true) {{
        for (float& value : features) {{
            if (!(std::cin >> value)) return std::cin.eof() ? 0 : 2;
        }}
        std::cout << learned_model::score(features) << '\\n';
    }}
}}
'''
    with tempfile.TemporaryDirectory(prefix="pipes-model-export-") as temp_dir:
        temp = Path(temp_dir)
        source_path = temp / "score_parity.cpp"
        binary_path = temp / "score_parity"
        source_path.write_text(source, encoding="utf-8")
        command = [
            *shlex.split(compiler), "-std=c++17", "-O0", str(source_path), "-o", str(binary_path)
        ]
        build = subprocess.run(command, capture_output=True, text=True, check=False)
        if build.returncode:
            raise RuntimeError(
                "C++ score parity compile failed:\n"
                + build.stdout[-4000:]
                + build.stderr[-4000:]
            )
        input_text = "".join(
            " ".join(format(float(value), ".9g") for value in row) + "\n"
            for row in features
        )
        run = subprocess.run(
            [str(binary_path)], input=input_text, capture_output=True, text=True, check=False
        )
        if run.returncode:
            raise RuntimeError(
                f"C++ score parity executable failed ({run.returncode}): {run.stderr[-4000:]}"
            )
        cpp_scores = [float(line) for line in run.stdout.splitlines() if line.strip()]
    if len(cpp_scores) != len(features):
        raise RuntimeError(f"expected {len(features)} C++ scores, got {len(cpp_scores)}")
    expected = cpp_order_scores(features, mean, scale, params).astype(np.float64)
    scalar_count = min(8, len(features))
    scalar_expected = np.asarray(
        [
            scalar_cpp_order_score(features[index], mean, scale, params)
            for index in range(scalar_count)
        ],
        dtype=np.float64,
    )
    if not np.array_equal(expected[:scalar_count], scalar_expected):
        raise RuntimeError("vectorized float32 reference differs from scalar C++-order reference")
    actual = np.asarray(cpp_scores, dtype=np.float64)
    differences = np.abs(actual - expected)
    max_difference = float(differences.max(initial=0.0))
    if max_difference > tolerance:
        raise RuntimeError(
            f"C++ score parity failed: max_abs_diff={max_difference:.9g} > {tolerance:.9g}"
        )
    diagnostic = {
        "samples": len(features),
        "tolerance_score_units": tolerance,
        "max_abs_diff_score_units": max_difference,
        "passed": True,
        "compiler_command": command,
    }
    return diagnostic, actual, expected


def compare_selection_actions(
    metadata: list[tuple[str, str, int, int]],
    cpp_scores: np.ndarray,
    python_scores: np.ndarray,
    margin: float,
) -> dict[str, Any]:
    if len(metadata) != len(cpp_scores) or len(metadata) != len(python_scores):
        raise ValueError("selection parity requires one score per complete CSV row")
    groups: dict[tuple[str, str], list[int]] = {}
    for index, (stream, state, _action, _is_base) in enumerate(metadata):
        groups.setdefault((stream, state), []).append(index)
    margin32 = np.float32(margin)
    action_mismatches = 0
    float64_float32_margin_changes = 0
    for key, rows in groups.items():
        base_rows = [row for row in rows if metadata[row][3] == 1]
        if len(base_rows) != 1:
            raise ValueError(f"state {key}: expected exactly one baseline row")
        base_row = base_rows[0]

        def selected_action(scores: np.ndarray) -> int | None:
            baseline_score = np.float32(scores[base_row])
            eligible: list[tuple[float, int]] = []
            for row in rows:
                if row == base_row:
                    continue
                candidate_score = np.float32(scores[row])
                if np.float32(baseline_score - candidate_score) > margin32:
                    eligible.append((float(candidate_score), metadata[row][2]))
            return min(eligible)[1] if eligible else None

        if selected_action(cpp_scores) != selected_action(python_scores):
            action_mismatches += 1
        baseline_python = float(np.float32(python_scores[base_row]))
        baseline_python32 = np.float32(baseline_python)
        for row in rows:
            if row == base_row:
                continue
            candidate = float(np.float32(python_scores[row]))
            candidate32 = np.float32(candidate)
            old_float64_eligible = candidate < baseline_python - float(margin)
            current_float32_eligible = (
                np.float32(baseline_python32 - candidate32) > margin32
            )
            if old_float64_eligible != current_float32_eligible:
                float64_float32_margin_changes += 1
    return {
        "states": len(groups),
        "deployment_margin": float(margin),
        "cpp_vs_python_selected_action_mismatches": action_mismatches,
        "float64_vs_float32_candidate_margin_changes": float64_float32_margin_changes,
        "passed": action_mismatches == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-json", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--parity-csv", type=Path)
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT)
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    parser.add_argument("--cxx", default=os.environ.get("CXX", "c++"))
    args = parser.parse_args()
    model_path = args.model_json.expanduser().resolve()
    output_path = args.header.expanduser().resolve()
    if args.sample_count <= 0 or args.tolerance < 0:
        parser.error("sample-count must be positive and tolerance nonnegative")
    trainer = load_trainer()
    record, mean, scale, params = read_model(model_path)
    diagnostic = record["calibration"]["diagnostic"]
    model_json_hash = trainer.file_sha256(model_path)
    parameter_hash = trainer.weights_sha256(mean, scale, params)
    recorded_parameter_hash = record.get("inference_parameters_sha256")
    if recorded_parameter_hash is not None and recorded_parameter_hash != parameter_hash:
        raise ValueError("saved inference_parameters_sha256 does not match model tensors")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_header = output_path.with_name(
        f".{output_path.name}.{os.getpid()}.{model_json_hash[:12]}.staged"
    )
    try:
        trainer.export_header(
            temporary_header, mean, scale, params, diagnostic,
            model_json_hash, parameter_hash,
        )
        parity = None
        selection_diagnostic = None
        if args.parity_csv:
            features, metadata, total_rows = read_parity_features(
                args.parity_csv.expanduser().resolve(), args.sample_count
            )
            parity, cpp_scores, python_scores = compile_and_check(
                temporary_header, features, mean, scale, params, args.cxx, args.tolerance
            )
            parity["csv"] = str(args.parity_csv.expanduser().resolve())
            if len(features) == total_rows:
                margin = (
                    diagnostic["deployment_margin"]
                    if diagnostic["deployable"]
                    else 1.0e30
                )
                selection_diagnostic = compare_selection_actions(
                    metadata, cpp_scores, python_scores, margin
                )
                if not selection_diagnostic["passed"]:
                    raise RuntimeError("C++ and Python runtime action selection differ")
        temporary_header.replace(output_path)
    finally:
        temporary_header.unlink(missing_ok=True)

    header_hash = trainer.file_sha256(output_path)
    manifest = {
        "model_json": str(model_path),
        "model_json_sha256": model_json_hash,
        "inference_parameters_sha256": parameter_hash,
        "header": str(output_path),
        "header_sha256": header_hash,
        "score_parity": parity,
        "selection_parity": selection_diagnostic,
    }
    trainer.write_text_atomic(
        output_path.with_suffix(output_path.suffix + ".manifest.json"),
        json.dumps(manifest, indent=2) + "\n",
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
