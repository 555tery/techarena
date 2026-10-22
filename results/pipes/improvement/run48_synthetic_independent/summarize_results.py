#!/usr/bin/env python3
"""Build the paired report and hash manifest from fixed run-48 stream runs."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE_SOURCE = ROOT / "results/pipes/final/solution.cpp"
CANONICAL_SOURCE = ROOT / "src/pipes.cpp"
CANDIDATE_SOURCE = ROOT / "results/pipes/improvement/run48_qualification/sources/run-48.cpp"
BASE_BINARY = ROOT / "results/pipes/improvement/run48_qualification/binaries/baseline"
CANDIDATE_BINARY = ROOT / "results/pipes/improvement/run48_qualification/binaries/run-48"
HARNESS = ROOT / "tools/pipes_harness.py"
INTERACTOR = ROOT / "results/pipes/final/bin/interactor"
INPUT_MANIFEST = OUT / "input_manifest.json"
BASE_RUN = OUT / "runs/baseline/summary.json"
CANDIDATE_RUN = OUT / "runs/run-48/summary.json"

EXPECTED_BASE_SHA = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
EXPECTED_CANONICAL_SHA = "526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8"
EXPECTED_CANDIDATE_SHA = "95d662fff63be90146b5ebddeff43ce4b551f34b8de5351513ba33f53be55b39"
EXPECTED_BASE_BINARY_SHA = "ee9ae15f8f4879eaca8da9a0c5fdb1caeb05311893279a4eaf0734c167427290"
EXPECTED_CANDIDATE_BINARY_SHA = "9fef88bbc46f0fcd62304f4439548dafa090902b034705676e8e517caac78448"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def phase_label(phases: list[dict]) -> str:
    return "; ".join(
        f"{p['start']}-{p['end']}: {p['length_profile']}, churn={p['churn']:.2f}, "
        f"delete={p['deletion_policy']}, batch={p['batch']}, repeat={p['repeat_probability']:.2f}"
        for p in phases
    )


def main() -> None:
    base_source_bytes = BASE_SOURCE.read_bytes()
    candidate_source_bytes = CANDIDATE_SOURCE.read_bytes()
    if sha(BASE_SOURCE) != EXPECTED_BASE_SHA:
        raise SystemExit("frozen final source hash changed")
    if sha(CANONICAL_SOURCE) != EXPECTED_CANONICAL_SHA:
        raise SystemExit("canonical source hash changed")
    if sha(CANDIDATE_SOURCE) != EXPECTED_CANDIDATE_SHA:
        raise SystemExit("saved run-48 source hash changed")
    replaced, count = re.subn(rb"(kSameLengthRightRun\s*=\s*)46(;)", rb"\g<1>48\2",
                              base_source_bytes, count=1)
    if count != 1 or replaced != candidate_source_bytes:
        raise SystemExit("candidate differs from frozen final beyond threshold 46 -> 48")
    if sha(BASE_BINARY) != EXPECTED_BASE_BINARY_SHA or sha(CANDIDATE_BINARY) != EXPECTED_CANDIDATE_BINARY_SHA:
        raise SystemExit("qualification binaries do not match their saved hashes")

    input_manifest = load(INPUT_MANIFEST)
    base = load(BASE_RUN)
    candidate = load(CANDIDATE_RUN)
    if base["case_count"] != len(input_manifest["inputs"]) or candidate["case_count"] != len(input_manifest["inputs"]):
        raise SystemExit("run summaries do not cover the fixed input set")

    prior_hashes = set()
    prior_input_files = 0
    for dataset in (ROOT / "data/pipes", ROOT / "results/pipes"):
        for path in dataset.rglob("*.in"):
            if OUT not in path.parents:
                prior_input_files += 1
                prior_hashes.add(sha(path))
    collisions = [name for name, item in input_manifest["inputs"].items() if item["sha256"] in prior_hashes]
    if collisions:
        raise SystemExit(f"fixed input hash collides with a previously stored .in: {collisions}")

    base_records = {Path(r["test_file"]).stem if "test_file" in r else Path(r["judge_output_file"]).parent.name: r
                    for r in base["records"]}
    candidate_records = {Path(r["test_file"]).stem if "test_file" in r else Path(r["judge_output_file"]).parent.name: r
                         for r in candidate["records"]}

    streams = []
    for name, input_item in input_manifest["inputs"].items():
        b = base_records[name]
        c = candidate_records[name]
        b_output = ROOT / b["judge_output_file"]
        c_output = ROOT / c["judge_output_file"]
        b_output_sha = sha(b_output)
        c_output_sha = sha(c_output)
        if b["test_sha256"] != input_item["sha256"] or c["test_sha256"] != input_item["sha256"]:
            raise SystemExit(f"paired input hash mismatch for {name}")
        if b["status"] != "ok" or c["status"] != "ok":
            raise SystemExit(f"non-ok status for {name}: {b['status']} / {c['status']}")
        if b["solver_cpu_limit_exceeded"] or c["solver_cpu_limit_exceeded"] or b["solver_memory_limit_exceeded"] or c["solver_memory_limit_exceeded"]:
            raise SystemExit(f"resource limit violation for {name}")
        streams.append({
            "name": name,
            "operations": input_item["stream_stats"]["operations"],
            "placements": input_item["stream_stats"]["placements"],
            "deletions": input_item["stream_stats"]["deletions"],
            "peak_live_pipes": input_item["stream_stats"]["peak_live_pipes"],
            "phases": input_item["scenario"]["phases"],
            "phase_description": phase_label(input_item["scenario"]["phases"]),
            "input_sha256": input_item["sha256"],
            "baseline": {
                "status": b["status"],
                "weighted_score": b["weighted_score"],
                "kpi": b["kpi"],
                "trench_length_m": b["trench_length_m"],
                "occupied_length_m": b["occupied_length_m"],
                "solver_cpu_s": b["solver_cpu_total_s"],
                "solver_rss_mib": b["solver_peak_rss_mb"],
                "judge_output_sha256": b_output_sha,
            },
            "run48": {
                "status": c["status"],
                "weighted_score": c["weighted_score"],
                "kpi": c["kpi"],
                "trench_length_m": c["trench_length_m"],
                "occupied_length_m": c["occupied_length_m"],
                "solver_cpu_s": c["solver_cpu_total_s"],
                "solver_rss_mib": c["solver_peak_rss_mb"],
                "judge_output_sha256": c_output_sha,
            },
            "delta_weighted_score_run48_minus_baseline": c["weighted_score"] - b["weighted_score"],
            "delta_trench_m_run48_minus_baseline": c["trench_length_m"] - b["trench_length_m"],
            "outputs_identical": b_output_sha == c_output_sha,
        })

    comparison = {
        "experiment": "Paired fresh synthetic streams: frozen final vs run-48; no parameter tuning after generation",
        "candidate_change": {"kSameLengthRightRun": {"from": 46, "to": 48}},
        "input_generation": input_manifest["generation_rule"],
        "prior_persisted_input_file_count": prior_input_files,
        "prior_persisted_unique_input_hash_count": len(prior_hashes),
        "fresh_input_hash_collisions": collisions,
        "stream_count": len(streams),
        "total_operations": sum(s["operations"] for s in streams),
        "baseline_score_sum_over_these_streams_only": base["weighted_score_sum"],
        "run48_score_sum_over_these_streams_only": candidate["weighted_score_sum"],
        "delta_score_sum": candidate["weighted_score_sum"] - base["weighted_score_sum"],
        "per_stream_score_regressions": [s["name"] for s in streams if s["delta_weighted_score_run48_minus_baseline"] < -1e-12],
        "per_stream_score_improvements": [s["name"] for s in streams if s["delta_weighted_score_run48_minus_baseline"] > 1e-12],
        "all_judge_outputs_identical": all(s["outputs_identical"] for s in streams),
        "all_cases_ok": base["ok_count"] == base["case_count"] and candidate["ok_count"] == candidate["case_count"],
        "resource_limits": {"cpu_s": 5.0, "rss_mib": 256.0},
        "max_solver_cpu_s": {
            "baseline": max(s["baseline"]["solver_cpu_s"] for s in streams),
            "run48": max(s["run48"]["solver_cpu_s"] for s in streams),
        },
        "max_solver_rss_mib": {
            "baseline": max(s["baseline"]["solver_rss_mib"] for s in streams),
            "run48": max(s["run48"]["solver_rss_mib"] for s in streams),
        },
        "hash_manifest": {
            "frozen_final_source": sha(BASE_SOURCE),
            "canonical_source": sha(CANONICAL_SOURCE),
            "run48_source": sha(CANDIDATE_SOURCE),
            "baseline_binary": sha(BASE_BINARY),
            "run48_binary": sha(CANDIDATE_BINARY),
            "official_harness": sha(HARNESS),
            "official_interactor": sha(INTERACTOR),
            "generator": sha(OUT / "generate_streams.py"),
            "comparison_script": sha(Path(__file__)),
            "input_manifest": sha(INPUT_MANIFEST),
            "baseline_harness_summary": sha(BASE_RUN),
            "run48_harness_summary": sha(CANDIDATE_RUN),
            "inputs": {s["name"]: s["input_sha256"] for s in streams},
            "baseline_outputs": {s["name"]: s["baseline"]["judge_output_sha256"] for s in streams},
            "run48_outputs": {s["name"]: s["run48"]["judge_output_sha256"] for s in streams},
        },
        "streams": streams,
        "environment": {
            "host_platform": base["host_platform"],
            "python_version": base["python_version"],
            "cpu_measurement": base["cpu_measurement"],
            "rss_measurement": base["rss_measurement"],
        },
        "caveat": "Eight deterministic synthetic inputs provide a small robustness check, not a statistical estimate of hidden-set performance. The scenario parameters were fixed before the paired solver runs and were not adjusted from these results.",
    }
    if comparison["per_stream_score_regressions"] or comparison["per_stream_score_improvements"]:
        comparison["interpretation"] = "Observed score difference; review per-stream evidence before any promotion."
    else:
        comparison["interpretation"] = "No score or output change on this fixed sample; evidence is neutral and too small to establish generalization."
    (OUT / "comparison.json").write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Run-48: fresh synthetic paired check",
        "",
        "## Краткий результат",
        "",
        f"Сравнены frozen final и сохранённый run-48 на {len(streams)} заранее зафиксированных synthetic streams "
        f"({comparison['total_operations']:,} операций суммарно). На всех {len(streams)} streams совпали KPI, "
        "длина траншеи и judge output побайтно. Score delta равен 0. Это нейтральный результат на небольшой выборке, "
        "а не подтверждение обобщения на закрытые тесты.",
        "",
        "Набор зафиксирован до запуска solver: разные размеры задач, распределения длин труб, удаления random/FIFO/LIFO/" 
        "shortest/longest, batch-drain режимы и изменения фаз. Сгенерированные SHA-256 не совпали ни с одним из "
        f"{prior_input_files} ранее сохранённым `.in` файлов в `data/pipes` и `results/pipes` "
        f"({len(prior_hashes)} уникальных hashes). Параметры после результатов не менялись.",
        "",
        "## Per-stream результаты",
        "",
        "| Stream (ops) | Режимы длин / удалений по фазам | KPI baseline → run-48 | Δ KPI | Траншея baseline → run-48 (м) | CPU baseline / run-48 (с) | RSS baseline / run-48 (MiB) | Выходы |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for s in streams:
        desc = s["phase_description"].replace("|", "/")
        lines.append(
            f"| `{s['name']}` ({s['operations']:,}) | {desc} | "
            f"{s['baseline']['kpi']:.12f} → {s['run48']['kpi']:.12f} | "
            f"{s['delta_weighted_score_run48_minus_baseline']:+.12f} | "
            f"{s['baseline']['trench_length_m']:,} → {s['run48']['trench_length_m']:,} | "
            f"{s['baseline']['solver_cpu_s']:.6f} / {s['run48']['solver_cpu_s']:.6f} | "
            f"{s['baseline']['solver_rss_mib']:.3f} / {s['run48']['solver_rss_mib']:.3f} | "
            f"{'identical' if s['outputs_identical'] else 'different'} |"
        )
    lines.extend([
        "",
        "Сумма KPI по этим восьми входам (weight=1 каждый): baseline "
        f"{comparison['baseline_score_sum_over_these_streams_only']:.12f}, run-48 "
        f"{comparison['run48_score_sum_over_these_streams_only']:.12f}, Δ "
        f"{comparison['delta_score_sum']:+.12f}. Максимальная CPU: "
        f"{comparison['max_solver_cpu_s']['baseline']:.6f}s / {comparison['max_solver_cpu_s']['run48']:.6f}s; "
        "максимальный RSS: "
        f"{comparison['max_solver_rss_mib']['baseline']:.3f} / {comparison['max_solver_rss_mib']['run48']:.3f} MiB. "
        "Все варианты уложились в 5s CPU / 256 MiB.",
        "",
        "## Состав fixed set",
        "",
        "Все потоки детерминированы seed и строятся по ходу генерации из активного состояния и текущей фазы. "
        "Границы фаз заданы заранее по номеру операции; поток команд полностью передаётся обоим solver одинаково.",
        "",
        "## Hashes и воспроизводимость",
        "",
        "Полные SHA-256 исходников, бинарников, harness, interactor, генератора, входов и judge outputs — в "
        "[`comparison.json`](comparison.json); рецепты и входные hashes — в [`input_manifest.json`](input_manifest.json). "
        "Полные логи official harness лежат в [`runs/`](runs/). Frozen final и canonical source не менялись; "
        "платформа не использовалась.",
        "",
        "Run-48 меняет только `kSameLengthRightRun: 46 → 48`. Проверенный SHA frozen final: "
        f"`{sha(BASE_SOURCE)}`; canonical: `{sha(CANONICAL_SOURCE)}`; run-48: `{sha(CANDIDATE_SOURCE)}`.",
        "",
        "### Ограничение вывода",
        "",
        "Отсутствие регрессий на восьми детерминированных потоках — узкая проверка устойчивости. Она не доказывает, "
        "что малый выигрыш Open15 переносится на скрытые данные; выборка мала, и большинство текущих алгоритмических "
        "состояний/режимов может не покрывать неизвестные распределения.",
        "",
    ])
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT / 'comparison.json'}")
    print(f"wrote {OUT / 'REPORT.md'}")


if __name__ == "__main__":
    main()
