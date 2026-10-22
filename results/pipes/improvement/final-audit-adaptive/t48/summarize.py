#!/usr/bin/env python3
"""Join T48 candidate, canonical S50, and UBSan official-harness reports."""

import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs" / "open"


def load(name):
    data = json.loads((RUNS / name / "summary.json").read_text(encoding="utf-8"))
    if data["ok_count"] != data["case_count"]:
        raise SystemExit(f"not all cases passed in {name}")
    return data


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    candidate = load("candidate")
    canonical = load("canonical-s50")
    ubsan = load("candidate-ubsan")
    sources = {
        name: {str(row["case"]): row for row in suite["records"]}
        for name, suite in (("candidate", candidate), ("canonical", canonical), ("ubsan", ubsan))
    }
    if any(set(rows) != set(sources["candidate"]) for rows in sources.values()):
        raise SystemExit("the three runs do not contain the same cases")

    rows = []
    for case in sources["candidate"]:
        c, b, u = (sources[name][case] for name in ("candidate", "canonical", "ubsan"))
        if len({c["test_sha256"], b["test_sha256"], u["test_sha256"]}) != 1:
            raise SystemExit(f"input mismatch on case {case}")
        if any(c[key] != u[key] for key in ("weighted_score", "kpi", "trench_length_m", "occupied_length_m")):
            raise SystemExit(f"optimized and UBSan builds differ on case {case}")
        rows.append({
            "case": case,
            "input_sha256": c["test_sha256"],
            "operation_count": c["operation_count"],
            "weight": c["official_weight"],
            "interactor_commands_including_zero": c["judge_commands_seen_including_final_zero"],
            "candidate_status": c["status"],
            "candidate_occupied_m": c["occupied_length_m"],
            "candidate_trench_m": c["trench_length_m"],
            "candidate_kpi": c["kpi"],
            "candidate_weighted_score": c["weighted_score"],
            "candidate_cpu_s": c["solver_cpu_total_s"],
            "candidate_rss_mib": c["solver_peak_rss_mb"],
            "canonical_status": b["status"],
            "canonical_occupied_m": b["occupied_length_m"],
            "canonical_trench_m": b["trench_length_m"],
            "canonical_kpi": b["kpi"],
            "canonical_weighted_score": b["weighted_score"],
            "canonical_cpu_s": b["solver_cpu_total_s"],
            "canonical_rss_mib": b["solver_peak_rss_mb"],
            "candidate_minus_canonical_score": c["weighted_score"] - b["weighted_score"],
            "ubsan_status": u["status"],
            "ubsan_weighted_score": u["weighted_score"],
            "ubsan_stderr": u.get("candidate_stderr", ""),
        })
    with (HERE / "per_case.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    source_candidate = Path("/Users/555tery/techarena/results/pipes/improvement/max_open_lookahead/candidate_adaptive_right4_w2048_s60_recent48_right.cpp")
    source_canonical = Path("/Users/555tery/techarena/src/pipes.cpp")
    harness = Path("/Users/555tery/techarena/tools/pipes_harness.py")
    interactor = Path("/Users/555tery/techarena/tools/interactor")
    summary = {
        "suite": "official open tests 1..15",
        "candidate": {
            "score_sum": candidate["weighted_score_sum"], "weight_sum": candidate["weight_sum"],
            "ok_count": candidate["ok_count"],
            "max_cpu_s": max(float(row["solver_cpu_total_s"]) for row in candidate["records"]),
            "max_rss_mib": max(float(row["solver_peak_rss_mb"]) for row in candidate["records"]),
            "total_commands_including_zero": sum(row["judge_commands_seen_including_final_zero"] for row in candidate["records"]),
        },
        "canonical_s50": {
            "score_sum": canonical["weighted_score_sum"], "weight_sum": canonical["weight_sum"],
            "ok_count": canonical["ok_count"],
            "max_cpu_s": max(float(row["solver_cpu_total_s"]) for row in canonical["records"]),
            "max_rss_mib": max(float(row["solver_peak_rss_mb"]) for row in canonical["records"]),
            "total_commands_including_zero": sum(row["judge_commands_seen_including_final_zero"] for row in canonical["records"]),
        },
        "candidate_ubsan": {
            "score_sum": ubsan["weighted_score_sum"], "weight_sum": ubsan["weight_sum"],
            "ok_count": ubsan["ok_count"],
            "max_cpu_s": max(float(row["solver_cpu_total_s"]) for row in ubsan["records"]),
            "max_rss_mib": max(float(row["solver_peak_rss_mb"]) for row in ubsan["records"]),
            "total_commands_including_zero": sum(row["judge_commands_seen_including_final_zero"] for row in ubsan["records"]),
            "stderr_empty_for_all_cases": all(not row.get("candidate_stderr", "") for row in ubsan["records"]),
            "case_scores_match_optimized_build": all(
                sources["candidate"][case]["weighted_score"] == sources["ubsan"][case]["weighted_score"]
                for case in sources["candidate"]
            ),
        },
        "candidate_minus_canonical_score_sum": candidate["weighted_score_sum"] - canonical["weighted_score_sum"],
        "case_count": len(rows),
        "pairwise_input_hashes_match": True,
        "files_sha256": {
            "candidate_source": sha256(source_candidate),
            "canonical_source": sha256(source_canonical),
            "candidate_strict_binary": sha256(HERE / "candidate_strict"),
            "canonical_strict_binary": sha256(HERE / "canonical_s50_strict"),
            "candidate_ubsan_binary": sha256(HERE / "candidate_ubsan"),
            "harness": sha256(harness),
            "interactor": sha256(interactor),
        },
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
