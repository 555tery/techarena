#!/usr/bin/env python3
"""Offline-only beam/oracle diagnosis for short Pipes cohort streams.

This is a research instrument, not an online solver. The beam may use the
future deletion schedule to rank states. No output from it is intended for
the final allocator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
DIG = 20
HISTORY = 2048
PENALTY = 60


def read_input(path: Path):
    values = list(map(int, path.read_text().split()))
    return values[2:2 + values[1]]


def make_two_cohort(first_len: int, next_len: int, count: int, mode: str, seed: int = 0):
    ops = [first_len] * count
    first = list(range(1, count + 1))
    if mode == "odd":
        removed = first[::2]
    elif mode == "even":
        removed = first[1::2]
    elif mode == "old-half":
        removed = first[:count // 2]
    elif mode == "new-half":
        removed = first[count // 2:]
    elif mode == "random-half":
        rng = random.Random(seed)
        removed = sorted(rng.sample(first, count // 2))
    else:
        raise ValueError(mode)
    ops.extend(-pid for pid in removed)
    ops.extend([next_len] * count)
    return ops, removed


class OnlineSim:
    """Small exact state simulator for the current allocator family."""

    def __init__(self, mode="t46"):
        self.mode = mode
        self.h = 0
        self.pipes = [None]
        self.history = deque()
        self.freq = [0] * 41
        self.deleted_parities = deque(maxlen=64)
        self.learned_delete_parity = None

    def gaps(self):
        live = sorted((start, start + length) for item in self.pipes[1:]
                      if item is not None for start, length in [item])
        result = []
        cursor = 0
        for start, end in live:
            if cursor < start:
                result.append((cursor, start))
            cursor = max(cursor, end)
        if cursor < self.h:
            result.append((cursor, self.h))
        return result

    def remove(self, pid):
        if pid > 0 and pid < len(self.pipes):
            if self.pipes[pid] is not None:
                self.pipes[pid] = None
                if self.mode in ("learned-parity", "learned-parity-owner"):
                    self.deleted_parities.append(pid % 2)
                    if len(self.deleted_parities) >= 8:
                        counts = Counter(self.deleted_parities)
                        parity, count = counts.most_common(1)[0]
                        if count * 100 >= len(self.deleted_parities) * 85:
                            self.learned_delete_parity = parity

    def _choose_gap(self, length, gaps, high_side=False):
        fitting = [(end - start, start, end) for start, end in gaps
                   if end - start >= length]
        if not fitting:
            return None
        if self.mode == "first-fit":
            return min(fitting, key=lambda gap: gap[1])
        if self.mode == "worst-fit":
            return max(fitting, key=lambda gap: (gap[0], -gap[1]))
        if self.mode == "best-fit":
            return min(fitting, key=lambda gap: (gap[0], gap[1]))

        n = len(self.history)
        def score(gap):
            slack = gap[0] - length
            misses = sum(self.freq[k] for k in range(slack + 1, 41)) if 0 < slack <= 40 else 0
            return slack * n + (PENALTY * misses if 0 < slack <= 40 else 0)
        return min(fitting, key=lambda gap: (score(gap), gap[0], -gap[1] if high_side else gap[1]))

    def place(self, length):
        gaps = self.gaps()
        pid = len(self.pipes)
        learned_side = (self.mode in ("learned-parity", "learned-parity-owner") and self.learned_delete_parity is not None)
        high_side = learned_side and pid % 2 == self.learned_delete_parity
        gap = self._choose_gap(length, gaps, high_side)
        if gap is None:
            tail_start = gaps[-1][0] if gaps and gaps[-1][1] == self.h else self.h
            tail = self.h - tail_start
            self.h += max(0, math.ceil((length - tail) / DIG)) * DIG
            start = self.h - length if high_side else tail_start
        else:
            gap_len, gap_start, gap_end = gap
            same_run = len(self.history) >= 46 and all(x == length for x in list(self.history)[-46:])
            if self.mode == "right-all":
                right = True
            elif learned_side:
                right = high_side
            elif self.mode == "left-all":
                right = False
            else:
                right = length <= 4 or same_run
            start = gap_end - length if right else gap_start
        self.pipes.append((start, length))
        self.history.append(length)
        self.freq[length] += 1
        if len(self.history) > HISTORY:
            self.freq[self.history.popleft()] -= 1

    def run(self, ops):
        for op in ops:
            if op > 0:
                self.place(op)
            elif op < 0:
                self.remove(-op)
        return self.h


class LearnedOwnerSim(OnlineSim):
    """Causal variant: learn deleted PID parity, then prefer matching holes."""

    def __init__(self):
        super().__init__("learned-parity-owner")
        self.gap_owners = {}

    def gaps(self):
        base = super().gaps()
        return [(left, right, self.gap_owners.get((left, right), -1))
                for left, right in base]

    def _erase_gap(self, left, right):
        self.gap_owners.pop((left, right), None)

    def _add_gap(self, left, right, owner):
        if left >= right:
            return
        joined = []
        for key in sorted(self.gap_owners):
            a, b = key
            if b >= left and a <= right:
                joined.append((a, b, self.gap_owners[key]))
        owners = {owner}
        for a, b, old_owner in joined:
            left = min(left, a)
            right = max(right, b)
            owners.add(old_owner)
            self._erase_gap(a, b)
        final_owner = owners.pop() if len(owners) == 1 else -1
        self.gap_owners[(left, right)] = final_owner

    def remove(self, pid):
        if pid <= 0 or pid >= len(self.pipes) or self.pipes[pid] is None:
            return
        start, length = self.pipes[pid]
        self.pipes[pid] = None
        self.deleted_parities.append(pid % 2)
        if len(self.deleted_parities) >= 8:
            counts = Counter(self.deleted_parities)
            parity, count = counts.most_common(1)[0]
            if count * 100 >= len(self.deleted_parities) * 85:
                self.learned_delete_parity = parity
        owner = pid % 2 if self.learned_delete_parity is not None else -1
        self._add_gap(start, start + length, owner)

    def place(self, length):
        pid = len(self.pipes)
        active = self.learned_delete_parity is not None
        cls = pid % 2
        high_side = active and cls == self.learned_delete_parity
        gaps = self.gaps()
        fitting = [(right - left, left, right, owner)
                   for left, right, owner in gaps if right - left >= length]
        gap = None
        same_run = len(self.history) >= 46 and all(x == length for x in list(self.history)[-46:])
        chosen_right = high_side if active else (length <= 4 or same_run)
        if fitting:
            if active:
                preferred = [g for g in fitting if g[3] == cls]
                if not preferred:
                    preferred = [g for g in fitting if g[3] == -1]
            else:
                preferred = fitting
            if preferred:
                n = len(self.history)
                def score(g):
                    slack = g[0] - length
                    misses = sum(self.freq[k] for k in range(slack + 1, 41)) if 0 < slack <= 40 else 0
                    cost = slack * n + (PENALTY * misses if 0 < slack <= 40 else 0)
                    tie = -g[1] if chosen_right else g[1]
                    return cost, g[0], tie
                gap = min(preferred, key=score)
        if gap is None:
            tail = gaps[-1] if gaps and gaps[-1][1] == self.h else None
            preserve_foreign = active and tail is not None and tail[2] >= 0 and tail[2] != cls
            tail_start = self.h if tail is None or preserve_foreign else tail[0]
            tail_len = self.h - tail_start
            old_h = self.h
            self.h += max(0, math.ceil((length - tail_len) / DIG)) * DIG
            if tail is not None and not preserve_foreign:
                self._erase_gap(tail[0], tail[1])
            start = self.h - length if high_side else tail_start
            if active:
                self._add_gap(tail_start, start, cls)
                self._add_gap(start + length, self.h, cls)
            else:
                self._add_gap(tail_start, start, -1)
                self._add_gap(start + length, self.h, -1)
        else:
            gap_len, left, right, owner = gap
            self._erase_gap(left, right)
            start = right - length if chosen_right else left
            new_owner = cls if active else owner
            self._add_gap(left, start, new_owner)
            self._add_gap(start + length, right, new_owner)
        self.pipes.append((start, length))
        self.history.append(length)
        self.freq[length] += 1
        if len(self.history) > HISTORY:
            self.freq[self.history.popleft()] -= 1

@dataclass(frozen=True)
class State:
    trench: int
    pipes: tuple[tuple[int, int] | None, ...]


def state_gaps(state: State):
    live = sorted((start, start + length) for item in state.pipes[1:]
                  if item is not None for start, length in [item])
    gaps = []
    cursor = 0
    for start, end in live:
        if cursor < start:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < state.trench:
        gaps.append((cursor, state.trench))
    return gaps


def beam_actions(state: State, length: int):
    gaps = state_gaps(state)
    candidates = []
    for left, right in gaps:
        if right - left >= length:
            # Every integer coordinate is legal in the official protocol.
            candidates.extend((left, length) for left in range(left, right - length + 1))
    if not candidates:
        tail_left = gaps[-1][0] if gaps and gaps[-1][1] == state.trench else state.trench
        tail_len = state.trench - tail_left
        new_trench = state.trench + max(0, math.ceil((length - tail_len) / DIG)) * DIG
        candidates = [(tail_left, length, new_trench)]
    result = []
    pid = len(state.pipes)
    for action in candidates:
        if len(action) == 2:
            start, pipe_len = action
            new_trench = state.trench
        else:
            start, pipe_len, new_trench = action
        result.append(State(new_trench, state.pipes + ((start, pipe_len),)))
    return result


def apply_delete(state: State, pid: int):
    if pid <= 0 or pid >= len(state.pipes) or state.pipes[pid] is None:
        return state
    pipes = list(state.pipes)
    pipes[pid] = None
    return State(state.trench, tuple(pipes))


def cluster_cost(state: State, removed: set[int], count: int):
    """Offline-only estimate: keep eventual survivors/deletions contiguous."""
    costs = []
    for target in (False, True):
        items = []
        for pid in range(1, min(len(state.pipes), count + 1)):
            item = state.pipes[pid]
            if item is not None and ((pid in removed) == target):
                items.append((item[0], item[0] + item[1]))
        if len(items) > 1:
            items.sort()
            occupied = sum(end - start for start, end in items)
            costs.append(items[-1][1] - items[0][0] - occupied)
    return sum(costs)


def future_fit_capacity(state: State, removed: set[int], count: int, need: int):
    projected = state
    for pid in removed:
        if pid < len(projected.pipes):
            projected = apply_delete(projected, pid)
    return sum((right - left) // need for left, right in state_gaps(projected))


def beam_search(ops, removed, count, next_length, width=256):
    """Beam over all coordinate choices; future deletion IDs are an oracle hint."""
    beam = [State(0, (None,))]
    expanded_total = 0
    for op in ops:
        if op > 0:
            generated = []
            for state in beam:
                generated.extend(beam_actions(state, op))
            expanded_total += len(generated)
        else:
            generated = [apply_delete(state, -op) for state in beam]

        unique = {}
        for state in generated:
            signature = (state.trench, state.pipes)
            unique.setdefault(signature, state)
        generated = list(unique.values())

        # Future information is used only in this diagnostic rank. The first
        # key, trench length, remains the measured objective.
        generated.sort(key=lambda s: (
            s.trench,
            -future_fit_capacity(s, removed, count, next_length),
            cluster_cost(s, removed, count),
            tuple((-1, -1) if item is None else item for item in s.pipes),
        ))
        beam = generated[:width]
    best = min(beam, key=lambda s: s.trench)
    return {
        "beam_trench_m": best.trench,
        "beam_width": width,
        "expanded_states_total": expanded_total,
        "survivor_layout_first_cohort": [
            {"pid": pid, "start": item[0], "length": item[1], "removed_later": pid in removed}
            for pid, item in enumerate(best.pipes[1:], 1) if item is not None and pid <= count
        ],
    }


def run_suite(width=256, count=16):
    records = []
    for first_len, next_len in ((1, 2), (2, 4), (4, 8), (8, 16), (16, 32)):
        for mode in ("odd", "even", "old-half", "new-half", "random-half"):
            ops, removed_list = make_two_cohort(first_len, next_len, count, mode, seed=20261016)
            removed = set(removed_list)
            baseline = OnlineSim("t46").run(ops)
            variants = {
                name: OnlineSim(name).run(ops)
                for name in ("left-all", "right-all", "first-fit", "worst-fit", "learned-parity")
            }
            variants["learned-parity-owner"] = LearnedOwnerSim().run(ops)
            beam = beam_search(ops, removed, count, next_len, width)
            records.append({
                "first_length": first_len,
                "next_length": next_len,
                "cohort_size": count,
                "deletion_mode": mode,
                "deleted_pids": sorted(removed),
                "online_t46_trench_m": baseline,
                "online_variants_trench_m": variants,
                "offline_beam": beam,
            })
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--count", type=int, default=16)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "beam_matrix.json")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    records = run_suite(args.width, args.count)
    payload = {
        "scope": "offline diagnosis only; beam uses future deletion IDs and is not an online candidate",
        "beam_action_space": "all integral starts in every fitting gap; exact feasible placements",
        "beam_width": args.width,
        "cohort_size": args.count,
        "cases": records,
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"saved {args.out} ({len(records)} cases)")
    for row in records:
        b = row["online_t46_trench_m"]
        q = row["offline_beam"]["beam_trench_m"]
        print(f"{row['first_length']:2d}->{row['next_length']:2d} {row['deletion_mode']:10s} T46={b:4d} beam={q:4d} gap={b-q:3d}")


if __name__ == "__main__":
    main()
