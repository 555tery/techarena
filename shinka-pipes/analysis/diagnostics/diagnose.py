"""Read saved SEARCH-v2 results and write separate diagnostic reports; never evaluate."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

SHINKA = Path(__file__).resolve().parents[2]
V2 = SHINKA / "search-v2"
RUNS = V2 / "runs"
ANALYSIS = SHINKA / "analysis"
sys.dont_write_bytecode = True
sys.path.insert(0, str(SHINKA))
from synthetic_eval import aggregate_report


def checked_path(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()) or resolved == root.resolve():
        raise ValueError(f"path outside the allowed directory: {path}")
    return resolved


def read_bytes(path: Path, root: Path, receipts: dict) -> bytes:
    path = checked_path(path, root)
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f"artifact changed while reading: {path}")
    receipts[str(path)] = hashlib.sha256(data).hexdigest()
    return data


def read_json(path: Path, root: Path, receipts: dict) -> dict:
    return json.loads(read_bytes(path, root, receipts))


def context(run: Path, receipts: dict) -> tuple[dict, dict]:
    run = checked_path(run, RUNS)
    run_manifest = read_json(run / "run-manifest.json", run, receipts)
    protocol = read_json(V2 / "protocol.json", V2, receipts)
    path = V2 / "task/data/search/manifest.json"
    manifest = read_json(path, V2, receipts)
    digest = receipts[str(path.resolve())]
    if (run_manifest.get("suite") != "search-v2"
            or run_manifest.get("search_manifest_sha256") != digest
            or protocol.get("manifest_sha256") != digest
            or manifest.get("version") != "search-v2" or manifest.get("split") != "search"
            or manifest.get("case_count") != 128 or manifest.get("cases_per_family") != 8):
        raise ValueError("expected a run bound to the fixed SEARCH-v2 manifest")
    cases, families = manifest["cases"], manifest["families"]
    if (len(cases) != 128 or len(families) != 16 or len(set(families)) != 16
            or len({c["id"] for c in cases}) != 128 or len({c["file"] for c in cases}) != 128
            or Counter(c["family"] for c in cases) != {f: 8 for f in families}
            or any(Path(c["file"]).name != c["file"] or not c["file"].endswith(".in") for c in cases)
            or any(c["stats"]["volume_lower_bound"] <= 0
                   or c["stats"]["volume_lower_bound"] % 20 != 0 for c in cases)):
        raise ValueError("invalid SEARCH-v2 metadata coverage")
    return run_manifest, manifest


def summarize(records: list[dict], manifest: dict) -> dict:
    """Pure arithmetic on already validated records; also usable with tiny fixtures."""
    specs = {c["file"]: c for c in manifest["cases"]}
    streams, grouped = [], defaultdict(list)
    for record in records:
        spec = specs[Path(record["test_file"]).name]
        bound, trench = spec["stats"]["volume_lower_bound"], record["trench_length_m"]
        row = {"case": spec["id"], "family": spec["family"], "bound_m": bound,
               "trench_m": trench, "score": bound / trench,
               "extra_m": trench - bound, "relative_excess": trench / bound - 1}
        streams.append(row)
        grouped[row["family"]].append(row)
    families = [{"family": name, "cases": len(rows),
                 "mean_score": math.fsum(r["score"] for r in rows) / len(rows),
                 "mean_relative_excess": math.fsum(r["relative_excess"] for r in rows) / len(rows),
                 "worst_score": min(r["score"] for r in rows)} for name, rows in grouped.items()]
    worst = sorted(streams, key=lambda r: (r["score"], r["case"]))[:16]
    return {"streams": sorted(streams, key=lambda r: r["case"]), "worst_16": worst,
            "worst_16_mean_score": math.fsum(r["score"] for r in worst) / len(worst),
            "families": sorted(families, key=lambda r: (r["mean_score"], r["family"])),
            "mean_relative_excess": math.fsum(r["mean_relative_excess"] for r in families) / len(families)}


def generation(run: Path, number: int, run_manifest: dict, manifest: dict, receipts: dict) -> dict:
    folder = checked_path(run / f"gen_{number}", run)
    results = folder / "results"
    correct_file = results / "correct.json"
    if not correct_file.is_file():
        return {"generation": number, "status": "incomplete"}
    correct = read_json(correct_file, run, receipts)
    metrics = read_json(results / "metrics.json", run, receipts)
    if correct.get("correct") is not True:
        return {"generation": number, "status": "rejected", "reason": metrics.get("error", "correct=false")}
    summary = read_json(results / "harness/summary.json", run, receipts)
    source_hash = hashlib.sha256(read_bytes(folder / "main.cpp", run, receipts)).hexdigest()
    bindings = {"program_sha256": source_hash,
                "manifest_sha256": run_manifest["search_manifest_sha256"],
                "snapshot_sha256": run_manifest["snapshot_sha256"],
                "evaluator_sha256": run_manifest["evaluator_sha256"]}
    if any(metrics.get(key) != value for key, value in bindings.items()):
        raise ValueError(f"generation {number}: saved provenance mismatch")
    if number == 0 and source_hash != run_manifest["source_sha256"]:
        raise ValueError("generation zero is not the run's selected initial program")
    recomputed, valid = aggregate_report(summary, manifest, V2 / "task/data/search", 0)
    if (not valid or metrics.get("suite") != "search" or metrics.get("corpus_version") != "search-v2"
            or metrics.get("public", {}).get("valid_cases") != 128
            or not math.isclose(metrics["combined_score"], recomputed["combined_score"], rel_tol=1e-12, abs_tol=1e-12)
            or set(metrics.get("family_scores", {})) != set(recomputed["family_scores"])
            or any(not math.isclose(metrics["family_scores"][f], q, rel_tol=1e-12, abs_tol=1e-12)
                   for f, q in recomputed["family_scores"].items())):
        raise ValueError(f"generation {number}: saved fitness does not match the full report")
    return {"generation": number, "status": "complete", "combined_score": metrics["combined_score"],
            "source_sha256": source_hash, **summarize(summary["records"], manifest)}


def compare(item: dict, baseline: dict) -> None:
    reference = {r["case"]: r for r in baseline["streams"]}
    by_id = {r["case"]: r for r in item["streams"]}
    for row in item["streams"]:
        old = reference[row["case"]]
        row["delta_trench_m_vs_baseline"] = row["trench_m"] - old["trench_m"]
        row["delta_score_vs_baseline"] = row["score"] - old["score"]
    base_families = {r["family"]: r for r in baseline["families"]}
    for row in item["families"]:
        row["delta_mean_score_vs_baseline"] = row["mean_score"] - base_families[row["family"]]["mean_score"]
    item["baseline_worst_16_ids"] = [r["case"] for r in baseline["worst_16"]]
    item["baseline_worst_16_mean_score"] = math.fsum(by_id[k]["score"] for k in item["baseline_worst_16_ids"]) / 16
    item["delta_combined_score_vs_baseline"] = item["combined_score"] - baseline["combined_score"]
    item["delta_mean_relative_excess_vs_baseline"] = item["mean_relative_excess"] - baseline["mean_relative_excess"]
    item["changes_vs_baseline"] = {
        "improved": sum(r["delta_trench_m_vs_baseline"] < 0 for r in item["streams"]),
        "regressed": sum(r["delta_trench_m_vs_baseline"] > 0 for r in item["streams"]),
        "tied": sum(r["delta_trench_m_vs_baseline"] == 0 for r in item["streams"])}
    item["regressions"] = sorted((r for r in item["streams"] if r["delta_trench_m_vs_baseline"] > 0),
                                 key=lambda r: (r["delta_score_vs_baseline"], r["case"]))


def collect(run: Path, numbers: list[int] | None = None) -> dict:
    run = checked_path(run, RUNS)
    receipts = {}
    run_manifest, manifest = context(run, receipts)
    if numbers is None:
        numbers = [int(p.name[4:]) for p in run.iterdir() if re.fullmatch(r"gen_(0|[1-9][0-9]*)", p.name)]
    items = [generation(run, n, run_manifest, manifest, receipts) for n in sorted(set([0, *numbers]))]
    baseline = next(item for item in items if item["generation"] == 0)
    if baseline["status"] != "complete":
        raise ValueError("a complete correct baseline is required for diagnostics")
    for item in items:
        if item["status"] == "complete":
            compare(item, baseline)
    return {"created_at": datetime.now(ZoneInfo("Asia/Novosibirsk")).isoformat(),
            "generator": {"path": str(Path(__file__).resolve()),
                          "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            "run_dir": str(run), "suite": "search-v2", "baseline_generation": 0,
            "seed_origin": run_manifest.get("seed_origin"), "generations": items,
            "definitions": {"mean_relative_excess": "mean_f mean_i_in_f(T_i/B_i - 1), fraction; not 1/mean(B/T)-1",
                            "worst_16": "16 lowest B/T values in this generation; ties ordered by case id",
                            "baseline_worst_16": "fixed 16 case ids selected from generation zero",
                            "families": "all 16 families ordered by increasing mean B/T",
                            "delta_trench_m": "candidate T minus baseline T; positive means regression"},
            "input_sha256": receipts, "current_fitness_modified": False, "feedback_injected": False,
            "candidate_evaluations_launched": 0, "raw_inputs_read": False,
            "validation_accessed": False, "open15_accessed": False}


def render(report: dict) -> str:
    lines = ["# Диагностика провалов SEARCH v2", "", f"Снимок: {report['created_at']}.",
             f"Прогон: `{Path(report['run_dir']).name}`. Baseline — поколение 0 этого запуска.",
             "Источник — сохранённые отчёты. Диагностика не меняет fitness, отбор или feedback модели.",
             "Перерасход — T/B − 1 относительно объёмной нижней границы, не доказанного оптимума.",
             "Худшие 16 определяются отдельно для каждого поколения; фиксированные 16 baseline позволяют сравнить одну группу.",
             "", "| Поколение | Fitness | Худшие 16 | Фиксированные 16 baseline | Худшее семейство | Средний перерасход | Лучше / хуже / равно |",
             "|---:|---:|---:|---:|---|---:|---:|"]
    for item in report["generations"]:
        if item["status"] != "complete":
            lines += [f"| {item['generation']} | {item['status']} | — | — | — | — | — |"]
            continue
        c, f = item["changes_vs_baseline"], item["families"][0]
        lines += [f"| {item['generation']} | {item['combined_score']:.9f} | {item['worst_16_mean_score']:.6f} | {item['baseline_worst_16_mean_score']:.6f} | {f['family']} ({f['mean_score']:.6f}) | {100*item['mean_relative_excess']:.4f}% | {c['improved']} / {c['regressed']} / {c['tied']} |"]
    for item in report["generations"]:
        if item["status"] != "complete":
            continue
        lines += ["", f"## Поколение {item['generation']}", "",
                  f"Изменение fitness к baseline: {item['delta_combined_score_vs_baseline']:+.9f}; изменение среднего перерасхода: {100*item['delta_mean_relative_excess_vs_baseline']:+.4f} п.п.",
                  "", "### Худшие 16 потоков", "",
                  "Положительное ΔT означает больше выкопанных метров относительно baseline.", "",
                  "| Поток | Семейство | B, м | T, м | T − B, м | B/T | Перерасход | ΔT, м |",
                  "|---|---|---:|---:|---:|---:|---:|---:|"]
        for row in item["worst_16"]:
            lines += [f"| {row['case']} | {row['family']} | {row['bound_m']} | {row['trench_m']} | {row['extra_m']} | {row['score']:.6f} | {100*row['relative_excess']:.2f}% | {row['delta_trench_m_vs_baseline']:+d} |"]
        lines += ["", "### Семейства от худшего к лучшему", "",
                  "| Семейство | Потоков | Среднее B/T | Средний перерасход | Худший B/T | Δ среднего B/T |",
                  "|---|---:|---:|---:|---:|---:|"]
        for row in item["families"]:
            lines += [f"| {row['family']} | {row['cases']} | {row['mean_score']:.6f} | {100*row['mean_relative_excess']:.2f}% | {row['worst_score']:.6f} | {row['delta_mean_score_vs_baseline']:+.6f} |"]
        lines += ["", "### Регрессии относительно baseline", ""]
        if item["regressions"]:
            lines += ["| Поток | ΔT, м | Δ B/T |", "|---|---:|---:|"]
            for row in item["regressions"]:
                lines += [f"| {row['case']} | {row['delta_trench_m_vs_baseline']:+d} | {row['delta_score_vs_baseline']:+.6f} |"]
        else:
            lines += ["Нет увеличений T относительно baseline."]
    lines += ["", "Машинные значения, формулы и SHA256 прочитанных артефактов: [diagnostics.json](diagnostics.json).",
              "Исходные потоки, Validation и Open15 не читались. Новые исполнения кандидатов не запускались.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--generation", type=int, action="append")
    args = parser.parse_args(argv)
    if args.generation and any(n < 0 for n in args.generation):
        parser.error("generation numbers must be nonnegative")
    output = checked_path(args.out_dir, ANALYSIS)
    if output.exists():
        raise ValueError("output directory already exists; use a new snapshot directory")
    report = collect(args.run_dir, args.generation)
    markdown = render(report)
    output.mkdir(parents=True, exist_ok=False)
    (output / "diagnostics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    (output / "REPORT.md").write_text(markdown)
    print(json.dumps({"report": str(output / "REPORT.md"), "generations": [
        {key: item[key] for key in ("generation", "status", "combined_score", "mean_relative_excess", "worst_16_mean_score") if key in item}
        for item in report["generations"]]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Diagnostics refused: {exc}", file=sys.stderr)
        raise SystemExit(2)
