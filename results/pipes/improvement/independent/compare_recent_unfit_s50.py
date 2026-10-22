#!/usr/bin/env python3
"""Paired open-set comparison against the recent_unfit_s50 reference."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"
RECENT_REPORT = RUNS / "recent-unfit-s50-reference" / "summary.json"
DEMAND_REPORT = RUNS / "demand-w32-b10" / "summary.json"
BASELINE_REPORT = RUNS / "baseline-policy4" / "summary.json"
HYBRID_REPORT = RUNS / "hybrid-age-interior-5" / "summary.json"
RECENT_SOURCE = Path("results/pipes/improvement/strategies/adaptive_allocator.cpp").resolve()
RECENT_BINARY = Path("results/pipes/improvement/strategies/binaries/recent_unfit_s50").resolve()


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(report: dict) -> dict[str, dict]:
    return {str(row["case"]): row for row in report["records"]}


recent, demand = read(RECENT_REPORT), read(DEMAND_REPORT)
baseline, hybrid = read(BASELINE_REPORT), read(HYBRID_REPORT)
reports = {
    "recent_unfit_s50": recent,
    "demand_w32_b10": demand,
    "policy4_baseline": baseline,
    "hybrid_age_5": hybrid,
}
for name, report in reports.items():
    assert report["case_count"] == report["ok_count"] == 15, name
    assert report["weight_sum"] == 32.1, name

by_name = {name: records(report) for name, report in reports.items()}
case_ids = sorted(by_name["recent_unfit_s50"], key=int)
assert len(case_ids) == 15
for name, cases in by_name.items():
    assert set(cases) == set(case_ids), name
    for case in case_ids:
        assert cases[case]["test_sha256"] == by_name["policy4_baseline"][case]["test_sha256"], (name, case)

rows = []
for case in case_ids:
    r = by_name["recent_unfit_s50"][case]
    d = by_name["demand_w32_b10"][case]
    b = by_name["policy4_baseline"][case]
    h = by_name["hybrid_age_5"][case]
    rows.append({
        "case": int(case),
        "weight": r["weight"],
        "test_sha256": r["test_sha256"],
        "recent_unfit_s50_kpi": r["kpi"],
        "recent_unfit_s50_trench_m": r["trench_length_m"],
        "demand_w32_b10_kpi": d["kpi"],
        "demand_w32_b10_trench_m": d["trench_length_m"],
        "demand_weighted_delta_vs_recent": d["weighted_score"] - r["weighted_score"],
        "baseline_kpi": b["kpi"],
        "baseline_trench_m": b["trench_length_m"],
        "hybrid_age5_kpi": h["kpi"],
        "hybrid_age5_trench_m": h["trench_length_m"],
    })

csv_path = ROOT / "per_case_vs_recent_unfit_s50.csv"
with csv_path.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

def resource_summary(report: dict) -> dict:
    return {
        "max_solver_cpu_s": max(r["solver_cpu_total_s"] for r in report["records"]),
        "max_solver_rss_mib": max(r["solver_peak_rss_mb"] for r in report["records"]),
    }

recent_build = read(Path("results/pipes/improvement/strategies/build_manifest.json"))
recent_entry = next(item for item in recent_build["candidates"] if item["name"] == "recent_unfit_s50")
assert recent_build["source_sha256"] == sha256(RECENT_SOURCE)
assert recent_entry["binary_sha256"] == sha256(RECENT_BINARY)

score_diff = demand["weighted_score_sum"] - recent["weighted_score_sum"]
result = {
    "scope": "same 15 official open tests only; no holdout-v2 data read or run",
    "test_hashes_match_across_all_reports": True,
    "case_count": 15,
    "weight_sum": 32.1,
    "demand_w32_b10": {
        "score": demand["weighted_score_sum"],
        "report": str(DEMAND_REPORT.relative_to(ROOT)),
        "source": "source/demand_aware.cpp",
        "source_sha256": sha256(ROOT / "source" / "demand_aware.cpp"),
        "binary": "bin/demand_w32_b10",
        "binary_sha256": sha256(ROOT / "bin" / "demand_w32_b10"),
        **resource_summary(demand),
    },
    "recent_unfit_s50": {
        "score": recent["weighted_score_sum"],
        "report": str(RECENT_REPORT.relative_to(ROOT)),
        "source_path": str(RECENT_SOURCE),
        "source_sha256": sha256(RECENT_SOURCE),
        "build_strategy": recent_entry["strategy"],
        "history_window": recent_entry["history_window"],
        "penalty_scale": recent_entry["penalty_scale"],
        "compile_command": recent_entry["command"],
        "binary_path": str(RECENT_BINARY),
        "binary_sha256": sha256(RECENT_BINARY),
        **resource_summary(recent),
    },
    "policy4_baseline_score": baseline["weighted_score_sum"],
    "hybrid_age5_score": hybrid["weighted_score_sum"],
    "demand_delta_vs_recent": score_diff,
    "per_case_csv": csv_path.name,
    "recent_report_is_independently_rerun": True,
}
(ROOT / "comparison_recent_unfit_s50.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

gains = [row for row in rows if row["demand_weighted_delta_vs_recent"] > 1e-12]
losses = [row for row in rows if row["demand_weighted_delta_vs_recent"] < -1e-12]
ties = [row for row in rows if abs(row["demand_weighted_delta_vs_recent"]) <= 1e-12]
report_lines = [
    "# Независимое сравнение с `recent_unfit_s50`",
    "",
    "Официальный harness повторно прогнал бинарник strategy-агента по всем 15 открытым тестам. Сверены SHA-256 файлов входных тестов с baseline и demand-aware запуском; совпали все 15. Frozen holdout-v2 не читался и не запускался.",
    "",
    "| Solver | Weighted score / 32.1 | OK | max CPU (s) | max RSS (MiB) |",
    "|---|---:|---:|---:|---:|",
]
for label, report in [("recent_unfit_s50", recent), ("demand W32/B10", demand), ("policy4 baseline", baseline), ("age hybrid L<=5", hybrid)]:
    resource = resource_summary(report)
    report_lines.append(f"| `{label}` | {report['weighted_score_sum']:.10f} | {report['ok_count']}/15 | {resource['max_solver_cpu_s']:.6f} | {resource['max_solver_rss_mib']:.4f} |")
report_lines += [
    "",
    f"Разница W32/B10 минус `recent_unfit_s50`: **{score_diff:+.10f}** балла. По суммарному score открытых тестов W32/B10 {'выше' if score_diff > 0 else 'ниже' if score_diff < 0 else 'равен'}.",
    "",
    f"По отдельным тестам W32/B10 выигрывает {len(gains)} раз, проигрывает {len(losses)} раз и совпадает {len(ties)} раз по взвешенному score с `recent_unfit_s50`. Разницы по кейсам приведены в [`{csv_path.name}`](./{csv_path.name}).",
    "",
    "| Case | Weight | recent KPI / trench (m) | demand KPI / trench (m) | demand weighted delta |",
    "|---:|---:|---:|---:|---:|",
]
for row in rows:
    report_lines.append(f"| {row['case']} | {row['weight']:g} | {row['recent_unfit_s50_kpi']:.9f} / {row['recent_unfit_s50_trench_m']} | {row['demand_w32_b10_kpi']:.9f} / {row['demand_w32_b10_trench_m']} | {row['demand_weighted_delta_vs_recent']:+.9f} |")
report_lines += [
    "",
    "## Идентификация артефактов",
    "",
    f"- Demand source: `results/pipes/improvement/independent/source/demand_aware.cpp`, SHA-256 `{result['demand_w32_b10']['source_sha256']}`.",
    f"- Demand binary: `results/pipes/improvement/independent/bin/demand_w32_b10`, SHA-256 `{result['demand_w32_b10']['binary_sha256']}`.",
    f"- Reference source: `{RECENT_SOURCE}`, SHA-256 `{result['recent_unfit_s50']['source_sha256']}`.",
    f"- Reference binary: `{RECENT_BINARY}`, SHA-256 `{result['recent_unfit_s50']['binary_sha256']}`.",
    f"- Reference build: `{recent_entry['command']}`.",
    f"- Exact official run report: `results/pipes/improvement/independent/{RECENT_REPORT.relative_to(ROOT)}`.",
    "",
    "Результаты показывают только эмпирическое сравнение на публичном наборе, а не ожидаемый балл на невидимых входах. W32/B10 выбран после sweep по шести конфигурациям на этом же наборе, поэтому лучший результат подвержен selection bias. `recent_unfit_s50` повторно прогнан по тем же 15 входам для парного сравнения.",
]
(ROOT / "REPORT_recent_unfit_s50.md").write_text("\n".join(report_lines) + "\n")
print(json.dumps(result, indent=2, ensure_ascii=False))
