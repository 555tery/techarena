import csv
import hashlib
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[4]
here = Path(__file__).resolve().parent
variants = ("seed", "horizon32")
datasets = ("open-15", "holdout-v2", "development")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_summary(dataset, variant):
    return json.loads((here / "reports" / dataset / variant / "summary.json").read_text())

def diag_counts(record):
    text = record.get("candidate_stderr", "")
    event = re.search(r"voluntary_dig_events=(\d+)", text)
    meters = re.search(r"voluntary_dig_m=(\d+)", text)
    return (int(event.group(1)) if event else 0, int(meters.group(1)) if meters else 0)

all_summaries = {ds: {v: read_summary(ds, v) for v in variants} for ds in datasets}
all_records = {
    ds: {v: {r["case"]: r for r in all_summaries[ds][v]["records"]} for v in variants}
    for ds in datasets
}

per_case_fields = [
    "dataset", "variant", "case", "weight", "input_sha256", "status",
    "weighted_score", "delta_weighted_score_vs_seed", "trench_m", "delta_trench_m_vs_seed",
    "occupied_length_m", "kpi", "solver_cpu_user_s", "solver_cpu_system_s",
    "solver_cpu_total_s", "solver_peak_rss_mib", "wall_orchestration_s",
    "voluntary_dig_events", "voluntary_dig_m", "judge_output_sha256",
    "interactor_stderr_sha256", "solver_stderr_sha256",
]
per_case_path = here / "per-case.csv"
with per_case_path.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=per_case_fields)
    writer.writeheader()
    for ds in datasets:
        for variant in variants:
            for case, rec in all_records[ds][variant].items():
                base = all_records[ds]["seed"][case]
                events, meters = diag_counts(rec)
                writer.writerow({
                    "dataset": ds,
                    "variant": variant,
                    "case": case,
                    "weight": rec["weight"],
                    "input_sha256": rec["test_sha256"],
                    "status": rec["status"],
                    "weighted_score": f"{rec['weighted_score']:.15f}",
                    "delta_weighted_score_vs_seed": f"{rec['weighted_score']-base['weighted_score']:+.15f}",
                    "trench_m": rec["trench_length_m"],
                    "delta_trench_m_vs_seed": rec["trench_length_m"]-base["trench_length_m"],
                    "occupied_length_m": rec["occupied_length_m"],
                    "kpi": f"{rec['kpi']:.15f}",
                    "solver_cpu_user_s": rec["solver_cpu_user_s"],
                    "solver_cpu_system_s": rec["solver_cpu_system_s"],
                    "solver_cpu_total_s": rec["solver_cpu_total_s"],
                    "solver_peak_rss_mib": rec["solver_peak_rss_mb"],
                    "wall_orchestration_s": rec["wall_orchestration_s"],
                    "voluntary_dig_events": events,
                    "voluntary_dig_m": meters,
                    "judge_output_sha256": sha(rec["judge_output_file"]),
                    "interactor_stderr_sha256": sha(rec["interactor_stderr_file"]),
                    "solver_stderr_sha256": sha(rec["candidate_stderr_file"]),
                })

summary_rows = []
for ds in datasets:
    for variant in variants:
        summary = all_summaries[ds][variant]
        base = all_summaries[ds]["seed"]
        records = summary["records"]
        cpu = [r["solver_cpu_total_s"] for r in records]
        rss = [r["solver_peak_rss_mb"] for r in records]
        counts = [diag_counts(r) for r in records]
        summary_rows.append({
            "dataset": ds,
            "variant": variant,
            "weighted_score_sum": f"{summary['weighted_score_sum']:.15f}",
            "delta_vs_seed": f"{summary['weighted_score_sum']-base['weighted_score_sum']:+.15f}",
            "weight_sum": summary["weight_sum"],
            "ok_count": summary["ok_count"],
            "case_count": summary["case_count"],
            "solver_cpu_sum_s": f"{sum(cpu):.9f}",
            "solver_cpu_max_s": f"{max(cpu):.9f}",
            "solver_peak_rss_max_mib": f"{max(rss):.6f}",
            "voluntary_dig_events": sum(x[0] for x in counts),
            "voluntary_dig_m": sum(x[1] for x in counts),
        })
with (here / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(summary_rows[0]))
    writer.writeheader()
    writer.writerows(summary_rows)

screen_variants = ("seed", "horizon32", "horizon64")
screen = {
    v: {
        case: json.loads((here / "reports/screen" / f"{v}-case{case}" / "summary.json").read_text())["records"][0]
        for case in (5, 9, 15)
    }
    for v in screen_variants
}
screen_fields = ["variant", "case", "weight", "weighted_score", "delta_vs_seed", "trench_m", "delta_trench_m", "cpu_total_s", "peak_rss_mib", "stderr", "judge_output_sha256"]
with (here / "screen-per-case.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=screen_fields)
    writer.writeheader()
    for variant in screen_variants:
        for case in (5, 9, 15):
            rec = screen[variant][case]
            base = screen["seed"][case]
            writer.writerow({
                "variant": variant,
                "case": case,
                "weight": rec["weight"],
                "weighted_score": f"{rec['weighted_score']:.15f}",
                "delta_vs_seed": f"{rec['weighted_score']-base['weighted_score']:+.15f}",
                "trench_m": rec["trench_length_m"],
                "delta_trench_m": rec["trench_length_m"]-base["trench_length_m"],
                "cpu_total_s": rec["solver_cpu_total_s"],
                "peak_rss_mib": rec["solver_peak_rss_mb"],
                "stderr": rec["candidate_stderr"],
                "judge_output_sha256": sha(rec["judge_output_file"]),
            })

files = {
    "target_source": root / "results/pipes/improvement/case9_policy/alternating_delete_parity_edges.cpp",
    "seed_copy": here / "src/seed.cpp",
    "voluntary_dig_source": here / "src/voluntary_dig.cpp",
    "harness": root / "tools/pipes_harness.py",
    "interactor": root / "tools/interactor",
}
for case in (5, 9, 15):
    files[f"open_{case}"] = root / f"data/pipes/open/{case}.in"
for path in sorted((root / "data/pipes/open").glob("*.in"), key=lambda p: int(p.stem)):
    files[f"open_{path.stem}"] = path
for ds, directory in (("holdout_v2", root / "data/pipes/synthetic/final-holdout-v2"),
                      ("development", root / "data/pipes/synthetic/development")):
    for path in sorted(directory.glob("*.in")):
        files[f"{ds}_{path.stem}"] = path
hashes = {name: sha(path) for name, path in files.items()}
binaries = {name: here / f"bin/{name}" for name in ("seed", "horizon32", "horizon64")}
binary_hashes = {name: sha(path) for name, path in binaries.items()}

flags = "-O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic"
commands = {
    "seed": f"clang++ {flags} results/pipes/improvement/voluntary_dig/src/seed.cpp -o results/pipes/improvement/voluntary_dig/bin/seed",
    "horizon32": f"clang++ {flags} -DOPTION_HORIZON=32 -DMC_ROLLOUT_DIAGNOSTICS results/pipes/improvement/voluntary_dig/src/voluntary_dig.cpp -o results/pipes/improvement/voluntary_dig/bin/horizon32",
    "horizon64": f"clang++ {flags} -DOPTION_HORIZON=64 -DMC_ROLLOUT_DIAGNOSTICS results/pipes/improvement/voluntary_dig/src/voluntary_dig.cpp -o results/pipes/improvement/voluntary_dig/bin/horizon64",
}
with (here / "build_manifest.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.writer(stream)
    writer.writerow(["variant", "compile_command", "source_sha256", "binary_sha256", "compiler"])
    for variant in binaries:
        writer.writerow([variant, commands[variant], hashes["seed_copy" if variant == "seed" else "voluntary_dig_source"], binary_hashes[variant], "Apple clang++ 17.0.0"])

manifest = {
    "scope": "first screen official open cases 5, 9, 15; extended comparison only for horizon32 and source seed on open15, final-holdout-v2, and previously used development synthetic",
    "target_source_sha256": hashes["target_source"],
    "seed_copy_sha256": hashes["seed_copy"],
    "voluntary_dig_source_sha256": hashes["voluntary_dig_source"],
    "harness_sha256": hashes["harness"],
    "interactor_sha256": hashes["interactor"],
    "input_sha256": {k: v for k, v in hashes.items() if k.startswith(("open_", "holdout_v2_", "development_"))},
    "binary_sha256": binary_hashes,
    "compile_commands": commands,
    "screen_harness_commands": (here / "screen_commands.txt").read_text().splitlines(),
    "extended_harness_commands": (here / "extended_commands.txt").read_text().splitlines(),
    "option_model": {
        "current_state": "selected best-fit gap and current expandable tail, plus exact counts of existing gaps fitting each pipe length 1..40",
        "past_state": "recentFrequency from the existing rolling window of up to 2048 past placements; minimum 64 observations",
        "incremental_demand_band": "future pipe sizes that fit the selected gap but not the remainder after placing the current pipe: (gap_length-current_length, min(gap_length,40)]",
        "scarcity": "each historical request frequency is divided by the current number of gaps that can fit it",
        "option_value": "probability of at least one discounted target-size request within the compile-time horizon, times the target-size-weighted avoided 20m-section cost",
        "decision": "voluntarily fall back to tail placement only when expected avoided dig metres are strictly greater than the immediate number of added 20m-section metres; no voluntary action when tail already fits without digging",
        "horizons_tested": [32, 64],
        "future_or_test_specific_data": "none; no case id, operation index, command index, or future command is read",
    },
    "summary": summary_rows,
    "screen_summary": {
        v: sum(screen[v][c]["weighted_score"]-screen["seed"][c]["weighted_score"] for c in (5, 9, 15))
        for v in screen_variants
    },
    "decision": "reject horizon32: its selected-case screen was slightly positive and case15 improved 40m, but full open15 and both secondary synthetic sets regressed; horizon64 was rejected at screening",
}
(here / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

open_seed = all_summaries["open-15"]["seed"]["weighted_score_sum"]
open_candidate = all_summaries["open-15"]["horizon32"]["weighted_score_sum"]
holdout_delta = all_summaries["holdout-v2"]["horizon32"]["weighted_score_sum"] - all_summaries["holdout-v2"]["seed"]["weighted_score_sum"]
development_delta = all_summaries["development"]["horizon32"]["weighted_score_sum"] - all_summaries["development"]["seed"]["weighted_score_sum"]
candidate_open_records = all_records["open-15"]["horizon32"]
base_open_records = all_records["open-15"]["seed"]
changed = [(case, base_open_records[case]["trench_length_m"], rec["trench_length_m"], rec["weighted_score"]-base_open_records[case]["weighted_score"]) for case, rec in candidate_open_records.items() if rec["trench_length_m"] != base_open_records[case]["trench_length_m"]]
candidate_open_cpu = [rec["solver_cpu_total_s"] for rec in all_summaries["open-15"]["horizon32"]["records"]]
candidate_open_rss = [rec["solver_peak_rss_mb"] for rec in all_summaries["open-15"]["horizon32"]["records"]]
trigger_events = sum(diag_counts(rec)[0] for rec in all_summaries["open-15"]["horizon32"]["records"])
trigger_meters = sum(diag_counts(rec)[1] for rec in all_summaries["open-15"]["horizon32"]["records"])
screen_delta32 = manifest["screen_summary"]["horizon32"]
screen_delta64 = manifest["screen_summary"]["horizon64"]

report = [
    "# Voluntary trench expansion as option value",
    "",
    "## Decision",
    "",
    "Candidate rejected. The 32-placement horizon passed the requested first-screen gate by only `+0.000354231338` on open cases 5/9/15 and saved 40 m on case 15. The full 15-case open run then lost `0.199786788394` weighted points. Previously used final-holdout-v2 and development synthetic also regressed. No candidate is recommended for final.",
    "",
    "## Policy",
    "",
    "For the gap selected by the existing adaptive Best-Fit (after its current rollout decision), compute the future request band that the full gap can fit but the remainder cannot: `(gap_length-current_length, min(gap_length, 40)]`. Use only the existing rolling histogram of up to 2,048 observed placements, requiring at least 64 observations. Discount demand for each size by the number of current gaps that already fit that size. Estimate the chance that one such demand arrives within the next 32 or 64 placements, multiply by its expected avoided 20 m section cost, then compare that expected value to the immediate cost of extending the current tail by `ceil(deficit/20)*20` metres. Voluntary tail placement occurs only when estimated benefit is strictly greater than immediate cost. It does not act when the tail can already fit without digging.",
    "",
    "The policy uses current gap state and past demand only. No test ID, operation count, command index, or future command enters the decision. Both variants preserve the original edge selection rule.",
    "",
    "## Results",
    "",
    "### First screen: official open cases 5, 9, 15",
    "",
    f"Horizon 32: **{screen_delta32:+.12f}** weighted points summed over weight 12.0; case 15 trench improved by 40 m. Horizon 64: **{screen_delta64:+.12f}**; case 15 trench worsened by 320 m. This gate selected horizon 32 for expanded validation.",
    "",
    "### Expanded comparison",
    "",
    "| Dataset | Seed score / weight | Horizon 32 score / weight | Delta | Horizon 32 status |",
    "|---|---:|---:|---:|---:|",
    f"| Official open 15 | {open_seed:.12f} / 32.1 | {open_candidate:.12f} / 32.1 | **{open_candidate-open_seed:+.12f}** | 15/15 OK |",
    f"| final-holdout-v2, previously used | {all_summaries['holdout-v2']['seed']['weighted_score_sum']:.12f} / {all_summaries['holdout-v2']['seed']['weight_sum']:.1f} | {all_summaries['holdout-v2']['horizon32']['weighted_score_sum']:.12f} / {all_summaries['holdout-v2']['horizon32']['weight_sum']:.1f} | **{holdout_delta:+.12f}** | 12/12 OK |",
    f"| development synthetic, previously used | {all_summaries['development']['seed']['weighted_score_sum']:.12f} / 4.0 | {all_summaries['development']['horizon32']['weighted_score_sum']:.12f} / 4.0 | **{development_delta:+.12f}** | 4/4 OK |",
    "",
    "On open case 15 the trench fell from 438,920 m to 438,880 m (−40 m), giving `+0.000869542694` weighted score. The full-open loss instead came mainly from case 7 (+240 m, −0.122037598545 score) and case 13 (+60 m, −0.069928435811), with smaller regressions on 5, 11, and 14. Changed open trenches are listed in `per-case.csv`.",
    "",
    f"Horizon 32 accepted {trigger_events:,} voluntary placements in open-15 and paid for {trigger_meters:,} m of extra trench. It used {sum(candidate_open_cpu):.6f} s CPU total / {max(candidate_open_cpu):.6f} s maximum per case and {max(candidate_open_rss):.6f} MiB peak RSS; all measured resource use stayed below 5 s and 256 MiB.",
    "",
    "Holdout-v2 and development are secondary checks from datasets already used in earlier experiments; they are not independent hidden-set evidence. The holdout-v2 regression was −0.327843319436 and development regressed by −1.159368016534. No other synthetic set was run.",
    "",
    "## Reproduction and hashes",
    "",
    "Exact build commands and binary hashes are in [build_manifest.csv](build_manifest.csv); exact harness commands are in [screen_commands.txt](screen_commands.txt) and [extended_commands.txt](extended_commands.txt). The full per-case table includes scores, trench lengths, CPU/RSS, input hashes, and judge/stdio transcript hashes in [per-case.csv](per-case.csv); first-screen rows are in [screen-per-case.csv](screen-per-case.csv). Aggregate results are in [summary.csv](summary.csv), and all source/input/output hashes plus the option-value definition are in [manifest.json](manifest.json).",
    "",
    f"The target source SHA-256 is `{hashes['target_source']}`; the isolated experiment source SHA-256 is `{hashes['voluntary_dig_source']}`. Files are confined to `results/pipes/improvement/voluntary_dig/`; canonical/final sources were not edited. Apple clang++ 17.0.0 compiled with C++20 and `-Wall -Wextra -Wconversion -Wshadow -Werror -pedantic`. Every harness run used 5 s CPU, 256 MiB RSS, and 120 s wall limits.",
    "",
    "## Next useful hypothesis",
    "",
    "The option model produces many paid dig actions for almost no improvement on case 15 and damages cases 7/13 and the synthetic workloads. If revisited, the most useful change is to value a preserved gap only when the historical request size is uniquely unsupported by all other gaps and appears in a stable recent size regime; do not increase the horizon or blanket-trigger on a raw gap count.",
]
(here / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
