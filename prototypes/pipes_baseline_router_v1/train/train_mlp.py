#!/usr/bin/env python3
"""Train the fixed small MLP scorer from counterfactual action labels."""

from __future__ import annotations

import argparse
import array
import csv
import hashlib
import json
import math
import os
import shlex
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


SEED = 20261017
INPUTS = 128
HIDDEN = 16
PARAMETER_COUNT = INPUTS * HIDDEN + HIDDEN + HIDDEN + 1
MAX_EPOCHS = 120
PATIENCE = 15
BATCH_STATES = 64
LEARNING_RATE = 0.001
BETA1 = 0.9
BETA2 = 0.999
ADAM_EPS = 1.0e-8
WEIGHT_DECAY = 1.0e-5
HUBER_DELTA = 1.0
REGRESSION_MIX = 0.5
PAIRWISE_MIX = 0.5
MARGINS = (0.0, 0.5, 1.0, 2.0)
CLIP_Z = 8.0


@dataclass
class Dataset:
    x: np.ndarray
    target: np.ndarray
    group_rows: list[np.ndarray]
    group_stream: list[str]
    group_state: list[str]
    base_trench: np.ndarray
    target_trench: np.ndarray
    baseline_row: np.ndarray
    action: list[int]
    pair_rows_i: list[np.ndarray]
    pair_rows_j: list[np.ndarray]
    pair_sign: list[np.ndarray]
    stream_groups: dict[str, list[int]]
    csv_path: str
    sha256: str

    @property
    def rows(self) -> int:
        return int(self.x.shape[0])

    @property
    def groups(self) -> int:
        return len(self.group_rows)

    @property
    def streams(self) -> int:
        return len(self.stream_groups)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def weights_sha256(
    mean: np.ndarray,
    scale: np.ndarray,
    params: dict[str, np.ndarray],
) -> str:
    """Hash the exact ordered float32 inference tensors in little-endian form."""
    digest = hashlib.sha256()
    digest.update(b"pipes_baseline_router_mlp_v1\0[128,16,1]\0")
    tensors = (
        ("mean", mean, (INPUTS,)),
        ("scale", scale, (INPUTS,)),
        ("w1", params["w1"], (INPUTS, HIDDEN)),
        ("b1", params["b1"], (HIDDEN,)),
        ("w2", params["w2"], (HIDDEN,)),
        ("b2", params["b2"], (1,)),
    )
    for name, tensor, shape in tensors:
        digest.update(name.encode("ascii") + b"\0")
        digest.update((",".join(map(str, shape))).encode("ascii") + b"\0")
        digest.update(np.asarray(tensor, dtype="<f4").reshape(shape).tobytes(order="C"))
    return digest.hexdigest()


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output_mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, output_mode)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def parse_bool01(text: str, column: str, line_no: int) -> int:
    value = text.strip()
    if value in ("0", "1"):
        return int(value)
    raise ValueError(f"line {line_no}: {column} must be 0 or 1, got {text!r}")


def load_csv(path: Path) -> Dataset:
    expected = [
        "stream", "state", "action", "is_base", "target_trench", "base_trench",
        *(f"f{i}" for i in range(INPUTS)),
    ]
    feature_values = array.array("f")
    targets: list[float] = []
    target_trench: list[float] = []
    base_trench: list[float] = []
    actions: list[int] = []
    grouped_rows: dict[tuple[str, str], list[int]] = {}
    group_stream: dict[tuple[str, str], str] = {}
    group_base_trench: dict[tuple[str, str], float] = {}
    group_base_rows: dict[tuple[str, str], list[int]] = {}

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"empty CSV: {path}")
        missing = [name for name in expected if name not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path}: missing CSV columns: {', '.join(missing)}")
        for line_no, row in enumerate(reader, start=2):
            stream = (row["stream"] or "").strip()
            state = (row["state"] or "").strip()
            action_text = (row["action"] or "").strip()
            if not stream or not state or not action_text:
                raise ValueError(f"line {line_no}: stream, state, and action must be nonempty")
            try:
                action = int(action_text)
            except ValueError as exc:
                raise ValueError(
                    f"line {line_no}: action must be a numeric candidate index"
                ) from exc
            if action < 0:
                raise ValueError(f"line {line_no}: action index must be nonnegative")
            key = (stream, state)
            is_base = parse_bool01(row["is_base"] or "", "is_base", line_no)
            try:
                y_trench = float(row["target_trench"])
                b_trench = float(row["base_trench"])
                feats = [float(row[f"f{i}"]) for i in range(INPUTS)]
            except (TypeError, ValueError) as exc:
                raise ValueError(f"line {line_no}: invalid numeric label or feature: {exc}") from exc
            if not math.isfinite(y_trench) or not math.isfinite(b_trench):
                raise ValueError(f"line {line_no}: non-finite trench label")
            if not all(map(math.isfinite, feats)):
                raise ValueError(f"line {line_no}: non-finite feature")
            if y_trench < 0.0 or b_trench < 0.0:
                raise ValueError(f"line {line_no}: trench lengths must be nonnegative")
            if key in group_base_trench:
                if abs(group_base_trench[key] - b_trench) > 1.0e-6:
                    raise ValueError(f"line {line_no}: base_trench varies within state {key}")
            else:
                grouped_rows[key] = []
                group_stream[key] = stream
                group_base_trench[key] = b_trench
                group_base_rows[key] = []
            if is_base:
                if action != 0:
                    raise ValueError(f"line {line_no}: baseline action index must be 0")
                if abs(y_trench - b_trench) > 1.0e-6:
                    raise ValueError(
                        f"line {line_no}: baseline target_trench must equal base_trench"
                    )
                group_base_rows[key].append(len(targets))
            index = len(targets)
            grouped_rows[key].append(index)
            feature_values.extend(feats)
            targets.append((y_trench - b_trench) / 20.0)
            target_trench.append(y_trench)
            base_trench.append(b_trench)
            actions.append(action)

    if not targets:
        raise ValueError(f"no label rows in {path}")
    group_keys = list(grouped_rows)
    group_rows = [np.asarray(grouped_rows[key], dtype=np.int64) for key in group_keys]
    streams: dict[str, list[int]] = {}
    baseline_rows: list[int] = []
    target_array = np.asarray(targets, dtype=np.float32)
    pair_rows_i: list[np.ndarray] = []
    pair_rows_j: list[np.ndarray] = []
    pair_sign: list[np.ndarray] = []
    for group_id, key in enumerate(group_keys):
        selected = group_base_rows[key]
        if len(selected) != 1:
            raise ValueError(f"state {key}: expected one is_base=1 row, found {len(selected)}")
        state_actions = [actions[row] for row in grouped_rows[key]]
        if len(set(state_actions)) != len(state_actions):
            raise ValueError(f"state {key}: duplicate action index")
        streams.setdefault(group_stream[key], []).append(group_id)
        baseline_rows.append(selected[0])
        rows = group_rows[group_id]
        left, right = np.triu_indices(len(rows), k=1)
        label_diff = target_array[rows[left]] - target_array[rows[right]]
        unequal = np.abs(label_diff) > 1.0e-7
        pair_rows_i.append(rows[left[unequal]])
        pair_rows_j.append(rows[right[unequal]])
        pair_sign.append(np.where(label_diff[unequal] < 0.0, 1.0, -1.0).astype(np.float32))

    x = np.frombuffer(feature_values, dtype=np.float32).reshape(len(targets), INPUTS)
    return Dataset(
        x=x,
        target=target_array,
        group_rows=group_rows,
        group_stream=[group_stream[key] for key in group_keys],
        group_state=[key[1] for key in group_keys],
        base_trench=np.asarray(base_trench, dtype=np.float32),
        target_trench=np.asarray(target_trench, dtype=np.float32),
        baseline_row=np.asarray(baseline_rows, dtype=np.int64),
        action=actions,
        pair_rows_i=pair_rows_i,
        pair_rows_j=pair_rows_j,
        pair_sign=pair_sign,
        stream_groups=streams,
        csv_path=str(path.resolve()),
        sha256=file_sha256(path),
    )


def feature_normalization(data: Dataset) -> tuple[np.ndarray, np.ndarray]:
    """Train-only feature moments with equal stream/state/row weighting."""
    mean = np.zeros(INPUTS, dtype=np.float64)
    second = np.zeros(INPUTS, dtype=np.float64)
    stream_weight = 1.0 / data.streams
    for group_ids in data.stream_groups.values():
        group_weight = stream_weight / len(group_ids)
        for group_id in group_ids:
            gx = data.x[data.group_rows[group_id]].astype(np.float64, copy=False)
            mean += group_weight * gx.mean(axis=0)
            second += group_weight * np.square(gx).mean(axis=0)
    std = np.sqrt(np.maximum(second - mean * mean, 1.0e-12))
    return mean.astype(np.float32), (1.0 / std).astype(np.float32)


def normalize_x(data: Dataset, mean: np.ndarray, scale: np.ndarray) -> np.ndarray:
    x = (data.x - mean) * scale
    np.clip(x, -CLIP_Z, CLIP_Z, out=x)
    return np.asarray(x, dtype=np.float32)


def initialize(rng: np.random.Generator) -> dict[str, np.ndarray]:
    limit1 = math.sqrt(6.0 / (INPUTS + HIDDEN))
    limit2 = math.sqrt(6.0 / (HIDDEN + 1))
    return {
        "w1": rng.uniform(-limit1, limit1, (INPUTS, HIDDEN)).astype(np.float32),
        "b1": np.zeros(HIDDEN, dtype=np.float32),
        "w2": rng.uniform(-limit2, limit2, HIDDEN).astype(np.float32),
        "b2": np.zeros(1, dtype=np.float32),
    }


def forward(x: np.ndarray, params: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    z1 = x @ params["w1"] + params["b1"]
    hidden = np.maximum(z1, 0.0)
    prediction = hidden @ params["w2"] + params["b2"][0]
    return z1, hidden, prediction


def batch_gradients(
    data: Dataset,
    x_all: np.ndarray,
    group_ids: np.ndarray,
    params: dict[str, np.ndarray],
) -> tuple[dict[str, np.ndarray], float, float]:
    rows = np.concatenate([data.group_rows[int(g)] for g in group_ids])
    global_to_local = np.full(data.rows, -1, dtype=np.int32)
    global_to_local[rows] = np.arange(len(rows), dtype=np.int32)
    xb = x_all[rows]
    yb = data.target[rows]
    z1, hidden, prediction = forward(xb, params)
    dpred = np.zeros(len(rows), dtype=np.float32)

    # Huber regression with equal stream/state weighting.
    row_weights = np.zeros(len(rows), dtype=np.float32)
    batch_state_mass = 0.0
    for gid_raw in group_ids:
        gid = int(gid_raw)
        stream = data.group_stream[gid]
        state_mass = 1.0 / data.streams / len(data.stream_groups[stream])
        state_rows = data.group_rows[gid]
        local_rows = global_to_local[state_rows]
        row_weights[local_rows] = state_mass / len(state_rows)
        batch_state_mass += state_mass
    row_weights /= max(batch_state_mass, 1.0e-12)
    error = prediction - yb
    huber_grad = np.clip(error, -HUBER_DELTA, HUBER_DELTA)
    dpred += REGRESSION_MIX * row_weights * huber_grad
    huber = np.where(
        np.abs(error) <= HUBER_DELTA,
        0.5 * error * error,
        HUBER_DELTA * (np.abs(error) - 0.5 * HUBER_DELTA),
    )
    regression_loss = float(np.sum(row_weights * huber))

    # Pairwise logistic loss over unequal-label actions in the same state.
    pair_i_parts: list[np.ndarray] = []
    pair_j_parts: list[np.ndarray] = []
    pair_sign_parts: list[np.ndarray] = []
    pair_weight_parts: list[np.ndarray] = []
    for gid_raw in group_ids:
        gid = int(gid_raw)
        pair_rows_i = data.pair_rows_i[gid]
        if len(pair_rows_i) == 0:
            continue
        stream = data.group_stream[gid]
        state_mass = 1.0 / data.streams / len(data.stream_groups[stream])
        per_pair = state_mass / len(pair_rows_i)
        pair_i_parts.append(global_to_local[pair_rows_i])
        pair_j_parts.append(global_to_local[data.pair_rows_j[gid]])
        pair_sign_parts.append(data.pair_sign[gid])
        pair_weight_parts.append(
            np.full(len(pair_rows_i), per_pair, dtype=np.float32)
        )

    pair_loss = 0.0
    if pair_i_parts:
        pi = np.concatenate(pair_i_parts)
        pj = np.concatenate(pair_j_parts)
        signs = np.concatenate(pair_sign_parts)
        weights = np.concatenate(pair_weight_parts)
        weights /= max(float(weights.sum()), 1.0e-12)
        margin = signs * (prediction[pj] - prediction[pi])
        pair_loss = float(np.sum(weights * np.logaddexp(0.0, -margin)))
        sigmoid_negative = 1.0 / (1.0 + np.exp(np.clip(margin, -40.0, 40.0)))
        d = PAIRWISE_MIX * weights * sigmoid_negative * signs
        np.add.at(dpred, pi, d)
        np.add.at(dpred, pj, -d)

    gradients = {
        "w2": hidden.T @ dpred + WEIGHT_DECAY * params["w2"],
        "b2": np.asarray([dpred.sum()], dtype=np.float32),
    }
    d_hidden = dpred[:, None] * params["w2"][None, :]
    d_z1 = d_hidden * (z1 > 0.0)
    gradients["w1"] = xb.T @ d_z1 + WEIGHT_DECAY * params["w1"]
    gradients["b1"] = d_z1.sum(axis=0)
    return gradients, regression_loss, pair_loss


def balanced_mean(values: list[tuple[str, float]]) -> float:
    per_stream: dict[str, list[float]] = {}
    for stream, value in values:
        per_stream.setdefault(stream, []).append(value)
    if not per_stream:
        return 0.0
    return float(np.mean([np.mean(items) for items in per_stream.values()]))


def evaluate(data: Dataset, x_all: np.ndarray, params: dict[str, np.ndarray]) -> dict[str, Any]:
    predictions = np.empty(data.rows, dtype=np.float32)
    for start in range(0, data.rows, 8192):
        stop = min(data.rows, start + 8192)
        _, _, predictions[start:stop] = forward(x_all[start:stop], params)

    state_mae: list[tuple[str, float]] = []
    state_pair_accuracy: list[tuple[str, float]] = []
    state_savings = {margin: [] for margin in MARGINS}
    state_coverage = {margin: [] for margin in MARGINS}
    zero_signal_states = 0
    hindsight_savings: list[tuple[str, float]] = []
    selected_nonpositive_savings = {margin: [] for margin in MARGINS}

    for gid, rows in enumerate(data.group_rows):
        stream = data.group_stream[gid]
        row_predictions = predictions[rows]
        row_targets = data.target[rows]
        state_mae.append((stream, float(np.abs(row_predictions - row_targets).mean() * 20.0)))
        pair_i = data.pair_rows_i[gid]
        if len(pair_i):
            pair_j = data.pair_rows_j[gid]
            margin = data.pair_sign[gid] * (predictions[pair_j] - predictions[pair_i])
            pair_scores = np.where(
                margin > 1.0e-7,
                1.0,
                np.where(margin < -1.0e-7, 0.0, 0.5),
            )
            state_pair_accuracy.append((stream, float(np.mean(pair_scores))))
        else:
            zero_signal_states += 1

        baseline_row = int(data.baseline_row[gid])
        baseline_score = float(predictions[baseline_row])
        candidate_rows = [int(row) for row in rows if int(row) != baseline_row]
        if candidate_rows:
            best_possible = max(
                0.0,
                max(
                    float(data.base_trench[row] - data.target_trench[row])
                    for row in candidate_rows
                ),
            )
        else:
            best_possible = 0.0
        hindsight_savings.append((stream, best_possible))
        for margin in MARGINS:
            eligible = [
                row for row in candidate_rows
                if np.float32(
                    np.float32(baseline_score) - np.float32(predictions[row])
                ) > np.float32(margin)
            ]
            if eligible:
                chosen = min(eligible, key=lambda row: (float(predictions[row]), data.action[row]))
                saving = float(data.base_trench[chosen] - data.target_trench[chosen])
                coverage = 1.0
            else:
                saving = 0.0
                coverage = 0.0
            state_savings[margin].append((stream, saving))
            state_coverage[margin].append((stream, coverage))
            selected_nonpositive_savings[margin].append(
                (stream, 1.0 if coverage and saving <= 0.0 else 0.0)
            )

    margins = {
        f"{margin:g}": {
            "mean_realized_saving_m": balanced_mean(state_savings[margin]),
            "selected_state_fraction": balanced_mean(state_coverage[margin]),
            "selected_nonpositive_saving_state_fraction": balanced_mean(
                selected_nonpositive_savings[margin]
            ),
        }
        for margin in MARGINS
    }
    best_margin = max(
        MARGINS,
        key=lambda margin: (margins[f"{margin:g}"]["mean_realized_saving_m"], margin),
    )
    best_saving = margins[f"{best_margin:g}"]["mean_realized_saving_m"]
    deployable = best_saving > 0.0
    return {
        "stream_balanced_mae_m": balanced_mean(state_mae),
        "stream_balanced_pairwise_accuracy": (
            balanced_mean(state_pair_accuracy) if state_pair_accuracy else 0.5
        ),
        "pairwise_evaluable_state_count": len(state_pair_accuracy),
        "zero_signal_state_count": zero_signal_states,
        "state_count": data.groups,
        "stream_count": data.streams,
        "rows": data.rows,
        "margin_grid": margins,
        "best_margin": best_margin,
        "best_mean_realized_saving_m": best_saving,
        "own_model_vs_base_mean_saving_m": best_saving,
        "hindsight_ceiling_mean_saving_m": balanced_mean(hindsight_savings),
        "mean_regret_to_hindsight_m": (
            balanced_mean(hindsight_savings) - best_saving
        ),
        "deployment_margin": best_margin if deployable else None,
        "deployable": deployable,
    }


def init_adam(params: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    return (
        {key: np.zeros_like(value) for key, value in params.items()},
        {key: np.zeros_like(value) for key, value in params.items()},
    )


def adam_step(
    params: dict[str, np.ndarray],
    gradients: dict[str, np.ndarray],
    first: dict[str, np.ndarray],
    second: dict[str, np.ndarray],
    step: int,
) -> None:
    for key in params:
        first[key] *= BETA1
        first[key] += (1.0 - BETA1) * gradients[key]
        second[key] *= BETA2
        second[key] += (1.0 - BETA2) * gradients[key] * gradients[key]
        mean_hat = first[key] / (1.0 - BETA1 ** step)
        variance_hat = second[key] / (1.0 - BETA2 ** step)
        params[key] -= LEARNING_RATE * mean_hat / (np.sqrt(variance_hat) + ADAM_EPS)


def cpp_float(value: float) -> str:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("cannot export non-finite model parameter")
    text = f"{value:.9g}"
    if "." not in text and "e" not in text.lower():
        text += ".0"
    return f"{text}f"


def cpp_array(name: str, values: np.ndarray) -> str:
    flat = np.asarray(values, dtype=np.float32).reshape(-1)
    lines = [f"inline constexpr std::array<float, {len(flat)}> {name} = {{"]
    for start in range(0, len(flat), 8):
        values_line = ", ".join(cpp_float(value) for value in flat[start : start + 8])
        lines.append(f"    {values_line},")
    lines.append("};")
    return "\n".join(lines)


def export_header(
    path: Path,
    mean: np.ndarray,
    scale: np.ndarray,
    params: dict[str, np.ndarray],
    diagnostic: dict[str, Any],
    model_json_sha256: str,
    parameters_sha256: str,
) -> None:
    for digest_name, digest in (
        ("model JSON SHA256", model_json_sha256),
        ("inference parameters SHA256", parameters_sha256),
    ):
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"invalid {digest_name}: {digest!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays = [
        cpp_array("kMean", mean),
        cpp_array("kScale", scale),
        cpp_array("kW1", params["w1"].reshape(-1)),
        cpp_array("kB1", params["b1"]),
        cpp_array("kW2", params["w2"]),
        cpp_array("kB2", params["b2"]),
    ]
    deployment_margin = (
        diagnostic["deployment_margin"] if diagnostic["deployable"] else 1.0e30
    )
    header = """#pragma once

#include <algorithm>
#include <array>
#include <cstddef>

namespace learned_model {
namespace detail {

""" + "\n\n".join(arrays) + """

}  // namespace detail

// Predicts (final trench - forced baseline final trench) / 20.
// Lower scores are better. Compare with the is_base=1 action using the
// calibration-selected abstention margin.
inline float score(const std::array<float, 128>& features) {
    std::array<float, __HIDDEN__> hidden = detail::kB1;
    for (std::size_t i = 0; i < 128; ++i) {
        float x = (features[i] - detail::kMean[i]) * detail::kScale[i];
        x = std::max(-8.0f, std::min(8.0f, x));
        for (std::size_t j = 0; j < __HIDDEN__; ++j) {
            hidden[j] += x * detail::kW1[i * __HIDDEN__ + j];
        }
    }
    float result = detail::kB2[0];
    for (std::size_t j = 0; j < __HIDDEN__; ++j) {
        const float activation = std::max(0.0f, hidden[j]);
        result += activation * detail::kW2[j];
    }
    return result;
}

inline constexpr float kMargin = """ + cpp_float(deployment_margin) + """;
inline constexpr bool kCalibrationDeployable = """ + (
        "true" if diagnostic["deployable"] else "false"
    ) + """;
inline constexpr float kCalibrationMargin = kMargin;
inline constexpr float kCalibrationSavingMeters = """ + cpp_float(
        diagnostic["best_mean_realized_saving_m"]
    ) + """;
inline constexpr char kModelJsonSha256[] = "__MODEL_JSON_SHA256__";
inline constexpr char kInferenceParametersSha256[] = "__PARAMETERS_SHA256__";

}  // namespace learned_model
"""
    header = header.replace("__HIDDEN__", str(HIDDEN))
    header = header.replace("__MODEL_JSON_SHA256__", model_json_sha256)
    header = header.replace("__PARAMETERS_SHA256__", parameters_sha256)
    write_text_atomic(path, header)


def train_model(
    train: Dataset,
    calibration: Dataset,
    output_dir: Path,
    header_path: Path,
) -> dict[str, Any]:
    mean, scale = feature_normalization(train)
    x_train = normalize_x(train, mean, scale)
    x_calibration = normalize_x(calibration, mean, scale)
    rng = np.random.default_rng(SEED)
    params = initialize(rng)
    first, second = init_adam(params)
    random_control_diagnostic = evaluate(calibration, x_calibration, params)
    best_params: dict[str, np.ndarray] | None = None
    best_diagnostic: dict[str, Any] | None = None
    best_epoch: int | None = None
    best_key: tuple[float, float, float, int] | None = None
    stale_epochs = 0
    optimizer_step = 0
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "train.log"

    with log_path.open("w", encoding="utf-8") as log:
        log.write("Fixed recipe; calibration selects checkpoint and abstention margin only.\n")
        log.write(f"python_executable={sys.executable}\n")
        log.write(f"command={shlex.join([sys.executable, *sys.argv])}\n")
        for name in (
            "OPENBLAS_NUM_THREADS",
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        ):
            log.write(f"{name}={os.environ.get(name, 'unset')}\n")
        log.write(
        f"seed={SEED} architecture={INPUTS}-{HIDDEN}-1 parameters={PARAMETER_COUNT} "
        f"max_epochs={MAX_EPOCHS} "
            f"batch_states={BATCH_STATES}\n"
        )
        log.write(
            f"train_rows={train.rows} train_states={train.groups} train_streams={train.streams}\n"
        )
        log.write(
            f"calibration_rows={calibration.rows} calibration_states={calibration.groups} "
            f"calibration_streams={calibration.streams}\n"
        )
        log.write(
            "epoch0_random_control_only="
            f"saving_m:{random_control_diagnostic['best_mean_realized_saving_m']:.8g},"
            f"margin:{random_control_diagnostic['best_margin']:g},"
            f"mae_m:{random_control_diagnostic['stream_balanced_mae_m']:.8g},"
            f"pair_acc:{random_control_diagnostic['stream_balanced_pairwise_accuracy']:.8g}\n"
        )
        log.write(
            "epoch,train_huber,train_pairwise,cal_saving_m,cal_margin,cal_mae_m,"
            "cal_pair_acc,cal_selected_fraction\n"
        )
        for epoch in range(1, MAX_EPOCHS + 1):
            order = rng.permutation(train.groups)
            regression_sum = 0.0
            pairwise_sum = 0.0
            batches = 0
            for start in range(0, train.groups, BATCH_STATES):
                group_batch = order[start : start + BATCH_STATES]
                gradients, regression_loss, pairwise_loss = batch_gradients(
                    train, x_train, group_batch, params
                )
                optimizer_step += 1
                adam_step(params, gradients, first, second, optimizer_step)
                regression_sum += regression_loss
                pairwise_sum += pairwise_loss
                batches += 1
            diagnostic = evaluate(calibration, x_calibration, params)
            margin_stats = diagnostic["margin_grid"][f"{diagnostic['best_margin']:g}"]
            key = (
                diagnostic["best_mean_realized_saving_m"],
                diagnostic["stream_balanced_pairwise_accuracy"],
                -diagnostic["stream_balanced_mae_m"],
                -epoch,
            )
            log.write(
                f"{epoch},{regression_sum/max(1,batches):.8g},"
                f"{pairwise_sum/max(1,batches):.8g},"
                f"{diagnostic['best_mean_realized_saving_m']:.8g},"
                f"{diagnostic['best_margin']:g},"
                f"{diagnostic['stream_balanced_mae_m']:.8g},"
                f"{diagnostic['stream_balanced_pairwise_accuracy']:.8g},"
                f"{margin_stats['selected_state_fraction']:.8g}\n"
            )
            log.flush()
            print(
                f"epoch {epoch:03d}: calibration saving="
                f"{diagnostic['best_mean_realized_saving_m']:.4f} m, "
                f"margin={diagnostic['best_margin']:g}, "
                f"MAE={diagnostic['stream_balanced_mae_m']:.3f} m, "
                f"pair accuracy={diagnostic['stream_balanced_pairwise_accuracy']:.4f}",
                flush=True,
            )
            if best_key is None or key > best_key:
                best_key = key
                best_params = {name: value.copy() for name, value in params.items()}
                best_diagnostic = diagnostic
                best_epoch = epoch
                stale_epochs = 0
            else:
                stale_epochs += 1
            if stale_epochs >= PATIENCE:
                log.write(f"early_stop_epoch={epoch} patience={PATIENCE}\n")
                break

    if best_params is None or best_diagnostic is None or best_epoch is None:
        raise RuntimeError("training completed without selecting a trained checkpoint")
    final_diagnostic = evaluate(calibration, x_calibration, best_params)
    record: dict[str, Any] = {
        "format": "pipes_baseline_router_mlp_v1",
        "architecture": [INPUTS, HIDDEN, 1],
        "trainable_parameter_count": PARAMETER_COUNT,
        "target": "(target_trench - base_trench) / 20; lower is better",
        "units": "20_m",
        "seed": SEED,
        "selected_epoch": best_epoch,
        "epoch0_random_control_only": random_control_diagnostic,
        "threshold_comparison": (
            "float32(baseline_score - candidate_score) > float32(margin)"
        ),
        "runtime": {
            "python_executable": sys.executable,
            "argv": [sys.executable, *sys.argv],
            "blas_thread_environment": {
                name: os.environ.get(name)
                for name in (
                    "OPENBLAS_NUM_THREADS",
                    "OMP_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS",
                )
            },
        },
        "deployable": final_diagnostic["deployable"],
        "deployment_margin": final_diagnostic["deployment_margin"],
        "checkpoint_selection": (
            "maximize stream-balanced calibration mean realized saving in meters over "
            "fixed margin grid; tie-break pairwise accuracy, MAE, earlier epoch; "
            "zero or negative means abstain"
        ),
        "config": {
            "max_epochs": MAX_EPOCHS,
            "patience": PATIENCE,
            "batch_states": BATCH_STATES,
            "learning_rate": LEARNING_RATE,
            "beta1": BETA1,
            "beta2": BETA2,
            "adam_epsilon": ADAM_EPS,
            "weight_decay": WEIGHT_DECAY,
            "huber_delta_20m": HUBER_DELTA,
            "regression_mix": REGRESSION_MIX,
            "pairwise_mix": PAIRWISE_MIX,
            "margin_grid_20m": list(MARGINS),
            "feature_clip_z": CLIP_Z,
            "normalization": "training only; equal stream, state, and row weights",
        },
        "train": {
            "csv": train.csv_path,
            "sha256": train.sha256,
            "rows": train.rows,
            "states": train.groups,
            "streams": train.streams,
        },
        "calibration": {
            "csv": calibration.csv_path,
            "sha256": calibration.sha256,
            "diagnostic": final_diagnostic,
        },
        "normalization": {
            "mean": mean.astype(float).tolist(),
            "scale": scale.astype(float).tolist(),
        },
        "weights": {
            "w1_row_major_128x16": best_params["w1"].reshape(-1).astype(float).tolist(),
            "b1": best_params["b1"].astype(float).tolist(),
            "w2": best_params["w2"].astype(float).tolist(),
            "b2": float(best_params["b2"][0]),
        },
    }
    record["inference_parameters_sha256"] = weights_sha256(mean, scale, best_params)
    model_json_path = output_dir / "model.json"
    write_text_atomic(model_json_path, json.dumps(record, indent=2) + "\n")
    model_json_hash = file_sha256(model_json_path)
    write_text_atomic(
        output_dir / "validation_diagnostic.json",
        json.dumps(final_diagnostic, indent=2) + "\n",
    )
    write_text_atomic(
        output_dir / "model.sha256",
        f"{model_json_hash}  model.json\n"
        f"{record['inference_parameters_sha256']}  inference-float32-tensors\n",
    )
    export_header(
        header_path, mean, scale, best_params, final_diagnostic,
        model_json_hash, record["inference_parameters_sha256"],
    )
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"selected_epoch={best_epoch}\n")
        log.write(f"deployable={final_diagnostic['deployable']}\n")
        log.write(f"deployment_margin={final_diagnostic['deployment_margin']}\n")
        log.write(
            "calibration_best_mean_realized_saving_m="
            f"{final_diagnostic['best_mean_realized_saving_m']:.8g}\n"
        )
    return record


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-csv", type=Path, required=True)
    parser.add_argument("--calibration-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=script_dir)
    parser.add_argument(
        "--header", type=Path, default=script_dir.parent / "src" / "trained_model.hpp"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    train_path = args.train_csv.expanduser().resolve()
    calibration_path = args.calibration_csv.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    header_path = args.header.expanduser().resolve()
    if not train_path.is_file():
        raise FileNotFoundError(f"training CSV not found: {train_path}")
    if not calibration_path.is_file():
        raise FileNotFoundError(f"calibration CSV not found: {calibration_path}")
    if train_path == calibration_path:
        raise ValueError("training and calibration CSVs must be distinct files")

    print(f"Loading training labels: {train_path}", flush=True)
    train = load_csv(train_path)
    print(f"Loading calibration labels: {calibration_path}", flush=True)
    calibration = load_csv(calibration_path)
    overlap = set(train.stream_groups).intersection(calibration.stream_groups)
    if overlap:
        raise ValueError(f"train/calibration stream overlap: {sorted(overlap)[:5]}")
    print(
        f"Loaded train {train.rows} rows / {train.groups} states / {train.streams} streams; "
        f"calibration {calibration.rows} rows / {calibration.groups} states / "
        f"{calibration.streams} streams",
        flush=True,
    )
    record = train_model(train, calibration, output_dir, header_path)
    diagnostic = record["calibration"]["diagnostic"]
    print(json.dumps({
        "selected_epoch": record["selected_epoch"],
        "deployable": record["deployable"],
        "deployment_margin": record["deployment_margin"],
        "best_mean_realized_saving_m": diagnostic["best_mean_realized_saving_m"],
        "calibration_mae_m": diagnostic["stream_balanced_mae_m"],
        "calibration_pairwise_accuracy": diagnostic["stream_balanced_pairwise_accuracy"],
        "model_json": str((output_dir / "model.json").resolve()),
        "train_log": str((output_dir / "train.log").resolve()),
        "validation_diagnostic": str((output_dir / "validation_diagnostic.json").resolve()),
        "header": str(header_path),
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"training failed: {exc}", file=sys.stderr)
        raise
