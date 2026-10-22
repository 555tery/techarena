#!/usr/bin/env python3
"""Replay causal, run-scoped left-edge gates on open cases 5 and 9."""

from __future__ import annotations

import json
from collections import Counter, deque
from pathlib import Path

import beam_diagnosis as bd


OUT = Path(__file__).parent / "rolling_left_screen.json"
K = 46
DELETE_WINDOW = 8


class RollingLeftSim(bd.OnlineSim):
    def __init__(self, gate_smooth=False, gate_skew=False):
        super().__init__("t46")
        self.gate_smooth = gate_smooth
        self.gate_skew = gate_skew
        self.disabled = False
        self.deleted_parities = deque(maxlen=DELETE_WINDOW)
        self.operation = 0
        self.events = []
        self.run_policy_active = False

    def _smooth_trend_with(self, length):
        distinct = []
        for old_length in reversed(self.history):
            if not distinct or old_length != distinct[-1]:
                distinct.append(old_length)
            if len(distinct) >= 2:
                break
        # If the current request starts a new run, prepend it to the last two
        # completed run lengths. Otherwise the current run is already present.
        values = distinct if distinct and distinct[0] == length else [length, *distinct]
        if len(values) < 3:
            return False
        return values[0] - values[1] == values[1] - values[2]

    def run(self, ops):
        for self.operation, op in enumerate(ops, 1):
            if op > 0:
                recent = list(self.history)[-K:]
                in_same_run = (len(recent) == K and all(x == op for x in recent))
                smooth = self.gate_smooth and self._smooth_trend_with(op)
                if smooth and not self.disabled:
                    self.disabled = True
                    self.events.append({"op": self.operation, "event": "smooth-trend-disables"})
                if in_same_run and not self.disabled:
                    self.mode = "left-all"
                    if not self.run_policy_active:
                        self.events.append({"op": self.operation, "event": "run-left-start", "length": op})
                    self.run_policy_active = True
                else:
                    self.mode = "t46"
                    if self.run_policy_active:
                        self.events.append({"op": self.operation, "event": "run-left-reset", "length": op})
                    self.run_policy_active = False
                self.place(op)
                self.mode = "t46"
            elif op < 0:
                pid = -op
                valid = 0 < pid < len(self.pipes) and self.pipes[pid] is not None
                if valid:
                    self.deleted_parities.append(pid % 2)
                self.remove(pid)
                if self.gate_skew and len(self.deleted_parities) == DELETE_WINDOW:
                    counts = Counter(self.deleted_parities)
                    if counts.most_common(1)[0][1] * 100 >= DELETE_WINDOW * 85 and not self.disabled:
                        self.disabled = True
                        self.events.append({"op": self.operation, "event": "pid-parity-skew-disables"})
        return self.h


def run_case(case, gate_smooth=False, gate_skew=False):
    ops = bd.read_input(bd.ROOT / f"data/pipes/open/{case}.in")
    baseline = bd.OnlineSim("t46").run(ops)
    sim = RollingLeftSim(gate_smooth, gate_skew)
    candidate = sim.run(ops)
    return {
        "case": case,
        "baseline_t46_m": baseline,
        "candidate_m": candidate,
        "delta_m": candidate - baseline,
        "gate_smooth": gate_smooth,
        "gate_skew": gate_skew,
        "events": sim.events,
    }


def main():
    rows = [run_case(case, smooth, skew)
            for case in (5, 9)
            for smooth, skew in ((False, False), (True, False), (False, True), (True, True))]
    OUT.write_text(json.dumps({
        "scope": "offline causal screening only",
        "run_policy": f"left only when the incoming length matches the last {K} placements; reset on a length change",
        "smooth_gate": "latch disabled when current plus the last two distinct run lengths have equal increments",
        "skew_gate": f"latch disabled when >=85% of the last {DELETE_WINDOW} valid deleted PIDs share parity",
        "records": rows,
    }, indent=2) + "\n")
    for row in rows:
        print(f"case{row['case']} smooth={row['gate_smooth']} skew={row['gate_skew']} "
              f"H={row['baseline_t46_m']}->{row['candidate_m']} delta={row['delta_m']:+} events={row['events'][:8]}")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
