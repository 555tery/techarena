#!/usr/bin/env python3
"""Pair W32/B10 with frozen policy4 and s50 synthetic official-harness runs."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[3]
STRATEGY_ROOT = PROJECT / "results/pipes/improvement/strategies"
SUITE_MANIFEST = STRATEGY_ROOT / "robustness_manifest.json"
SUITE_DIR = STRATEGY_ROOT / "robustness_inputs"
FROZEN_REPORTS = STRATEGY_ROOT / "reports/robustness-frozen"
POLICY4_REPORT = FROZEN_REPORTS / "policy4/summary.json"
S50_REPORT = FROZEN_REPORTS / "recent_unfit_s50/summary.json"
DEMAND_REPORT = ROOT / "runs/robustness-frozen-demand-w32-b10/summary.json"
DEMAND_BINARY = ROOT / "bin/demand_w32_b10"
FROZEN_COMPARISON = FROZEN_REPORTS / "comparison.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


suite = load(SUITE_MANIFEST)
assert suite["purpose"] == "post-freeze diagnostic only; no policy tuning based on these results"
assert len(suite["streams"]) == 10
suite_hashes: dict[str, str] = {}
for stream in suite["streams"]:
    input_path = SUITE_DIR / f"{stream['name']}.in"
    assert sha256(input_path) == stream["sha256"], stream["name"]
    suite_hashes[stream["name"]] = stream["sha256"]

policy4, s50, demand = map(load, (POLICY4_REPORT, S50_REPORT, DEMAND_REPORT))
reports = {"policy4": policy4, "recent_unfit_s50": s50, "demand_w32_b10": demand}
for name, report in reports.items():
    assert report["case_count"] == report["ok_count"] == 10, name
    assert report["weight_sum"] == 10.0, name
    assert all(record["status"] == "ok" for record in report["records"]), name

by_name = {
    name: {str(record["case"]): record for record in report["records"]}
    for name, report in reports.items()
}
expected_cases = set(suite_hashes)
for name, records in by_name.items():
    assert set(records) == expected_cases, (name, set(records) ^ expected_cases)
    for case, expected_hash in suite_hashes.items():
        assert records[case]["test_sha256"] == expected_hash, (name, case)

frozen_comparison = load(FROZEN_COMPARISON)
frozen_entries = {entry["label"]: entry for entry in frozen_comparison["solvers"]}
interactor = Path(frozen_comparison["interactor"])
assert sha256(interactor) == frozen_comparison["interactor_sha256"]
assert all(Path(report["interactor"]).resolve() == interactor.resolve()
           for report in reports.values())
assert frozen_entries["policy4"]["binary_sha256"] == sha256(
    STRATEGY_ROOT / "binaries/policy4_baseline"
)
assert frozen_entries["recent_unfit_s50"]["binary_sha256"] == sha256(
    STRATEGY_ROOT / "binaries/recent_unfit_s50"
)
assert demand["solver_argv"][0] == str(DEMAND_BINARY.resolve())
independent_manifest = load(ROOT / "manifest.json")
w32_cfg = next(row for row in independent_manifest["configurations"]
               if row["candidate"] == "demand-w32-b10")
assert w32_cfg["binary_sha256"] == sha256(DEMAND_BINARY)

rows = []
for case in sorted(expected_cases, key=lambda name: next(
        i for i, item in enumerate(suite["streams"]) if item["name"] == name)):
    b, s, d = (by_name[name][case] for name in
               ("policy4", "recent_unfit_s50", "demand_w32_b10"))
    rows.append({
        "case": case,
        "test_sha256": suite_hashes[case],
        "weight": d["weight"],
        "policy4_kpi": b["kpi"],
        "policy4_trench_m": b["trench_length_m"],
        "policy4_weighted_score": b["weighted_score"],
        "recent_unfit_s50_kpi": s["kpi"],
        "recent_unfit_s50_trench_m": s["trench_length_m"],
        "recent_unfit_s50_weighted_score": s["weighted_score"],
        "demand_w32_b10_kpi": d["kpi"],
        "demand_w32_b10_trench_m": d["trench_length_m"],
        "demand_w32_b10_weighted_score": d["weighted_score"],
        "demand_delta_vs_policy4": d["weighted_score"] - b["weighted_score"],
        "demand_delta_vs_s50": d["weighted_score"] - s["weighted_score"],
    })

csv_path = ROOT / "per_case_robustness_frozen.csv"
with csv_path.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)


def resource_summary(report: dict) -> dict:
    return {
        "max_solver_cpu_s": max(r["solver_cpu_total_s"] for r in report["records"]),
        "max_solver_rss_mib": max(r["solver_peak_rss_mb"] for r in report["records"]),
    }


def pair_stats(column: str, ref: str) -> dict:
    deltas = [row[column] for row in rows]
    return {
        "delta_sum": sum(deltas),
        "wins": sum(delta > 1e-12 for delta in deltas),
        "losses": sum(delta < -1e-12 for delta in deltas),
        "ties": sum(abs(delta) <= 1e-12 for delta in deltas),
        "reference": ref,
    }


result = {
    "suite": str(SUITE_MANIFEST),
    "suite_purpose": suite["purpose"],
    "master_seed": suite["master_seed"],
    "generator_sha256": suite["generator_sha256"],
    "case_count": 10,
    "input_hashes_verified": True,
    "all_reports_same_input_hashes": True,
    "all_three_runs_ok": True,
    "official_interactor_sha256": sha256(interactor),
    "weight_sum": 10.0,
    "scores": {name: report["weighted_score_sum"] for name, report in reports.items()},
    "demand_delta_vs_policy4": demand["weighted_score_sum"] - policy4["weighted_score_sum"],
    "demand_delta_vs_s50": demand["weighted_score_sum"] - s50["weighted_score_sum"],
    "pairwise": {
        "demand_vs_policy4": pair_stats("demand_delta_vs_policy4", "policy4"),
        "demand_vs_s50": pair_stats("demand_delta_vs_s50", "recent_unfit_s50"),
    },
    "resources": {name: resource_summary(report) for name, report in reports.items()},
    "binary_hashes": {
        "demand_w32_b10": sha256(DEMAND_BINARY),
        "policy4": frozen_entries["policy4"]["binary_sha256"],
        "recent_unfit_s50": frozen_entries["recent_unfit_s50"]["binary_sha256"],
    },
    "reports": {
        "demand_w32_b10": str(DEMAND_REPORT.relative_to(ROOT)),
        "policy4": str(POLICY4_REPORT),
        "recent_unfit_s50": str(S50_REPORT),
    },
    "per_case_csv": csv_path.name,
}
(ROOT / "robustness_frozen_comparison.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False) + "\n"
)

lines = [
    "# Synthetic robustness: W32/B10 против policy4 и `recent_unfit_s50`",
    "",
    "Проверен существующий бинарник W32/B10 без изменения solver и параметров. Suite содержит 10 заранее замороженных синтетических потоков; manifest и SHA-256 всех входов сверены. Для policy4 и `recent_unfit_s50` использованы уже сохранённые official-harness отчёты; их input hashes совпали с manifest и новым прогоном W32/B10. Все три варианта прошли 10/10 потоков.",
    "",
    "| Solver | Весовой score / 10 | Δ к policy4 | Δ к s50 | Максимум CPU, s | Максимум RSS, MiB |",
    "|---|---:|---:|---:|---:|---:|",
]
for name in ("policy4", "recent_unfit_s50", "demand_w32_b10"):
    rs = resource_summary(reports[name])
    score = reports[name]["weighted_score_sum"]
    delta_b = score - policy4["weighted_score_sum"]
    delta_s = score - s50["weighted_score_sum"]
    lines.append(f"| `{name}` | {score:.10f} | {delta_b:+.10f} | {delta_s:+.10f} | {rs['max_solver_cpu_s']:.6f} | {rs['max_solver_rss_mib']:.4f} |")
lines += [
    "",
    f"По сравнению с policy4 W32/B10 уступает **{-result['demand_delta_vs_policy4']:.10f}** балла; по сравнению с s50 выигрывает **{result['demand_delta_vs_s50']:.10f}**. На кейсах: против policy4 {result['pairwise']['demand_vs_policy4']['wins']} выигрыша / {result['pairwise']['demand_vs_policy4']['losses']} проигрыша / {result['pairwise']['demand_vs_policy4']['ties']} равенств; против s50 — {result['pairwise']['demand_vs_s50']['wins']} / {result['pairwise']['demand_vs_s50']['losses']} / {result['pairwise']['demand_vs_s50']['ties']}.",
    "",
    "## Покейсовая таблица",
    "",
    f"См. [`{csv_path.name}`](./{csv_path.name}): KPI, длины траншеи, взвешенные вклады и парные дельты для всех потоков.",
    "",
    "## Рекомендация",
    "",
    "На этой заранее замороженной диагностической suite W32/B10 занимает промежуточное положение: выше s50 на 0.0332, ниже policy4 на 0.1150 из 10 баллов. Самая заметная деградация относительно обоих — short-skew random; при этом W32/B10 улучшает s50 при удалении длиннейших труб и на uniform random. Эти 10 специально сконструированных synthetic-потоков не являются официальными или hidden тестами и не дают оценки ожидаемого конкурсного score. Это полезная проверка переносимости, но оснований менять зафиксированный winner только по этой suite недостаточно.",
    "",
    "## Идентификация",
    "",
    f"- W32/B10 binary: `{DEMAND_BINARY}`, SHA-256 `{result['binary_hashes']['demand_w32_b10']}`.",
    f"- policy4 binary SHA-256: `{result['binary_hashes']['policy4']}`.",
    f"- `recent_unfit_s50` binary SHA-256: `{result['binary_hashes']['recent_unfit_s50']}`.",
    f"- Seed master: `{suite['master_seed']}`; generator SHA-256: `{suite['generator_sha256']}`.",
    f"- Official interactor SHA-256 (identical for all three reports): `{result['official_interactor_sha256']}`.",
    "- Результаты W32/B10: `runs/robustness-frozen-demand-w32-b10/summary.json`.",
    "- Результаты policy4 и s50: сохранённые отчёты в `results/pipes/improvement/strategies/reports/robustness-frozen/`.",
]
(ROOT / "ROBUSTNESS_REPORT.md").write_text("\n".join(lines) + "\n")
print(json.dumps(result, indent=2, ensure_ascii=False))
