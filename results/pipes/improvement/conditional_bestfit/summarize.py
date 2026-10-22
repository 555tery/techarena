import csv
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[4]
here = Path(__file__).resolve().parent
reports = here / "reports/screen"
cases = (5, 9, 15)
variants = ("seed", "fragment_tight", "small_demand", "large_demand")

records = {}
for variant in variants:
    records[variant] = {}
    for case in cases:
        summary = json.loads((reports / f"{variant}-case{case}/summary.json").read_text())
        records[variant][case] = summary["records"][0]

seed = records["seed"]
per_case_path = here / "per-case.csv"
with per_case_path.open("w", newline="", encoding="utf-8") as stream:
    fields = [
        "variant", "case", "weight", "input_sha256", "status", "weighted_score",
        "delta_weighted_score_vs_seed", "trench_m", "delta_trench_m_vs_seed",
        "cpu_user_s", "cpu_system_s", "cpu_total_s", "peak_rss_mib",
        "judge_output_sha256", "interactor_stderr_sha256",
    ]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for variant in variants:
        for case in cases:
            rec = records[variant][case]
            base = seed[case]
            judge_output = Path(rec["judge_output_file"])
            interactor_stderr = Path(rec["interactor_stderr_file"])
            writer.writerow({
                "variant": variant,
                "case": case,
                "weight": rec["weight"],
                "input_sha256": rec["test_sha256"],
                "status": rec["status"],
                "weighted_score": f"{rec['weighted_score']:.15f}",
                "delta_weighted_score_vs_seed": f"{rec['weighted_score']-base['weighted_score']:+.15f}",
                "trench_m": rec["trench_length_m"],
                "delta_trench_m_vs_seed": rec["trench_length_m"]-base["trench_length_m"],
                "cpu_user_s": rec["solver_cpu_user_s"],
                "cpu_system_s": rec["solver_cpu_system_s"],
                "cpu_total_s": rec["solver_cpu_total_s"],
                "peak_rss_mib": rec["solver_peak_rss_mb"],
                "judge_output_sha256": hashlib.sha256(judge_output.read_bytes()).hexdigest(),
                "interactor_stderr_sha256": hashlib.sha256(interactor_stderr.read_bytes()).hexdigest(),
            })

weights = {case: seed[case]["weight"] for case in cases}
summary_rows = []
for variant in variants:
    total_score = sum(records[variant][case]["weighted_score"] for case in cases)
    base_total = sum(seed[case]["weighted_score"] for case in cases)
    cpu = [records[variant][case]["solver_cpu_total_s"] for case in cases]
    rss = [records[variant][case]["solver_peak_rss_mb"] for case in cases]
    row = {
        "variant": variant,
        "screen_weighted_score": f"{total_score:.15f}",
        "delta_vs_seed": f"{total_score-base_total:+.15f}",
        "weight_sum": sum(weights.values()),
        "ok_cases": sum(records[variant][case]["status"] == "ok" for case in cases),
        "cpu_sum_s": f"{sum(cpu):.9f}",
        "cpu_max_s": f"{max(cpu):.9f}",
        "rss_max_mib": f"{max(rss):.6f}",
    }
    for case in cases:
        row[f"case{case}_score"] = f"{records[variant][case]['weighted_score']:.15f}"
        row[f"case{case}_delta"] = f"{records[variant][case]['weighted_score']-seed[case]['weighted_score']:+.15f}"
        row[f"case{case}_trench_m"] = records[variant][case]["trench_length_m"]
    summary_rows.append(row)

summary_path = here / "summary.csv"
with summary_path.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(summary_rows[0]))
    writer.writeheader()
    writer.writerows(summary_rows)

source_map = {
    "input_candidate_source": root / "results/pipes/improvement/case9_policy/alternating_delete_parity_edges.cpp",
    "seed_copy": here / "src/seed.cpp",
    "conditional_source": here / "src/conditional_bestfit.cpp",
    "harness": root / "tools/pipes_harness.py",
    "interactor": root / "tools/interactor",
}
for case in cases:
    source_map[f"open_case_{case}"] = root / f"data/pipes/open/{case}.in"
binary_map = {name: here / f"bin/{name}" for name in variants}
hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in source_map.items()}
binary_hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in binary_map.items()}

build_flags = "-O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic"
commands = {
    "seed": f"clang++ {build_flags} results/pipes/improvement/conditional_bestfit/src/seed.cpp -o results/pipes/improvement/conditional_bestfit/bin/seed",
    "fragment_tight": f"clang++ {build_flags} -DCONDITIONAL_POLICY=1 results/pipes/improvement/conditional_bestfit/src/conditional_bestfit.cpp -o results/pipes/improvement/conditional_bestfit/bin/fragment_tight",
    "small_demand": f"clang++ {build_flags} -DCONDITIONAL_POLICY=2 results/pipes/improvement/conditional_bestfit/src/conditional_bestfit.cpp -o results/pipes/improvement/conditional_bestfit/bin/small_demand",
    "large_demand": f"clang++ {build_flags} -DCONDITIONAL_POLICY=3 results/pipes/improvement/conditional_bestfit/src/conditional_bestfit.cpp -o results/pipes/improvement/conditional_bestfit/bin/large_demand",
}
with (here / "build_manifest.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream)
    writer.writerow(["variant", "compile_command", "source_sha256", "binary_sha256", "compiler"])
    for variant in variants:
        source_name = "seed_copy" if variant == "seed" else "conditional_source"
        writer.writerow([variant, commands[variant], hashes[source_name], binary_hashes[variant], "Apple clang++ 17.0.0"])

manifest = {
    "scope": "official open cases 5, 9, 15 only; no other official cases or holdout data run",
    "target_source_sha256": hashes["input_candidate_source"],
    "seed_copy_sha256": hashes["seed_copy"],
    "conditional_source_sha256": hashes["conditional_source"],
    "harness_sha256": hashes["harness"],
    "interactor_sha256": hashes["interactor"],
    "test_sha256": {str(case): hashes[f"open_case_{case}"] for case in cases},
    "binary_sha256": binary_hashes,
    "compile_commands": commands,
    "harness_commands": (here / "screen_commands.txt").read_text().splitlines(),
    "variants": {
        "seed": "exact copy of requested source, compiled as C++20; reference",
        "fragment_tight": "when gap count >=256 and aggregate free volume >=8 times largest gap, set recent-large-demand penalty scale from 60 to 0",
        "small_demand": "same fragmentation trigger plus current request <=8 and >=75% of last up-to-2048 observed placements are sizes 1..8; then penalty scale 0",
        "large_demand": "same fragmentation trigger plus >=25% of last up-to-2048 observed placements are sizes 16..40; then penalty scale 120",
    },
    "results": summary_rows,
    "decision": "no candidate had positive summed weighted-score delta over screened cases 5, 9, 15; full open15 and holdout not run",
}
(here / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

best = max(summary_rows[1:], key=lambda row: float(row["delta_vs_seed"]))
report = [
    "# Условный Best-Fit: экран случаев 5, 9 и 15",
    "",
    "## Решение",
    "",
    "Положительного кандидата нет. Проверены только официальные открытые случаи 5, 9 и 15; полный open-15 и holdout не запускались, потому что ни один вариант не дал положительной суммарной дельты на первом экране.",
    "",
    f"Лучший из трех вариантов на экране — `{best['variant']}` с суммарной дельтой `{best['delta_vs_seed']}` weighted points при весе случаев 5+9+15 = 12.0. Это всё равно отрицательный результат.",
    "",
    "## Политики и результаты",
    "",
    "Все варианты сохраняют исходный выбор стороны укладки. Меняется только множитель недавнего спроса в live Best-Fit score. Фрагментация задана как одновременно `gap_count >= 256` и `total_free_volume >= 8 * largest_gap`; это состояние текущего аллокатора. Дополнительный size-distribution триггер использует только последние уже наблюдавшиеся размещения.",
    "",
    "| Вариант | Случай 5 Δscore / Δтраншея | Случай 9 Δscore / Δтраншея | Случай 15 Δscore / Δтраншея | Сумма Δscore | CPU сумма / максимум (с) | RSS max (MiB) |",
    "|---|---:|---:|---:|---:|---:|---:|",
]
for row in summary_rows[1:]:
    per = []
    for case in cases:
        rec = records[row["variant"]][case]
        base = seed[case]
        per.append(f"{rec['weighted_score']-base['weighted_score']:+.12f} / {rec['trench_length_m']-base['trench_length_m']:+d} m")
    report.append(
        f"| `{row['variant']}` | {per[0]} | {per[1]} | {per[2]} | {row['delta_vs_seed']} | {row['cpu_sum_s']} / {row['cpu_max_s']} | {row['rss_max_mib']} |"
    )
report += [
    "",
    "Все 12 прогонов получили `ok`. Случай 15 наиболее весомый: pure-tight-fit потерял 2,840 м и 0.061335041019 weighted score; large-demand branch потерял 640 м и 0.013891160159. Small-demand branch не изменил 5 и 15, но потерял 160 м на случае 9. Поэтому рост fragmentation сам по себе не подтверждает полезность перехода к tight Best-Fit.",
    "",
    "Для каждого случая записаны исходный и итоговый score, trench length, CPU user/system/total, peak RSS, входной SHA-256, judge-output SHA-256 и interactor-stderr SHA-256 в [per-case.csv](per-case.csv). Сводка лежит в [summary.csv](summary.csv). Команды harness — [screen_commands.txt](screen_commands.txt), build-команды и бинарные хеши — [build_manifest.csv](build_manifest.csv), полный набор хешей и формулировки триггеров — [manifest.json](manifest.json).",
    "",
    "Исходный кандидат и baseline-копия имеют SHA-256 `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`. Экспериментальные файлы находятся только в этом подкаталоге; `src/pipes.cpp` и финальный артефакт не изменялись. Сборка: Apple clang++ 17.0.0, C++20, `-Wall -Wextra -Wconversion -Wshadow -Werror -pedantic`. Лимиты каждого harness run: 5 s CPU, 256 MiB RSS, 120 s wall.",
    "",
    "## Следующие гипотезы",
    "",
    "1. Не усиливать demand penalty во всей фрагментированной фазе: проверенный глобальный переход к tight Best-Fit ухудшает случай 15. Следующий кандидат должен выбирать только внутри лучшей группы gap sizes, оставляя размерную cost function неизменной.",
    "2. Проверить условный tie-break среди равных gap lengths: при доступном expandable tail выбрать интерьерную дыру только при близкой adaptive cost, чтобы удержать tail для fallback-expansion. Это проверит адрес/соседство и wilderness отдельно от penalty.",
]
(here / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
