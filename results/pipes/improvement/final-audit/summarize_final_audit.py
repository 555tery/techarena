#!/usr/bin/env python3
"""Cross-check the integrated source audit against frozen official reports."""

from __future__ import annotations

import hashlib
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[3]
STRATEGIES = PROJECT / "results/pipes/improvement/strategies"
REPORTS = STRATEGIES / "reports/integrated-final"
ROBUST_REPORTS = STRATEGIES / "reports/robustness-frozen"
SOURCE = PROJECT / "src/pipes.cpp"
UBSAN_BINARY = ROOT / "integrated_ubsan"


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-14


verification = read(REPORTS / "verification.json")
integrated = read(REPORTS / "integrated_s50/summary.json")
frozen_open = read(REPORTS / "frozen_s50/summary.json")
frozen_robust = read(ROBUST_REPORTS / "recent_unfit_s50/summary.json")
open_oracle = read(ROOT / "official-open-plus-generated.json")
robust_oracle = read(ROOT / "robustness-10-oracle.json")

source_sha = sha(SOURCE)
assert source_sha == verification["build"]["source_sha256"]
release_binary = PROJECT / verification["build"]["binary"]
assert sha(release_binary) == verification["build"]["binary_sha256"]
assert verification["build"]["integrated_and_frozen_s50_open_results_identical"] is True
assert sha(STRATEGIES / "binaries/recent_unfit_s50") == verification["build"]["frozen_s50_binary_sha256"]

open_cases = {str(row["case"]): row for row in integrated["records"]}
frozen_open_cases = {str(row["case"]): row for row in frozen_open["records"]}
oracle_open_cases = {Path(row["name"]).stem: row for row in open_oracle["cases"]
                     if row["name"].endswith(".in")}
expected_open_hashes = verification["official_open_run"]["tests_sha256"]
open_comparison_rows = []
assert integrated["case_count"] == integrated["ok_count"] == 15
assert open_oracle["pass"] == 26 and open_oracle["fail"] == 0
assert set(open_cases) == set(frozen_open_cases) == set(oracle_open_cases) == {str(i) for i in range(1, 16)}
for case in sorted(open_cases, key=int):
    actual = open_cases[case]
    frozen = frozen_open_cases[case]
    oracle = oracle_open_cases[case]
    input_path = PROJECT / "data/pipes/open" / f"{case}.in"
    assert sha(input_path) == expected_open_hashes[f"{case}.in"]
    assert actual["test_sha256"] == frozen["test_sha256"] == expected_open_hashes[f"{case}.in"]
    assert actual["trench_length_m"] == frozen["trench_length_m"] == oracle["dug_m"]
    assert actual["occupied_length_m"] == frozen["occupied_length_m"] == oracle["occupied_m"]
    assert close(actual["kpi"], frozen["kpi"]) and close(actual["kpi"], oracle["kpi"])
    assert close(actual["weighted_score"], frozen["weighted_score"])
    open_comparison_rows.append({
        "case": case,
        "test_sha256": expected_open_hashes[f"{case}.in"],
        "weight": actual["weight"],
        "integrated_official_kpi": actual["kpi"],
        "oracle_kpi": oracle["kpi"],
        "kpi_delta": oracle["kpi"] - actual["kpi"],
        "integrated_official_H_m": actual["trench_length_m"],
        "oracle_H_m": oracle["dug_m"],
        "H_delta_m": oracle["dug_m"] - actual["trench_length_m"],
        "integrated_occupied_m": actual["occupied_length_m"],
        "oracle_occupied_m": oracle["occupied_m"],
    })
assert len(open_oracle["cases"]) == 26
assert all(row["verdict"] == "OK" for row in open_oracle["cases"])
large = next(row for row in open_oracle["cases"] if row["name"] == "max-200k-fragment-seed-f1a1")
assert large["commands"] == large["responses"] == 200_000

robust_manifest = read(STRATEGIES / "robustness_manifest.json")
assert len(robust_manifest["streams"]) == 10
assert robust_oracle["case_count"] == robust_oracle["pass"] == 10 and robust_oracle["fail"] == 0
assert robust_oracle["command_count"] == robust_oracle["response_count"] == 460_000
robust_frozen_cases = {row["case"]: row for row in frozen_robust["records"]}
robust_oracle_cases = {row["name"]: row for row in robust_oracle["cases"]}
robust_comparison_rows = []
assert set(robust_frozen_cases) == set(robust_oracle_cases) == {row["name"] for row in robust_manifest["streams"]}
for item in robust_manifest["streams"]:
    name = item["name"]
    recorded = robust_frozen_cases[name]
    oracle = robust_oracle_cases[name]
    input_path = STRATEGIES / "robustness_inputs" / f"{name}.in"
    assert sha(input_path) == item["sha256"] == oracle["input_sha256"] == recorded["test_sha256"]
    assert oracle["commands"] == oracle["responses"] == item["operation_count"]
    assert oracle["dug_m"] == recorded["trench_length_m"]
    assert oracle["occupied_m"] == recorded["occupied_length_m"]
    assert close(oracle["kpi"], recorded["kpi"])
    robust_comparison_rows.append({
        "case": name,
        "input_sha256": item["sha256"],
        "operations": item["operation_count"],
        "frozen_official_kpi": recorded["kpi"],
        "oracle_kpi": oracle["kpi"],
        "kpi_delta": oracle["kpi"] - recorded["kpi"],
        "frozen_official_H_m": recorded["trench_length_m"],
        "oracle_H_m": oracle["dug_m"],
        "H_delta_m": oracle["dug_m"] - recorded["trench_length_m"],
        "frozen_occupied_m": recorded["occupied_length_m"],
        "oracle_occupied_m": oracle["occupied_m"],
    })


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


write_csv(ROOT / "per_case_open_comparison.csv", open_comparison_rows)
write_csv(ROOT / "per_case_robustness_comparison.csv", robust_comparison_rows)

source_text = SOURCE.read_text()
for required in [
    "constexpr std::size_t kHistoryWindow = 128;",
    "constexpr std::int64_t kUnfitPenaltyScale = 50;",
    "std::int64_t score = slack * historySize;",
    "score += kUnfitPenaltyScale * misses;",
    "for (int request = static_cast<int>(slack) + 1; request <= 40; ++request)",
    "std::cout << digs << ' ' << start << '\\n' << std::flush;",
    "std::cout << pipe.start << '\\n' << std::flush;",
    "if (command == 0) return 0;",
]:
    assert required in source_text, required
assert not re.search(r"\b(?:argc|argv)\b|data/pipes/open|test[_ -]?id|case[_ -]?(?:1[0-5]|[1-9])\b|0x[fF]1[aA]1", source_text)

summary = {
    "source": str(SOURCE),
    "source_sha256": source_sha,
    "frozen_strategy_source_sha256": sha(STRATEGIES / "adaptive_allocator.cpp"),
    "frozen_strategy_binary_sha256": sha(STRATEGIES / "binaries/recent_unfit_s50"),
    "integrated_release_binary": str(release_binary),
    "integrated_release_binary_sha256": sha(release_binary),
    "ubsan_binary": str(UBSAN_BINARY),
    "ubsan_binary_sha256": sha(UBSAN_BINARY),
    "open_official_cases": 15,
    "open_official_commands": sum(row["commands"] for row in oracle_open_cases.values()),
    "open_official_responses": sum(row["responses"] for row in oracle_open_cases.values()),
    "open_weighted_score": integrated["weighted_score_sum"],
    "open_weight_sum": integrated["weight_sum"],
    "open_kpi_and_trench_match_integrated_report_exactly": True,
    "integrated_and_frozen_open_results_identical_recorded": True,
    "open_test_hashes_verified": True,
    "open_per_case_csv": "per_case_open_comparison.csv",
    "frozen_robustness_cases": 10,
    "frozen_robustness_commands": robust_oracle["command_count"],
    "frozen_robustness_responses": robust_oracle["response_count"],
    "frozen_robustness_matches_saved_s50_kpi_and_trench": True,
    "robustness_per_case_csv": "per_case_robustness_comparison.csv",
    "additional_oracle_cases": len(open_oracle["cases"]) - 15,
    "additional_oracle_commands_including_open_15_and_seed_f1a1": sum(row.get("commands", 0) for row in open_oracle["cases"]),
    "seed_f1a1_commands": large["commands"],
    "seed_f1a1_responses": large["responses"],
    "seed_f1a1_trench_m": large["dug_m"],
    "seed_f1a1_occupied_m": large["occupied_m"],
    "seed_f1a1_kpi": large["kpi"],
    "oracle_verdicts": {"official_plus_generated": "26/26 OK", "frozen_robustness": "10/10 OK"},
    "all_streams_case_count": len(open_oracle["cases"]) + len(robust_oracle["cases"]),
    "all_streams_command_count": sum(row.get("commands", 0) for row in open_oracle["cases"]) + robust_oracle["command_count"],
    "all_streams_response_count": sum(row.get("responses", 0) for row in open_oracle["cases"]) + robust_oracle["response_count"],
    "protocol": "one command then one flushed newline response; independent treap rejects overlaps and checks active PID/start mapping; sentinel 0 termination and no trailing stdout checked",
    "test_id_or_sequence_recognition_found": False,
    "official_release_resource_maxima": {
        "cpu_s": max(row["solver_cpu_total_s"] for row in integrated["records"]),
        "rss_mib": max(row["solver_peak_rss_mb"] for row in integrated["records"]),
        "origin": "pre-existing integrated-final official harness report for binary with matching source and binary hashes",
    },
    "ubsan_resource_measurements": "not collected; the independent streaming oracle is not a resource-measurement harness",
    "limitations": [
        "The random 200000-command case is deterministically regenerated by review/audit_streams.py with seed 0xF1A1; it is not a committed input file.",
        "The frozen robustness suite is synthetic and diagnostic, not an estimate of hidden official-test performance.",
        "Static source comparison and observed KPI/trench equality do not constitute a formal proof over every possible legal command stream.",
    ],
}
(ROOT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")

lines = [
    "# Финальный независимый аудит `src/pipes.cpp`",
    "",
    "## Исходник и соответствие frozen candidate",
    "",
    f"- `src/pipes.cpp` SHA-256: `{source_sha}`; совпал с хешем, записанным в integrated-final verification.",
    f"- Frozen source `adaptive_allocator.cpp`: SHA-256 `{summary['frozen_strategy_source_sha256']}`.",
    f"- Frozen `recent_unfit_s50` binary: SHA-256 `{summary['frozen_strategy_binary_sha256']}`.",
    f"- Интегрированный optimized binary из integrated-final отчёта: SHA-256 `{summary['integrated_release_binary_sha256']}`; совпадает с сохранённой сборкой из текущего source SHA.",
    "- В исходнике параметры `window=128`, `scale=50`; penalty формула учитывает `previous_pipe_length > slack`, tie-break — размер затем низкий адрес; хвост участвует как обычная свободная дыра. Семантика соответствует frozen `PIPES_STRATEGY=2`, `PIPES_HISTORY_WINDOW=128`, `PIPES_PENALTY_SCALE=50`.",
    "- Поиск по исходнику не обнаружил `argv`, путей тестов, test ID, номера кейса, seed или ветвления по позиции команды. Аллокатор обрабатывает только текущую команду и историю последних 128 вставок.",
    "",
    "## Сборка и онлайн-проверка",
    "",
    "- UBSan + строгие предупреждения: сборка прошла с `-Werror`, предупреждений и runtime sanitizer ошибок не было.",
    "- Independent oracle работает интерактивно: передаёт одну команду, ждёт ровно одну newline-terminated flushed строку; проверяет формат/границы координат, отсутствие пересечений, удаление активного PID по ожидаемому адресу, окончание по sentinel `0`, отсутствие stdout после sentinel и нормальный exit.",
    f"- Официальные открытые тесты: {summary['open_official_cases']}/15; `{summary['open_official_commands']}` команд и `{summary['open_official_responses']}` ответов.",
    f"- Frozen robustness suite: {summary['frozen_robustness_cases']}/10; `{summary['frozen_robustness_commands']}` команд и столько же ответов.",
    f"- Всего по двум oracle-прогонам: {summary['all_streams_case_count']} streams, `{summary['all_streams_command_count']}` команд и `{summary['all_streams_response_count']}` ответов.",
    f"- Дополнительные независимые oracle streams: {summary['additional_oracle_cases'] - 1}; вместе с opens и отдельным max stream всего `{summary['additional_oracle_commands_including_open_15_and_seed_f1a1']}` интерактивных команд.",
    f"- Максимальный поток seed `0xF1A1`: {summary['seed_f1a1_commands']} команд, {summary['seed_f1a1_responses']} ответов, OK; траншея `{summary['seed_f1a1_trench_m']} м`, занято `{summary['seed_f1a1_occupied_m']} м`, KPI `{summary['seed_f1a1_kpi']:.12f}`.",
    "",
    "## Сверка с сохранёнными official результатами",
    "",
    f"Independent oracle совпал по KPI, занятым метрам и H (длине траншеи) с integrated-final отчётом на всех 15 opens. Взвешенный score: `{integrated['weighted_score_sum']:.12f}/{integrated['weight_sum']}`. Также integrated-final записывает идентичность результатов integrated source и frozen s50 binary; наши измерения согласуются с этими per-case отчетами.",
    "Все 10 robustness KPI/H совпали с уже сохранённым official-harness отчётом frozen `recent_unfit_s50`; каждый вход подтверждён manifest SHA-256.",
    "Построчные сверки KPI/H/занятых метров: [`per_case_open_comparison.csv`](./per_case_open_comparison.csv) и [`per_case_robustness_comparison.csv`](./per_case_robustness_comparison.csv).",
    "",
    "## Ресурсы и ограничения вывода",
    "",
    f"Максимумы CPU `{summary['official_release_resource_maxima']['cpu_s']:.6f} s` и RSS `{summary['official_release_resource_maxima']['rss_mib']:.4f} MiB` взяты из предыдущего official-harness integrated-final отчёта для бинарника, чьи source/binary hashes совпадают. Для UBSan oracle отдельное измерение CPU/RSS не собиралось.",
    "Оценка ограничена перечисленными тестами и синтетическими потоками; она не доказывает корректность для любых возможных входов и не оценивает скрытое распределение. Максимальный поток F1A1 воспроизводится скриптом по seed, а не хранится как отдельный `.in`.",
]
(ROOT / "AUDIT.md").write_text("\n".join(lines) + "\n")
print(json.dumps(summary, indent=2, ensure_ascii=False))
