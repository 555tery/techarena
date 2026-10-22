import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
RUNS = {
    "baseline_open": ROOT / "full/baseline_open",
    "candidate_open_run1": ROOT / "full/exact_open_run1",
    "candidate_open_run2": ROOT / "full/exact_open_run2",
    "baseline_holdout_v2": ROOT / "full/baseline_holdout_v2",
    "candidate_holdout_v2": ROOT / "full/exact_holdout_v2",
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_run(path):
    summary = json.loads((path / "summary.json").read_text())
    cases = {}
    for row in csv.DictReader((path / "cases.csv").open(newline="")):
        key = str(row["case"])
        out_path = Path(row["judge_output_file"])
        if not out_path.is_absolute():
            out_path = REPO / out_path
        cases[key] = {
            "status": row["status"],
            "test_sha256": row["test_sha256"],
            "weight": float(row["official_weight"]),
            "occupied_m": int(row["occupied_length_m"]),
            "trench_m": int(row["trench_length_m"]),
            "kpi": float(row["kpi"]),
            "weighted_score": float(row["weighted_score"]),
            "cpu_user_s": float(row["solver_cpu_user_s"]),
            "cpu_system_s": float(row["solver_cpu_system_s"]),
            "cpu_total_s": float(row["solver_cpu_total_s"]),
            "rss_mb": float(row["solver_peak_rss_mb"]),
            "judge_output_sha256": sha(out_path),
            "judge_output_file": str(out_path.relative_to(REPO)),
            "candidate_stderr": row["candidate_stderr"],
            "solver_cpu_limit_exceeded": row["solver_cpu_limit_exceeded"] == "True",
            "solver_memory_limit_exceeded": row["solver_memory_limit_exceeded"] == "True",
        }
    return summary, cases

loaded = {name: read_run(path) for name, path in RUNS.items()}

open_baseline = loaded["baseline_open"][1]
open_candidate = loaded["candidate_open_run1"][1]
open_repeat = loaded["candidate_open_run2"][1]
hold_baseline = loaded["baseline_holdout_v2"][1]
hold_candidate = loaded["candidate_holdout_v2"][1]

open_rows = []
for case in sorted(open_baseline, key=int):
    b, c, r = open_baseline[case], open_candidate[case], open_repeat[case]
    open_rows.append({
        "suite": "open",
        "case": case,
        "weight": b["weight"],
        "test_sha256": b["test_sha256"],
        "baseline_occupied_m": b["occupied_m"],
        "baseline_trench_m": b["trench_m"],
        "baseline_kpi": b["kpi"],
        "baseline_weighted_score": b["weighted_score"],
        "candidate_occupied_m": c["occupied_m"],
        "candidate_trench_m": c["trench_m"],
        "candidate_kpi": c["kpi"],
        "candidate_weighted_score": c["weighted_score"],
        "delta_trench_m": c["trench_m"] - b["trench_m"],
        "delta_weighted_score": c["weighted_score"] - b["weighted_score"],
        "repeat_trench_m": r["trench_m"],
        "repeat_weighted_score": r["weighted_score"],
        "candidate_output_sha256": c["judge_output_sha256"],
        "repeat_output_sha256": r["judge_output_sha256"],
        "baseline_output_sha256": b["judge_output_sha256"],
        "candidate_repeat_transcript_identical": c["judge_output_sha256"] == r["judge_output_sha256"],
        "candidate_baseline_transcript_identical": c["judge_output_sha256"] == b["judge_output_sha256"],
        "baseline_cpu_s": b["cpu_total_s"],
        "candidate_cpu_s": c["cpu_total_s"],
        "repeat_cpu_s": r["cpu_total_s"],
        "baseline_rss_mb": b["rss_mb"],
        "candidate_rss_mb": c["rss_mb"],
        "repeat_rss_mb": r["rss_mb"],
    })

hold_rows = []
for case in sorted(hold_baseline, key=lambda s: int(s.split("-")[-1])):
    b, c = hold_baseline[case], hold_candidate[case]
    hold_rows.append({
        "suite": "holdout-v2",
        "case": case,
        "weight": b["weight"],
        "test_sha256": b["test_sha256"],
        "baseline_occupied_m": b["occupied_m"],
        "baseline_trench_m": b["trench_m"],
        "baseline_kpi": b["kpi"],
        "baseline_weighted_score": b["weighted_score"],
        "candidate_occupied_m": c["occupied_m"],
        "candidate_trench_m": c["trench_m"],
        "candidate_kpi": c["kpi"],
        "candidate_weighted_score": c["weighted_score"],
        "delta_trench_m": c["trench_m"] - b["trench_m"],
        "delta_weighted_score": c["weighted_score"] - b["weighted_score"],
        "candidate_output_sha256": c["judge_output_sha256"],
        "baseline_output_sha256": b["judge_output_sha256"],
        "candidate_baseline_transcript_identical": c["judge_output_sha256"] == b["judge_output_sha256"],
        "baseline_cpu_s": b["cpu_total_s"],
        "candidate_cpu_s": c["cpu_total_s"],
        "baseline_rss_mb": b["rss_mb"],
        "candidate_rss_mb": c["rss_mb"],
    })

fieldnames = list(open_rows[0])
with (ROOT / "per_case_open.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader(); w.writerows(open_rows)
fieldnames = list(hold_rows[0])
with (ROOT / "per_case_holdout_v2.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader(); w.writerows(hold_rows)

file_hashes = {}
for relative in [
    "source/baseline.cpp", "source/pseudorandom_exact.cpp", "source/pseudorandom_near1.cpp", "source/pseudorandom_near2.cpp",
    "bin/baseline", "bin/pseudorandom_exact", "bin/pseudorandom_near1", "bin/pseudorandom_near2", "bin/interactor",
    "generate_candidates.py", "summarize.py",
]:
    path = ROOT / relative
    if path.exists(): file_hashes[relative] = sha(path)

runs = {}
for name, path in RUNS.items():
    summary, cases = loaded[name]
    runs[name] = {
        "directory": str(path.relative_to(REPO)),
        "summary_sha256": sha(path / "summary.json"),
        "cases_csv_sha256": sha(path / "cases.csv"),
        "case_count": summary["case_count"],
        "ok_count": summary["ok_count"],
        "weighted_score_sum": summary["weighted_score_sum"],
        "weight_sum": summary["weight_sum"],
        "max_solver_cpu_s": max(x["cpu_total_s"] for x in cases.values()),
        "max_solver_rss_mb": max(x["rss_mb"] for x in cases.values()),
        "all_transcript_output_sha256": {case: row["judge_output_sha256"] for case, row in cases.items()},
    }

screen_runs = {}
for name in ["baseline", "pseudorandom_exact", "pseudorandom_near1", "pseudorandom_near2"]:
    path = ROOT / "screen" / name
    summary, cases = read_run(path)
    screen_runs[name] = {
        "directory": str(path.relative_to(REPO)),
        "summary_sha256": sha(path / "summary.json"),
        "cases_csv_sha256": sha(path / "cases.csv"),
        "case_count": summary["case_count"],
        "ok_count": summary["ok_count"],
        "weighted_score_sum": summary["weighted_score_sum"],
        "weight_sum": summary["weight_sum"],
        "max_solver_cpu_s": max(x["cpu_total_s"] for x in cases.values()),
        "max_solver_rss_mb": max(x["rss_mb"] for x in cases.values()),
        "cases": cases,
    }

open_repeat_identical = all(row["candidate_repeat_transcript_identical"] for row in open_rows)
open_input_hashes_match = all(
    open_baseline[case]["test_sha256"] == open_candidate[case]["test_sha256"] == open_repeat[case]["test_sha256"]
    for case in open_baseline
)
holdout_input_hashes_match = all(
    hold_baseline[case]["test_sha256"] == hold_candidate[case]["test_sha256"]
    for case in hold_baseline
)
all_full_runs_ok = all(
    row["status"] == "ok" and not row["solver_cpu_limit_exceeded"] and not row["solver_memory_limit_exceeded"]
    for _, cases in loaded.values() for row in cases.values()
)
manifest = {
    "experiment": "causal deterministic pseudorandom hash selection among exact minimum-score fitting gaps",
    "source_baseline_sha256": file_hashes["source/baseline.cpp"],
    "source_candidate_sha256": file_hashes["source/pseudorandom_exact.cpp"],
    "binary_hashes": {name: file_hashes[f"bin/{name}"] for name in ["baseline", "pseudorandom_exact", "pseudorandom_near1", "pseudorandom_near2"]},
    "interactor_sha256": file_hashes["bin/interactor"],
    "harness_sha256": sha(REPO / "tools/pipes_harness.py"),
    "source_hashes": file_hashes,
    "build": {
        "compiler": "Apple clang version 17.0.0 (clang-1700.0.13.5), arm64-apple-darwin25.6.0",
        "flags": "-O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic",
        "diagnostics_enabled_for_full_runs": False,
    },
    "runs": runs,
    "screen_runs": screen_runs,
    "open_candidate_repeat_deterministic": open_repeat_identical,
    "open_input_hashes_match_all_runs": open_input_hashes_match,
    "holdout_input_hashes_match_baseline_and_candidate": holdout_input_hashes_match,
    "all_full_runs_protocol_ok_and_within_limits": all_full_runs_ok,
    "open_candidate_vs_baseline_transcripts_identical_count": sum(r["candidate_baseline_transcript_identical"] for r in open_rows),
    "open_candidate_repeat_transcripts_identical_count": sum(r["candidate_repeat_transcript_identical"] for r in open_rows),
    "holdout_candidate_vs_baseline_transcripts_identical_count": sum(r["candidate_baseline_transcript_identical"] for r in hold_rows),
    "open_case_deltas": open_rows,
    "holdout_case_deltas": hold_rows,
}
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print(json.dumps({
    "scores": {name: runs[name]["weighted_score_sum"] for name in runs},
    "open_deterministic": open_repeat_identical,
    "open_transcripts_same_vs_baseline": manifest["open_candidate_vs_baseline_transcripts_identical_count"],
    "holdout_transcripts_same_vs_baseline": manifest["holdout_candidate_vs_baseline_transcripts_identical_count"],
    "max_resources": {name: [runs[name]["max_solver_cpu_s"], runs[name]["max_solver_rss_mb"]] for name in runs},
}, indent=2))
for row in open_rows:
    print("OPEN", row["case"], f"dscore={row['delta_weighted_score']:+.12f}", f"dtrench={row['delta_trench_m']:+d}", f"same_repeat={row['candidate_repeat_transcript_identical']}")
for row in hold_rows:
    print("HOLD", row["case"], f"dscore={row['delta_weighted_score']:+.12f}", f"dtrench={row['delta_trench_m']:+d}")

def fmt(x, n=12):
    return f"{x:.{n}f}"

report = [
    "# TECH ARENA Pipes: causal pseudorandom tie-break",
    "",
    "## Итог",
    "",
    "Кандидат `pseudorandom_exact` **отклонён**. Положительный screen на случаях 5/9/15 (+0.006563736670) не перенёсся: Open15 снизился с **29.789717928594** до **29.701931820514** (−0.087786108080), holdout-v2 — с **5.135264324280** до **5.134608723382** (−0.000655600898). Повтор Open15 дал тот же score и побайтно те же 15 judge transcripts. Все полные прогоны прошли 15/15 и 12/12 случаев без protocol errors; CPU/RSS в лимитах. Кандидат не копировался в final и не загружался на платформу.",
    "",
    "## Что проверялось",
    "",
    "Текущая политика считает исходную fit-cost для каждого подходящего размера свободного промежутка. В `exact` кандидатах выбирается псевдослучайным детерминированным hash-ключом один из адресов, у которых cost **точно равен глобальному минимуму**. Для каждого уникального размера промежутка рассматриваются до четырёх самых низких и четырёх самых высоких адресов. Hash включает rolling hash уже полученных команд, текущий PID, длину запроса, адрес, размер дыры, длину траншеи и сторону укладки. Состояние hash обновляется после обработки команды. Нет обращения к будущим командам, test ID, внешнему RNG или файлам.",
    "",
    "В качестве контроля были также собраны варианты с полосой до `historySize × 1 м` и `historySize × 2 м` над минимумом cost. Они не прошли screen и дальше не проверялись. До эксперимента просмотренные отчёты подтвердили близкие, но иные прошлые подходы: детерминированные equal-cost и lifetime-aware ties, геометрические tie-break и Monte Carlo RNG только для выборки исторических сценариев; отдельного hash-based tie-break размещения не было.",
    "",
    "## Общие результаты",
    "",
    "| Сборка/набор | Открытые 15 | Δ к baseline | Holdout-v2 | Δ к baseline | Max CPU / RSS Open15 | Max CPU / RSS holdout |",
    "|---|---:|---:|---:|---:|---:|---:|",
    f"| Frozen baseline | {fmt(runs['baseline_open']['weighted_score_sum'])}/32.1 | — | {fmt(runs['baseline_holdout_v2']['weighted_score_sum'])}/12 | — | {fmt(runs['baseline_open']['max_solver_cpu_s'],6)} с / {fmt(runs['baseline_open']['max_solver_rss_mb'],6)} MiB | {fmt(runs['baseline_holdout_v2']['max_solver_cpu_s'],6)} с / {fmt(runs['baseline_holdout_v2']['max_solver_rss_mb'],6)} MiB |",
    f"| `pseudorandom_exact` | {fmt(runs['candidate_open_run1']['weighted_score_sum'])}/32.1 | {fmt(runs['candidate_open_run1']['weighted_score_sum'] - runs['baseline_open']['weighted_score_sum'],12)} | {fmt(runs['candidate_holdout_v2']['weighted_score_sum'])}/12 | {fmt(runs['candidate_holdout_v2']['weighted_score_sum'] - runs['baseline_holdout_v2']['weighted_score_sum'],12)} | {fmt(runs['candidate_open_run1']['max_solver_cpu_s'],6)} с / {fmt(runs['candidate_open_run1']['max_solver_rss_mb'],6)} MiB | {fmt(runs['candidate_holdout_v2']['max_solver_cpu_s'],6)} с / {fmt(runs['candidate_holdout_v2']['max_solver_rss_mb'],6)} MiB |",
    "",
    "В обоих наборах все solver CPU ниже 5 секунд и RSS ниже 256 MiB. Open15 baseline собран из побайтной копии текущего final; оба исходника строго собраны Apple Clang 17 для arm64 с одинаковыми флагами.",
    "",
    "## Open15: все случаи",
    "",
    "| Case | Вес | Траншея baseline → candidate, м (Δ) | Weighted score baseline → candidate | Δ score | Повтор: transcript идентичен |",
    "|---:|---:|---:|---:|---:|:---:|",
]
for r in open_rows:
    report.append(
        f"| {r['case']} | {fmt(r['weight'],1)} | {r['baseline_trench_m']:,} → {r['candidate_trench_m']:,} ({r['delta_trench_m']:+,}) | {fmt(r['baseline_weighted_score'])} → {fmt(r['candidate_weighted_score'])} | {fmt(r['delta_weighted_score'],12)} | {'да' if r['candidate_repeat_transcript_identical'] else 'нет'} |".replace(",", " ")
    )
report += [
    "",
    "Open15 transcript SHA-256 совпал между двумя кандидатскими прогонами на **15/15** случаях. Совпадение transcript candidate с baseline — 4/15; в остальных случаях изменившееся размещение закономерно изменило ответы. Test SHA совпадает между baseline и candidate по каждому кейсу.",
    "",
    "## Holdout-v2: все случаи",
    "",
    "| Case | Вес | Траншея baseline → candidate, м (Δ) | Weighted score baseline → candidate | Δ score | Transcript идентичен baseline |",
    "|---|---:|---:|---:|---:|:---:|",
]
for r in hold_rows:
    report.append(
        f"| {r['case']} | {fmt(r['weight'],1)} | {r['baseline_trench_m']:,} → {r['candidate_trench_m']:,} ({r['delta_trench_m']:+,}) | {fmt(r['baseline_weighted_score'])} → {fmt(r['candidate_weighted_score'])} | {fmt(r['delta_weighted_score'],12)} | {'да' if r['candidate_baseline_transcript_identical'] else 'нет'} |".replace(",", " ")
    )
report += [
    "",
    "Holdout transcripts совпали с baseline на 1/12 случаях; test SHA совпадает для всех 12. Суммарная оценка кандидата ниже baseline: case-07 увеличил траншею на 500 м и дал −0.001061932875 weighted score; улучшение case-02 (+0.000634057971) потерю не компенсировало.",
    "",
    "## Screen и причины отклонения",
    "",
    "| Кандидат | Screen baseline | Screen candidate | Δ | Case 5 / 9 / 15 траншея, м | Max CPU / RSS |",
    "|---|---:|---:|---:|---|---:|",
]
screen_base = screen_runs["baseline"]
for name, label in [("pseudorandom_exact", "exact score"), ("pseudorandom_near1", "near +1 м"), ("pseudorandom_near2", "near +2 м")]:
    run = screen_runs[name]
    trenches = [run["cases"][c]["trench_m"] for c in ("5", "9", "15")]
    report.append(
        f"| {label} | {fmt(screen_base['weighted_score_sum'])}/12 | {fmt(run['weighted_score_sum'])}/12 | {fmt(run['weighted_score_sum'] - screen_base['weighted_score_sum'],12)} | {trenches[0]:,} / {trenches[1]:,} / {trenches[2]:,} | {fmt(run['max_solver_cpu_s'],6)} с / {fmt(run['max_solver_rss_mb'],6)} MiB |".replace(",", " ")
    )
report += [
    "",
    "Exact screen выбрал адрес hash-минимума среди точных minimizers; это увеличило case 5 и case 15, но ухудшило case 9. В полном Open15 дополнительные потери проявились на кейсах 8, 11–14; выигрыш screen не является переносимым. Допуск до +1/+2 м по score ухудшил даже screen. Поэтому никакой вариант не прошёл критерий promotion.",
    "",
    "## Ресурсы и протокол",
    "",
    "| Полный прогон | Cases ok | Score | Max solver CPU | Max solver RSS | Превышения лимитов |",
    "|---|---:|---:|---:|---:|:---:|",
]
for name in RUNS:
    run = runs[name]
    report.append(
        f"| `{name}` | {run['ok_count']}/{run['case_count']} | {fmt(run['weighted_score_sum'])}/{fmt(run['weight_sum'],1)} | {fmt(run['max_solver_cpu_s'],6)} с | {fmt(run['max_solver_rss_mb'],6)} MiB | нет |"
    )
report += [
    "",
    "Harness использовал официальный исходный interactor (`tools/interactor`) и лимиты 5 секунд CPU / 256 MiB. В raw outputs сохранены stdout judge transcript, отчёты interactor, stderr, per-case CPU/RSS и JSON/CSV каждого запуска.",
    "",
    "## Воспроизводимость и хеши",
    "",
    f"- Frozen baseline source SHA-256: `{file_hashes['source/baseline.cpp']}`; совпадает с `results/pipes/final/solution.cpp`.",
    f"- Exact candidate source SHA-256: `{file_hashes['source/pseudorandom_exact.cpp']}`.",
    f"- Baseline binary SHA-256: `{file_hashes['bin/baseline']}`.",
    f"- Exact candidate binary SHA-256: `{file_hashes['bin/pseudorandom_exact']}`.",
    f"- `near1` source/binary SHA-256: `{file_hashes['source/pseudorandom_near1.cpp']}` / `{file_hashes['bin/pseudorandom_near1']}`.",
    f"- `near2` source/binary SHA-256: `{file_hashes['source/pseudorandom_near2.cpp']}` / `{file_hashes['bin/pseudorandom_near2']}`.",
    f"- Interactor SHA-256: `{file_hashes['bin/interactor']}`; harness SHA-256: `{manifest['harness_sha256']}`.",
    f"- `src/pipes.cpp` SHA-256 (перед/после): `{sha(REPO / 'src/pipes.cpp')}`; final SHA-256 (перед/после): `{sha(REPO / 'results/pipes/final/solution.cpp')}`.",
    "- Строгая сборка: `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic <source> -o <binary>`.",
    "- Машиночитаемая сводка и все transcript hashes: [manifest.json](manifest.json). Покейсовые таблицы: [per_case_open.csv](per_case_open.csv), [per_case_holdout_v2.csv](per_case_holdout_v2.csv).",
    "- Полные harness outputs: [baseline Open15](full/baseline_open/), [candidate Open15 run 1](full/exact_open_run1/), [candidate Open15 run 2](full/exact_open_run2/), [baseline holdout-v2](full/baseline_holdout_v2/), [candidate holdout-v2](full/exact_holdout_v2/).",
    "",
]
(ROOT / "REPORT.md").write_text("\n".join(report))
print(f"Report: {ROOT / 'REPORT.md'}")
