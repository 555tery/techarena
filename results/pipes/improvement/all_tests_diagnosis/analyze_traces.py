#!/usr/bin/env python3
"""Replay exact final Pipes traces and quantify volume bound and fragmentation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "results/pipes/final/solution.cpp"
EXPECTED_SOURCE_SHA = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
BIN = ROOT / "results/pipes/final/bin/solution"
INTERACTOR = ROOT / "results/pipes/final/bin/interactor"
HARNESS = ROOT / "tools/pipes_harness.py"
DATA = ROOT / "data/pipes/open"
TRACE_ROOT = ROOT / "results/pipes/final/open-run-size-cohort-lanes"
SUMMARY = TRACE_ROOT / "summary.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def splitmix64(x: int) -> int:
    x = (x + 0x9E3779B97F4A7C15) & ((1 << 64) - 1)
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & ((1 << 64) - 1)
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & ((1 << 64) - 1)
    return x ^ (x >> 31)


class GapNode:
    __slots__ = ("start", "end", "priority", "left", "right", "count", "max_len")

    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end
        self.priority = splitmix64(start)
        self.left: GapNode | None = None
        self.right: GapNode | None = None
        self.count = 1
        self.max_len = end - start


def _count(node: GapNode | None) -> int:
    return node.count if node else 0


def _max_len(node: GapNode | None) -> int:
    return node.max_len if node else 0


def _pull(node: GapNode) -> None:
    node.count = 1 + _count(node.left) + _count(node.right)
    node.max_len = max(node.end - node.start, _max_len(node.left), _max_len(node.right))


def _merge(left: GapNode | None, right: GapNode | None) -> GapNode | None:
    if left is None:
        return right
    if right is None:
        return left
    if left.priority < right.priority:
        left.right = _merge(left.right, right)
        _pull(left)
        return left
    right.left = _merge(left, right.left)
    _pull(right)
    return right


def _split(root: GapNode | None, key: int) -> tuple[GapNode | None, GapNode | None]:
    if root is None:
        return None, None
    if root.start < key:
        a, b = _split(root.right, key)
        root.right = a
        _pull(root)
        return root, b
    a, b = _split(root.left, key)
    root.left = b
    _pull(root)
    return a, root


def _insert(root: GapNode | None, node: GapNode) -> GapNode:
    if root is None:
        return node
    if node.priority < root.priority:
        node.left, node.right = _split(root, node.start)
        _pull(node)
        return node
    if node.start < root.start:
        root.left = _insert(root.left, node)
    elif node.start > root.start:
        root.right = _insert(root.right, node)
    else:
        raise ValueError(f"duplicate free-gap start {node.start}")
    _pull(root)
    return root


def _erase(root: GapNode | None, key: int) -> tuple[GapNode | None, GapNode | None]:
    if root is None:
        return None, None
    if key == root.start:
        removed = root
        joined = _merge(root.left, root.right)
        removed.left = removed.right = None
        return joined, removed
    if key < root.start:
        root.left, removed = _erase(root.left, key)
    else:
        root.right, removed = _erase(root.right, key)
    if removed is not None:
        _pull(root)
    return root, removed


def _predecessor(root: GapNode | None, key: int, inclusive: bool = True) -> GapNode | None:
    best = None
    while root:
        if root.start < key or (inclusive and root.start == key):
            best = root
            root = root.right
        else:
            root = root.left
    return best


def _lower_bound(root: GapNode | None, key: int) -> GapNode | None:
    best = None
    while root:
        if root.start >= key:
            best = root
            root = root.left
        else:
            root = root.right
    return best


def _inorder(root: GapNode | None, out: list[tuple[int, int]]) -> None:
    if root is None:
        return
    _inorder(root.left, out)
    out.append((root.start, root.end))
    _inorder(root.right, out)


class FreeIntervals:
    def __init__(self) -> None:
        self.root: GapNode | None = None
        self.total = 0
        self.small_counts = {4: 0, 10: 0, 20: 0, 40: 0}
        self.small_volume = {4: 0, 10: 0, 20: 0, 40: 0}

    def _track(self, start: int, end: int, delta: int) -> None:
        length = end - start
        self.total += delta * length
        for threshold in self.small_counts:
            if length <= threshold:
                self.small_counts[threshold] += delta
                self.small_volume[threshold] += delta * length

    def erase(self, start: int) -> tuple[int, int]:
        self.root, node = _erase(self.root, start)
        if node is None:
            raise ValueError(f"free gap {start} was absent")
        self._track(node.start, node.end, -1)
        return node.start, node.end

    def insert_raw(self, start: int, end: int) -> None:
        if start >= end:
            return
        self.root = _insert(self.root, GapNode(start, end))
        self._track(start, end, +1)

    def add(self, start: int, end: int) -> None:
        if start >= end:
            return
        prev = _predecessor(self.root, start, inclusive=True)
        if prev is not None and prev.end >= start:
            pstart, pend = self.erase(prev.start)
            start = pstart
            end = max(end, pend)
        while True:
            nxt = _lower_bound(self.root, start)
            if nxt is None or nxt.start > end:
                break
            nstart, nend = self.erase(nxt.start)
            end = max(end, nend)
        self.insert_raw(start, end)

    def consume(self, start: int, end: int) -> None:
        node = _predecessor(self.root, start, inclusive=True)
        if node is None or node.start > start or node.end < end:
            raise ValueError(f"placement [{start},{end}) not inside one free interval")
        gs, ge = self.erase(node.start)
        self.add(gs, start)
        self.add(end, ge)

    @property
    def count(self) -> int:
        return _count(self.root)

    @property
    def max_len(self) -> int:
        return _max_len(self.root)

    def items(self) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        _inorder(self.root, out)
        return out

    def tail_length(self, trench: int) -> int:
        node = _predecessor(self.root, trench, inclusive=True)
        if node is not None and node.end == trench:
            return node.end - node.start
        return 0


def parse_case(path: Path) -> tuple[float, list[int]]:
    tokens = path.read_text().split()
    weight, n = float(tokens[0]), int(tokens[1])
    commands = [int(x) for x in tokens[2:]]
    if len(commands) == n + 1 and commands[-1] == 0:
        commands.pop()
    if len(commands) != n:
        raise ValueError(f"{path}: declared {n} commands, got {len(commands)}")
    return weight, commands


def shannon_entropy(counts: Counter[int], total: int) -> float:
    if total == 0:
        return 0.0
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def replay(case_num: int, input_path: Path, trace_path: Path, summary_row: dict) -> dict:
    weight, commands = parse_case(input_path)
    lines = trace_path.read_text().splitlines()
    if len(lines) != len(commands):
        raise ValueError(f"case {case_num}: {len(commands)} commands but {len(lines)} response lines")

    free = FreeIntervals()
    trench = 0
    active: dict[int, dict] = {}
    all_pipes: list[dict] = [{}]
    active_volume = 0
    peak_volume = 0
    placement_lengths: list[int] = []
    length_counts: Counter[int] = Counter()
    size_runs: list[tuple[int, int]] = []
    deletions: list[dict] = []
    expansions: list[dict] = []
    pipeno = 0
    current_run_length = None
    current_run_count = 0
    fenwick = [0] * (sum(command > 0 for command in commands) + 1)

    def fenwick_add(index: int, delta: int) -> None:
        while index < len(fenwick):
            fenwick[index] += delta
            index += index & -index

    def fenwick_prefix(index: int) -> int:
        total = 0
        while index > 0:
            total += fenwick[index]
            index -= index & -index
        return total

    for op_index, (command, line) in enumerate(zip(commands, lines), start=1):
        try:
            response = [int(x) for x in line.split()]
        except ValueError as exc:
            raise ValueError(f"case {case_num}, op {op_index}: malformed trace line {line!r}") from exc

        if command > 0:
            if len(response) != 2:
                raise ValueError(f"case {case_num}, op {op_index}: placement response needs 2 integers")
            digs, start = response
            length = command
            if digs < 0 or start < 0:
                raise ValueError(f"case {case_num}, op {op_index}: negative dig/start")
            old_trench = trench
            max_gap_before = free.max_len
            free_before = free.total
            tail_before = free.tail_length(trench)
            if digs:
                expansion = digs * 20
                new_trench = trench + expansion
                expansions.append({
                    "op": op_index,
                    "pid": pipeno + 1,
                    "length": length,
                    "digs_sections": digs,
                    "growth_m": expansion,
                    "trench_before_m": trench,
                    "trench_after_m": new_trench,
                    "free_volume_before_m": free_before,
                    "largest_free_gap_before_m": max_gap_before,
                    "tail_gap_before_m": tail_before,
                    "free_volume_sufficed": free_before >= length,
                    "single_free_gap_sufficed": max_gap_before >= length,
                    "growth_m_above_free_volume_deficit": max(0, expansion - max(0, length - free_before)),
                })
                free.add(trench, new_trench)
                trench = new_trench
            free.consume(start, start + length)
            pipeno += 1
            pipe = {"pid": pipeno, "start": start, "length": length,
                    "place_op": op_index, "active": True, "remove_op": None}
            all_pipes.append(pipe)
            active[pipeno] = pipe
            fenwick_add(pipeno, +1)
            active_volume += length
            peak_volume = max(peak_volume, active_volume)
            placement_lengths.append(length)
            length_counts[length] += 1
            if current_run_length == length:
                current_run_count += 1
            else:
                if current_run_length is not None:
                    size_runs.append((current_run_length, current_run_count))
                current_run_length = length
                current_run_count = 1
        elif command < 0:
            if len(response) != 1:
                raise ValueError(f"case {case_num}, op {op_index}: deletion response needs 1 integer")
            pid = -command
            if pid not in active:
                raise ValueError(f"case {case_num}, op {op_index}: input deletes inactive PID {pid}")
            pipe = active[pid]
            if response[0] != pipe["start"]:
                raise ValueError(f"case {case_num}, op {op_index}: deletion start mismatch for PID {pid}")
            active_count_before = len(active)
            newer = active_count_before - fenwick_prefix(pid)
            active.pop(pid)
            fenwick_add(pid, -1)
            rank_newest = newer / (active_count_before - 1) if active_count_before > 1 else 0.5
            age = op_index - pipe["place_op"]
            pipe["active"] = False
            pipe["remove_op"] = op_index
            pipe["lifetime_ops"] = age
            active_volume -= pipe["length"]
            free.add(pipe["start"], pipe["start"] + pipe["length"])
            deletions.append({
                "pid": pid,
                "length": pipe["length"],
                "age_ops": age,
                "rank_from_newest_fraction": rank_newest,
                "active_count_before": active_count_before,
            })
        else:
            raise ValueError(f"case {case_num}, op {op_index}: unexpected zero in declared input")

    if current_run_length is not None:
        size_runs.append((current_run_length, current_run_count))
    final_active = sorted(active.values(), key=lambda p: p["start"])
    final_gaps = free.items()
    final_occupied = sum(p["length"] for p in final_active)
    if trench != summary_row["trench_length_m"]:
        raise ValueError(f"case {case_num}: replay trench {trench} != judge {summary_row['trench_length_m']}")
    if final_occupied != summary_row["occupied_length_m"]:
        raise ValueError(f"case {case_num}: replay occupancy {final_occupied} != judge {summary_row['occupied_length_m']}")
    if peak_volume != summary_row["peak_live_pipe_length_m"]:
        raise ValueError(f"case {case_num}: replay peak {peak_volume} != harness {summary_row['peak_live_pipe_length_m']}")

    lower_bound = ((peak_volume + 19) // 20) * 20
    upper_kpi = min(1.0, final_occupied / lower_bound) if lower_bound else 0.0
    current_kpi = final_occupied / trench if trench else 0.0
    current_score = weight * current_kpi
    upper_score = weight * upper_kpi
    headroom = upper_score - current_score

    removed_by_length: dict[int, list[int]] = defaultdict(list)
    survivor_by_length: Counter[int] = Counter()
    for pipe in all_pipes[1:]:
        if pipe["active"]:
            survivor_by_length[pipe["length"]] += 1
        else:
            removed_by_length[pipe["length"]].append(pipe["lifetime_ops"])

    left_gap_ends = {end for _, end in final_gaps}
    right_gap_starts = {start for start, _ in final_gaps}
    separators = []
    for pipe in final_active:
        has_left_gap = pipe["start"] in left_gap_ends
        has_right_gap = pipe["start"] + pipe["length"] in right_gap_starts
        if has_left_gap and has_right_gap:
            separators.append(pipe)

    final_gap_lengths = [end - start for start, end in final_gaps]
    expansion_total = sum(x["growth_m"] for x in expansions)
    expanded_fragmented = [x for x in expansions if x["free_volume_sufficed"] and not x["single_free_gap_sufficed"]]
    expanded_with_fitting_gap = [x for x in expansions if x["single_free_gap_sufficed"]]
    expanded_free_short = [x for x in expansions if not x["free_volume_sufficed"]]

    del_rank = [x["rank_from_newest_fraction"] for x in deletions]
    del_ages = [x["age_ops"] for x in deletions]
    placements = len(placement_lengths)
    entropy = shannon_entropy(length_counts, placements)
    dominant_len, dominant_count = length_counts.most_common(1)[0] if length_counts else (0, 0)
    max_run = max((r for _, r in size_runs), default=0)
    runs46 = sum(1 for _, run_len in size_runs if run_len >= 46)
    # rank_from_newest_fraction is 0 for the newest live PID and 1 for the oldest.
    newest_share = sum(rank <= 0.2 for rank in del_rank) / len(del_rank) if del_rank else 0.0
    oldest_share = sum(rank >= 0.8 for rank in del_rank) / len(del_rank) if del_rank else 0.0
    mean_delete_rank = statistics.mean(del_rank) if del_rank else None

    flow_parts = []
    if placements:
        if dominant_count / placements >= 0.8:
            flow_parts.append(f"размерный поток с доминированием {dominant_len} м ({dominant_count / placements:.0%})")
        elif entropy >= 4.5:
            flow_parts.append("разнообразные размеры (высокая энтропия)")
        else:
            flow_parts.append("смешанные размеры")
        if max_run >= 46:
            flow_parts.append(f"есть серия одинаковой длины до {max_run} укладок")
    if deletions:
        if newest_share >= 0.7:
            flow_parts.append(f"удаления LIFO-подобные ({newest_share:.0%} из самых новых 20% PID)")
        elif oldest_share >= 0.7:
            flow_parts.append(f"удаления FIFO-подобные ({oldest_share:.0%} из самых старых 20% PID)")
        else:
            flow_parts.append("удаления по PID смешанные/не имеют сильного FIFO/LIFO сигнала")
    if not flow_parts:
        flow_parts.append("недостаточно событий для устойчивой классификации")

    rec = {
        "case": case_num,
        "weight": weight,
        "input_sha256": sha256(input_path),
        "trace_sha256": sha256(trace_path),
        "operations": len(commands),
        "placements": placements,
        "deletions": len(deletions),
        "placement_size_unique_count": len(length_counts),
        "placement_size_entropy_bits": entropy,
        "dominant_placement_length_m": dominant_len,
        "dominant_placement_fraction": dominant_count / placements if placements else 0,
        "max_same_size_placement_run": max_run,
        "same_size_runs_at_least_46": runs46,
        "mean_active_count_before_deletion": statistics.mean(x["active_count_before"] for x in deletions) if deletions else None,
        "mean_delete_rank_from_newest_fraction": mean_delete_rank,
        "newest_20pct_delete_share": newest_share,
        "oldest_20pct_delete_share": oldest_share,
        "median_removed_lifetime_ops": statistics.median(del_ages) if del_ages else None,
        "p90_removed_lifetime_ops": sorted(del_ages)[math.ceil(0.9 * len(del_ages)) - 1] if del_ages else None,
        "removed_lifetime_mean_by_length": {str(k): round(statistics.mean(v), 3) for k, v in sorted(removed_by_length.items())},
        "end_survivor_count": len(final_active),
        "end_survivor_volume_m": final_occupied,
        "end_survivors_by_length": dict(sorted(survivor_by_length.items())),
        "end_survivor_mean_age_ops": statistics.mean(len(commands) - p["place_op"] + 1 for p in final_active) if final_active else None,
        "end_survivor_separator_count": len(separators),
        "end_survivor_separator_length_m": sum(p["length"] for p in separators),
        "flow_type": "; ".join(flow_parts),
        "peak_active_volume_m": peak_volume,
        "final_occupied_length_m": final_occupied,
        "active_volume_lower_bound_trench_m": lower_bound,
        "final_occupied_upper_bound_kpi": upper_kpi,
        "actual_trench_m": trench,
        "actual_kpi": current_kpi,
        "official_weight": weight,
        "current_weighted_score": current_score,
        "upper_bound_weighted_score": upper_score,
        "max_possible_weighted_gain": headroom,
        "trench_over_volume_lower_bound_m": trench - lower_bound,
        "final_free_volume_m": free.total,
        "final_free_gap_count": free.count,
        "final_largest_free_gap_m": free.max_len,
        "final_free_gap_count_le_4m": free.small_counts[4],
        "final_free_volume_le_4m": free.small_volume[4],
        "final_free_gap_count_le_10m": free.small_counts[10],
        "final_free_volume_le_10m": free.small_volume[10],
        "final_free_gap_count_le_20m": free.small_counts[20],
        "final_free_volume_le_20m": free.small_volume[20],
        "final_free_gap_count_le_40m": free.small_counts[40],
        "final_free_volume_le_40m": free.small_volume[40],
        "final_free_gap_length_histogram": dict(sorted(Counter(final_gap_lengths).items())),
        "trench_growth_events": len(expansions),
        "trench_growth_m": expansion_total,
        "fragmentation_growth_events_free_volume_enough_but_no_single_gap": len(expanded_fragmented),
        "fragmentation_growth_m_free_volume_enough_but_no_single_gap": sum(x["growth_m"] for x in expanded_fragmented),
        "growth_events_despite_an_existing_physically_fitting_gap": len(expanded_with_fitting_gap),
        "growth_m_despite_an_existing_physically_fitting_gap": sum(x["growth_m"] for x in expanded_with_fitting_gap),
        "growth_events_total_free_volume_below_request": len(expanded_free_short),
        "growth_m_above_local_free_volume_deficit": sum(x["growth_m_above_free_volume_deficit"] for x in expansions),
        "median_largest_gap_before_growth_m": statistics.median(x["largest_free_gap_before_m"] for x in expansions) if expansions else None,
        "mean_free_volume_before_growth_m": statistics.mean(x["free_volume_before_m"] for x in expansions) if expansions else None,
        "actual_solver_cpu_s": summary_row["solver_cpu_total_s"],
        "actual_solver_peak_rss_mib": summary_row["solver_peak_rss_mb"],
        "actual_status": summary_row["status"],
    }
    rec["diagnostic_growth_events"] = expansions
    return rec


def main() -> None:
    source_sha = sha256(SOURCE)
    if source_sha != EXPECTED_SOURCE_SHA:
        raise SystemExit(f"Current final source SHA changed: {source_sha}")
    summary = json.loads(SUMMARY.read_text())
    by_case = {int(r["case"]): r for r in summary["records"]}
    if len(by_case) != 15 or summary["ok_count"] != 15:
        raise SystemExit("Expected exact 15/15 accepted final baseline traces")

    records = []
    for case_num in range(1, 16):
        input_path = DATA / f"{case_num}.in"
        trace_path = TRACE_ROOT / "runs" / str(case_num) / "judge_output.txt"
        records.append(replay(case_num, input_path, trace_path, by_case[case_num]))

    current_score = sum(r["current_weighted_score"] for r in records)
    upper_score = sum(r["upper_bound_weighted_score"] for r in records)
    weight_sum = sum(r["weight"] for r in records)
    if abs(current_score - summary["weighted_score_sum"]) > 1e-12:
        raise SystemExit("Per-case replay weighted sum does not match the stored final summary")
    if abs(weight_sum - summary["weight_sum"]) > 1e-12:
        raise SystemExit("Per-case weights do not match the stored final summary")

    # Save verbose per-event growth diagnostics separately so the CSV is usable.
    growth_events = []
    for r in records:
        for event in r.pop("diagnostic_growth_events"):
            growth_events.append({"case": r["case"], **event})

    ranking = sorted(records, key=lambda r: (-r["max_possible_weighted_gain"], r["case"]))
    fields = [k for k, v in records[0].items() if not isinstance(v, (dict, list))]
    with (OUT / "per_case.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r[k] for k in fields}
                         for r in sorted(records, key=lambda r: r["case"]))
    growth_fields = list(growth_events[0]) if growth_events else []
    with (OUT / "growth_events.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=growth_fields)
        if growth_fields:
            writer.writeheader()
            writer.writerows(growth_events)

    case_summary = {
        "source_sha256": source_sha,
        "binary_sha256": sha256(BIN),
        "interactor_sha256": sha256(INTERACTOR),
        "harness_sha256": sha256(HARNESS),
        "open_summary_sha256": sha256(SUMMARY),
        "open_cases_csv_sha256": sha256(TRACE_ROOT / "cases.csv"),
        "source_trace_dir": str(TRACE_ROOT.relative_to(ROOT)),
        "input_sha256_by_case": {str(r["case"]): r["input_sha256"] for r in records},
        "judge_output_sha256_by_case": {str(r["case"]): r["trace_sha256"] for r in records},
        "analysis_script_sha256": sha256(Path(__file__)),
        "method": {
            "score_bound": "min(1, final occupied length / (ceil(peak live length / 20) * 20)) * official test weight",
            "headroom": "volume upper-bound weighted score minus exact baseline weighted score",
            "trace_replay": "For each positive command, consume the judge trace start coordinate and extend free space by the reported 20m-section count; for each negative PID, validate the returned start and merge that interval. Replay checks trench, final occupancy, and peak live volume against the saved official harness summary.",
            "growth_fragmentation": "At each positive command that digs, record free volume and largest single free gap immediately before growth. Existing free volume sufficient but no single gap large enough is classified as fragmentation-sensitive growth; a physically fitting existing gap at a growth event is separately reported as a possible algorithmic lane/eligibility constraint.",
            "permanent_blockers": "End-surviving pipes are only called end survivors; separator count is the subset with a final free gap directly on both sides. No claim is made that these pipes are permanent beyond the input.",
            "flow_type": "Descriptive placement-size entropy/dominance/run metrics and deletion PID-rank shares; labels are heuristic and are not claims about the hidden generator.",
        },
        "environment": platform.platform(),
        "current_weighted_score": current_score,
        "sum_volume_upper_bound_weighted_scores": upper_score,
        "open_weight_sum": weight_sum,
        "residual_headroom_to_32_1": weight_sum - current_score,
        "max_headroom_from_volume_bound": upper_score - current_score,
        "32_1_reachable_under_per_case_volume_bounds": upper_score >= weight_sum - 1e-12,
        "ranked_cases_by_weighted_headroom": [
            {"rank": i, "case": r["case"], "weight": r["weight"],
             "current": r["current_weighted_score"], "upper": r["upper_bound_weighted_score"],
             "headroom": r["max_possible_weighted_gain"]}
            for i, r in enumerate(ranking, 1)
        ],
        "per_case": sorted(records, key=lambda r: r["case"]),
    }
    (OUT / "manifest.json").write_text(json.dumps(case_summary, indent=2) + "\n")
    print(json.dumps({
        "current_score": current_score,
        "volume_bound_score": upper_score,
        "weight_sum": weight_sum,
        "max_headroom": upper_score - current_score,
        "full_32_1_possible_under_volume_bounds": upper_score >= weight_sum - 1e-12,
        "ranked": case_summary["ranked_cases_by_weighted_headroom"],
    }, indent=2))


if __name__ == "__main__":
    main()
