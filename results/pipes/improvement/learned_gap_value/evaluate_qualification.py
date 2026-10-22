#!/usr/bin/env python3
"""Pair local interactor results and apply the preregistered synthetic gate."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import random
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
INPUT_MANIFEST = HERE / "inputs/qualification_confirmatory/manifest.json"
GATE = HERE / "qualification-gate.md"
BASELINE_RUN = HERE / "runs/qualification-frozen"
LEARNED_RUN = HERE / "runs/qualification-learned"
OUT_DIR = HERE / "runs/qualification-analysis"
BOOTSTRAP_REPLICATES = 20_000
BOOTSTRAP_SEED = 2_026_101_718


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    result: dict[str, dict[str, str]] = {}
    for row in records:
        key = Path(row["test_file"]).name
        if key in result:
            raise RuntimeError(f"duplicate test in {path}: {key}")
        result[key] = row
    return result


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(sorted_values: list[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    fraction = position - low
    return sorted_values[low] * (1.0 - fraction) + sorted_values[high] * fraction


def paired_bootstrap(differences: list[float]) -> list[float]:
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(differences)
    samples = []
    for _ in range(BOOTSTRAP_REPLICATES):
        samples.append(sum(differences[rng.randrange(n)] for _ in range(n)) / n)
    samples.sort()
    return [percentile(samples, 0.025), percentile(samples, 0.975)]


def summarise(rows: list[dict[str, object]], key: str) -> dict[str, object]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        groups.setdefault(str(row[key]), []).append(float(row["delta_kpi"]))
    return {
        group: {"count": len(values), "mean_delta_kpi": mean(values)}
        for group, values in sorted(groups.items())
    }


def main() -> None:
    input_manifest = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    baseline_csv = BASELINE_RUN / "cases.csv"
    learned_csv = LEARNED_RUN / "cases.csv"
    baseline = load_csv(baseline_csv)
    learned = load_csv(learned_csv)
    expected = {Path(row["path"]).name: row for row in input_manifest["records"]}
    if set(baseline) != set(expected) or set(learned) != set(expected):
        raise RuntimeError(
            f"case set mismatch expected={len(expected)} baseline={len(baseline)} learned={len(learned)}"
        )

    rows: list[dict[str, object]] = []
    for name in sorted(expected):
        b, c, meta = baseline[name], learned[name], expected[name]
        if b["test_sha256"] != c["test_sha256"] or b["test_sha256"] != meta["sha256"]:
            raise RuntimeError(f"paired input hash mismatch for {name}")
        if b["status"] != "ok" or c["status"] != "ok":
            raise RuntimeError(f"non-ok run status for {name}: frozen={b['status']} learned={c['status']}")
        expected_replies = int(meta["operations"]) + 1
        baseline_seen = int(b["judge_commands_seen_including_final_zero"])
        learned_seen = int(c["judge_commands_seen_including_final_zero"])
        if baseline_seen != expected_replies or learned_seen != expected_replies:
            raise RuntimeError(
                f"transcript length mismatch for {name}: expected={expected_replies} "
                f"frozen={baseline_seen} learned={learned_seen}"
            )
        baseline_kpi = float(b["kpi"])
        learned_kpi = float(c["kpi"])
        rows.append({
            "case": name,
            "test_sha256": meta["sha256"],
            "seed": meta["seed"],
            "operations": meta["operations"],
            "profile": meta["profile"],
            "deletion_policy": meta["deletion_policy"],
            "regime": meta["regime"],
            "weight": meta["weight"],
            "expected_judge_commands_including_terminator": expected_replies,
            "baseline_judge_commands_seen": baseline_seen,
            "learned_judge_commands_seen": learned_seen,
            "baseline_transcript_accepted": True,
            "learned_transcript_accepted": True,
            "baseline_kpi": baseline_kpi,
            "learned_kpi": learned_kpi,
            "delta_kpi": learned_kpi - baseline_kpi,
            "baseline_trench_m": int(b["trench_length_m"]),
            "learned_trench_m": int(c["trench_length_m"]),
            "delta_trench_m": int(c["trench_length_m"]) - int(b["trench_length_m"]),
            "baseline_cpu_s": float(b["solver_cpu_total_s"]),
            "learned_cpu_s": float(c["solver_cpu_total_s"]),
            "baseline_peak_rss_mb": float(b["solver_peak_rss_mb"]),
            "learned_peak_rss_mb": float(c["solver_peak_rss_mb"]),
            "baseline_wall_s": float(b["wall_orchestration_s"]),
            "learned_wall_s": float(c["wall_orchestration_s"]),
            "baseline_cpu_limit_exceeded": b["solver_cpu_limit_exceeded"],
            "learned_cpu_limit_exceeded": c["solver_cpu_limit_exceeded"],
            "baseline_memory_limit_exceeded": b["solver_memory_limit_exceeded"],
            "learned_memory_limit_exceeded": c["solver_memory_limit_exceeded"],
        })

    deltas = [float(row["delta_kpi"]) for row in rows]
    long_deltas = [float(row["delta_kpi"]) for row in rows if int(row["operations"]) == 200_000]
    ci = paired_bootstrap(deltas)
    wins = sum(delta > 1e-12 for delta in deltas)
    losses = sum(delta < -1e-12 for delta in deltas)
    ties = len(deltas) - wins - losses
    passed = ci[0] > 0.0 and mean(long_deltas) >= 0.0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    case_csv = OUT_DIR / "per-case.csv"
    columns = list(rows[0])
    with case_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "decision": "PASS" if passed else "NO_GO",
        "stream_count": len(rows),
        "accepted_transcripts": len(rows) * 2,
        "mean_delta_kpi": mean(deltas),
        "whole_stream_bootstrap_95_ci": ci,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "long_200000_mean_delta_kpi": mean(long_deltas),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "mean_baseline_kpi": mean([float(row["baseline_kpi"]) for row in rows]),
        "mean_learned_kpi": mean([float(row["learned_kpi"]) for row in rows]),
        "baseline_weighted_score_sum": sum(float(b["weighted_score"]) for b in baseline.values()),
        "learned_weighted_score_sum": sum(float(c["weighted_score"]) for c in learned.values()),
        "by_horizon": summarise(rows, "operations"),
        "by_profile": summarise(rows, "profile"),
        "by_deletion_policy": summarise(rows, "deletion_policy"),
        "by_regime": summarise(rows, "regime"),
        "baseline_cpu_max_s": max(float(row["baseline_cpu_s"]) for row in rows),
        "learned_cpu_max_s": max(float(row["learned_cpu_s"]) for row in rows),
        "baseline_peak_rss_max_mb": max(float(row["baseline_peak_rss_mb"]) for row in rows),
        "learned_peak_rss_max_mb": max(float(row["learned_peak_rss_mb"]) for row in rows),
        "baseline_cpu_limit_exceedances": sum(row["baseline_cpu_limit_exceeded"] == "True" for row in rows),
        "learned_cpu_limit_exceedances": sum(row["learned_cpu_limit_exceeded"] == "True" for row in rows),
        "baseline_memory_limit_exceedances": sum(row["baseline_memory_limit_exceeded"] == "True" for row in rows),
        "learned_memory_limit_exceedances": sum(row["learned_memory_limit_exceeded"] == "True" for row in rows),
        "gate_sha256": sha256(GATE),
        "input_manifest_sha256": sha256(INPUT_MANIFEST),
        "baseline_cases_csv_sha256": sha256(baseline_csv),
        "learned_cases_csv_sha256": sha256(learned_csv),
        "per_case_csv_sha256": sha256(case_csv),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    json_path = OUT_DIR / "summary.json"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    baseline_source = ROOT / "results/pipes/final/solution.cpp"
    canonical_source = ROOT / "src/pipes.cpp"
    learned_source = HERE / "src/learned_gap_value.cpp"
    model_header = HERE / "src/learned_model.hpp"
    training_manifest = HERE / "training/manifest.json"
    forest_json = HERE / "training/forest.json"
    baseline_binary = HERE / "bin/frozen_final"
    learned_binary = HERE / "bin/learned_gap_value"
    interactor = ROOT / "tools/interactor"
    harness = ROOT / "tools/pipes_harness.py"
    clang_version = subprocess.run(
        ["clang++", "--version"], check=True, capture_output=True, text=True
    ).stdout.splitlines()[0]
    commands = [
        "clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic results/pipes/final/solution.cpp -o results/pipes/improvement/learned_gap_value/bin/frozen_final",
        "clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic -I results/pipes/improvement/learned_gap_value/src results/pipes/improvement/learned_gap_value/src/learned_gap_value.cpp -o results/pipes/improvement/learned_gap_value/bin/learned_gap_value",
        "python3 tools/pipes_harness.py --solver results/pipes/improvement/learned_gap_value/bin/frozen_final --name frozen-final --interactor tools/interactor --tests results/pipes/improvement/learned_gap_value/inputs/qualification_confirmatory --out results/pipes/improvement/learned_gap_value/runs/qualification-frozen --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 tools/pipes_harness.py --solver results/pipes/improvement/learned_gap_value/bin/learned_gap_value --name learned-gap-value --interactor tools/interactor --tests results/pipes/improvement/learned_gap_value/inputs/qualification_confirmatory --out results/pipes/improvement/learned_gap_value/runs/qualification-learned --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120",
        "python3 results/pipes/improvement/learned_gap_value/evaluate_qualification.py",
    ]
    manifest = {
        "purpose": "Reproducibility manifest for the precommitted synthetic confirmation.",
        "created_utc": report["created_utc"],
        "decision": report["decision"],
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "compiler": clang_version,
        "runtime_and_acceptance": {
            "accepted_transcripts": report["accepted_transcripts"],
            "tested_streams": report["stream_count"],
            "baseline_max_solver_cpu_s": report["baseline_cpu_max_s"],
            "candidate_max_solver_cpu_s": report["learned_cpu_max_s"],
            "baseline_max_solver_rss_mb": report["baseline_peak_rss_max_mb"],
            "candidate_max_solver_rss_mb": report["learned_peak_rss_max_mb"],
            "baseline_cpu_limit_exceedances": report["baseline_cpu_limit_exceedances"],
            "candidate_cpu_limit_exceedances": report["learned_cpu_limit_exceedances"],
            "baseline_memory_limit_exceedances": report["baseline_memory_limit_exceedances"],
            "candidate_memory_limit_exceedances": report["learned_memory_limit_exceedances"],
        },
        "statistical_result": {
            "mean_delta_kpi": report["mean_delta_kpi"],
            "whole_stream_bootstrap_95_ci": report["whole_stream_bootstrap_95_ci"],
            "long_200000_mean_delta_kpi": report["long_200000_mean_delta_kpi"],
            "wins": report["wins"],
            "losses": report["losses"],
            "ties": report["ties"],
        },
        "commands": commands,
        "sha256": {
            "frozen_source": sha256(baseline_source),
            "canonical_source": sha256(canonical_source),
            "learned_candidate_source": sha256(learned_source),
            "learned_model_header": sha256(model_header),
            "training_manifest": sha256(training_manifest),
            "trained_forest_json": sha256(forest_json),
            "frozen_binary": sha256(baseline_binary),
            "learned_candidate_binary": sha256(learned_binary),
            "interactor_binary": sha256(interactor),
            "harness": sha256(harness),
            "qualification_gate": sha256(GATE),
            "qualification_input_manifest": sha256(INPUT_MANIFEST),
            "frozen_case_results": sha256(baseline_csv),
            "learned_case_results": sha256(learned_csv),
            "per_case_comparison": sha256(case_csv),
            "summary": sha256(json_path),
        },
        "frozen_source_path": str(baseline_source.relative_to(ROOT)),
        "canonical_source_path": str(canonical_source.relative_to(ROOT)),
        "candidate_source_path": str(learned_source.relative_to(ROOT)),
        "baseline_cases_path": str(baseline_csv.relative_to(ROOT)),
        "candidate_cases_path": str(learned_csv.relative_to(ROOT)),
        "qualification_input_records": input_manifest["records"],
        "qualification_input_record_count": len(input_manifest["records"]),
        "qualification_input_seed_range": input_manifest["seed_range"],
        "per_case_comparison_path": str(case_csv.relative_to(ROOT)),
        "summary_path": str(json_path.relative_to(ROOT)),
    }
    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"per_case_csv={case_csv}")
    print(f"manifest={manifest_path}")


if __name__ == "__main__":
    main()
