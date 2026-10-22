"""Small, deterministic research memory; no model calls or candidate execution."""

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import uuid

VERSION = "research-memory-v1"
PROMPT_LIMIT = 9000


def code_hash(code):
    # Deliberately no whitespace/comment/identifier normalization.
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


def read_programs(run):
    """Read one consistent SQLite snapshot, including WAL, without writing to it."""
    path = Path(run) / "programs.sqlite"
    if not path.is_file():
        raise ValueError("research memory requires the initialized run database")
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT id,generation,parent_id,code,correct,combined_score,island_idx,"
                          "metadata,private_metrics FROM programs ORDER BY generation,id").fetchall()
    programs = []
    for row in rows:
        item = dict(row)
        item["metadata"] = json.loads(item["metadata"] or "{}")
        item["private_metrics"] = json.loads(item["private_metrics"] or "{}")
        item["source_sha256"] = code_hash(item.pop("code"))
        programs.append(item)
    return programs


def unique_programs(programs):
    """Collapse island copies, while retaining separately evaluated generations."""
    seen, result = set(), []
    for p in programs:
        key = (p["generation"], p["source_sha256"])
        if key not in seen:
            seen.add(key)
            result.append(p)
    return result


def exact_duplicate(code, programs):
    sha = code_hash(code)
    return next((p for p in programs if p["correct"] and p["source_sha256"] == sha), None)


def checked_cases(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("missing complete per-case research evidence")
    result = {}
    for row in rows:
        if row["id"] in result:
            raise ValueError("duplicate research case")
        if not all(math.isfinite(row[k]) for k in ("kpi", "trench", "bound", "final")):
            raise ValueError("nonfinite research evidence")
        if (row["trench"] < row["bound"] or row["bound"] <= 0 or row["trench"] % 20
                or row["final"] < 0 or row["final"] > row["bound"]
                or not math.isclose(row["kpi"], row["final"] / row["trench"], abs_tol=1e-12, rel_tol=0)):
            raise ValueError("inconsistent research evidence")
        result[row["id"]] = row
    return result


def paired(candidate_rows, reference_rows):
    """Positive delta_score / negative delta_trench means an improvement."""
    candidate, reference = checked_cases(candidate_rows), checked_cases(reference_rows)
    if candidate.keys() != reference.keys():
        raise ValueError("cannot compare different case coverage")
    changes, grouped = [], defaultdict(list)
    for key, row in candidate.items():
        old = reference[key]
        if any(row[k] != old[k] for k in ("family", "bound", "final", "test_sha256")):
            raise ValueError("cannot compare different inputs or volume metadata")
        change = {"id": key, "family": row["family"], "delta_score": row["kpi"] - old["kpi"],
                  "delta_trench": row["trench"] - old["trench"]}
        changes.append(change)
        grouped[row["family"]].append(change["delta_score"])
    families = [{"family": f, "delta_score": math.fsum(values) / len(values)}
                for f, values in grouped.items()]
    families.sort(key=lambda r: (r["delta_score"], r["family"]))
    return {"delta_score": math.fsum(r["delta_score"] for r in families) / len(families),
            "improved": sum(r["delta_trench"] < 0 for r in changes),
            "regressed": sum(r["delta_trench"] > 0 for r in changes),
            "tied": sum(r["delta_trench"] == 0 for r in changes),
            "family_deltas": families,
            "largest_regressions": sorted((r for r in changes if r["delta_score"] < 0),
                                          key=lambda r: (r["delta_score"], r["id"]))[:8],
            "largest_gains": sorted((r for r in changes if r["delta_score"] > 0),
                                    key=lambda r: (-r["delta_score"], r["id"]))[:8]}


def comparison_text(label, comparison):
    c = comparison
    lines = [f"Against {label}: delta mean F/T={c['delta_score']:+.9f}; "
             f"improved/regressed/tied={c['improved']}/{c['regressed']}/{c['tied']}."]
    families = c["family_deltas"]
    chosen = sorted(families, key=lambda r: -abs(r["delta_score"]))[:6]
    lines += [f"family={r['family']} delta_F/T={r['delta_score']:+.9f}" for r in chosen]
    for title, rows in (("Regressions", c["largest_regressions"]), ("Gains", c["largest_gains"])):
        lines.append(title + ":")
        lines += [f"{r['id']}: delta_F/T={r['delta_score']:+.9f}, delta_T={r['delta_trench']:+d}"
                  for r in rows[:4]]
    return "\n".join(lines)


def enrich_metrics(metrics, context, programs, manifest_sha):
    """Only add diagnostics. Never replace fitness, correctness or resource gates."""
    by_id = {p["id"]: p for p in programs}
    if metrics["manifest_sha256"] != manifest_sha:
        raise ValueError("research feedback corpus mismatch")
    comparisons, texts = {}, []
    for label in ("parent", "leader"):
        identity = context[label]
        if identity is None:
            continue
        ref = by_id.get(identity["id"])
        if not ref or ref["source_sha256"] != identity["source_sha256"] or not ref["correct"]:
            raise ValueError("research reference is missing, changed or incorrect")
        private = ref["private_metrics"]
        if private.get("research_manifest_sha256") != manifest_sha:
            raise ValueError("reference belongs to another corpus")
        comparison = paired(metrics["private"]["research_cases"], private["research_cases"])
        if not math.isclose(comparison["delta_score"], metrics["combined_score"] - ref["combined_score"],
                            abs_tol=1e-12, rel_tol=0):
            raise ValueError("paired feedback disagrees with saved scalar score")
        comparisons[label] = {"generation": ref["generation"], **comparison}
        texts.append(comparison_text(f"{label} gen{ref['generation']}", comparison))
    metrics["research_comparisons"] = comparisons
    metrics["private"]["research_comparisons"] = comparisons
    metrics["text_feedback"] += "\n\nPAIRED SEARCH EVIDENCE\n" + "\n\n".join(texts)
    return metrics


def identity(program):
    return {k: program[k] for k in ("id", "generation", "source_sha256")} if program else None


def proposal_context(programs, parent_id, generation):
    parent = next((p for p in programs if p["id"] == parent_id), None)
    if not parent:
        raise ValueError("sampled parent absent from research snapshot")
    eligible = [p for p in programs if p["correct"] and p["generation"] < generation]
    leader = max(eligible, key=lambda p: (p["combined_score"], -p["generation"]), default=None)
    return {"version": VERSION, "generation": generation, "parent": identity(parent),
            "leader": identity(leader), "leader_selection": "best completed at proposal time"}


def memory(programs):
    by_id = {p["id"]: p for p in programs}
    cards, signatures = [], defaultdict(list)
    for p in unique_programs(programs):
        meta = p["metadata"]
        parent = by_id.get(p["parent_id"])
        comparisons = p["private_metrics"].get("research_comparisons", {})
        rows = p["private_metrics"].get("research_cases")
        if p["correct"] and rows:
            vector = [(key, row["test_sha256"], row["trench"])
                      for key, row in sorted(checked_cases(rows).items())]
            signature = hashlib.sha256(json.dumps(vector).encode()).hexdigest()
            signatures[signature].append(p["generation"])
        cards.append({"generation": p["generation"], "source_sha256": p["source_sha256"],
                      "parent_generation": parent["generation"] if parent else None,
                      "name": str(meta.get("patch_name") or "unnamed")[:120],
                      "claimed_mechanism": str(meta.get("patch_description") or "")[:600],
                      "correct": bool(p["correct"]), "score": p["combined_score"],
                      "delta_to_parent": p["combined_score"] - parent["combined_score"]
                      if p["correct"] and parent and parent["correct"] else None,
                      "comparison": comparisons.get("parent")})
    groups = sorted((values for values in signatures.values() if len(values) > 1), key=len, reverse=True)
    return {"version": VERSION, "corpus": "search-v3.1", "fitness": "F/T", "cards": cards,
            "same_result_vector_groups": groups}


def prompt_memory(ledger, prior, parent_generation):
    lines = ["RESEARCH MEMORY — measured evidence, descriptions are unverified author claims.",
             "Past failures are not universal bans. Explain changed behavior/assumptions when retrying.",
             "Do not rename an already tested policy and present it as a new mechanism.",
             "No equivalence is inferred from a shared score or a shared finite case vector."]
    # A bounded mechanism summary prevents an old repeated failure disappearing
    # merely because recent generations filled the prompt window.
    groups = defaultdict(list)
    for card in ledger["cards"]:
        groups[card["name"]].append(card)
    lines.append("CURRENT SEARCH-v3.1 (F/T):")
    for group in ledger["same_result_vector_groups"][:3]:
        lines.append(f"Same complete saved trench vector: generations {group}. Advisory only, not equivalence.")
    for name, cards in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:12]:
        valid = [c["score"] for c in cards if c["correct"]]
        scores = f"score_range={min(valid):.9f}..{max(valid):.9f}" if valid else "no correct result"
        lines.append(f"{name}: attempts={len(cards)}; {scores}")
    cards = ledger["cards"]
    important = sorted(cards, key=lambda c: (c["generation"] == parent_generation,
                                            c["correct"] and c["score"] == max(
                                                (x["score"] for x in cards if x["correct"]), default=-1),
                                            c["generation"]), reverse=True)[:8]
    for c in important:
        delta = "n/a" if c["delta_to_parent"] is None else f"{c['delta_to_parent']:+.9f}"
        lines.append(f"gen{c['generation']} {c['name']}; correct={c['correct']}; "
                     f"parent={c['parent_generation']}; delta_F/T={delta}; claim={c['claimed_mechanism'][:220]}")
        comparison = c["comparison"]
        if comparison:
            lines.append(f"  improved/regressed/tied={comparison['improved']}/"
                         f"{comparison['regressed']}/{comparison['tied']}")
            lines += [f"  regression {r['id']}: delta_F/T={r['delta_score']:+.9f}"
                      for r in comparison["largest_regressions"][:2]]
    lines.append("HISTORICAL SEARCH-v2 (different inputs AND B/T objective; not a v3.1 ranking):")
    lines.extend(prior["prompt_lines"])
    result = "\n".join(lines)
    if len(result) > PROMPT_LIMIT:
        result = result[:PROMPT_LIMIT] + "\n[Memory shortened; complete ledger remains in run/research-memory.json.]"
    return result
