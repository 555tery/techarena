#!/usr/bin/env python3
"""Generate and compare six fresh Pipes transfer streams, baseline vs frozen #33."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
INPUTS = HERE / "inputs"
GENERATOR = ROOT / "tools" / "generate_pipes_synthetic.py"
HARNESS = ROOT / "tools" / "pipes_harness.py"
INTERACTOR = ROOT / "tools" / "interactor"
BASELINE_BIN = HERE / "bin" / "baseline"
CANDIDATE_BIN = HERE / "bin" / "tree_033"
BASELINE_SRC = ROOT / "results/pipes/final/solution.cpp"
CANDIDATE_SRC = ROOT / "results/pipes/improvement/program_synthesis/src/tree_033_frozen.cpp"

CASES = [
    {"name": "01_uniform_random_n5000", "seed": 20263001, "operations": 5000,
     "profile": "uniform", "churn": 0.42, "deletion": "random",
     "schedule": "stationary uniform lengths 1..40; random deletion"},
    {"name": "02_short_fifo_n25000", "seed": 20263002, "operations": 25000,
     "profile": "short-heavy", "churn": 0.42, "deletion": "oldest",
     "schedule": "stationary short-heavy profile; FIFO deletion"},
    {"name": "03_long_lifo_n100000", "seed": 20263003, "operations": 100000,
     "profile": "long-heavy", "churn": 0.42, "deletion": "newest",
     "schedule": "stationary long-heavy profile; LIFO deletion"},
    {"name": "04_uniform_to_long_n25000", "seed": 20263004, "operations": 25000,
     "profile": "phase_uniform_to_long", "churn": 0.42, "deletion": "random",
     "schedule": "uniform lengths 1..40 for ops 1..12500, then long-heavy; random deletion"},
    {"name": "05_blocks_16_256_n50000", "seed": 20263005, "operations": 50000,
     "profile": "alternating_short16_long256", "churn": 0.42, "deletion": "random",
     "schedule": "placement-length blocks: 16 short (1..5), then 256 long (21..40), repeating; random deletion"},
    {"name": "06_blocks_64_1024_delete_shift_n100000", "seed": 20263006, "operations": 100000,
     "profile": "alternating_short64_long1024", "churn": 0.42, "deletion": "fifo_to_lifo",
     "schedule": "placement-length blocks: 64 short (1..5), then 1024 long (21..40), repeating; FIFO before op 50000 then LIFO"},
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_profile(rng: random.Random, profile: str, operation: int, placement_index: int, n: int) -> int:
    if profile == "uniform":
        return rng.randint(1, 40)
    if profile == "short-heavy":
        x = rng.random()
        if x < 0.65:
            return rng.randint(1, 5)
        if x < 0.90:
            return rng.randint(6, 20)
        return rng.randint(21, 40)
    if profile == "long-heavy":
        x = rng.random()
        if x < 0.10:
            return rng.randint(1, 5)
        if x < 0.35:
            return rng.randint(6, 20)
        return rng.randint(21, 40)
    if profile == "phase_uniform_to_long":
        phase = "uniform" if operation < n // 2 else "long-heavy"
        return sample_profile(rng, phase, operation, placement_index, n)
    if profile == "alternating_short16_long256":
        pos = placement_index % (16 + 256)
        return rng.randint(1, 5) if pos < 16 else rng.randint(21, 40)
    if profile == "alternating_short64_long1024":
        pos = placement_index % (64 + 1024)
        return rng.randint(1, 5) if pos < 64 else rng.randint(21, 40)
    raise ValueError(profile)


def delete_index(rng: random.Random, live: list[int], policy: str, operation: int, n: int) -> int:
    if policy == "random":
        return rng.randrange(len(live))
    if policy == "oldest":
        return 0
    if policy == "newest":
        return len(live) - 1
    if policy == "fifo_to_lifo":
        return 0 if operation < n // 2 else len(live) - 1
    raise ValueError(policy)


def make_case(case: dict) -> dict:
    rng = random.Random(case["seed"])
    n = case["operations"]
    live: list[int] = []
    lengths: dict[int, int] = {}
    commands: list[int] = []
    next_pid = 1
    placements = 0
    deletions = 0
    length_counts = [0] * 41
    for operation in range(n):
        remove = operation < n - 1 and bool(live) and rng.random() < case["churn"]
        if remove:
            index = delete_index(rng, live, case["deletion"], operation, n)
            pid = live.pop(index)
            del lengths[pid]
            commands.append(-pid)
            deletions += 1
        else:
            length = sample_profile(rng, case["profile"], operation, placements, n)
            commands.append(length)
            live.append(next_pid)
            lengths[next_pid] = length
            next_pid += 1
            placements += 1
            length_counts[length] += 1
    path = INPUTS / f"{case['name']}.in"
    content = "\n".join([f"1.0 {n}", *(str(command) for command in commands), "0", ""])
    path.write_text(content, encoding="ascii")
    live_total = sum(lengths.values())
    return {
        **case,
        "input_file": str(path.relative_to(ROOT)),
        "input_sha256": sha256(path),
        "placement_count": placements,
        "deletion_count": deletions,
        "final_live_count": len(live),
        "final_live_length_m": live_total,
        "placement_length_histogram": {str(i): count for i, count in enumerate(length_counts) if count},
    }


def run_solver(name: str, binary: Path, out_dir: Path) -> dict:
    cmd = [sys.executable, str(HARNESS), "--solver", str(binary), "--name", name,
           "--interactor", str(INTERACTOR), "--tests", str(INPUTS), "--out", str(out_dir),
           "--cpu-limit", "5", "--memory-limit-mb", "256", "--wall-timeout", "1800"]
    print(f"RUN {name}", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)
    return json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))


def record_map(summary: dict) -> dict[str, dict]:
    return {r["case"]: r for r in summary["records"]}


def main() -> None:
    INPUTS.mkdir(parents=True, exist_ok=True)
    case_manifest = [make_case(case) for case in CASES]
    (HERE / "input_manifest.json").write_text(json.dumps({
        "purpose": "fresh synthetic transfer matrix; not used for search or tuning",
        "generator": str(Path(__file__).relative_to(ROOT)),
        "generator_sha256": sha256(Path(__file__)),
        "python_version": sys.version,
        "host_platform": platform.platform(),
        "cases": case_manifest,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    baseline = run_solver("baseline", BASELINE_BIN, HERE / "baseline")
    candidate = run_solver("frozen-tree-033", CANDIDATE_BIN, HERE / "tree_033")
    base_records, cand_records = record_map(baseline), record_map(candidate)
    rows = []
    for case in case_manifest:
        key = case["name"]
        b, c = base_records[key], cand_records[key]
        b_out, c_out = ROOT / b["judge_output_file"], ROOT / c["judge_output_file"]
        rows.append({
            "case": key,
            "seed": case["seed"],
            "operations": case["operations"],
            "schedule": case["schedule"],
            "input_sha256": case["input_sha256"],
            "placements": case["placement_count"],
            "deletions": case["deletion_count"],
            "baseline_status": b["status"],
            "baseline_kpi": b["kpi"],
            "baseline_occupied_m": b["occupied_length_m"],
            "baseline_trench_m": b["trench_length_m"],
            "baseline_cpu_s": b.get("solver_cpu_total_s"),
            "baseline_rss_mb": b.get("solver_peak_rss_mb"),
            "baseline_output_sha256": sha256(b_out),
            "candidate_status": c["status"],
            "candidate_kpi": c["kpi"],
            "candidate_occupied_m": c["occupied_length_m"],
            "candidate_trench_m": c["trench_length_m"],
            "candidate_cpu_s": c.get("solver_cpu_total_s"),
            "candidate_rss_mb": c.get("solver_peak_rss_mb"),
            "candidate_output_sha256": sha256(c_out),
            "candidate_minus_baseline_weighted_delta": c["weighted_score"] - b["weighted_score"],
            "fraction_of_bound_baseline": b["fraction_of_bound"],
            "fraction_of_bound_candidate": c["fraction_of_bound"],
        })
    delta_sum = sum(r["candidate_minus_baseline_weighted_delta"] for r in rows)
    total_weight = sum(float(r["official_weight"]) for r in baseline["records"])
    comparison = {
        "purpose": "independent transfer validation only; no policy search or selection",
        "baseline_source_sha256": sha256(BASELINE_SRC),
        "baseline_binary_sha256": sha256(BASELINE_BIN),
        "candidate_id": "frozen #33; no changes made",
        "candidate_source_sha256": sha256(CANDIDATE_SRC),
        "candidate_binary_sha256": sha256(CANDIDATE_BIN),
        "case_count": len(rows),
        "weight_sum": total_weight,
        "baseline_weighted_score_sum": baseline["weighted_score_sum"],
        "candidate_weighted_score_sum": candidate["weighted_score_sum"],
        "weighted_delta_sum": delta_sum,
        "weighted_mean_delta_per_case": delta_sum / total_weight if total_weight else None,
        "positive_cases": sum(r["candidate_minus_baseline_weighted_delta"] > 0 for r in rows),
        "negative_cases": sum(r["candidate_minus_baseline_weighted_delta"] < 0 for r in rows),
        "neutral_cases": sum(r["candidate_minus_baseline_weighted_delta"] == 0 for r in rows),
        "all_status_ok": all(r["baseline_status"] == "ok" and r["candidate_status"] == "ok" for r in rows),
        "all_outputs_identical": all(r["baseline_output_sha256"] == r["candidate_output_sha256"] for r in rows),
        "max_baseline_cpu_s": max(r["baseline_cpu_s"] or 0 for r in rows),
        "max_candidate_cpu_s": max(r["candidate_cpu_s"] or 0 for r in rows),
        "max_baseline_rss_mb": max(r["baseline_rss_mb"] or 0 for r in rows),
        "max_candidate_rss_mb": max(r["candidate_rss_mb"] or 0 for r in rows),
        "per_stream": rows,
    }
    (HERE / "comparison.json").write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    keys = list(rows[0])
    with (HERE / "comparison.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({k: comparison[k] for k in ["baseline_weighted_score_sum", "candidate_weighted_score_sum", "weighted_delta_sum", "positive_cases", "negative_cases", "neutral_cases", "all_outputs_identical", "max_baseline_cpu_s", "max_candidate_cpu_s", "max_baseline_rss_mb", "max_candidate_rss_mb"]}, indent=2))


if __name__ == "__main__":
    main()
