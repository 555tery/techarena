#!/usr/bin/env python3
"""Full-run audit, paired KPI/resource analysis and explicit score scenarios."""
from __future__ import annotations
import collections
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import random
import re
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / "prototypes/pipes_all2537_comparison_20261020"
METHODS = ("online_cj", "hybrid_cpp", "hybrid_cj")
COMPARED = ("online_cj", "hybrid_cj")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location("audited_analysis", OLD / "analyze.py")
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)

def top2_expectation(values):
    v = sorted(values)
    n = len(v)
    choose = lambda a, b: math.comb(a, b) if a >= b else 0
    weights = [choose(i, 3) + (n - i - 1) * choose(i, 2) for i in range(n)]
    denominator = choose(n, 4)
    assert denominator and sum(weights) == 2 * denominator
    return math.fsum(x * w for x, w in zip(v, weights)) / denominator

def simple_stats(values):
    if not values:
        return dict(mean=None, p05=None, median=None, p95=None, minimum=None, maximum=None)
    return dict(mean=statistics.fmean(values), p05=shared.percentile(values, .05),
                median=statistics.median(values), p95=shared.percentile(values, .95),
                minimum=min(values), maximum=max(values))

def score_scenario(name, cheap_ids, expensive_ids, shared_pool, records, open_scores, seed):
    cheap = [tuple(float(records[i, m]["adjusted"]) for m in COMPARED) for i in cheap_ids]
    expensive = [tuple(float(records[i, m]["adjusted"]) for m in COMPARED) for i in expensive_ids]
    rng = random.Random(seed)
    totals = {m: [] for m in COMPARED}
    deltas = []
    for _ in range(100000):
        if shared_pool:
            sample = rng.sample(cheap, 15)
            eleven, four = sample[:11], sample[11:]
        else:
            eleven, four = rng.sample(cheap, 11), rng.sample(expensive, 4)
        pair = []
        for j, method in enumerate(COMPARED):
            ks = [r[j] for r in four]
            s = open_scores[method] + 4 * math.fsum(r[j] for r in eleven)
            s += 10 * math.fsum(ks) + 10 * math.fsum(sorted(ks)[-2:])
            totals[method].append(s)
            pair.append(s)
        deltas.append(pair[1] - pair[0])
    expected = {}
    for j, method in enumerate(COMPARED):
        expected[method] = {
            "open15": open_scores[method],
            "closed11_weight4": 44 * statistics.fmean(r[j] for r in cheap),
            "closed4_weight10": 40 * statistics.fmean(r[j] for r in expensive),
            "cangjie_top2_bonus": 10 * top2_expectation([r[j] for r in expensive]),
        }
        expected[method]["total"] = math.fsum(expected[method].values())
    return dict(name=name, cheap_count=len(cheap), expensive_count=len(expensive),
                shared_pool=shared_pool, exact_expected=expected,
                exact_delta=expected["hybrid_cj"]["total"] - expected["online_cj"]["total"],
                seed=seed, paired_draws=100000, distributions={m: simple_stats(v) for m, v in totals.items()},
                paired_delta=simple_stats(deltas),
                hybrid_higher_fraction=sum(x > 0 for x in deltas) / len(deltas),
                equal_fraction=sum(x == 0 for x in deltas) / len(deltas),
                not_a_probability_of_winning_actual_competition=True)

def main():
    frozen = json.loads((HERE / "freeze.json").read_text())
    protocol = json.loads((HERE / "protocol.json").read_text())
    assert sha(HERE / "protocol.json") == frozen["protocol_sha256"]
    assert sha(HERE / "fresh/manifest.json") == frozen["fresh_manifest_sha256"]
    assert sha(OLD / "freeze.json") == frozen["old_freeze_sha256"]
    previous = json.loads((OLD / "freeze.json").read_text())
    assert sha(ROOT / "vendor/pipes_official/interactor.cpp") == previous["official_source_sha256"]
    # Official output is canonical integer text; verify its full SHA and LF count.
    frozen["official_source_sha256"] = previous["official_source_sha256"]
    artifacts = shared.verify_artifacts(HERE, frozen)
    records, audit = shared.load_records(HERE, frozen, sha(HERE / "freeze.json"), True)
    cases = {c["id"]: c for c in frozen["cases"]}
    assert len(records) == 7911 and len(cases) == 2637
    assert all((i, m) in records for i in cases for m in METHODS)
    assert all(r["workers"] == 1 for r in records.values())
    selected = [i for i, c in cases.items() if c["selected"]]
    fresh = [i for i, c in cases.items() if c["cohort"] == "fresh"]
    assert len(selected) == 2537 and len(fresh) == 96
    groups = {"archive2537": selected, "fresh96": fresh,
              "fresh_prefix60": [i for i in fresh if cases[i]["kind"] == "public_prefix"],
              "fresh_composition32": [i for i in fresh if cases[i]["kind"] == "composition"],
              "fresh_stress4": [i for i in fresh if cases[i]["kind"] == "stress"],
              "all2637": list(cases)}
    groups["short_le200"] = [i for i in cases if cases[i]["meta"]["operation_count"] <= 200]
    groups["long_gt100000"] = [i for i in cases if cases[i]["meta"]["operation_count"] > 100000]
    summaries = {}
    for name, ids in groups.items():
        summaries[name] = {
            "count": len(ids),
            "methods": {m: shared.summarize(records[i, m] for i in ids) for m in METHODS},
            "hybrid_minus_online": shared.pair_summary("hybrid_cj", "online_cj", ids, records, cases),
            "paired_cpu_ratio_hybrid_cj_over_online_cj": simple_stats(
                [records[i, "hybrid_cj"]["cpu"] / records[i, "online_cj"]["cpu"]
                 for i in ids if records[i, "hybrid_cj"]["cpu"] is not None and records[i, "online_cj"]["cpu"]]),
            "paired_cpu_ratio_hybrid_cj_over_cpp": simple_stats(
                [records[i, "hybrid_cj"]["cpu"] / records[i, "hybrid_cpp"]["cpu"]
                 for i in ids if records[i, "hybrid_cj"]["cpu"] is not None and records[i, "hybrid_cpp"]["cpu"]]),
        }
        measured = [i for i in ids if all(records[i, m]["cpu"] is not None for m in METHODS)]
        cpu_sums = {m: math.fsum(records[i, m]["cpu"] for i in measured) for m in METHODS}
        summaries[name]["paired_cpu_totals"] = {
            "measured_pairs": len(measured), "process_cpu_s": cpu_sums,
            "hybrid_cj_over_online_cj": cpu_sums["hybrid_cj"] / cpu_sums["online_cj"] if cpu_sums["online_cj"] else None,
            "hybrid_cj_over_cpp": cpu_sums["hybrid_cj"] / cpu_sums["hybrid_cpp"] if cpu_sums["hybrid_cpp"] else None,
        }
    families = {}
    for family in sorted({cases[i]["family"] for i in fresh}):
        ids = [i for i in fresh if cases[i]["family"] == family]
        families[family] = {"count": len(ids),
                           "methods": {m: shared.summarize(records[i, m] for i in ids) for m in COMPARED},
                           "pair": shared.pair_summary("hybrid_cj", "online_cj", ids, records, cases)}
    raw_records = [json.loads(line) for line in (HERE / "records.jsonl").read_text().splitlines()]
    raw_index = {(r["id"], r["method"]): r for r in raw_records}
    parity = {"checked": len(cases), "identical": 0, "mismatches": []}
    diagnostic_counts = collections.Counter()
    for i in cases:
        a, b = records[i, "hybrid_cpp"], records[i, "hybrid_cj"]
        equal = a["valid"] and b["valid"] and a["normalized_response_sha256"] == b["normalized_response_sha256"]
        if equal:
            assert a["trench"] == b["trench"] and a["raw"] == b["raw"]
            parity["identical"] += 1
        else:
            parity["mismatches"].append(i)
        diagnostic = re.search(r"\babort_reason=(\S+)", raw_index[i, "hybrid_cj"]["candidate_stderr"])
        diagnostic_counts[diagnostic.group(1) if diagnostic else "missing"] += 1
    old_audit = json.loads((OLD / "final_audit.json").read_text())
    assert sha(OLD / "records.jsonl") == old_audit["artifact_sha256"]["records.jsonl"]
    old_online = {r["id"]: r for line in (OLD / "records.jsonl").read_text().splitlines()
                  if (r := json.loads(line))["method"] == "online_cj"}
    baseline_mismatches = [i for i in old_online
                          if old_online[i]["response_sha256"] != records[i, "online_cj"]["normalized_response_sha256"]]
    assert len(old_online) == 2541
    open_cases = sorted((c for c in cases.values() if c["public_number"] is not None),
                        key=lambda c: c["public_number"])
    assert [c["public_number"] for c in open_cases] == list(range(1, 16))
    open15 = {
        m: dict(raw=math.fsum(c["meta"]["weight"] * float(records[c["id"], m]["raw"] or 0) for c in open_cases),
                adjusted=math.fsum(c["meta"]["weight"] * float(records[c["id"], m]["adjusted"]) for c in open_cases))
        for m in METHODS
    }
    # Verify nonlinear bonus against exhaustive small finite populations.
    for v in ([0., .1, .1, .4, .8, 1.], [.9] * 6):
        expected = statistics.fmean(sum(sorted(x)[-2:]) for x in itertools.combinations(v, 4))
        assert math.isclose(expected, top2_expectation(v), abs_tol=1e-14)
    nonpublic = [i for i in selected if cases[i]["public_number"] is None]
    coverage = json.loads((OLD / "coverage.json").read_text())
    additional_ids = set(coverage["id_sets"]["other_selected"])
    additional = [i for i in nonpublic if i in additional_ids]
    n = lambda i: cases[i]["meta"]["operation_count"]
    nonshort = [i for i in nonpublic if n(i) > 200]
    short = [i for i in nonpublic if n(i) <= 200]
    long = [i for i in nonpublic if n(i) > 100000]
    notlong = [i for i in nonpublic if n(i) <= 100000]
    prefix = groups["fresh_prefix60"]
    composition = groups["fresh_composition32"] + groups["fresh_stress4"]
    configurations = [
        ("archive_uniform", nonpublic, nonpublic, True),
        ("additional_archive", additional, additional, True),
        ("without_short", nonshort, nonshort, True),
        ("long_only", long, long, True),
        ("expensive_are_long", notlong, long, False),
        ("short_only", short, short, True),
        ("fresh_uniform", fresh, fresh, True),
        ("fresh_prefix", prefix, prefix, True),
        ("fresh_nonpublic", composition, composition, True),
    ]
    scores = [score_scenario(name, cheap, expensive, shared_pool, records,
                            {m: open15[m]["adjusted"] for m in COMPARED}, 202610202637 + j * 1009)
              for j, (name, cheap, expensive, shared_pool) in enumerate(configurations)]
    per_case = []
    for i, c in cases.items():
        diagnostic = raw_index[i, "hybrid_cj"]["candidate_stderr"].strip()
        per_case.append({**shared.case_description(c),
                         "cohort": c["cohort"], "family": c["family"], "name": c["name"],
                         "kind": c.get("kind"), "input": c["input"],
                         "methods": {m: shared.public_result(records[i, m]) for m in METHODS},
                         "delta": float(records[i, "hybrid_cj"]["adjusted"] - records[i, "online_cj"]["adjusted"]),
                         "hybrid_diagnostic": diagnostic})
    worst = sorted(per_case, key=lambda c: (c["delta"], c["id"]))
    resources = {}
    for m in METHODS:
        resources[m] = {
            "max_cpu_case": max(per_case, key=lambda c: c["methods"][m]["cpu_process_s"] or -1)["id"],
            "max_rss_case": max(per_case, key=lambda c: c["methods"][m]["peak_rss_MiB"] or -1)["id"],
        }
    result = dict(
        complete=True, total_runs=7911, total_cases=2637,
        protocol=protocol, freeze_sha256=sha(HERE / "freeze.json"),
        hash_verification={**audit, **artifacts},
        hybrid_cpp_cj_parity=parity,
        unchanged_online_baseline=dict(checked=2541, identical=2541-len(baseline_mismatches),
                                       mismatch_ids=baseline_mismatches),
        summaries=summaries, fresh_families=families, open15=open15,
        score_scenarios=scores, hybrid_abort_reasons=dict(diagnostic_counts),
        resource_extremes=resources, worst20=worst[:20], best20=list(reversed(worst[-20:])),
        fresh_worst10=sorted((c for c in per_case if c["cohort"] == "fresh"), key=lambda c: c["delta"])[:10],
        per_case=per_case,
        limitations=[
            "Observed archive is not an independent holdout. Fresh streams use independent seeds but known broad mechanisms.",
            "Fresh insertion-only tails constitute 31–38% of new suffixes and can dilute prefix damage.",
            "U is only a volume upper bound; the selected archive is not a certificate of attainable KPI>=0.85 on every test.",
            "Contest-score rows are explicit sampling scenarios; hidden distribution and expensive-group mechanisms are unknown.",
            "All primary runs serial, cjProcessorNum=1, whole process CPU; macOS does not provide hard one-logical-CPU affinity.",
            "Windows/G5420 and contest compiler not tested here; no cross-CPU time extrapolation.",
            "Replay guard bounds trench only while replay is active, not final KPI relative to pure online.",
        ])
    (HERE / "analysis.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "complete": True, "parity": parity, "online_baseline_mismatches": len(baseline_mismatches),
        "open15": open15,
        "archive_pair": {k: summaries["archive2537"]["hybrid_minus_online"][k]
                         for k in ("wins", "ties", "losses", "delta_mean_adjusted_kpi")},
        "fresh_pair": {k: summaries["fresh96"]["hybrid_minus_online"][k]
                      for k in ("wins", "ties", "losses", "delta_mean_adjusted_kpi")},
        "scores": {s["name"]: s["exact_delta"] for s in scores},
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
