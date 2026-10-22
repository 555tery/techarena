#!/usr/bin/env python3
"""Serial, resumable comparison against all frozen baseline response hashes."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = HERE.parent / "pipes_current_hybrid_cj_20261020"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "shinka-pipes/evaluator-native"))
import native_harness as nh


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", type=Path, required=True)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    os.environ["cjProcessorNum"] = "1"
    assert not any(x in os.environ for x in ["cjHeapSize", "cjGCThreshold", "cjGCInterval"])
    freeze = json.loads((BASE / "freeze.json").read_text())
    baseline = {
        row["id"]: row
        for row in map(json.loads, (BASE / "records.jsonl").read_text().splitlines())
        if row["method"] == "hybrid_cj"
    }
    for path, digest in freeze["support_sha256"].items():
        assert sha(ROOT / path) == digest
    native = (BASE / freeze["native_binary"]).resolve()
    assert sha(native) == freeze["native_binary_sha256"]
    spec = importlib.util.spec_from_file_location("official_base", ROOT / "tools/pipes_harness.py")
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    # Prioritize the complete Open15 and independent new traps. All cases are
    # still selected by the existing frozen manifest, without score filtering.
    cases = sorted(freeze["cases"], key=lambda c: (
        0 if c["public_number"] is not None else 1 if c["cohort"] == "fresh" else 2,
        c["public_number"] or 0, c["id"],
    ))
    selected = set(json.loads(args.ids.read_text()))
    cases = [c for c in cases if c["id"] in selected]
    assert len(cases) == len(selected)
    output = HERE / "corpus" / args.name
    output.mkdir(parents=True, exist_ok=True)
    identity = dict(
        binary=str(args.binary.resolve()), binary_sha256=sha(args.binary),
        source=str(args.source.resolve()), source_sha256=sha(args.source),
        selected_ids=sorted(selected),
        baseline_freeze_sha256=sha(BASE / "freeze.json"),
        baseline_records_sha256=sha(BASE / "records.jsonl"),
        runner_sha256=sha(__file__), workers=1, cjProcessorNum=1,
        cpu_limit_s=5, memory_limit_mib=256,
        measurement="Whole solver process CPU user+system; macOS arm64; no hard CPU affinity",
    )
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        assert args.resume
        assert json.loads(manifest_path.read_text()) == identity
    else:
        manifest_path.write_text(json.dumps(identity, indent=2) + "\n")
    records = output / "records.jsonl"
    done = {}
    if records.exists():
        assert args.resume
        for line in records.read_text().splitlines():
            row = json.loads(line)
            assert row["id"] not in done
            done[row["id"]] = row
    started = time.monotonic()
    last_print = started
    new_count = 0
    with records.open("a", buffering=1) as sink:
        for case in cases:
            if case["id"] in done:
                continue
            if args.limit is not None and new_count >= args.limit:
                break
            test = (BASE / case["input"]).resolve()
            assert sha(test) == case["input_sha256"]
            base = SimpleNamespace(**original.__dict__)
            base.parse_test = lambda path, meta=case["meta"]: dict(meta)
            destination = output / "runs" / case["id"]
            if destination.exists():
                destination = destination.with_name(case["id"] + "-retry-" + str(time.time_ns()))
            row = nh.run_case(base, [str(args.binary.resolve())], native, test, destination, 5, 240)
            response = Path(row["judge_output_file"])
            row.update(
                id=case["id"], public_number=case["public_number"],
                cohort=case["cohort"], family=case["family"], origin=case["origin"],
                response_sha256=sha(response) if response.exists() else None,
                source_sha256=identity["source_sha256"],
                binary_sha256=identity["binary_sha256"],
            )
            previous = baseline[case["id"]]
            row["response_equal"] = row["response_sha256"] == previous["response_sha256"]
            row["kpi_equal"] = row.get("kpi") == previous["kpi"]
            row["within_limits"] = not nh.failed(row, 5, 256)
            if response.exists():
                packed = response.with_suffix(".txt.gz")
                with response.open("rb") as src, gzip.open(packed, "wb", compresslevel=1) as dst:
                    shutil.copyfileobj(src, dst)
                assert hashlib.sha256(gzip.decompress(packed.read_bytes())).hexdigest() == row["response_sha256"]
                response.unlink()
                row["judge_output_file"] = str(packed)
            sink.write(json.dumps(row, separators=(",", ":")) + "\n")
            done[case["id"]] = row
            new_count += 1
            progress = dict(
                completed=len(done), total=len(cases), new_runs=new_count,
                elapsed_this_run_s=time.monotonic() - started,
                mismatches=sum(not r["response_equal"] or not r["kpi_equal"] for r in done.values()),
                failures=sum(r["status"] != "ok" for r in done.values()),
                resource_failures=sum(not r["within_limits"] for r in done.values()),
                max_cpu_s=max((r.get("solver_cpu_total_s") or 0) for r in done.values()),
                max_rss_mib=max((r.get("solver_peak_rss_mb") or 0) for r in done.values()),
                latest=dict(id=case["id"], public_number=case["public_number"],
                            status=row["status"], response_equal=row["response_equal"]),
            )
            temporary = output / "progress.tmp"
            temporary.write_text(json.dumps(progress, indent=2) + "\n")
            temporary.replace(output / "progress.json")
            if time.monotonic() - last_print > 30 or not row["within_limits"] or len(done) == len(cases):
                print(json.dumps(progress), flush=True)
                last_print = time.monotonic()
            if row["status"] != "ok" or not row["response_equal"] or not row["kpi_equal"]:
                raise SystemExit("Correctness/parity failure")
    print("CHECKED", len(done), "of", len(cases), flush=True)


if __name__ == "__main__":
    main()
