"""Regression profiles and family champions from complete main-corpus evidence."""

from collections import defaultdict
import json
import math

from research import checked_cases, identity
from support import ROOT

VERSION = "family-specialists-v1"


def load_policy():
    policy = json.loads((ROOT / "selection-policy.json").read_text())
    if (policy["version"] != VERSION or policy["parent_cycle"] != ["score", "score", "robust", "score", "specialist"]
            or policy["tail_fraction"] != .1 or policy["robust_mean_tolerance"] != .005
            or policy["numeric_tolerance"] != 1e-12):
        raise ValueError("unsupported selection policy; revise implementation and checks together")
    return policy


def checked_profile(program, manifest, manifest_sha):
    private = program["private_metrics"]
    if private.get("research_manifest_sha256") != manifest_sha:
        raise ValueError("selection evidence belongs to another corpus")
    rows = checked_cases(private.get("research_cases"))
    expected = {c["id"]: c for c in manifest["cases"]}
    if len(expected) != manifest["case_count"] or rows.keys() != expected.keys():
        raise ValueError("selection requires the complete main corpus")
    families = defaultdict(list)
    for key, row in rows.items():
        case = expected[key]
        if (row["family"] != case["family"] or row["test_sha256"] != case["sha256"]
                or row["bound"] != case["stats"]["volume_lower_bound"]
                or row["final"] != case["stats"]["final_live_volume"]
                or type(row["trench"]) is not int
                or not math.isfinite(row["solver_cpu_s"]) or not 0 <= row["solver_cpu_s"] < 5
                or not math.isfinite(row["solver_rss_mib"]) or not 0 <= row["solver_rss_mib"] < 256):
            raise ValueError("selection input, resource or trench evidence disagrees")
        families[row["family"]].append(row["kpi"])
    if (set(families) != set(manifest["families"])
            or any(len(v) != manifest["cases_per_family"] for v in families.values())):
        raise ValueError("selection family coverage differs from manifest")
    scores = {f: math.fsum(values) / len(values) for f, values in sorted(families.items())}
    mean = math.fsum(scores.values()) / len(scores)
    if not math.isclose(mean, program["combined_score"], abs_tol=1e-12, rel_tol=0):
        raise ValueError("selection profile does not match primary mean F/T")
    return {**identity(program), "island_idx": program.get("island_idx"),
            "mean": program["combined_score"], "family_scores": scores, "cases": rows}


def regression(profile, baseline, policy):
    losses = sorted(({
        "id": key, "family": row["family"],
        "loss": max(0., baseline["cases"][key]["kpi"] - row["kpi"]),
        "delta_trench": row["trench"] - baseline["cases"][key]["trench"],
    } for key, row in profile["cases"].items()), key=lambda x: (-x["loss"], x["id"]))
    count = max(1, math.ceil(policy["tail_fraction"] * len(losses)))
    deltas = {f: profile["family_scores"][f] - baseline["family_scores"][f]
              for f in profile["family_scores"]}
    return {"baseline": {k: baseline[k] for k in ("id", "generation", "source_sha256")},
            "tail_count": count, "tail_loss": math.fsum(x["loss"] for x in losses[:count]) / count,
            "max_case_loss": losses[0]["loss"],
            "regressed_cases": sum(x["loss"] > policy["numeric_tolerance"] for x in losses),
            "family_deltas": deltas,
            "worst_family_delta": min(deltas.values()),
            "largest_losses": [x for x in losses[:8] if x["loss"] > policy["numeric_tolerance"]]}


def profiles(programs, manifest, manifest_sha, policy, before_generation=None):
    eligible = [p for p in programs if p["correct"] and
                (before_generation is None or p["generation"] < before_generation)]
    result = [checked_profile(p, manifest, manifest_sha) for p in eligible]
    seeds = [p for p in result if p["generation"] == 0]
    if not seeds or len({p["source_sha256"] for p in seeds}) != 1:
        raise ValueError("selection needs one fixed correct generation-zero baseline")
    baseline = min(seeds, key=lambda p: p["id"])
    # Island copies and exact sources must retain the same deterministic result.
    vectors = {}
    for p in result:
        vector = tuple((key, row["trench"]) for key, row in sorted(p["cases"].items()))
        if p["source_sha256"] in vectors and vectors[p["source_sha256"]] != vector:
            raise ValueError("identical source has conflicting complete result vectors")
        vectors[p["source_sha256"]] = vector
        p["regression"] = regression(p, baseline, policy)
    return result, baseline


def stable_key(p):
    return p["generation"], p["source_sha256"], p["id"]


def mean_key(p):
    return -p["mean"], p["regression"]["tail_loss"], *stable_key(p)


def deduplicated(pool):
    by_source = {}
    for p in sorted(pool, key=stable_key):
        by_source.setdefault(p["source_sha256"], p)
    return list(by_source.values())


def family_champions(pool):
    pool = deduplicated(pool)
    if not pool:
        return {}
    return {f: min(pool, key=lambda p: (-p["family_scores"][f], -p["mean"],
                                       p["regression"]["tail_loss"], *stable_key(p)))
            for f in sorted(pool[0]["family_scores"])}


def summary(p):
    return {k: p[k] for k in ("id", "generation", "source_sha256", "island_idx", "mean", "family_scores", "regression")}


def registry(pool, baseline, manifest_sha, policy):
    islands = sorted({p["island_idx"] for p in pool if p["island_idx"] is not None})
    return {"version": VERSION, "manifest_sha256": manifest_sha,
            "baseline": summary(baseline), "mean_leader": summary(min(pool, key=mean_key)),
            "family_champions": {f: summary(p) for f, p in family_champions(pool).items()},
            "islands": {str(i): {f: summary(p) for f, p in family_champions(
                [p for p in pool if p["island_idx"] == i]).items()} for i in islands},
            "profiles": [summary(p) for p in sorted(pool, key=lambda p: (p["generation"], p["id"]))],
            "parent_cycle": policy["parent_cycle"],
            "retention": "derived index; all source code and results remain in programs.sqlite, independent of archive membership"}


def choose(pool, upstream_id, generation, policy, initialized=True):
    if type(generation) is not int or generation < 1:
        raise ValueError("selection needs the actual positive target generation")
    upstream = next((p for p in pool if p["id"] == upstream_id), None)
    if upstream is None:
        raise ValueError("upstream parent lacks complete eligible evidence")
    if type(upstream["island_idx"]) is not int:
        raise ValueError("sampled parent has no island")
    local = deduplicated([p for p in pool if p["island_idx"] == upstream["island_idx"]])
    leader = min(local, key=mean_key)
    requested = policy["parent_cycle"][(generation - 1) % len(policy["parent_cycle"])]
    chosen, mode, families = upstream, requested, []
    if not initialized:
        mode = "bootstrap"
    elif mode == "robust":
        near = [p for p in local if p["mean"] >= leader["mean"] - policy["robust_mean_tolerance"] - 1e-12]
        chosen = min(near, key=lambda p: (p["regression"]["tail_loss"], p["regression"]["max_case_loss"],
                                          -p["mean"], *stable_key(p)))
    elif mode == "specialist":
        champions = family_champions(local)
        alternatives = deduplicated([p for p in champions.values() if p["source_sha256"] != leader["source_sha256"]])
        if alternatives:
            alternatives.sort(key=lambda p: p["source_sha256"])
            chosen = alternatives[((generation - 1) // len(policy["parent_cycle"])) % len(alternatives)]
            families = [f for f, p in champions.items() if p["source_sha256"] == chosen["source_sha256"]]
        else:
            mode = "score_fallback_no_distinct_specialist"
    return chosen, {"version": VERSION, "generation": generation, "requested_mode": requested, "mode": mode,
                    "island_idx": upstream["island_idx"], "upstream_parent": summary(upstream),
                    "selected_parent": summary(chosen), "island_mean_leader": summary(leader),
                    "specialist_families": families, "primary_metric_changed": False}


def selection_text(profile):
    r = profile["regression"]
    return (f"Fixed gen0 baseline: mean F/T={profile['mean']:.9f}; "
            f"mean positive loss on worst {r['tail_count']} cases={r['tail_loss']:.9f}; "
            f"max case loss={r['max_case_loss']:.9f}; regressed cases={r['regressed_cases']}; "
            f"worst family delta F/T={r['worst_family_delta']:+.9f}. "
            "These are selection diagnostics; primary fitness remains mean F/T.")
