#!/usr/bin/env python3
"""Fit Bayesian categorical prior and select BOCPD hyperparameters on train only."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / "input_manifest.json").read_text(encoding="utf-8"))
K = 48
MAX_RUN = 128
HAZARDS = (1 / 128, 1 / 512, 1 / 2048)
CONCENTRATIONS = (8.0, 32.0)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_symbols(path: Path) -> list[int]:
    lines = path.read_text(encoding="ascii").splitlines()
    commands = [int(value) for value in lines[1:] if value and int(value) != 0]
    tree = [0] * (len(commands) + 2)
    symbols = []
    active = 0
    next_pid = 1

    def add(pid: int, delta: int) -> None:
        i = pid
        while i < len(tree):
            tree[i] += delta
            i += i & -i

    def prefix(pid: int) -> int:
        total = 0
        i = pid
        while i > 0:
            total += tree[i]
            i -= i & -i
        return total

    for command in commands:
        if command > 0:
            symbols.append(command - 1)
            add(next_pid, 1)
            next_pid += 1
            active += 1
        else:
            pid = -command
            newer = active - prefix(pid)
            rank = 0 if active <= 1 else newer * 1000 // (active - 1)
            symbols.append(40 + min(7, rank * 8 // 1001))
            add(pid, -1)
            active -= 1
    if len(symbols) != int(lines[0].split()[1]):
        raise ValueError(f"command count mismatch in {path}")
    return symbols


def prior_for(streams: list[list[int]]) -> list[float]:
    counts = [1] * K
    for stream in streams:
        for symbol in stream:
            counts[symbol] += 1
    total = float(sum(counts))
    return [count / total for count in counts]


def logloss(symbols: list[int], prior: list[float], hazard: float,
            concentration: float) -> float:
    posterior = [0.0] * (MAX_RUN + 1)
    posterior[0] = 1.0
    history: list[int] = []
    loss = 0.0
    for symbol in symbols:
        run_counts = [0] * (MAX_RUN + 1)
        seen = 0
        limit = min(len(history), MAX_RUN)
        for run in range(1, limit + 1):
            if history[-run] == symbol:
                seen += 1
            run_counts[run] = seen
        predictive_by_run = [prior[symbol]] * (MAX_RUN + 1)
        for run in range(1, limit + 1):
            predictive_by_run[run] = (
                run_counts[run] + concentration * prior[symbol]
            ) / (run + concentration)
        cp_likelihood = prior[symbol]
        continuation_likelihood = sum(
            posterior[run] * predictive_by_run[run]
            for run in range(MAX_RUN + 1))
        predictive = hazard * cp_likelihood + (1.0 - hazard) * continuation_likelihood
        loss -= math.log(max(predictive, 1e-300))

        updated = [0.0] * (MAX_RUN + 1)
        updated[0] = hazard * cp_likelihood
        for run in range(MAX_RUN):
            updated[run + 1] += ((1.0 - hazard) * posterior[run]
                                 * predictive_by_run[run])
        updated[MAX_RUN] += ((1.0 - hazard) * posterior[MAX_RUN]
                             * predictive_by_run[MAX_RUN])
        normalizer = sum(updated)
        posterior = [value / normalizer for value in updated]
        history.append(symbol)
        if len(history) > MAX_RUN:
            history.pop(0)
    return loss / max(1, len(symbols))


def main() -> None:
    train_records = MANIFEST["train"]
    names = sorted(train_records)
    streams = []
    input_hashes = {}
    for name in names:
        path = ROOT / train_records[name]["path"]
        digest = sha(path)
        if digest != train_records[name]["sha256"]:
            raise SystemExit(f"training input hash mismatch: {name}")
        streams.append(load_symbols(path))
        input_hashes[name] = digest

    scores = []
    for hazard in HAZARDS:
        for concentration in CONCENTRATIONS:
            fold_scores = []
            for heldout_index, heldout in enumerate(streams):
                fitting = [stream for i, stream in enumerate(streams)
                           if i != heldout_index]
                prior = prior_for(fitting)
                fold_scores.append(logloss(heldout, prior, hazard, concentration))
            scores.append({
                "hazard": hazard, "concentration": concentration,
                "mean_stream_logloss": sum(fold_scores) / len(fold_scores),
                "per_stream_logloss": fold_scores,
            })
    scores.sort(key=lambda row: (row["mean_stream_logloss"],
                                 row["hazard"], -row["concentration"]))
    selected = scores[0]
    final_prior = prior_for(streams)
    symbol_counts = [0] * K
    for stream in streams:
        for symbol in stream:
            symbol_counts[symbol] += 1
    result = {
        "purpose": "Synthetic-only train fit; frozen before fresh validation.",
        "train_input_hashes": input_hashes,
        "train_stream_count": len(streams),
        "train_event_count": sum(map(len, streams)),
        "max_run_length": MAX_RUN,
        "selected_hazard": selected["hazard"],
        "selected_concentration": selected["concentration"],
        "selected_crossvalidated_logloss": selected["mean_stream_logloss"],
        "grid_scores": scores,
        "global_symbol_counts": symbol_counts,
        "base_prior": final_prior,
    }
    out = ROOT / "model_params.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"selected hazard={selected['hazard']:.9f} "
          f"concentration={selected['concentration']:.1f} "
          f"LOSO logloss={selected['mean_stream_logloss']:.8f}")
    for row in scores:
        print(f"  h={row['hazard']:.9f} kappa={row['concentration']:.1f} "
              f"logloss={row['mean_stream_logloss']:.8f}")
    print(f"params={out.relative_to(ROOT.parents[3])} sha256={sha(out)}")


if __name__ == "__main__":
    main()
