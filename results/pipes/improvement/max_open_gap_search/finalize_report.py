#!/usr/bin/env python3
"""Freeze hashes, per-case comparisons, and a compact search report."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
REPORTS = BASE / "reports"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1 << 20), b""):
            h.update(data)
    return h.hexdigest()


def read_summary(name):
    return json.loads((REPORTS / name / "summary.json").read_text())


def read_cases(name):
    with (REPORTS / name / "cases.csv").open(newline="", encoding="utf-8") as stream:
        return {str(row["case"]): row for row in csv.DictReader(stream)}


def write_case_comparison():
    names = ["policy4_baseline", "s50_baseline", "right_tie_low",
             "right_tie_high", "adaptive_right4_w2048_s60_fixed"]
    cases = read_cases("s50_baseline")
    candidate_cases = {name: read_cases(name) for name in names}
    header = ["case", "weight", "s50_kpi", "s50_H_m", "winner_kpi", "winner_H_m",
              "winner_weighted_delta_vs_s50", "policy4_kpi", "policy4_H_m",
              "w1024_all_right_kpi", "w1024_all_right_H_m",
              "w1024_tie_high_kpi", "w1024_tie_high_H_m"]
    output = REPORTS / "final_per_case_comparison.csv"
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=header)
        writer.writeheader()
        for case in sorted(cases, key=int):
            ref = cases[case]
            win = candidate_cases["adaptive_right4_w2048_s60_fixed"][case]
            p4 = candidate_cases["policy4_baseline"][case]
            right1024 = candidate_cases["right_tie_low"][case]
            tiehigh = candidate_cases["right_tie_high"][case]
            weight = float(ref["weight"])
            writer.writerow({
                "case": case, "weight": ref["weight"],
                "s50_kpi": ref["kpi"], "s50_H_m": ref["trench_length_m"],
                "winner_kpi": win["kpi"], "winner_H_m": win["trench_length_m"],
                "winner_weighted_delta_vs_s50": weight * (float(win["kpi"]) - float(ref["kpi"])),
                "policy4_kpi": p4["kpi"], "policy4_H_m": p4["trench_length_m"],
                "w1024_all_right_kpi": right1024["kpi"], "w1024_all_right_H_m": right1024["trench_length_m"],
                "w1024_tie_high_kpi": tiehigh["kpi"], "w1024_tie_high_H_m": tiehigh["trench_length_m"],
            })
    return output


def main():
    p4 = read_summary("policy4_baseline")
    s50 = read_summary("s50_baseline")
    winner = read_summary("adaptive_right4_w2048_s60_fixed")
    variants = []
    for summary_path in REPORTS.glob("*/summary.json"):
        data = json.loads(summary_path.read_text())
        if data.get("is_official_open_test_set"):
            variants.append({"name": summary_path.parent.name,
                             "weighted_score": data["weighted_score_sum"],
                             "delta_vs_s50": data["weighted_score_sum"] - s50["weighted_score_sum"],
                             "valid": data["ok_count"], "case_count": data["case_count"]})
    variants.sort(key=lambda x: x["weighted_score"], reverse=True)
    with (REPORTS / "all_official_candidates.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["name", "weighted_score", "delta_vs_s50", "valid", "case_count"])
        writer.writeheader()
        writer.writerows(variants)

    input_hashes = {p.name: sha(p) for p in sorted((ROOT / "data/pipes/open").glob("*.in"), key=lambda p: int(p.stem))}
    interactor = ROOT / "tools/interactor"
    wrapper = BASE / "src/adaptive_right4_w2048_s60.cpp"
    shared_source = BASE / "src/gap_search.cpp"
    binary = BASE / "binaries/adaptive_right4_w2048_s60_fixed"
    compile_command = ("g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic "
                       "results/pipes/improvement/max_open_gap_search/src/adaptive_right4_w2048_s60.cpp "
                       "-o results/pipes/improvement/max_open_gap_search/binaries/adaptive_right4_w2048_s60_fixed")
    manifest = {
        "candidate": "adaptive_right4_w2048_s60",
        "description": "recent-unfit gap scoring, history window 2048, scale 60; place requests of length <=4 at the chosen gap's right edge, longer requests at the left edge",
        "source_wrapper": str(wrapper), "source_wrapper_sha256": sha(wrapper),
        "shared_source": str(shared_source), "shared_source_sha256": sha(shared_source),
        "binary": str(binary), "binary_sha256": sha(binary), "compile_command": compile_command,
        "interactor": str(interactor), "interactor_sha256": sha(interactor),
        "test_directory": str(ROOT / "data/pipes/open"), "test_sha256": input_hashes,
        "official_harness_report": str(REPORTS / "adaptive_right4_w2048_s60_fixed/summary.json"),
        "open_weighted_score": winner["weighted_score_sum"], "weight_sum": winner["weight_sum"],
        "valid_cases": winner["ok_count"], "case_count": winner["case_count"],
        "delta_vs_s50": winner["weighted_score_sum"] - s50["weighted_score_sum"],
        "s50_score": s50["weighted_score_sum"], "policy4_score": p4["weighted_score_sum"],
        "delta_vs_policy4": winner["weighted_score_sum"] - p4["weighted_score_sum"],
        "max_solver_cpu_s": max(r.get("solver_cpu_total_s") or 0 for r in winner["records"]),
        "max_solver_rss_mib": max(r.get("solver_peak_rss_mb") or 0 for r in winner["records"]),
        "all_open_candidate_scores": variants,
        "heuristic_screen_manifest": str(REPORTS / "adaptive_grid/manifest.json"),
        "heuristic_screen_results": str(REPORTS / "adaptive_grid/grid.csv"),
        "canonical_modified": False,
    }
    (REPORTS / "final_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_case_comparison()
    s50delta = manifest["delta_vs_s50"]
    report = f"""# Поиск максимального weighted open score: Pipes

## Лидер и независимая проверка

Фиксированный кандидат `adaptive_right4_w2048_s60` набрал **{winner['weighted_score_sum']:.12f}/{winner['weight_sum']:.1f}** на всех 15 официальных открытых кейсах. Проверка проведена локальным `tools/pipes_harness.py` с официальным интерактором; 15/15 кейсов valid. Это на **{s50delta:+.12f}** больше S50 ({s50['weighted_score_sum']:.12f}) и на **{manifest['delta_vs_policy4']:+.12f}** больше policy4 ({p4['weighted_score_sum']:.12f}).

Правило: история последних 2048 положительных размещений; для каждой подходящей дыры используется recent-unfit scoring `slack * history_size + 60 * count(recent_length > slack)`. Трубы длиной 1–4 м размещаются у правого края выбранной дыры, более длинные — у левого. Правило не использует номер теста, будущие операции или идентификаторы кейсов.

На максимальном официальном кейсе измерено {manifest['max_solver_cpu_s']:.6f} с CPU и {manifest['max_solver_rss_mib']:.3f} МиБ RSS. Сборка с `-Werror` прошла.

## Крупнейшие per-case изменения относительно S50

Покейсовые KPI, длины траншей, и взвешенная дельта приведены в [final_per_case_comparison.csv](final_per_case_comparison.csv). Основные вклады:

- кейс 3: **+0.375000** score (траншея 40→20 м);
- кейс 10: **+0.133478** (18 460→15 380 м);
- кейс 13: **+0.046900** (3320→3280 м);
- кейс 7: **−0.045373** (1680→1760 м);
- кейс 12: **−0.007684**;
- кейс 15: **−0.009138**.

В сумме положительные изменения перевешивают регрессии; это open-tuned score, а не claim о закрытых тестах.

## Отбор

Стандартные best-fit/first-fit/worst-fit/age-first варианты не превзошли S50. Полная таблица проверенных official-interactor кандидатов доступна в [all_official_candidates.csv](all_official_candidates.csv); покейсовые дельты ранних стратегий к S50 — в [per_case_scoreboard_vs_s50.csv](per_case_scoreboard_vs_s50.csv). Затем параметры recent-history были проверены на официальных тестах. Для полного right-endpoint при W=1024/S50 результат 29.049090580812; правый конец для всех длин работал лучше левого, а high-address tie-break этот результат немного ухудшил (29.040212877829).

После обнаружения смешанного endpoint проведён быстрый 27-точечный screen: W ∈ {{1024, 2048, 4096}}, scale ∈ {{50, 60, 70}}, right-max ∈ {{3, 4, 5}}. Лучший симуляционный результат — W2048/S60/right-max4; он дополнительно и независимо прошёл официальный harness. Полные данные screen и hash симулятора находятся в [adaptive_grid](adaptive_grid/).

## Воспроизведение

```sh
{compile_command}
python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_gap_search/binaries/adaptive_right4_w2048_s60_fixed --name adaptive_right4_w2048_s60_fixed --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/max_open_gap_search/reports/adaptive_right4_w2048_s60_fixed
```

Исходник с фиксированными параметрами: [adaptive_right4_w2048_s60.cpp](../src/adaptive_right4_w2048_s60.cpp). Общая реализация правил и режимов: [gap_search.cpp](../src/gap_search.cpp). Хеши всех сборочных артефактов, тестов и интерактора сохранены в [final_manifest.json](final_manifest.json). `src/pipes.cpp` и канонические файлы не менялись.
"""
    (REPORTS / "REPORT.md").write_text(report, encoding="utf-8")
    print(f"wrote {REPORTS / 'REPORT.md'}")


if __name__ == "__main__":
    main()
