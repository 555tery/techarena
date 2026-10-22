#!/usr/bin/env python3
"""Offline screen of causal right-to-left triggers for Pipes."""

from __future__ import annotations

import json
from collections import Counter, deque
from pathlib import Path

import beam_diagnosis as bd


OUT = Path(__file__).parent / "signal_screen.json"


class SignalLeftSim(bd.OnlineSim):
    def __init__(self, run_threshold=None, delete_window=None, dominance=85):
        super().__init__("t46")
        self.run_threshold = run_threshold
        self.delete_window = delete_window
        self.dominance = dominance
        self.recent_deleted_parities = deque(maxlen=delete_window or 1)
        self.left_latched = False
        self.trigger = None

    def remove(self, pid):
        if (self.delete_window is not None and 0 < pid < len(self.pipes)
                and self.pipes[pid] is not None):
            self.recent_deleted_parities.append(pid % 2)
            if len(self.recent_deleted_parities) == self.delete_window:
                counts = Counter(self.recent_deleted_parities)
                if 100 * counts.most_common(1)[0][1] >= self.dominance * self.delete_window:
                    self.left_latched = True
                    self.trigger = self.trigger or "deletion-parity"
        super().remove(pid)

    def place(self, length):
        if self.run_threshold is not None and len(self.history) >= self.run_threshold:
            recent = list(self.history)[-self.run_threshold:]
            if all(value == recent[0] for value in recent):
                self.left_latched = True
                self.trigger = self.trigger or "same-length-run"
        if self.left_latched:
            self.mode = "left-all"
        super().place(length)


def run_policy(ops, run_threshold=None, delete_window=None):
    sim = SignalLeftSim(run_threshold, delete_window)
    trench = sim.run(ops)
    return {"trench_m": trench, "trigger": sim.trigger}


def main():
    records = []
    case9_ops = bd.read_input(bd.ROOT / "data/pipes/open/9.in")
    for policy, run_k, del_m in [
        ("run-8", 8, None), ("run-16", 16, None), ("run-32", 32, None),
        ("run-46", 46, None), ("run-64", 64, None),
        ("run-128", 128, None),
        ("deletions-8", None, 8), ("deletions-16", None, 16),
        ("deletions-32", None, 32), ("deletions-64", None, 64),
        ("run-16-or-deletions-8", 16, 8),
        ("run-46-or-deletions-8", 46, 8),
    ]:
        result = run_policy(case9_ops, run_k, del_m)
        records.append({"stream": "case9", "policy": policy, **result})

    for first_len, next_len in ((1, 2), (2, 4), (4, 8), (8, 16), (16, 32)):
        for mode in ("odd", "even", "old-half", "new-half", "random-half"):
            ops, _ = bd.make_two_cohort(first_len, next_len, 16, mode, seed=20261016)
            baseline = bd.OnlineSim("t46").run(ops)
            row = {
                "stream": f"{first_len}->{next_len}/{mode}",
                "baseline_t46_m": baseline,
                "left_all_m": bd.OnlineSim("left-all").run(ops),
                "policies": {},
            }
            for policy, run_k, del_m in [
                ("run-8", 8, None), ("run-16", 16, None),
                ("run-32", 32, None), ("run-46", 46, None),
                ("deletions-8", None, 8), ("deletions-16", None, 16),
                ("deletions-32", None, 32),
                ("run-16-or-deletions-8", 16, 8),
                ("run-46-or-deletions-8", 46, 8),
            ]:
                row["policies"][policy] = run_policy(ops, run_k, del_m)
            records.append(row)

    payload = {
        "scope": "offline causal screening only; policies use observed history, no test IDs/positions/future operations",
        "deletion_trigger": "last M valid deleted PIDs have >=85% matching parity",
        "run_trigger": "last K placed lengths are identical; latch left edge for subsequent placements",
        "case9_baselines_m": {
            "t46": bd.OnlineSim("t46").run(case9_ops),
            "left_all": bd.OnlineSim("left-all").run(case9_ops),
            "right_all": bd.OnlineSim("right-all").run(case9_ops),
        },
        "records": records,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"saved {OUT} ({len(records)} records)")
    for row in records[:12]:
        print(f"case9 {row['policy']:25s} H={row['trench_m']:6d} trigger={row['trigger']}")
    for policy in ("run-8", "run-16", "run-32", "run-46", "deletions-8", "deletions-16", "deletions-32", "run-16-or-deletions-8", "run-46-or-deletions-8"):
        deltas = [r["policies"][policy]["trench_m"] - r["baseline_t46_m"] for r in records if "policies" in r]
        print(f"{policy:25s} wins={sum(x < 0 for x in deltas):2d} equal={sum(x == 0 for x in deltas):2d} losses={sum(x > 0 for x in deltas):2d} sum_delta={sum(deltas):+d}")


if __name__ == "__main__":
    main()
