"""One-shot, input-only extension. Keeps the old 128 inputs and all stress artifacts."""

import json
from pathlib import Path
import sys

from generate import FAMILIES, MAIN, V2, generate_case, make_specs, overview
from micro import MICRO_FAMILIES
from support import ROOT, digest, verify_dependencies

ARCHIVE = ROOT / "revisions/pre-micro-r1"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def prepare_micro():
    if (ROOT / "runs").exists() and any((ROOT / "runs").iterdir()):
        raise ValueError("refusing to revise a corpus with an existing run")
    old_path = ARCHIVE / "task/data/search/manifest.json"
    if digest(MAIN / "manifest.json") != digest(old_path):
        raise ValueError("expected the archived, unextended 128-case main manifest")
    old = json.loads(old_path.read_text())
    if old["case_count"] != 128:
        raise ValueError("unexpected predecessor")
    stress_path = ROOT / "stress/data/manifest.json"
    if digest(stress_path) != digest(ARCHIVE / "stress/data/manifest.json"):
        raise ValueError("diagnostic stress changed")
    verify_dependencies(include_stress=True)
    for case in old["cases"]:
        if digest(MAIN / case["file"]) != case["sha256"]:
            raise ValueError("retained input changed")
    stress = json.loads(stress_path.read_text())
    hashes = {c["sha256"] for m in (old, stress) for c in m["cases"]}
    seeds = {c["seed"] for m in (old, stress) for c in m["cases"]}
    # Existing search metadata only; held-out inputs and candidate results are not read.
    for rel in ("task-synthetic/data/search/manifest.json", "search-v2/task/data/search/manifest.json",
                "search-v3/task/data/search/manifest.json"):
        prior = json.loads((ROOT.parent / rel).read_text())
        hashes.update(c["sha256"] for c in prior["cases"])
        seeds.update(c["seed"] for c in prior["cases"])
    stage = ROOT / "preparation-staging/micro-r1"
    stage.mkdir(parents=True, exist_ok=False)
    parser = V2.parser_module()
    added = []
    for spec in make_specs("search"):
        if spec["family"] not in MICRO_FAMILIES:
            continue
        commands, actual, stats = generate_case(spec)
        path = stage / (spec["id"] + ".in")
        path.write_text("1\n" + str(len(commands)) + "\n" + "\n".join(map(str, commands)) + "\n0\n", encoding="ascii")
        sha = digest(path)
        if sha in hashes or actual["seed"] in seeds:
            raise ValueError("duplicate micro input or seed")
        hashes.add(sha)
        seeds.add(actual["seed"])
        parsed = parser.parse_test(path)
        expected = {"operation_count": len(commands), "weight": 1., "test_sha256": sha,
                    "peak_live_pipe_length_m": stats["peak_live_volume"],
                    "final_occupied_length_m": stats["final_live_volume"],
                    "minimum_trench_lower_bound_m": stats["volume_lower_bound"]}
        if any(parsed[k] != v for k, v in expected.items()):
            raise ValueError("independent parser disagrees on micro input")
        added.append({**actual, "file": path.name, "sha256": sha, "stats": stats})
    if len(added) != 24:
        raise ValueError("expected exactly 24 additional cases")
    cases = old["cases"] + added
    manifest = {**old, "corpus_revision": "micro-r1", "case_count": len(cases),
                "families": list(FAMILIES), "generator_sha256": digest(ROOT / "generate.py"),
                "micro_generator_sha256": digest(ROOT / "micro.py"),
                "micro_design_sha256": digest(ROOT / "micro-design.json"),
                "retained_predecessor": {"manifest_sha256": digest(old_path), "cases": 128,
                                         "archive": "revisions/pre-micro-r1/", "input_bytes_unchanged": True,
                                         "generator_sha256": old["generator_sha256"]},
                "input_conditioning": "fixed seed construction and legal structure; no candidate or Open15 matching",
                "python_version": sys.version.split()[0], "cases": cases}
    write_json(stage / "manifest.json", manifest)
    for case in added:
        target = MAIN / case["file"]
        if target.exists():
            raise FileExistsError(target)
    for case in added:
        (stage / case["file"]).rename(MAIN / case["file"])
    # The old manifest and full support were copied to ARCHIVE before any revision.
    (stage / "manifest.json").replace(MAIN / "manifest.json")
    protocol = json.loads((ROOT / "protocol.json").read_text())
    protocol.update(corpus_revision="micro-r1", case_count=152, family_count=38, family_weights="1/38",
                    design_policy="64 retained broad prior + 64 retained expanded + 24 micro cases",
                    micro_design_sha256=digest(ROOT / "micro-design.json"))
    protocol["manifest_sha256"]["search"] = digest(MAIN / "manifest.json")
    protocol["planned_main_regimes"]["micro"] = 24
    write_json(ROOT / "protocol.json", protocol)
    report = json.loads((ARCHIVE / "preparation.json").read_text())
    report.update(corpus_revision="micro-r1", search={**overview(cases), "manifest_sha256": digest(MAIN / "manifest.json")},
                  independent_parser_cases=24, retained_previously_parsed_cases=192,
                  generator_sha256=digest(ROOT / "generate.py"), micro_generator_sha256=digest(ROOT / "micro.py"),
                  protocol_sha256=digest(ROOT / "protocol.json"),
                  previous_preparation="revisions/pre-micro-r1/preparation.json",
                  retained_main_input_hashes_verified=128, stress_manifest_unchanged=True)
    report["micro"] = overview(added)
    write_json(ROOT / "preparation.json", report)
    print(json.dumps({"status": "prepared_not_run", "main_cases": 152, "families": 38,
                      "added": 24, "retained": 128, "stress_changed": False,
                      "candidate_evaluations": 0, "micro": overview(added)}, indent=2))


if __name__ == "__main__":
    prepare_micro()
