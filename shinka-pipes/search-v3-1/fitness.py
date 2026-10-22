"""SEARCH-v3.1 F/T fitness with strict coverage, correctness and resource gates."""

from collections import Counter
import math
from pathlib import Path

CPU_LIMIT, RSS_LIMIT = 5.0, 256.0
DEFINITION = "mean_over_families(mean_over_cases(final_live_volume / trench_length))"


def aggregate_report(summary, manifest, suite_path, returncode):
    if (manifest.get("version") != "search-v3.1" or manifest.get("split") != "search"
            or manifest.get("role") != "fitness"):
        raise ValueError("only SEARCH-v3.1 main inputs may produce fitness")
    cases, families = manifest["cases"], manifest["families"]
    expected = {c["file"]: c for c in cases}
    if (not cases or not families or len(set(families)) != len(families)
            or len(expected) != len(cases) or len(cases) != manifest["case_count"]
            or Counter(c["family"] for c in cases) != {f: manifest["cases_per_family"] for f in families}
            or manifest["weight_per_case"] != 1):
        raise ValueError("invalid case/family coverage or weighting")
    records = summary.get("records", [])
    if returncode != 0 or len(records) != len(expected):
        raise ValueError("harness failed or case coverage is incomplete")
    by_file = {}
    for record in records:
        file = Path(record["test_file"])
        if (file.name not in expected or file.name in by_file
                or file.resolve() != (suite_path / file.name).resolve()):
            raise ValueError("unexpected, duplicate or misplaced case")
        by_file[file.name] = record
    grouped = {f: [] for f in families}
    details, cpus, rss_values = [], [], []
    for case in cases:  # Fixed manifest order, independent of parallel completion.
        record = by_file[case["file"]]
        if record["status"] != "ok" or record["test_sha256"] != case["sha256"]:
            raise ValueError("wrong input or invalid solver result")
        cpu, rss = float(record["solver_cpu_total_s"]), float(record["solver_peak_rss_mb"])
        trench, kpi = float(record["trench_length_m"]), float(record["kpi"])
        if not all(math.isfinite(x) for x in (cpu, rss, trench, kpi)):
            raise ValueError("nonfinite score or resource measurement")
        if (not 0 <= cpu < CPU_LIMIT or not 0 <= rss < RSS_LIMIT
                or record.get("solver_cpu_limit_exceeded") or record.get("solver_memory_limit_exceeded")):
            raise ValueError("solver resource limit exceeded")
        bound, final = case["stats"]["volume_lower_bound"], case["stats"]["final_live_volume"]
        if (trench <= 0 or trench < bound or trench % 20 != 0
                or record["minimum_trench_lower_bound_m"] != bound
                or record["final_occupied_length_m"] != final
                or record["occupied_length_m"] != final
                or record["operation_count"] != case["operations"]
                or record["judge_commands_seen_including_final_zero"] != case["operations"] + 1
                or record["official_weight"] != 1 or record["weight"] != 1
                or not math.isclose(kpi, final / trench, rel_tol=0, abs_tol=1e-12)
                or not math.isclose(float(record["weighted_score"]), kpi, rel_tol=0, abs_tol=1e-12)):
            raise ValueError("inconsistent volume, trench, protocol, weight or official KPI")
        grouped[case["family"]].append(kpi)
        cpus.append(cpu)
        rss_values.append(rss)
        details.append({"id": case["id"], "family": case["family"], "kpi": kpi,
                        "final": final, "test_sha256": case["sha256"],
                        "final_to_bound": final / bound, "bound_to_trench": bound / trench,
                        "overrun": trench / bound - 1, "trench": int(trench), "bound": bound,
                        "solver_cpu_s": cpu, "solver_rss_mib": rss})
    family_scores = {f: sum(grouped[f]) / len(grouped[f]) for f in families}
    fitness = sum(family_scores.values()) / len(family_scores)
    worst = sorted(details, key=lambda d: (d["kpi"], d["id"]))[:16]
    worst_overrun = sorted(details, key=lambda d: (-d["overrun"], d["id"]))[:16]
    family_order = sorted(family_scores, key=lambda f: (family_scores[f], f))
    feedback = [f"Fitness F/T={fitness:.12f}; stress excluded. B/T is diagnostic only."]
    feedback += [f"family={f} mean_F/T={family_scores[f]:.9f}" for f in family_order]
    for label, rows in (("Worst F/T", worst), ("Largest T/B-1 (diagnostic only)", worst_overrun)):
        feedback.append(label + "; F/B is an input-only ceiling, not an allocator loss.")
        feedback += [f"case={d['id']} family={d['family']} F/T={d['kpi']:.9f} "
                     f"F/B={d['final_to_bound']:.9f} B/T={d['bound_to_trench']:.9f} overrun={d['overrun']:.6f} "
                     f"cpu_s={d['solver_cpu_s']:.6f} rss_mib={d['solver_rss_mib']:.3f}" for d in rows]
    mean_overrun = sum(d["overrun"] for d in details) / len(details)
    return {"combined_score": fitness, "suite": "search", "corpus_version": "search-v3.1",
            "fitness_definition": DEFINITION, "family_scores": family_scores,
            "public": {"valid_cases": len(details), "family_count": len(families),
                       "mean_raw_kpi": sum(d["kpi"] for d in details) / len(details),
                       "worst_family_score": min(family_scores.values()), "mean_overrun": mean_overrun,
                       "mean_bound_to_trench": sum(d["bound_to_trench"] for d in details) / len(details),
                       "max_solver_cpu_seconds": max(cpus), "max_solver_rss_mib": max(rss_values)},
            "diagnostics": {"worst_16": worst, "worst_16_by_overrun": worst_overrun,
                            "worst_families": [{"family": f, "mean_kpi": family_scores[f]} for f in family_order],
                            "mean_overrun": mean_overrun,
                            "worst_16_mean_overrun": sum(d["overrun"] for d in worst) / len(worst),
                            "max_overrun": max(d["overrun"] for d in details)},
            "private": {"research_cases": details},
            "solver_cpu_total_s": sum(cpus), "stress_evaluated": False,
            "text_feedback": "\n".join(feedback)}, True
