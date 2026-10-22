#!/usr/bin/env python3
"""Freeze new candidates and validated inputs without looking at fresh results."""
import hashlib
import importlib.util
import json
import platform
import shutil
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / "prototypes/pipes_all2537_comparison_20261020"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert not (HERE / "freeze.json").exists()
    protocol = json.loads((HERE / "protocol.json").read_text())
    previous = json.loads((OLD / "freeze.json").read_text())
    old_audit = json.loads((OLD / "final_audit.json").read_text())
    assert sha(OLD / "freeze.json") == old_audit["artifact_sha256"]["freeze.json"]
    fresh_path = HERE / "fresh/manifest.json"
    assert sha(fresh_path) == protocol["corpus"]["fresh_manifest_sha256"]
    fresh = json.loads(fresh_path.read_text())
    spec = importlib.util.spec_from_file_location("parser", ROOT / "tools/pipes_harness.py")
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    methods = []
    old_online = next(m for m in previous["methods"] if m["id"] == "online_cj")
    assert sha(OLD / old_online["source"]) == old_online["source_sha256"]
    assert sha(OLD / old_online["binary"]) == old_online["binary_sha256"]
    for name, source, binary in [
        ("online_cj", OLD / old_online["source"], OLD / old_online["binary"]),
        ("hybrid_cpp", HERE / "cpp/solution.cpp", HERE / "cpp/solution"),
        ("hybrid_cj", HERE / "release/solution.cj", HERE / "bin/hybrid-cj"),
    ]:
        folder = HERE / "methods" / name
        folder.mkdir(parents=True)
        local_source = folder / source.name
        local_binary = folder / "solver"
        shutil.copy2(source, local_source)
        shutil.copy2(binary, local_binary)
        methods.append(dict(id=name, label=name, original_source=str(source.relative_to(ROOT)),
                            source=str(local_source.relative_to(HERE)), source_sha256=sha(source),
                            binary=str(local_binary.relative_to(HERE)), binary_sha256=sha(binary)))
    cj_build = json.loads((HERE / "bin/hybrid-cj.build.json").read_text())
    assert cj_build["source_sha256"]["solution.cj"] == methods[2]["source_sha256"]
    assert cj_build["binary_sha256"] == methods[2]["binary_sha256"]
    cases = []
    for old in previous["cases"]:
        c = dict(old, cohort="archive", family=old["source_group"], name=old["id"])
        c["input"] = str((OLD / old["input"]).relative_to(HERE.parent.parent))
        c["input"] = str(Path("../pipes_all2537_comparison_20261020") / old["input"])
        assert sha(HERE / c["input"]) == c["input_sha256"]
        cases.append(c)
    for f in fresh["cases"]:
        path = HERE / "fresh" / f["path"]
        assert sha(path) == f["sha256"]
        meta = parser.parse_test(path)
        assert meta == f["parser_validation"]
        cases.append(dict(id=f["canonical_sha256"], selected=False, public_number=None,
                          cohort="fresh", family=f["family"], kind=f["kind"], name=f["name"],
                          origin=str(path.relative_to(ROOT)), source_group=f"fresh/{f['kind']}/{f['family']}",
                          input=str(path.relative_to(HERE)), input_sha256=f["sha256"], meta=meta))
    assert len(cases) == 2637 and len({c["id"] for c in cases}) == 2637
    # Same predeclared, outcome-independent order for all methods; rotate method order.
    cases.sort(key=lambda c: c["id"])
    native = OLD / previous["native_binary"]
    freeze = dict(created_unix=time.time(), methods=methods, cases=cases,
                  protocol_sha256=sha(HERE / "protocol.json"),
                  old_freeze_sha256=sha(OLD / "freeze.json"),
                  fresh_manifest_sha256=sha(fresh_path), host=platform.platform(),
                  machine=platform.machine(), cpu_limit_s=5, memory_limit_mib=256,
                  response_timeout_s=5, wall_timeout_s=240, workers=1,
                  runtime_environment={"cjProcessorNum": "1"}, hard_cpu_affinity=False,
                  native_windows_tested=False,
                  native_binary="../pipes_all2537_comparison_20261020/" + previous["native_binary"],
                  native_binary_sha256=sha(native), support_sha256=previous["support_sha256"],
                  provenance=dict(cj_source_manifest_sha256=sha(HERE / "cj_source_manifest.json"),
                                  cpp_build_sha256=sha(HERE / "cpp/build.json"),
                                  cj_build_sha256=sha(HERE / "bin/hybrid-cj.build.json"),
                                  smoke_sha256=sha(HERE / "smoke.json")))
    for name, expected in freeze["support_sha256"].items():
        assert sha(ROOT / name) == expected
    (HERE / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    for m in methods:
        (HERE / m["source"]).chmod(0o444)
        (HERE / m["binary"]).chmod(0o555)
    (HERE / "freeze.json").chmod(0o444)
    print(json.dumps({"cases": len(cases), "methods": len(methods),
                      "runs": len(cases) * len(methods), "freeze_sha256": sha(HERE / "freeze.json")}))

if __name__ == "__main__":
    main()
