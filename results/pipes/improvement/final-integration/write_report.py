#!/usr/bin/env python3
"""Build the final canonical T46 integration report from fresh harness outputs."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
FROZEN = ROOT / "results/pipes/improvement/max_open_lookahead/candidate_adaptive_right4_w2048_s60_recent46_right.cpp"
CANONICAL = ROOT / "src/pipes.cpp"
T46_BIN = OUT / "pipes_t46_canonical"
S50_BIN = ROOT / "results/pipes/improvement/strategies/binaries/canonical_recent_unfit_s50_cxx20"
INTERACTOR = ROOT / "tools/interactor"
T46_SUMMARY = OUT / "t46_fresh/summary.json"
S50_SUMMARY = OUT / "s50_fresh/summary.json"
EXPECTED_SOURCE_SHA = "526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1 << 20), b""):
            h.update(data)
    return h.hexdigest()


def summary(path):
    return json.loads(Path(path).read_text())


def main():
    source_sha = sha(CANONICAL)
    frozen_sha = sha(FROZEN)
    if source_sha != EXPECTED_SOURCE_SHA or frozen_sha != EXPECTED_SOURCE_SHA or source_sha != frozen_sha:
        raise SystemExit(f"source hash mismatch: canonical={source_sha}, frozen={frozen_sha}")

    t46 = summary(T46_SUMMARY)
    s50 = summary(S50_SUMMARY)
    if t46["ok_count"] != 15 or t46["case_count"] != 15:
        raise SystemExit("T46 did not pass all 15 open tests")
    if s50["ok_count"] != 15 or s50["case_count"] != 15:
        raise SystemExit("S50 reference did not pass all 15 open tests")
    t46_records = {str(r["case"]): r for r in t46["records"]}
    s50_records = {str(r["case"]): r for r in s50["records"]}
    if set(t46_records) != set(s50_records) or len(t46_records) != 15:
        raise SystemExit("candidate/reference cases differ")

    rows = []
    for case in sorted(t46_records, key=int):
        a = t46_records[case]
        b = s50_records[case]
        if a["test_sha256"] != b["test_sha256"]:
            raise SystemExit(f"input hash differs for case {case}")
        if a["official_weight"] != b["official_weight"]:
            raise SystemExit(f"official weight differs for case {case}")
        weight = float(a["official_weight"])
        rows.append({
            "case": case,
            "test_sha256": a["test_sha256"],
            "weight": weight,
            "T46_status": a["status"],
            "T46_kpi": a["kpi"],
            "T46_occupied_m": a["occupied_length_m"],
            "T46_trench_m": a["trench_length_m"],
            "S50_status": b["status"],
            "S50_kpi": b["kpi"],
            "S50_occupied_m": b["occupied_length_m"],
            "S50_trench_m": b["trench_length_m"],
            "T46_weighted_delta_vs_S50": weight * (float(a["kpi"]) - float(b["kpi"])),
        })

    case_csv = OUT / "per_case_vs_s50.csv"
    with case_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    weights = [r["weight"] for r in rows]
    test_hashes = {r["case"]: r["test_sha256"] for r in rows}
    t46_cpu = [r.get("solver_cpu_total_s") or 0.0 for r in t46["records"]]
    t46_rss = [r.get("solver_peak_rss_mb") or 0.0 for r in t46["records"]]
    t46_wall = [r.get("wall_orchestration_s") or 0.0 for r in t46["records"]]
    s50_cpu = [r.get("solver_cpu_total_s") or 0.0 for r in s50["records"]]
    s50_rss = [r.get("solver_peak_rss_mb") or 0.0 for r in s50["records"]]
    s50_wall = [r.get("wall_orchestration_s") or 0.0 for r in s50["records"]]
    compile_command = ("g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror "
                       "src/pipes.cpp -o results/pipes/improvement/final-integration/pipes_t46_canonical")
    t46_command = ("python3 tools/pipes_harness.py --solver "
                   "results/pipes/improvement/final-integration/pipes_t46_canonical "
                   "--name t46_canonical --interactor tools/interactor --tests data/pipes/open "
                   "--out results/pipes/improvement/final-integration/t46_fresh "
                   "--cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120")
    s50_command = ("python3 tools/pipes_harness.py --solver "
                   "results/pipes/improvement/strategies/binaries/canonical_recent_unfit_s50_cxx20 "
                   "--name s50_reference --interactor tools/interactor --tests data/pipes/open "
                   "--out results/pipes/improvement/final-integration/s50_fresh "
                   "--cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120")
    verify = {
        "candidate": "T46: W=2048, S=60, right4 plus 46-placement lookback run rule",
        "frozen_source": str(FROZEN), "frozen_source_sha256": frozen_sha,
        "canonical_source": str(CANONICAL), "canonical_source_sha256": source_sha,
        "canonical_matches_frozen_source": source_sha == frozen_sha == EXPECTED_SOURCE_SHA,
        "canonical_binary": str(T46_BIN), "canonical_binary_sha256": sha(T46_BIN),
        "s50_reference_binary": str(S50_BIN), "s50_reference_binary_sha256": sha(S50_BIN),
        "interactor": str(INTERACTOR), "interactor_sha256": sha(INTERACTOR),
        "open_test_sha256": test_hashes,
        "candidate_harness_summary": str(T46_SUMMARY),
        "s50_harness_summary": str(S50_SUMMARY),
        "candidate_weighted_score": t46["weighted_score_sum"],
        "s50_weighted_score": s50["weighted_score_sum"],
        "weight_sum": t46["weight_sum"],
        "delta_vs_s50": t46["weighted_score_sum"] - s50["weighted_score_sum"],
        "candidate_valid": t46["ok_count"], "case_count": t46["case_count"],
        "s50_valid": s50["ok_count"],
        "candidate_cpu_sum_s": sum(t46_cpu), "candidate_cpu_max_s": max(t46_cpu),
        "candidate_rss_max_mib": max(t46_rss), "candidate_wall_sum_s": sum(t46_wall),
        "candidate_wall_max_s": max(t46_wall),
        "s50_cpu_sum_s": sum(s50_cpu), "s50_cpu_max_s": max(s50_cpu),
        "s50_rss_max_mib": max(s50_rss), "s50_wall_sum_s": sum(s50_wall),
        "s50_wall_max_s": max(s50_wall),
        "compile_command": compile_command,
        "candidate_harness_command": t46_command,
        "s50_harness_command": s50_command,
        "closed_test_result": "not measured",
        "sweep_claim": "best in the checked sweep; not a proof of global optimum",
    }
    (OUT / "verification.json").write_text(json.dumps(verify, indent=2) + "\n", encoding="utf-8")

    report = f"""# Canonical T46 integration report

## Frozen source and build

The requested frozen candidate was hash-checked before copying. Frozen source and canonical `src/pipes.cpp` both have SHA-256 `{frozen_sha}`. The strict C++20 build succeeded with `-Wall -Wextra -Wconversion -Wshadow -pedantic -Werror`; canonical binary SHA-256 is `{verify['canonical_binary_sha256']}`.

## Fresh official open run

Canonical T46 passed **{t46['ok_count']}/15** open tests and scored **{t46['weighted_score_sum']:.12f}/{t46['weight_sum']:.1f}**. A fresh run of the S50 reference binary on the same inputs and interactor scored **{s50['weighted_score_sum']:.12f}/{s50['weight_sum']:.1f}**. The T46 improvement is **{verify['delta_vs_s50']:+.12f}** weighted points. Input hashes match case-by-case between both runs and all weights are identical.

T46 resource measurements: CPU sum/max **{verify['candidate_cpu_sum_s']:.6f}/{verify['candidate_cpu_max_s']:.6f} s**, maximum RSS **{verify['candidate_rss_max_mib']:.3f} MiB**, harness wall sum/max **{verify['candidate_wall_sum_s']:.3f}/{verify['candidate_wall_max_s']:.3f} s**. The S50 reference run measured CPU sum/max **{verify['s50_cpu_sum_s']:.6f}/{verify['s50_cpu_max_s']:.6f} s**, maximum RSS **{verify['s50_rss_max_mib']:.3f} MiB**, harness wall sum/max **{verify['s50_wall_sum_s']:.3f}/{verify['s50_wall_max_s']:.3f} s**.

The algorithm uses W=2048 and S=60. For the selected free interval it places lengths up to 4 m at the right endpoint. A longer current pipe also uses the right endpoint when the last 46 positive placement lengths all equal the current length; otherwise it uses the left endpoint. Deletions do not reset this insertion-history run.

T46 was the best candidate in the checked sweep. This is not a proof of global optimality. Closed-test performance was **not measured**.

## Per-case results

The full per-case KPI, occupied length, trench length, input hash, and weighted delta to S50 are in [per_case_vs_s50.csv](per_case_vs_s50.csv). Full raw harness outputs are retained in [t46_fresh](t46_fresh/) and [s50_fresh](s50_fresh/); `verification.json` contains source, binary, interactor, input hashes and exact commands.

## Reproduction

```sh
{compile_command}
{t46_command}
{s50_command}
```
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(f"T46={t46['weighted_score_sum']:.12f}, S50={s50['weighted_score_sum']:.12f}, "
          f"delta={verify['delta_vs_s50']:+.12f}; reports written to {OUT}")


if __name__ == "__main__":
    main()
