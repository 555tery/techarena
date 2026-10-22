"""Freeze historical SEARCH-v2 evidence; read saved reports only, never inputs."""

from collections import defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from support import ROOT, PARENT, digest
from research import atomic_json, read_programs, unique_programs


def build(run):
    run = Path(run).resolve()
    if run.parent != PARENT / "search-v2/runs":
        raise ValueError("only saved SEARCH-v2 runs are allowed")
    spec_path = PARENT / "search-v2/task/data/search/manifest.json"
    spec = json.loads(spec_path.read_text())
    run_manifest = json.loads((run / "run-manifest.json").read_text())
    if run_manifest["suite"] != "search-v2" or run_manifest["search_manifest_sha256"] != digest(spec_path):
        raise ValueError("historical run corpus mismatch")
    expected = {c["file"]: c for c in spec["cases"]}
    programs = unique_programs(read_programs(run))
    cards, signatures, receipts = [], defaultdict(list), {}
    for p in programs:
        if not p["correct"]:
            continue
        folder = run / f"gen_{p['generation']}"
        result = folder / "results"
        if (folder / "native-results/metrics.json").exists():
            result = folder / "native-results"
        metrics_path, summary_path = result / "metrics.json", result / "harness/summary.json"
        metrics, summary = json.loads(metrics_path.read_text()), json.loads(summary_path.read_text())
        receipts[str(metrics_path)] = digest(metrics_path)
        receipts[str(summary_path)] = digest(summary_path)
        if (metrics["program_sha256"] != p["source_sha256"] or metrics["corpus_version"] != "search-v2"
                or metrics["manifest_sha256"] != digest(spec_path)):
            raise ValueError("historical candidate provenance mismatch")
        records = summary["records"]
        by_file = {Path(r["test_file"]).name: r for r in records}
        if len(records) != 128 or len(by_file) != 128 or by_file.keys() != expected.keys():
            raise ValueError("historical report is incomplete")
        grouped = defaultdict(list)
        vector = []
        for name, case in expected.items():
            record = by_file[name]
            if record["status"] != "ok" or record["test_sha256"] != case["sha256"]:
                raise ValueError("historical report uses another case or failed")
            trench = record["trench_length_m"]
            bound = case["stats"]["volume_lower_bound"]
            if trench < bound or trench % 20 or not 0 <= record["solver_cpu_total_s"] < 5:
                raise ValueError("invalid historical result")
            grouped[case["family"]].append(bound / trench)
            vector.append((case["id"], trench))
        score = sum(sum(v) / len(v) for v in grouped.values()) / len(grouped)
        if abs(score - p["combined_score"]) > 1e-12 or abs(score - metrics["combined_score"]) > 1e-12:
            raise ValueError("historical score does not match saved case evidence")
        signature = hashlib.sha256(json.dumps(vector).encode()).hexdigest()
        signatures[signature].append(p["generation"])
        cards.append({"generation": p["generation"], "name": p["metadata"].get("patch_name"),
                      "source_sha256": p["source_sha256"], "score_B_over_T": score,
                      "result_vector_sha256": signature,
                      "claimed_mechanism": str(p["metadata"].get("patch_description", ""))[:500]})
    best = max(cards, key=lambda c: c["score_B_over_T"])
    repeated = sorted((g for g in signatures.values() if len(g) > 1), key=len, reverse=True)
    lines = [f"Frozen prior: {len(cards)} correct generations through gen{max(c['generation'] for c in cards)}.",
             "Only historical SEARCH-v2. Changed corpus/objective warrants a new check; no inherited scores or bans."]
    for group in repeated[:4]:
        names = sorted({c["name"] for c in cards if c["generation"] in group})
        lines.append(f"Identical final trench vector on all 128 old cases: generations {group}; "
                     f"names={', '.join(names)[:450]}. This is not proof of algorithmic equivalence.")
    lines += [f"Old leader gen{best['generation']} ({best['name']}), B/T={best['score_B_over_T']:.9f}.",
              "Broad mechanisms already attempted: interior-before-tail, free-gap age ties, exact address First-Fit, "
              "age-conditioned release risk and coalesced-neighbor release cost.",
              "Avoid spending many proposals merely reimplementing address First-Fit after a new-corpus comparison. "
              "Explain changes to behavior, interactions or assumptions."]
    return {"version": "historical-search-v2-prior-v1", "observed_at": datetime.now(ZoneInfo("Asia/Novosibirsk")).isoformat(),
            "source_run": str(run), "source_run_status_at_read": run_manifest["status"],
            "manifest_sha256": digest(spec_path), "run_manifest_sha256_at_read": digest(run / "run-manifest.json"),
            "read_only": True, "raw_inputs_read": False, "validation_accessed": False, "open15_accessed": False,
            "score_comparable_to_v31": False, "prompt_lines": lines, "cards": cards,
            "identical_result_vector_groups": repeated, "artifact_sha256": receipts}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    target = ROOT / "research-prior.json"
    if target.exists():
        raise SystemExit("Prior already frozen; do not overwrite research history.")
    result = build(args.run_dir)
    atomic_json(target, result)
    print(f"Frozen {len(result['cards'])} historical correct candidates; no solver/model calls.")
