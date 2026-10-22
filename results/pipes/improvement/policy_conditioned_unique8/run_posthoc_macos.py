#!/usr/bin/env python3
"""Post-hoc native macOS Open15/holdout comparison for the frozen candidate."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BRANCH_MANIFEST = HERE / "manifest.json"
NATIVE_BIN = HERE / "bin" / "macos_native_20261017_compat"
OUT = HERE / "validation" / "posthoc_macos_open15_holdout_20261017"
HARNESS = ROOT / "tools" / "pipes_harness.py"
GROUPS = {
    "open15": (ROOT / "data" / "pipes" / "open", 15),
    "holdout_v2": (ROOT / "data" / "pipes" / "synthetic" / "final-holdout-v2", 12),
}
STRATEGIES = {
    "frozen-final": NATIVE_BIN / "frozen_final_macos",
    "policy-conditioned": NATIVE_BIN / "policy_conditioned_macos",
}
INTERACTOR = NATIVE_BIN / "interactor_macos"
CPU_LIMIT_S = 5.0
MEMORY_LIMIT_MIB = 256.0
WALL_TIMEOUT_S = 240.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def verify_manifest_sources(manifest: dict) -> dict:
    resolved = {}
    for field in ("candidate_source", "baseline_source", "interactor_source"):
        item = manifest[field]
        path = ROOT / item["path"]
        actual = sha256(path)
        if actual != item["sha256"]:
            raise RuntimeError(f"source SHA mismatch for {field}: {actual} != {item['sha256']}")
        resolved[field] = {"path": str(path), "sha256": actual}
    return resolved


def run_one(group: str, strategy: str, solver: Path, tests: Path, expected_cases: int) -> dict:
    out = OUT / group / strategy
    if out.exists():
        summary_path = out / "summary.json"
        if not summary_path.is_file():
            raise RuntimeError(f"partial output exists without summary; refusing to rerun: {out}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("case_count") != expected_cases:
            raise RuntimeError(f"recovered case count mismatch for {group}/{strategy}")
        expected_exit = int(any(
            record.get("status") != "ok"
            or record.get("solver_cpu_limit_exceeded")
            or record.get("solver_memory_limit_exceeded")
            for record in summary.get("records", [])
        ))
        return {
            "group": group,
            "strategy": strategy,
            "exit_code": expected_exit,
            "exit_code_recovered_from_summary": True,
            "command": None,
            "out_dir": str(out.relative_to(HERE)),
            "summary": summary,
        }
    out.mkdir(parents=True)
    command = [
        sys.executable, str(HARNESS),
        "--solver", str(solver),
        "--interactor", str(INTERACTOR),
        "--tests", str(tests),
        "--out", str(out),
        "--name", strategy,
        "--cpu-limit", str(CPU_LIMIT_S),
        "--memory-limit-mb", str(MEMORY_LIMIT_MIB),
        "--wall-timeout", str(WALL_TIMEOUT_S),
    ]
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    (out / "harness.stdout.txt").write_text(process.stdout, encoding="utf-8")
    (out / "harness.stderr.txt").write_text(process.stderr, encoding="utf-8")
    (out / "harness_exit_code.txt").write_text(f"{process.returncode}\n", encoding="ascii")
    summary_path = out / "summary.json"
    if not summary_path.exists():
        raise RuntimeError(
            f"harness produced no summary for {group}/{strategy}; exit={process.returncode}; "
            f"stderr={process.stderr[-2000:]}"
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("case_count") != expected_cases:
        raise RuntimeError(f"case count mismatch for {group}/{strategy}: {summary.get('case_count')}")
    return {
        "group": group,
        "strategy": strategy,
        "exit_code": process.returncode,
        "exit_code_recovered_from_summary": False,
        "command": command,
        "out_dir": str(out.relative_to(HERE)),
        "summary": summary,
    }


def accepted(record: dict, expected_operations: int, expected_hash: str) -> bool:
    return (
        record.get("status") == "ok"
        and record.get("judge_commands_seen_including_final_zero") == expected_operations + 1
        and record.get("test_sha256") == expected_hash
    )


def main() -> None:
    branch_manifest = json.loads(BRANCH_MANIFEST.read_text(encoding="utf-8"))
    sources = verify_manifest_sources(branch_manifest)
    inputs = {}
    for group, (tests, expected_count) in GROUPS.items():
        files = sorted(tests.glob("*.in"), key=lambda p: (0, int(p.stem)) if p.stem.isdigit() else (1, p.name))
        if len(files) != expected_count:
            raise RuntimeError(f"expected {expected_count} inputs for {group}, got {len(files)}")
        inputs[group] = {p.stem: sha256(p) for p in files}
    for path in [*STRATEGIES.values(), INTERACTOR]:
        if not path.is_file():
            raise RuntimeError(f"native binary not found: {path}")

    clang = subprocess.run(["clang++", "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    binary_hashes = {path.name: sha256(path) for path in [*STRATEGIES.values(), INTERACTOR]}
    env = {
        "platform": platform.platform(),
        "uname": subprocess.run(["uname", "-a"], capture_output=True, text=True, check=True).stdout.strip(),
        "macos_version": subprocess.run(["sw_vers", "-productVersion"], capture_output=True, text=True, check=True).stdout.strip(),
        "compiler": clang,
        "python": sys.version,
        "cpu_measurement_comparable_to_linux_gate": False,
        "kpi_comparability": "Both strategies use identical input hashes and the same locally compiled official interactor; source algorithms are deterministic integer code.",
    }
    progress = {
        "status": "running",
        "purpose": "post-hoc local evaluation only; not a qualification gate",
        "environment": env,
        "source_hashes": sources,
        "native_build": {
            "binary_directory": str(NATIVE_BIN.relative_to(HERE)),
            "binary_sha256": binary_hashes,
            "build_script": str((HERE / "build_macos_native_compat.sh").relative_to(HERE)),
            "baseline_flags": "-O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic",
            "candidate_flags": "-O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Wno-unused-but-set-variable -pedantic -Werror",
            "interactor_flags": "-O2 -std=c++17 -pipe",
            "clang_note": "The only warning suppression is for two diagnostic-only counters unused in the production candidate build under Apple Clang; source was not modified.",
        },
        "inputs": inputs,
        "harness_parameters": {
            "cpu_limit_s_reported_by_harness": CPU_LIMIT_S,
            "memory_limit_mib_reported_by_harness": MEMORY_LIMIT_MIB,
            "wall_timeout_s": WALL_TIMEOUT_S,
            "sequential": True,
        },
        "runs": [],
    }
    progress_path = OUT / "run_manifest.json"
    if OUT.exists():
        if not progress_path.is_file():
            raise RuntimeError(f"output root exists without a resumable run manifest: {OUT}")
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        if progress.get("status") != "running":
            raise RuntimeError(f"existing run is not resumable: {progress.get('status')}")
        if progress.get("source_hashes") != sources or progress.get("inputs") != inputs:
            raise RuntimeError("existing run manifest source/input provenance mismatch")
    else:
        OUT.mkdir(parents=True)
        atomic_json(progress_path, progress)

    all_records: dict[str, dict[str, list[dict]]] = {}
    for group, (tests, expected_count) in GROUPS.items():
        all_records[group] = {}
        for strategy, solver in STRATEGIES.items():
            result = run_one(group, strategy, solver, tests, expected_count)
            all_records[group][strategy] = result["summary"]["records"]
            progress["runs"].append({
                "group": group,
                "strategy": strategy,
                "exit_code": result["exit_code"],
                "exit_code_recovered_from_summary": result.get("exit_code_recovered_from_summary", False),
                "command": result["command"],
                "out_dir": result["out_dir"],
                "accepted_count": result["summary"].get("ok_count"),
                "case_count": result["summary"].get("case_count"),
                "summary_sha256": sha256(HERE / result["out_dir"] / "summary.json"),
            })
            atomic_json(progress_path, progress)
            print(
                f"finished {group}/{strategy}: accepted="
                f"{result['summary'].get('ok_count')}/{expected_count}, "
                f"harness_exit={result['exit_code']}",
                flush=True,
            )

    comparison = []
    for group in GROUPS:
        baseline = {record["case"]: record for record in all_records[group]["frozen-final"]}
        candidate = {record["case"]: record for record in all_records[group]["policy-conditioned"]}
        if baseline.keys() != candidate.keys():
            raise RuntimeError(f"baseline/candidate case sets differ for {group}")
        for case in sorted(baseline, key=lambda s: (0, int(s)) if s.isdigit() else (1, s)):
            b, c = baseline[case], candidate[case]
            if b.get("test_sha256") != c.get("test_sha256"):
                raise RuntimeError(f"baseline/candidate input hash differs for {group}/{case}")
            b_out, c_out = Path(b["judge_output_file"]), Path(c["judge_output_file"])
            if not b_out.is_absolute():
                b_out = (OUT / group / "frozen-final" / b_out).resolve()
            if not c_out.is_absolute():
                c_out = (OUT / group / "policy-conditioned" / c_out).resolve()
            comparison.append({
                "group": group,
                "case": case,
                "input_sha256": b["test_sha256"],
                "baseline_status": b["status"],
                "candidate_status": c["status"],
                "baseline_transcript_accepted": accepted(b, b["operation_count"], b["test_sha256"]),
                "candidate_transcript_accepted": accepted(c, c["operation_count"], c["test_sha256"]),
                "operation_count": b["operation_count"],
                "baseline_kpi": b["kpi"],
                "candidate_kpi": c["kpi"],
                "delta_kpi_candidate_minus_baseline": c["kpi"] - b["kpi"],
                "baseline_trench_m": b["trench_length_m"],
                "candidate_trench_m": c["trench_length_m"],
                "delta_trench_m_candidate_minus_baseline": c["trench_length_m"] - b["trench_length_m"],
                "baseline_cpu_s_macos": b["solver_cpu_total_s"],
                "candidate_cpu_s_macos": c["solver_cpu_total_s"],
                "candidate_cpu_limit_exceeded_macos_measurement": c["solver_cpu_limit_exceeded"],
                "baseline_rss_mib": b["solver_peak_rss_mb"],
                "candidate_rss_mib": c["solver_peak_rss_mb"],
                "baseline_answers_sha256": sha256(b_out),
                "candidate_answers_sha256": sha256(c_out),
                "answer_transcripts_identical": b_out.read_bytes() == c_out.read_bytes(),
                "measurement_os": env["platform"],
                "compiler": clang,
                "cpu_comparable_to_linux_gate": False,
            })

    csv_path = OUT / "comparison.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison[0]))
        writer.writeheader()
        writer.writerows(comparison)

    descriptive = {}
    for group in GROUPS:
        rows = [r for r in comparison if r["group"] == group]
        descriptive[group] = {
            "cases": len(rows),
            "baseline_all_transcripts_accepted": all(r["baseline_transcript_accepted"] for r in rows),
            "candidate_all_transcripts_accepted": all(r["candidate_transcript_accepted"] for r in rows),
            "baseline_weighted_score_sum": sum(float(all_records[group]["frozen-final"][i]["weighted_score"]) for i in range(len(rows))),
            "candidate_weighted_score_sum": sum(float(all_records[group]["policy-conditioned"][i]["weighted_score"]) for i in range(len(rows))),
            "mean_delta_kpi_equal_case_weight": sum(r["delta_kpi_candidate_minus_baseline"] for r in rows) / len(rows),
            "mean_delta_trench_m_equal_case_weight": sum(r["delta_trench_m_candidate_minus_baseline"] for r in rows) / len(rows),
            "identical_answer_transcripts": sum(r["answer_transcripts_identical"] for r in rows),
            "different_answer_transcripts": sum(not r["answer_transcripts_identical"] for r in rows),
            "max_candidate_cpu_s_macos": max(float(r["candidate_cpu_s_macos"]) for r in rows),
            "max_candidate_rss_mib": max(float(r["candidate_rss_mib"]) for r in rows),
        }
    progress.update({
        "status": "completed_descriptive_posthoc",
        "qualification_gate": "not evaluated; this mixed-platform post-hoc run does not qualify the candidate or validate Linux CPU limits",
        "descriptive_summary": descriptive,
        "comparison_csv": str(csv_path.relative_to(HERE)),
        "comparison_csv_sha256": sha256(csv_path),
    })
    atomic_json(progress_path, progress)
    report = [
        "# Post-hoc Pipes evaluation — native macOS",
        "",
        "This is a local descriptive evaluation of the existing frozen candidate on 27 cases (Open15 and holdout-v2). It is not a qualification gate. The synthetic validation matrix remains a separate mixed-platform set (16 Linux/GCC 14.2 results plus two macOS results); CPU measurements from macOS are not comparable to the Linux safe/official CPU limits.",
        "",
        f"Environment: `{env['platform']}`; `{env['compiler']}`; Python `{sys.version.split()[0]}`.",
        f"Candidate source: `{sources['candidate_source']['path']}` SHA-256 `{sources['candidate_source']['sha256']}`.",
        f"Frozen baseline SHA-256 `{sources['baseline_source']['sha256']}`. Interactor source SHA-256 `{sources['interactor_source']['sha256']}`.",
        "",
        "KPI and trench values are compared within each exact input against the frozen baseline. Both solvers use the same local official interactor and exact input hash; algorithm decisions use the source's explicit deterministic integer RNG. Native macOS CPU values are reported for diagnosis only and do not establish Linux-limit compliance.",
        "",
        "## Per-case outcomes",
        "",
        "| Set | Case | Baseline KPI | Candidate KPI | ΔKPI | Baseline trench (m) | Candidate trench (m) | Δtrench (m) | Answers identical | Accepted B/C |",
        "|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    for row in comparison:
        report.append(
            f"| {row['group']} | {row['case']} | {row['baseline_kpi']:.9f} | {row['candidate_kpi']:.9f} | "
            f"{row['delta_kpi_candidate_minus_baseline']:+.9f} | {row['baseline_trench_m']} | "
            f"{row['candidate_trench_m']} | {row['delta_trench_m_candidate_minus_baseline']:+d} | "
            f"{'yes' if row['answer_transcripts_identical'] else 'no'} | "
            f"{'yes' if row['baseline_transcript_accepted'] and row['candidate_transcript_accepted'] else 'no'} |"
        )
    report.extend([
        "",
        "## Descriptive summaries",
        "",
        "| Set | Cases | Frozen weighted score sum | Candidate weighted score sum | Mean ΔKPI | Mean Δtrench (m) | Matching answer transcripts |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for group, stats in descriptive.items():
        report.append(
            f"| {group} | {stats['cases']} | {stats['baseline_weighted_score_sum']:.9f} | "
            f"{stats['candidate_weighted_score_sum']:.9f} | {stats['mean_delta_kpi_equal_case_weight']:+.9f} | "
            f"{stats['mean_delta_trench_m_equal_case_weight']:+.2f} | "
            f"{stats['identical_answer_transcripts']}/{stats['cases']} |"
        )
    report.extend([
        "",
        "No Open15/holdout qualification gate or bootstrap claim is made here. Existing synthetic protocol-stop status is unchanged.",
        "",
        "Detailed per-case CPU/RSS, transcript hashes, input hashes, harness exit codes, exact commands, and binary hashes are in `comparison.csv` and `run_manifest.json`.",
        "",
    ])
    report_path = OUT / "REPORT.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    progress["report"] = str(report_path.relative_to(HERE))
    progress["report_sha256"] = sha256(report_path)
    atomic_json(progress_path, progress)
    print(json.dumps(descriptive, indent=2), flush=True)


if __name__ == "__main__":
    main()
