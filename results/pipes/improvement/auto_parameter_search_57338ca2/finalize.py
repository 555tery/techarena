#!/usr/bin/env python3
"""Freeze the report and manifest for the bounded Pipes knob search."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
EXPECTED = "57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f"
KNOBS = {
    "unfit_penalty": "kUnfitPenaltyScale",
    "same_length_run": "kSameLengthRightRun",
    "right_edge_cap": "kRightEdgeMaxPipeLength",
    "mc_min_saving": "kMcMinimumMeanSavingM",
    "mc_decision_budget": "kMcDecisionBudget",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary_info(path: Path) -> dict:
    d = json.loads(path.read_text())
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha(path),
        "case_count": d["case_count"],
        "ok_count": d["ok_count"],
        "weighted_score_sum": d["weighted_score_sum"],
        "weight_sum": d["weight_sum"],
        "max_solver_cpu_s": max(r["solver_cpu_total_s"] for r in d["records"]),
        "max_solver_cpu_case": max(d["records"], key=lambda r: r["solver_cpu_total_s"])["case"],
        "max_solver_peak_rss_mib": max(r["solver_peak_rss_mb"] for r in d["records"]),
        "max_solver_rss_case": max(d["records"], key=lambda r: r["solver_peak_rss_mb"])["case"],
        "per_case": [{
            "case": r["case"], "input_sha256": r["test_sha256"],
            "weighted_score": r["weighted_score"],
            "solver_cpu_s": r["solver_cpu_total_s"],
            "solver_peak_rss_mib": r["solver_peak_rss_mb"],
            "status": r["status"],
        } for r in d["records"]],
    }


def main() -> None:
    final_source = ROOT / "results/pipes/final/solution.cpp"
    if sha(final_source) != EXPECTED:
        raise SystemExit("Frozen final source hash changed")
    search = json.loads((OUT / "search-results.json").read_text())
    rows = search["ranking"]
    control = next(r for r in rows if r["index"] == 0)
    challenger = next(r for r in rows if r["index"] != 0)
    if control["weighted_score_sum"] != max(r["weighted_score_sum"] for r in rows):
        raise SystemExit("Baseline is no longer top-ranked")

    base_lines = final_source.read_text().splitlines()
    by_index = []
    for row in rows:
        d = OUT / "configs" / row["name"]
        source = d / "solution.cpp"
        candidate_lines = source.read_text().splitlines()
        changed = [(a, b) for a, b in zip(base_lines, candidate_lines) if a != b]
        if any(not any(name in line for name in KNOBS.values()) for _, line in changed):
            raise SystemExit(f"Unexpected source edit in {row['name']}")
        for key, name in KNOBS.items():
            declared = re.search(rf"\b{re.escape(name)} = (\d+);", "\n".join(candidate_lines))
            if not declared or int(declared.group(1)) != row["parameters"][key]:
                raise SystemExit(f"Parameter mismatch in {row['name']}: {key}")
        if sha(source) != row["source_sha256"]:
            raise SystemExit(f"Source hash mismatch in {row['name']}")
        by_index.append({
            **row,
            "source_path": str(source.relative_to(ROOT)),
            "binary_path": str((d / "solver").relative_to(ROOT)),
            "open_summary_path": str((d / "open/summary.json").relative_to(ROOT)),
            "open_cases_csv_path": str((d / "open/cases.csv").relative_to(ROOT)),
        })

    control_dir = OUT / "configs" / control["name"]
    challenger_dir = OUT / "configs" / challenger["name"]
    base_summary = json.loads((control_dir / "open/summary.json").read_text())
    challenger_summary = json.loads((challenger_dir / "open/summary.json").read_text())
    with (OUT / "best-challenger-per-case.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case", "weight", "input_sha256", "baseline_weighted_score",
                         "best_challenger_weighted_score", "delta_vs_baseline",
                         "baseline_trench_m", "challenger_trench_m"])
        for b, c in zip(base_summary["records"], challenger_summary["records"]):
            writer.writerow([b["case"], b["official_weight"], b["test_sha256"],
                             b["weighted_score"], c["weighted_score"],
                             c["weighted_score"] - b["weighted_score"],
                             b["trench_length_m"], c["trench_length_m"]])

    open_info = summary_info(control_dir / "open/summary.json")
    holdout = summary_info(control_dir / "holdout-v2/summary.json")
    synthetic = summary_info(control_dir / "synthetic-development/summary.json")
    ranked_resources = {
        "max_solver_cpu_s": max(r["max_solver_cpu_s"] for r in rows),
        "max_solver_cpu_config": max(rows, key=lambda r: r["max_solver_cpu_s"])["name"],
        "max_solver_peak_rss_mib": max(r["max_solver_peak_rss_mib"] for r in rows),
        "max_solver_rss_config": max(rows, key=lambda r: r["max_solver_peak_rss_mib"])["name"],
    }
    manifest = {
        "task": "Bounded automatic parameter search on frozen final Pipes source",
        "source": {
            "path": "results/pipes/final/solution.cpp", "sha256": EXPECTED,
            "final_source_unchanged_at_report_time": True,
            "baseline_copy_path": "results/pipes/improvement/auto_parameter_search_57338ca2/base-source.cpp",
            "baseline_copy_sha256": sha(OUT / "base-source.cpp"),
            "candidate_generation_changes_only_named_numeric_constants": True,
            "parity_trigger_and_allocator_logic_unchanged": True,
        },
        "search": {
            "method": search["method"], "seed": search["seed"],
            "sampling_attempt": search["attempt"],
            "count_including_baseline": search["config_count_including_baseline"],
            "objective": "Exact sum of harness weighted_score over all 15 official open cases",
            "screening_used": False, "fixed_parity_trigger": True,
            "domains": search["domains"], "baseline_parameters": search["baseline_parameters"],
            "baseline_score": control["weighted_score_sum"],
            "best_configuration": control["name"], "best_is_unchanged_baseline": True,
            "best_new_configuration": challenger["name"],
            "best_new_score": challenger["weighted_score_sum"],
            "best_new_delta_vs_baseline": challenger["weighted_score_sum"] - control["weighted_score_sum"],
            "no_new_configuration_improved_baseline": all(
                r["weighted_score_sum"] <= control["weighted_score_sum"] for r in rows if r["index"] != 0
            ),
            "multiple_comparison_overfit_caveat": (
                "All 15 open cases selected among 19 generated variants plus the baseline; the maximum is tuned to this open set. "
                "Holdout-v2 and development synthetic sets were run only after selection, but earlier project experiments in the repository reused these datasets, so they are not pristine independent blind holdouts."
            ),
        },
        "tools": {
            "search_script_path": "results/pipes/improvement/auto_parameter_search_57338ca2/search.py",
            "search_script_sha256": sha(OUT / "search.py"),
            "harness_path": "tools/pipes_harness.py", "harness_sha256": sha(ROOT / "tools/pipes_harness.py"),
            "interactor_path": "tools/interactor", "interactor_sha256": sha(ROOT / "tools/interactor"),
            "compiler": "clang++", "flags": ["-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra", "-Wconversion", "-Wshadow", "-pedantic", "-Werror"],
        },
        "limits": {"solver_cpu_seconds": 5.0, "solver_memory_mib": 256.0},
        "ranking": by_index,
        "winner_validation": {
            "open": open_info, "holdout_v2": holdout,
            "synthetic_development_modes": synthetic,
            "all_runs_ok": all(x["ok_count"] == x["case_count"] for x in [open_info, holdout, synthetic]),
        },
        "aggregate_search_resources": ranked_resources,
        "comparison_artifact": {
            "path": "results/pipes/improvement/auto_parameter_search_57338ca2/best-challenger-per-case.csv",
            "sha256": sha(OUT / "best-challenger-per-case.csv"),
        },
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    report = [
        "# Автоматический поиск параметров на frozen Pipes source", "",
        f"Исходник: `results/pipes/final/solution.cpp`, SHA-256 `{EXPECTED}`. Final source не менялся.", "",
        "## Метод", "",
        "Проверены 20 конфигураций: frozen baseline и 19 уникальных точек seeded randomized Latin-hypercube search (seed `20261016`). Каждый вариант прошёл полный официальный open-набор из 15 тестов; screening не применялся. Цель — точная сумма `weighted_score` по этим 15 кейсам. Менялись только числовые константы `kUnfitPenaltyScale`, `kSameLengthRightRun`, `kRightEdgeMaxPipeLength`, `kMcMinimumMeanSavingM`, `kMcDecisionBudget`. Parity trigger и allocator logic не менялись. Полные исходники, бинарники и harness output каждого прогона сохранены в `configs/`.", "",
        "## Результат", "",
        f"Лучший результат — исходная конфигурация: **{control['weighted_score_sum']:.12f}**. Лучший новый вариант `{challenger['name']}` получил **{challenger['weighted_score_sum']:.12f}** (дельта **{challenger['weighted_score_sum']-control['weighted_score_sum']:+.12f}**). Ни одна из 19 новых конфигураций baseline не превзошла; новых кандидатов для переноса нет.", "",
        "| Ранг | Конфигурация | Параметры (penalty/run/edge/minSaving/budget) | Open weighted sum | Δ к baseline | Max CPU | Max RSS |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for i, row in enumerate(rows[:5], 1):
        p = row["parameters"]
        report.append(f"| {i} | `{row['name']}` | {p['unfit_penalty']}/{p['same_length_run']}/{p['right_edge_cap']}/{p['mc_min_saving']}/{p['mc_decision_budget']} | {row['weighted_score_sum']:.12f} | {row['weighted_score_sum']-control['weighted_score_sum']:+.12f} | {row['max_solver_cpu_s']:.6f}s | {row['max_solver_peak_rss_mib']:.3f} MiB |")
    report += [
        "", "Полный ranking и SHA-256: [`open-ranking.csv`](open-ranking.csv), [`search-results.json`](search-results.json); per-case разность лучшего нового варианта к baseline: [`best-challenger-per-case.csv`](best-challenger-per-case.csv).", "",
        "## Проверки top-ranked winner", "",
        f"Frozen baseline с тем же SHA прошёл open15: {open_info['ok_count']}/15, **{open_info['weighted_score_sum']:.12f}**, max {open_info['max_solver_cpu_s']:.6f}s CPU / {open_info['max_solver_peak_rss_mib']:.3f} MiB RSS.", "",
        f"После выбора на open были выполнены фиксированные дополнительные наборы: holdout-v2 — {holdout['ok_count']}/{holdout['case_count']}, weighted sum **{holdout['weighted_score_sum']:.12f}**, max {holdout['max_solver_cpu_s']:.6f}s / {holdout['max_solver_peak_rss_mib']:.3f} MiB; synthetic development modes — {synthetic['ok_count']}/{synthetic['case_count']}, sum **{synthetic['weighted_score_sum']:.12f}**, max {synthetic['max_solver_cpu_s']:.6f}s / {synthetic['max_solver_peak_rss_mib']:.3f} MiB.", "",
        "## Caveat по split и переобучению", "",
        "Все 15 open cases использованы непосредственно для отбора максимума среди 19 случайных конфигураций и baseline, поэтому результат на open настроен по этому набору. Holdout-v2 и четыре synthetic development режима запускались только после выбора; однако эти файлы и ранее использовались в экспериментах, отражённых в репозитории, поэтому их нельзя считать полностью нетронутыми независимыми holdout-наборами.", "",
        "Точный frozen source hash, команды, input hashes, per-case CPU/RSS, артефакты и перечень всех 20 вариантов — в [`manifest.json`](manifest.json). Повторный запуск поиска: `python3 results/pipes/improvement/auto_parameter_search_57338ca2/search.py`.", "",
    ]
    (OUT / "REPORT.md").write_text("\n".join(report))
    print("report_sha256", sha(OUT / "REPORT.md"))
    print("manifest_sha256", sha(OUT / "manifest.json"))
    print("baseline", control["weighted_score_sum"], "best new", challenger["weighted_score_sum"])


if __name__ == "__main__":
    main()
