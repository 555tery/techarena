#!/usr/bin/env python3
"""Diagnostic oracle only: this uses exact future deletion labels from the trace.

It is not a solver candidate and must never be copied into production. Survivors
are placed in a birth-ordered prefix. Each temporary placement is first-fit in
free space at/above the survivor-prefix volume required by its known death op.
"""
from __future__ import annotations

import argparse
import array
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path

INPUT = Path("/Users/555tery/techarena/data/pipes/open/15.in")
OUT = Path(__file__).resolve().parent
DIG_UNIT = 20


@dataclass(slots=True)
class Node:
    start: int
    end: int
    priority: int
    left: "Node | None" = None
    right: "Node | None" = None
    max_len: int = 0
    min_key: int = 0
    max_key: int = 0

    def __post_init__(self) -> None:
        self.max_len = self.end - self.start
        self.min_key = self.start
        self.max_key = self.start


def update(n: Node | None) -> Node | None:
    if n is None:
        return None
    n.max_len = n.end - n.start
    n.min_key = n.max_key = n.start
    if n.left:
        n.max_len = max(n.max_len, n.left.max_len)
        n.min_key = n.left.min_key
    if n.right:
        n.max_len = max(n.max_len, n.right.max_len)
        n.max_key = n.right.max_key
    return n


def split(root: Node | None, key: int) -> tuple[Node | None, Node | None]:
    if root is None:
        return None, None
    if root.start < key:
        root.right, right = split(root.right, key)
        return update(root), right
    left, root.left = split(root.left, key)
    return left, update(root)


def merge(left: Node | None, right: Node | None) -> Node | None:
    if left is None:
        return right
    if right is None:
        return left
    if left.priority > right.priority:
        left.right = merge(left.right, right)
        return update(left)
    right.left = merge(left, right.left)
    return update(right)


def insert(root: Node | None, node: Node) -> Node:
    if root is None:
        return node
    if node.start == root.start:
        raise RuntimeError(f"duplicate free-gap key {node.start}")
    if node.priority > root.priority:
        node.left, node.right = split(root, node.start)
        return update(node)  # type: ignore[return-value]
    if node.start < root.start:
        root.left = insert(root.left, node)
    else:
        root.right = insert(root.right, node)
    return update(root)  # type: ignore[return-value]


def erase(root: Node | None, key: int) -> Node | None:
    if root is None:
        raise RuntimeError(f"free gap not found: {key}")
    if key == root.start:
        return merge(root.left, root.right)
    if key < root.start:
        root.left = erase(root.left, key)
    else:
        root.right = erase(root.right, key)
    return update(root)


def predecessor(root: Node | None, key: int) -> Node | None:
    best = None
    while root:
        if root.start <= key:
            best, root = root, root.right
        else:
            root = root.left
    return best


def lower_bound(root: Node | None, key: int) -> Node | None:
    best = None
    while root:
        if root.start >= key:
            best, root = root, root.left
        else:
            root = root.right
    return best


def first_fit(root: Node | None, low: int, length: int) -> int | None:
    if root is None or root.max_key < low:
        return None
    # Prune a whole subtree only when all its gaps begin at/above the bound.
    if root.min_key >= low and root.max_len < length:
        return None
    found = first_fit(root.left, low, length)
    if found is not None:
        return found
    candidate = max(root.start, low)
    if root.end - candidate >= length:
        return candidate
    return first_fit(root.right, low, length)


def max_gap_from(root: Node | None, low: int) -> int:
    """Largest contiguous free extent whose usable start is at/above low."""
    if root is None or root.max_key < low:
        return 0
    left_max = max_gap_from(root.left, low)
    own = root.end - max(root.start, low)
    right_max = max_gap_from(root.right, low)
    return max(0, left_max, own, right_max)


def add_free(root: Node | None, start: int, end: int, rng: random.Random) -> Node | None:
    if start >= end:
        return root
    prev = predecessor(root, start)
    if prev is not None and prev.end >= start:
        start = prev.start
        end = max(end, prev.end)
        root = erase(root, prev.start)
    nxt = lower_bound(root, start)
    while nxt is not None and nxt.start <= end:
        end = max(end, nxt.end)
        root = erase(root, nxt.start)
        nxt = lower_bound(root, start)
    return insert(root, Node(start, end, rng.getrandbits(64)))


def consume_free(root: Node | None, start: int, end: int,
                 rng: random.Random) -> Node | None:
    """Remove a fully-free address interval; fail if any part is occupied."""
    cursor = start
    while cursor < end:
        gap = predecessor(root, cursor)
        if gap is None or gap.end <= cursor:
            gap = lower_bound(root, cursor)
        if gap is None or gap.start > cursor or gap.end <= cursor:
            raise RuntimeError(f"oracle overlap/untracked interval at [{cursor},{end})")
        gap_start, gap_end = gap.start, gap.end
        root = erase(root, gap_start)
        if gap_start < cursor:
            root = add_free(root, gap_start, cursor, rng)
        consumed_end = min(end, gap_end)
        if gap_end > consumed_end:
            root = add_free(root, consumed_end, gap_end, rng)
        cursor = consumed_end
    return root


class RangeMinMax:
    """Independent range occupancy checker for answer replay."""
    def __init__(self, capacity: int):
        size = 1
        while size < capacity:
            size <<= 1
        self.size = size
        cells = size * 2
        self.lo = array.array("i", [0]) * cells
        self.hi = array.array("i", [0]) * cells
        self.lazy = array.array("i", [0]) * cells

    def _push(self, node: int) -> None:
        value = self.lazy[node]
        if value:
            for child in (node * 2, node * 2 + 1):
                self.lo[child] += value
                self.hi[child] += value
                self.lazy[child] += value
            self.lazy[node] = 0

    def add(self, ql: int, qr: int, value: int, node: int = 1,
            left: int = 0, right: int | None = None) -> None:
        if right is None:
            right = self.size
        if ql <= left and right <= qr:
            self.lo[node] += value
            self.hi[node] += value
            self.lazy[node] += value
            return
        self._push(node)
        mid = (left + right) // 2
        if ql < mid:
            self.add(ql, qr, value, node * 2, left, mid)
        if qr > mid:
            self.add(ql, qr, value, node * 2 + 1, mid, right)
        self.lo[node] = min(self.lo[node * 2], self.lo[node * 2 + 1])
        self.hi[node] = max(self.hi[node * 2], self.hi[node * 2 + 1])

    def query(self, ql: int, qr: int, node: int = 1,
              left: int = 0, right: int | None = None) -> tuple[int, int]:
        if right is None:
            right = self.size
        if ql <= left and right <= qr:
            return self.lo[node], self.hi[node]
        self._push(node)
        mid = (left + right) // 2
        values = []
        if ql < mid:
            values.append(self.query(ql, qr, node * 2, left, mid))
        if qr > mid:
            values.append(self.query(ql, qr, node * 2 + 1, mid, right))
        return min(v[0] for v in values), max(v[1] for v in values)


def parse_input(path: Path) -> tuple[bytes, float, list[int]]:
    raw = path.read_bytes()
    tokens = raw.split()
    weight, count = float(tokens[0]), int(tokens[1])
    commands = [int(x) for x in tokens[2:]]
    if len(commands) != count + 1 or commands[-1] != 0:
        raise RuntimeError("unexpected input shape")
    return raw, weight, commands


def run(path: Path, out_dir: Path) -> dict:
    raw, weight, commands = parse_input(path)
    count = len(commands) - 1
    lengths: list[int] = [0]
    births: list[int] = [0]
    death_op: dict[int, int] = {}
    pid = 0
    for op, command in enumerate(commands[:count], 1):
        if command > 0:
            pid += 1
            lengths.append(command)
            births.append(op)
        elif command < 0:
            target = -command
            if target <= 0 or target > pid or target in death_op:
                raise RuntimeError(f"invalid deletion at op {op}: PID {target}")
            death_op[target] = op
        else:
            raise RuntimeError(f"unexpected zero before terminal at op {op}")
    if pid != len(lengths) - 1:
        raise RuntimeError("PID/birth count mismatch")

    # Clairvoyant labels: exact EOF-survivor set and death op of every temp pipe.
    survivor = {p for p in range(1, pid + 1) if p not in death_op}
    prefix_at = [0] * (count + 1)
    survivor_start: dict[int, int] = {}
    prefix = 0
    pid = 0
    for op, command in enumerate(commands[:count], 1):
        if command > 0:
            pid += 1
            if pid in survivor:
                survivor_start[pid] = prefix
                prefix += lengths[pid]
        prefix_at[op] = prefix
    final_survivor_volume = prefix

    rng = random.Random(0xC1A1F00D)  # deterministic treap priorities; not a policy parameter
    free: Node | None = None
    trench = 0
    live_volume = peak_live_volume = 0
    active: dict[int, tuple[int, int]] = {}
    answers: list[str] = []
    extension_events: list[dict] = []
    allocations = 0
    temporary_allocations = 0
    total_digs = 0
    pid = 0

    def place(start: int, length: int, context: dict) -> int:
        nonlocal free, trench, live_volume, peak_live_volume
        end = start + length
        old_trench = trench
        digs = 0
        if end > old_trench:
            digs = (end - old_trench + DIG_UNIT - 1) // DIG_UNIT
            new_trench = old_trench + digs * DIG_UNIT
            if new_trench > 418780:
                low = context["minimum_start"]
                extension_events.append({
                    **context,
                    "start": start,
                    "end": end,
                    "old_trench": old_trench,
                    "new_trench": new_trench,
                    "digs": digs,
                    "max_free_extent_at_or_above_required_start": max_gap_from(free, low),
                    "lower_bound_gap_shortfall": max(0, context["length"] - max_gap_from(free, low)),
                })
            free = add_free(free, old_trench, new_trench, rng)
            trench = new_trench
        free = consume_free(free, start, end, rng)
        live_volume += length
        peak_live_volume = max(peak_live_volume, live_volume)
        return digs

    for op, command in enumerate(commands[:count], 1):
        if command > 0:
            pid += 1
            length = command
            if pid in survivor:
                start = survivor_start[pid]
                context = {"op": op, "pid": pid, "kind": "final-survivor", "length": length,
                           "minimum_start": start}
            else:
                death = death_op[pid]
                low = prefix_at[death]
                candidate = first_fit(free, low, length)
                start = max(trench, low) if candidate is None else candidate
                context = {"op": op, "pid": pid, "kind": "temporary", "length": length,
                           "death_op": death, "minimum_start": low,
                           "first_fit_candidate_found": candidate is not None}
                temporary_allocations += 1
            digs = place(start, length, context)
            total_digs += digs
            active[pid] = (start, length)
            answers.append(f"{digs} {start}")
            allocations += 1
        else:
            pid_to_remove = -command
            if pid_to_remove not in active:
                raise RuntimeError(f"oracle lost live PID {pid_to_remove} at op {op}")
            start, length = active.pop(pid_to_remove)
            free = add_free(free, start, start + length, rng)
            live_volume -= length
            answers.append(str(start))

    out_dir.mkdir(parents=True, exist_ok=True)
    answer_path = out_dir / "clairvoyant-answer.txt"
    answer_path.write_text("\n".join(answers) + "\n")
    if len(answers) != count:
        raise RuntimeError(f"answer count {len(answers)} != operation count {count}")

    # Independent physical replay from the serialized answer, checking every
    # allocation and deletion with a range min/max tree (no oracle free-list reuse).
    answer_lines = answer_path.read_text().splitlines()
    if len(answer_lines) != count:
        raise RuntimeError("serialized output line count mismatch")
    occupancy = RangeMinMax(trench + 1)
    replay_trench = 0
    replay_live: dict[int, tuple[int, int]] = {}
    replay_pid = 0
    replay_live_volume = replay_peak_live = 0
    replay_total_digs = 0
    for op, command in enumerate(commands[:count], 1):
        fields = [int(x) for x in answer_lines[op - 1].split()]
        if command > 0:
            replay_pid += 1
            if len(fields) != 2:
                raise RuntimeError(f"allocation op {op}: expected digs,start")
            digs, start = fields
            if digs < 0 or start < 0:
                raise RuntimeError(f"allocation op {op}: negative answer")
            replay_trench += digs * DIG_UNIT
            replay_total_digs += digs
            end = start + command
            if end > replay_trench:
                raise RuntimeError(f"allocation op {op}: end {end} exceeds trench {replay_trench}")
            mn, mx = occupancy.query(start, end)
            if (mn, mx) != (0, 0):
                raise RuntimeError(f"allocation op {op}: overlap; occupancy={mn}..{mx}")
            occupancy.add(start, end, 1)
            replay_live[replay_pid] = (start, command)
            replay_live_volume += command
            replay_peak_live = max(replay_peak_live, replay_live_volume)
        elif command < 0:
            target = -command
            if len(fields) != 1 or target not in replay_live:
                raise RuntimeError(f"deletion op {op}: malformed output or inactive PID")
            start, length = replay_live.pop(target)
            if fields[0] != start:
                raise RuntimeError(f"deletion op {op}: output start mismatch")
            mn, mx = occupancy.query(start, start + length)
            if (mn, mx) != (1, 1):
                raise RuntimeError(f"deletion op {op}: interval not fully occupied ({mn}..{mx})")
            occupancy.add(start, start + length, -1)
            replay_live_volume -= length
        else:
            raise RuntimeError(f"unexpected zero at op {op}")

    if replay_trench != trench or replay_total_digs != total_digs:
        raise RuntimeError(f"replay trench/digs mismatch: {replay_trench}/{replay_total_digs} vs {trench}/{total_digs}")
    if replay_live_volume != final_survivor_volume or replay_peak_live != peak_live_volume:
        raise RuntimeError("live-volume replay mismatch")
    if set(replay_live) != survivor:
        raise RuntimeError("EOF survivors mismatch")
    for survivor_pid, (start, length) in replay_live.items():
        if start != survivor_start[survivor_pid] or length != lengths[survivor_pid]:
            raise RuntimeError(f"survivor PID {survivor_pid} not at designated prefix interval")
    if final_survivor_volume:
        if occupancy.query(0, final_survivor_volume) != (1, 1):
            raise RuntimeError("final survivor prefix is not fully occupied")
    if final_survivor_volume < trench and occupancy.query(final_survivor_volume, trench) != (0, 0):
        raise RuntimeError("temporary intervals remain at EOF outside survivor prefix")

    return {
        "explicit_future": True,
        "online_solver_or_candidate": False,
        "heuristic": "EOF survivors in birth-ordered contiguous prefix; each temporary uses first-fit free gap with start >= prefixFinalVolume[known_death_op], else extend suffix",
        "input_path": str(path),
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "weight": weight,
        "operations": count,
        "placements": allocations,
        "temporary_placements": temporary_allocations,
        "eof_survivors": len(survivor),
        "final_survivor_volume": final_survivor_volume,
        "peak_live_volume": peak_live_volume,
        "trench_length_m": trench,
        "bound_gap_m": trench - 418780,
        "dig_unit_m": DIG_UNIT,
        "dig_count": total_digs,
        "extensions_beyond_volume_bound": extension_events,
        "answer_path": str(answer_path),
        "answer_sha256": hashlib.sha256(answer_path.read_bytes()).hexdigest(),
        "physical_replay": {
            "all_answer_lines_replayed": len(answer_lines),
            "allocation_validity_checked": True,
            "interval_nonoverlap_checked_by_independent_range_tree": True,
            "deletion_start_and_active_pid_checked": True,
            "survivor_prefix_checked": True,
            "final_temporary_volume_checked_zero": True,
            "trench_replayed_m": replay_trench,
            "replay_peak_live_volume_m": replay_peak_live,
            "replay_final_live_volume_m": replay_live_volume,
        },
        "interpretation": "If trench_length_m <= 418780, this serialized clairvoyant schedule witnesses reachability of the volume bound for this trace only. If larger, this single first-fit oracle is inconclusive; it does not prove impossibility.",
        "restrictions": {
            "validation_or_holdouts_accessed": False,
            "platform_accessed": False,
            "official_evaluator_called": False,
            "future_labels_used": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--out-dir", type=Path, default=OUT)
    args = parser.parse_args()
    result = run(args.input, args.out_dir)
    result_path = args.out_dir / "clairvoyant-result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
