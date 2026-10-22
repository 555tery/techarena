#!/usr/bin/env python3
"""Read-only replay of the saved baseline prefix for the barrier bound."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[2]
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "shinka-pipes" / "search-v3-1"))
from usage_guard import gate  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def next_int(lines, what: str) -> int:
    for line in lines:
        value = line.strip()
        if value:
            return int(value)
    raise ValueError(f"unexpected EOF while reading {what}")


def verify(input_path: Path, output_path: Path, manifest_path: Path,
           summary_path: Path, audit_path: Path, prefix_n: int = 100_000,
           cut: int = 8, dig_section_m: int = 20) -> dict:
    manifest = json.loads(manifest_path.read_text())
    summary = json.loads(summary_path.read_text())
    prior = json.loads(audit_path.read_text())
    input_hash = sha256(input_path)
    output_hash = sha256(output_path)
    expected_hash = manifest["input_sha256"][str(input_path.resolve())]
    source_path = Path(manifest["source"])
    source_hash = sha256(source_path)
    compiled_solver = Path(manifest["compile_command"][-1])
    compiled_solver_hash = sha256(compiled_solver)
    if input_hash != expected_hash:
        raise ValueError("input SHA-256 does not match the saved evaluator manifest")
    if source_hash != manifest["source_sha256"]:
        raise ValueError("baseline source SHA-256 does not match the saved evaluator manifest")
    if compiled_solver_hash != manifest["solver_sha256"]:
        raise ValueError("saved solver binary SHA-256 does not match the evaluator manifest")
    if sha256(summary_path) != manifest["summary_sha256"]:
        raise ValueError("saved summary SHA-256 does not match the evaluator manifest")
    if manifest["status"] != "completed" or not manifest["correct"]:
        raise ValueError("saved baseline evaluation was not a completed correct run")
    if manifest["source_sha256"] != "c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c":
        raise ValueError("saved baseline source hash differs from the specified baseline")

    prefix_trench = 0
    pid = 0
    live_sizes: dict[int, int] = {}
    starts: dict[int, int] = {}
    prefix_live_sizes = None
    prefix_positions = None
    declared_count = None
    with input_path.open("r", encoding="ascii") as input_stream, output_path.open("r", encoding="ascii") as output_stream:
        lines = iter(input_stream)
        header = next(lines).split()
        if len(header) == 2:
            weight, declared_count = float(header[0]), int(header[1])
        elif len(header) == 1:
            weight = float(header[0])
            declared_count = next_int(lines, "operation count")
        else:
            raise ValueError("unrecognized input header")
        if declared_count < prefix_n:
            raise ValueError("prefix exceeds declared operation count")

        for index in range(1, declared_count + 1):
            command = next_int(lines, f"command {index}")
            if command == 0:
                raise ValueError(f"unexpected sentinel inside declared operations at {index}")
            if command > 0:
                pid += 1
                live_sizes[pid] = command
                if index <= prefix_n:
                    reply = next(output_stream).split()
                    if len(reply) != 2:
                        raise ValueError(f"bad allocation response at operation {index}")
                    digs, start = map(int, reply)
                    if digs < 0 or start < 0:
                        raise ValueError(f"negative allocation response at operation {index}")
                    prefix_trench += digs * dig_section_m
                    if start + command > prefix_trench:
                        raise ValueError(f"allocation outside trench at operation {index}")
                    # The saved run was already accepted by the official native
                    # checker (manifest status/correctness are checked above).
                    # Keep this replay linear: collision checking every new
                    # interval against all live intervals would be quadratic.
                    starts[pid] = start
            else:
                deleted_pid = -command
                if deleted_pid not in live_sizes:
                    raise ValueError(f"delete of inactive PID {deleted_pid} at operation {index}")
                if index <= prefix_n:
                    reply = next(output_stream).split()
                    if len(reply) != 1 or int(reply[0]) != starts[deleted_pid]:
                        raise ValueError(f"wrong deletion response at operation {index}")
                    starts.pop(deleted_pid)
                live_sizes.pop(deleted_pid)
            if index == prefix_n:
                prefix_live_sizes = dict(live_sizes)
                prefix_positions = dict(starts)

        # The protocol file may append a zero sentinel after the declared trace.
        trailing = [line.strip() for line in lines if line.strip()]
        if trailing not in ([], ["0"]):
            raise ValueError("unexpected data after declared operations")

    if prefix_live_sizes is None or prefix_positions is None:
        raise AssertionError("prefix snapshot was not captured")
    final_ids = set(live_sizes)
    prefix_ids = set(prefix_live_sizes)
    prefix_survivor_ids = prefix_ids & final_ids
    survivors = sorted((prefix_positions[pipe_id], prefix_live_sizes[pipe_id], pipe_id)
                       for pipe_id in prefix_survivor_ids)

    bounded_gap_m = 0
    gap_count = 0
    previous_end = 0
    for start, size, _pipe_id in survivors:
        gap = start - previous_end
        if gap < 0:
            raise ValueError("prefix survivor intervals overlap")
        if gap < cut:
            bounded_gap_m += gap
            gap_count += 1
        previous_end = start + size

    new_final_small_volume = sum(
        size for pipe_id, size in live_sizes.items()
        if pipe_id not in prefix_ids and size < cut
    )
    unfillable_lower_bound = max(0, bounded_gap_m - new_final_small_volume)
    final_volume = sum(live_sizes.values())
    raw_lower_bound = final_volume + unfillable_lower_bound
    trench_lower_bound = math.ceil(raw_lower_bound / dig_section_m) * dig_section_m

    case15 = next(row for row in summary["records"] if row["case"] == "15")
    if str(output_path.resolve()) != case15["judge_output_file"]:
        raise ValueError("saved output path is not the case-15 output referenced by summary")
    observed_final_trench = case15["trench_length_m"]
    new_final_size_histogram: dict[str, int] = {}
    for pipe_id, size in live_sizes.items():
        if pipe_id not in prefix_ids:
            key = str(size)
            new_final_size_histogram[key] = new_final_size_histogram.get(key, 0) + 1
    new_final_size_histogram = dict(sorted(new_final_size_histogram.items(), key=lambda item: int(item[0])))
    score_ceiling = summary["weighted_score_sum"] - case15["weighted_score"] + (
        case15["official_weight"] * final_volume / trench_lower_bound
    )

    report = {
        "read_only_replay": True,
        "quota_gate": "passed before processing",
        "input_sha256": input_hash,
        "saved_output_sha256": output_hash,
        "baseline_source_sha256": source_hash,
        "compiled_solver_sha256": compiled_solver_hash,
        "summary_sha256_verified": True,
        "prefix_operations_replayed": prefix_n,
        "declared_operation_count": declared_count,
        "prefix_trench_m_replayed": prefix_trench,
        "prefix_active_count_replayed": len(prefix_live_sizes),
        "final_survivor_count_replayed_from_eof_labels": len(final_ids),
        "prefix_survivors_immovable_count": len(prefix_survivor_ids),
        "new_final_pipe_size_histogram_recomputed": new_final_size_histogram,
        "cut_m": cut,
        "bounded_gap_m_recomputed_excluding_tail": bounded_gap_m,
        "bounded_gap_segments_count": gap_count,
        "new_final_pipe_volume_below_cut_m_recomputed": new_final_small_volume,
        "unfillable_gap_lower_bound_m_recomputed": unfillable_lower_bound,
        "final_occupied_volume_m_recomputed": final_volume,
        "raw_trench_lower_bound_m_before_20m_rounding": raw_lower_bound,
        "conditional_trench_lower_bound_m_recomputed": trench_lower_bound,
        "saved_baseline_final_trench_m": observed_final_trench,
        "remaining_possible_saving_at_same_prefix_m": observed_final_trench - trench_lower_bound,
        "max_whole_score_at_same_prefix_recomputed": score_ceiling,
        "matches_root_audit": {
            "prefix_T": prefix_trench == prior["prefix_T"],
            "prefix_active_count": len(prefix_live_sizes) == prior["prefix_active_count"],
            "final_prefix_survivors": len(prefix_survivor_ids) == prior["final_prefix_survivor_count"],
            "bounded_gap": bounded_gap_m == prior["best_capacity_bound"]["bounded_gap_m"],
            "new_final_small_volume": new_final_small_volume == prior["best_capacity_bound"]["new_final_small_pipe_volume_m"],
            "new_final_size_histogram": new_final_size_histogram == prior["new_final_pipe_size_histogram"],
            "unfillable": unfillable_lower_bound == prior["best_capacity_bound"]["unfillable_m_lower_bound"],
            "final_volume": final_volume == prior["final_volume"],
            "trench_bound": trench_lower_bound == prior["continuation_trench_lower_bound_from_immutable_survivor_barriers"],
            "baseline_final_trench": observed_final_trench == prior["observed_final_T"],
            "remaining_saving": observed_final_trench - trench_lower_bound == prior["remaining_possible_saving_at_same_prefix_m"],
        },
        "interpretation_limit": (
            "This is a hindsight bound conditional on this saved baseline prefix layout and EOF survivor labels; "
            "it is neither an unconditional optimum nor a new solver/evaluator result."
        ),
    }
    if not all(report["matches_root_audit"].values()):
        raise AssertionError(f"independent replay disagrees with audit: {report['matches_root_audit']}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "data/pipes/open/15.in")
    parser.add_argument("--output", type=Path, default=CAMPAIGN / "evaluations/baseline-open15/harness/runs/15/judge_output.txt")
    parser.add_argument("--manifest", type=Path, default=CAMPAIGN / "evaluations/baseline-open15/manifest.json")
    parser.add_argument("--summary", type=Path, default=CAMPAIGN / "evaluations/baseline-open15/harness/summary.json")
    parser.add_argument("--audit", type=Path, default=CAMPAIGN / "branches/immutable_barriers/audit.json")
    parser.add_argument("--out", type=Path, default=CAMPAIGN / "branches/immutable_barriers/independent_replay.json")
    parser.add_argument("--prefix", type=int, default=100_000)
    parser.add_argument("--cut", type=int, default=8)
    args = parser.parse_args()
    gate(CAMPAIGN, max_age_seconds=60)
    result = verify(args.input, args.output, args.manifest, args.summary,
                    args.audit, args.prefix, args.cut)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
