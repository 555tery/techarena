#!/usr/bin/env python3
"""Bounded transport benchmark, official checker + toy client, no SEARCH reads."""

import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import queue
import statistics
import tempfile

from fast_harness import build_harness
from fixture_tools import build_tools, write_input
from reference import ROOT, check_reference, digest


def count_raw_reads(buffered: bool) -> dict:
    class CountedRaw(io.RawIOBase):
        def __init__(self, data):
            self.data, self.offset, self.calls = data, 0, 0

        def readable(self):
            return True

        def readinto(self, target):
            self.calls += 1
            count = min(len(target), len(self.data) - self.offset)
            target[:count] = self.data[self.offset:self.offset + count]
            self.offset += count
            return count

    raw, out = CountedRaw(b"123 456\n" * 10000), queue.Queue()
    thread = build_harness(transport="buffered" if buffered else "reference").start_line_reader(raw, out, "read-count")
    thread.join(10)
    if thread.is_alive():
        raise RuntimeError("read-count fixture hung")
    lines = 0
    while out.get_nowait() is not None:
        lines += 1
    result = {"bytes": len(raw.data), "lines": lines, "raw_read_calls": raw.calls}
    raw.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--commands", type=int, default=32768, choices=range(1024, 65537), metavar="1024..65536")
    parser.add_argument("--pairs", type=int, default=5, choices=range(1, 8))
    args = parser.parse_args()
    if args.out.exists():
        parser.error("output exists; refusing to overwrite evidence")
    preservation = check_reference()
    records = {"reference": [], "buffered": [], "selector": []}
    with tempfile.TemporaryDirectory(prefix="pipes-transport-benchmark-") as temporary:
        directory = Path(temporary)
        solver, judge = build_tools(directory)
        test = directory / "generated-transport.in"
        commands = [1 + index % 40 for index in range(args.commands)]
        write_input(test, commands)
        expected_trench = sum(((value + 19) // 20) * 20 for value in commands)
        transcripts = set()
        for pair in range(args.pairs):
            # Alternate order to reduce simple warmup / system-load bias.
            order = ("reference", "buffered", "selector")
            # Rotate positions as well as reversing them across rounds.
            order = order[pair % 3:] + order[:pair % 3]
            if pair % 2:
                order = order[::-1]
            for name in order:
                harness = build_harness(transport=name)
                record = harness.run_case([str(solver), "valid"], judge, test,
                                          directory / f"{pair}-{name}", 5, 180)
                if (record["status"] != "ok" or record["trench_length_m"] != expected_trench
                        or record["solver_cpu_total_s"] >= 5 or record["solver_peak_rss_mb"] >= 256):
                    raise RuntimeError(f"benchmark fixture failed: {record}")
                transcripts.add(digest(Path(record["judge_output_file"])))
                records[name].append({key: record[key] for key in (
                    "wall_orchestration_s", "solver_cpu_total_s", "solver_peak_rss_mb",
                    "interactor_cpu_total_s", "trench_length_m", "kpi", "lower_bound_to_actual_trench_ratio")})
        if len(transcripts) != 1:
            raise RuntimeError("transcripts differ")
        test_sha256 = digest(test)
    medians = {key: statistics.median(record["wall_orchestration_s"] for record in values)
               for key, values in records.items()}
    for index in range(args.pairs):
        for key in ("trench_length_m", "kpi", "lower_bound_to_actual_trench_ratio"):
            if len({records[name][index][key] for name in records}) != 1:
                raise RuntimeError("fixture scores differ")
    if check_reference() != preservation:
        raise RuntimeError("reference changed during benchmark")
    output = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "generated transport fixture, official unchanged checker and append-only toy client; NOT SEARCH-v2 baseline",
        "commands": args.commands, "pairs": args.pairs, "input_sha256": test_sha256,
        "transcript_sha256": next(iter(transcripts)), "records": records,
        "median_wall_s": medians, "median_speedup": medians["reference"] / medians["selector"],
        "buffered_median_speedup": medians["reference"] / medians["buffered"],
        "raw_read_fixture": {"reference": count_raw_reads(False), "buffered": count_raw_reads(True)},
        "support_files_unchanged": len(preservation["checked_files"]),
        "snapshot_sha256": preservation["snapshot_sha256"],
        "implementation_sha256": {name: digest(ROOT / name) for name in
                                  ("fast_harness.py", "selector_transport.py", "reference.py", "evaluator.py", "fixture_tools.py",
                                   "fixtures/protocol_solver.cpp", "benchmark_transport.py")},
        "search_evaluations_started": 0, "models_called": 0,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as stream:
        json.dump(output, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"median_wall_s": medians, "median_speedup": output["median_speedup"],
                      "output": str(args.out.resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
