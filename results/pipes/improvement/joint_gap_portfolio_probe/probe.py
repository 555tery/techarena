#!/usr/bin/env python3
"""Offline ranking probe for causal joint-gap scenario values.

The observed input suffix is used only for evaluation. Forecast scenarios are
sampled from the already-observed 256-event history, then replayed over the
entire free-gap portfolio with the frozen allocator's greedy placement rule.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import random
import subprocess
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
DIG = 20
HISTORY_WINDOW = 2048
OBS_WINDOW = 256
UNFIT_SCALE = 60
SCENARIO_DEPTH = 4
SCENARIO_TRIALS = 16


@dataclass
class Pipe:
    pid: int
    start: int
    length: int
    cohort: int


@dataclass(frozen=True)
class Action:
    start: int
    high_side: bool
    label: str


class Sim:
    def __init__(self) -> None:
        self.gaps: dict[int, tuple[int, int]] = {}
        self.active: list[Pipe] = []
        self.trench = 0
        self.next_pid = 1
        self.length_history: deque[int] = deque()
        self.length_freq = [0] * 41
        self.length_occurrences = [0] * 41
        self.removed_cohort = [[0, 0] for _ in range(41)]
        self.observations: deque[tuple[int, int]] = deque(maxlen=OBS_WINDOW)
        self.parity_cohort_mode = False
        self.run_left_disabled = False
        self.alternating_delete_mode = False
        self.predicted_deleted_parity = 1
        self.last_deleted_pid = -1
        self.last_deleted_length = -1
        self.stride_two_transitions = 0

    def clone(self) -> "Sim":
        return copy.deepcopy(self)

    def _runs_from_newest(self) -> list[int]:
        runs: list[int] = []
        last = -1
        for value in reversed(self.length_history):
            if value != last:
                runs.append(value)
                last = value
                if len(runs) == 3:
                    break
        return runs

    def has_steady_trend(self) -> bool:
        if len(self.length_history) < 128:
            return False
        runs = self._runs_from_newest()
        return len(runs) >= 3 and runs[0] - runs[1] == runs[1] - runs[2]

    def has_same_run(self, length: int, need: int = 46) -> bool:
        if len(self.length_history) < need:
            return False
        return all(value == length for value in list(self.length_history)[-need:])

    def has_smooth_trend_with(self, current_length: int) -> bool:
        if not self.length_history:
            return False
        history = list(self.length_history)
        current_already_in_history = history[-1] == current_length
        prior: list[int] = []
        first_run = True
        last_run = -1
        for value in reversed(history):
            if first_run:
                first_run = False
                last_run = value
                if not current_already_in_history:
                    prior.append(value)
                continue
            if value == last_run:
                continue
            last_run = value
            prior.append(value)
            if len(prior) == 2:
                break
        return len(prior) == 2 and current_length - prior[0] == prior[0] - prior[1]

    def high_side(self, length: int) -> bool:
        if self.has_smooth_trend_with(length):
            self.run_left_disabled = True
        run_active = not self.run_left_disabled and self.has_same_run(length)
        if run_active:
            return self.length_occurrences[length] % 2 != 0
        if self.alternating_delete_mode:
            return (self.next_pid & 1) != self.predicted_deleted_parity
        if self.parity_cohort_mode:
            return self.length_occurrences[length] % 2 == 0
        return length <= 4 or self.has_same_run(length)

    def fit_score(self, gap_length: int, length: int) -> int:
        slack = gap_length - length
        score = slack * len(self.length_history)
        if 0 < slack <= 40:
            score += UNFIT_SCALE * sum(self.length_freq[slack + 1 : 41])
        return score

    def _best_gap_from(self, length: int, high_side: bool, cohort: int | None) -> int | None:
        entries: list[tuple[int, int, int]] = []
        for start, (end, gap_cohort) in self.gaps.items():
            if cohort is not None and gap_cohort != cohort:
                continue
            gap_length = end - start
            if gap_length >= length:
                entries.append((gap_length, start, gap_cohort))
        entries.sort()
        if not entries:
            return None
        best_start: int | None = None
        best_score: int | None = None
        last_size: int | None = None
        for gap_length, start, _ in entries:
            if gap_length == last_size:
                continue
            last_size = gap_length
            score = self.fit_score(gap_length, length)
            if best_score is None or score < best_score:
                best_start, best_score = start, score
            elif score == best_score and best_start is not None:
                if (high_side and start > best_start) or (not high_side and start < best_start):
                    best_start = start
            if gap_length - length > 40:
                break
        return best_start

    def best_gap(self, length: int, high_side: bool, size_cohort: int) -> int | None:
        if self.parity_cohort_mode:
            preferred_exists = any(
                end - start >= length and cohort == size_cohort
                for start, (end, cohort) in self.gaps.items()
            )
            cohort = size_cohort if preferred_exists else -1
            return self._best_gap_from(length, high_side, cohort)
        return self._best_gap_from(length, high_side, None)

    def _add_gap(self, start: int, end: int, cohort: int) -> None:
        if start >= end:
            return
        left = start
        right = end
        merged_cohort = cohort
        overlapping = [
            (gap_start, gap_end, gap_cohort)
            for gap_start, (gap_end, gap_cohort) in self.gaps.items()
            if gap_start <= right and gap_end >= left
        ]
        for gap_start, gap_end, gap_cohort in overlapping:
            if gap_cohort != merged_cohort:
                merged_cohort = -1
            left = min(left, gap_start)
            right = max(right, gap_end)
            del self.gaps[gap_start]
        self.gaps[left] = (right, merged_cohort)

    def _place_at(self, gap_start: int, length: int, high_side: bool) -> tuple[int, int]:
        end, cohort = self.gaps.pop(gap_start)
        start = end - length if high_side else gap_start
        if gap_start < start:
            self._add_gap(gap_start, start, cohort)
        pipe_end = start + length
        if pipe_end < end:
            self._add_gap(pipe_end, end, cohort)
        return start, cohort

    def _append_pipe(self, length: int, start: int, size_cohort: int) -> None:
        self.active.append(Pipe(self.next_pid, start, length, size_cohort))
        self.next_pid += 1
        self.length_occurrences[length] += 1
        self.length_history.append(length)
        self.length_freq[length] += 1
        if len(self.length_history) > HISTORY_WINDOW:
            oldest = self.length_history.popleft()
            self.length_freq[oldest] -= 1

    def place_candidate(self, length: int, action: Action) -> tuple[int, int]:
        size_cohort = self.length_occurrences[length] % 2
        start, _ = self._place_at(action.start, length, action.high_side)
        self._append_pipe(length, start, size_cohort)
        self.observations.append((1, length))
        return 0, start

    def tail_start(self) -> int | None:
        if not self.gaps:
            return None
        start = max(self.gaps)
        return start if self.gaps[start][0] == self.trench else None

    def place(self, length: int, record_observation: bool = True) -> tuple[int, int]:
        size_cohort = self.length_occurrences[length] % 2
        high_side = self.high_side(length)
        gap = self.best_gap(length, high_side, size_cohort)
        digs = 0
        if gap is not None:
            start, _ = self._place_at(gap, length, high_side)
        else:
            tail = self.tail_start()
            tail_cohort = size_cohort if self.parity_cohort_mode else -1
            preserve_foreign_tail = False
            if self.parity_cohort_mode and tail is not None:
                tail_cohort = self.gaps[tail][1]
                preserve_foreign_tail = tail_cohort >= 0 and tail_cohort != size_cohort
                if preserve_foreign_tail:
                    tail_cohort = size_cohort
            tail_start = self.trench if tail is None or preserve_foreign_tail else tail
            tail_length = self.trench - tail_start
            digs = max(0, (length - tail_length + DIG - 1) // DIG)
            if tail is not None and not preserve_foreign_tail:
                del self.gaps[tail]
            self.trench += digs * DIG
            start = self.trench - length if self.parity_cohort_mode and high_side and not preserve_foreign_tail else tail_start
            if tail_start < start:
                self._add_gap(tail_start, start, tail_cohort)
            remainder_start = start + length
            if remainder_start < self.trench:
                self._add_gap(remainder_start, self.trench, tail_cohort)
        self._append_pipe(length, start, size_cohort)
        if record_observation:
            self.observations.append((1, length))
        return digs, start

    def _record_delete_pattern(self, pid: int, length: int) -> None:
        if self.last_deleted_pid >= 0 and self.last_deleted_length == length and pid == self.last_deleted_pid + 2:
            self.stride_two_transitions += 1
        else:
            self.stride_two_transitions = 0
            self.alternating_delete_mode = False
        if self.stride_two_transitions >= 7:
            self.alternating_delete_mode = True
            self.predicted_deleted_parity = pid & 1
        self.last_deleted_pid = pid
        self.last_deleted_length = length

    def remove_pipe(self, index: int, record_observation: bool = True, rank_permille: int | None = None) -> int:
        pipe = self.active.pop(index)
        self._add_gap(pipe.start, pipe.start + pipe.length, pipe.cohort)
        self._record_delete_pattern(pipe.pid, pipe.length)
        self.removed_cohort[pipe.length][pipe.cohort] += 1
        total = sum(self.removed_cohort[pipe.length])
        dominant = max(self.removed_cohort[pipe.length])
        if total >= 8 and dominant * 100 >= total * 85 and self.has_steady_trend():
            self.parity_cohort_mode = True
        if record_observation:
            if rank_permille is None:
                newer = sum(1 for active in self.active if active.pid > pipe.pid)
                n = len(self.active) + 1
                rank_permille = 0 if n <= 1 else newer * 1000 // (n - 1)
            self.observations.append((-1, rank_permille))
        return pipe.start

    def remove_pid(self, pid: int, record_observation: bool = True) -> int:
        for idx, pipe in enumerate(self.active):
            if pipe.pid == pid:
                return self.remove_pipe(idx, record_observation)
        raise ValueError(f"unknown active pid {pid}")

    def remove_rank(self, rank_permille: int) -> int | None:
        if not self.active:
            return None
        n = len(self.active)
        rank = 0 if n <= 1 else rank_permille * (n - 1) // 1000
        index = n - 1 - min(rank, n - 1)
        return self.remove_pipe(index, rank_permille=rank_permille)

    def apply_observation(self, event: tuple[int, int]) -> None:
        kind, value = event
        if kind > 0:
            self.place(value)
        elif kind < 0:
            self.remove_rank(value)

    def tail_option_cost(self) -> float:
        tail = self.tail_start()
        tail_length = 0 if tail is None else self.trench - tail
        total = sum(self.length_freq)
        if total == 0:
            return 0.0
        cost_numerator = 0
        internal_gaps = [
            end - start for start, (end, _) in self.gaps.items() if start != tail
        ]
        for length in range(1, 41):
            frequency = self.length_freq[length]
            if frequency == 0 or any(gap_length >= length for gap_length in internal_gaps):
                continue
            deficit = max(0, length - tail_length)
            digs = ((deficit + DIG - 1) // DIG) * DIG
            cost_numerator += frequency * digs
        return cost_numerator / total


def parse_commands(path: Path) -> list[int]:
    lines = path.read_text(encoding="utf-8").split()
    if len(lines) < 3:
        raise RuntimeError(f"malformed input header: {path}")
    count = int(lines[1])
    commands = [int(token) for token in lines[2:]]
    if len(commands) != count + 1 or commands[-1] != 0:
        raise RuntimeError(f"input count/terminator mismatch: {path}")
    return commands


def read_solver_outputs(binary: Path, commands: list[int]) -> list[list[int]]:
    proc = subprocess.run(
        [str(binary)], input="\n".join(map(str, commands)) + "\n",
        text=True, capture_output=True, check=True,
    )
    lines = [line.strip() for line in proc.stdout.splitlines()]
    expected = sum(command != 0 for command in commands)
    if len(lines) != expected:
        raise RuntimeError(f"solver emitted {len(lines)} lines for {expected} commands")
    return [[int(token) for token in line.split()] for line in lines]


def baseline_action_list(sim: Sim, length: int) -> tuple[list[Action], Action]:
    high_side = sim.high_side(length)
    selected = sim.best_gap(length, high_side, sim.length_occurrences[length] % 2)
    if selected is None:
        return [], Action(-1, high_side, "no-fit")
    baseline = Action(selected, high_side, "baseline")
    candidates: list[tuple[int, int, int]] = []
    for start, (end, cohort) in sim.gaps.items():
        gap_length = end - start
        if gap_length < length:
            continue
        if sim.parity_cohort_mode:
            preferred_exists = any(
                gap_end - gap_start >= length and gap_cohort == sim.length_occurrences[length] % 2
                for gap_start, (gap_end, gap_cohort) in sim.gaps.items()
            )
            if preferred_exists and cohort != sim.length_occurrences[length] % 2:
                continue
            if not preferred_exists and cohort >= 0:
                continue
        candidates.append((sim.fit_score(gap_length, length), start, gap_length))
    candidates.sort(key=lambda item: (item[0], -item[1] if high_side else item[1]))
    options = [Action(start, high_side, "ranked-gap") for _, start, gap_len in candidates if gap_len - length <= 40][:3]
    if baseline not in options:
        options.insert(0, baseline)
    tail = sim.tail_start()
    if tail is not None and sim.gaps[tail][0] - tail >= length:
        tail_action = Action(tail, high_side, "tail")
        if tail_action not in options:
            options.append(tail_action)
    dedup: list[Action] = []
    seen: set[tuple[int, bool]] = set()
    for option in options:
        key = (option.start, option.high_side)
        if key not in seen:
            dedup.append(option)
            seen.add(key)
    return dedup, baseline


def potential_loss(sim: Sim, gap_length: int, length: int, cap: int = 40) -> int:
    before = min(gap_length, cap)
    after = min(gap_length - length, cap)
    return sum(sim.length_freq[request] * (before // request - after // request)
               for request in range(1, 41))


def sample_scenarios(sim: Sim, state_key: int, length: int) -> list[list[tuple[int, int]]]:
    history = list(sim.observations)
    n = len(history)
    depth = SCENARIO_DEPTH
    if n < depth + 2:
        return []
    minimum = n - min(n, 128)
    maximum = n - depth
    possible: list[int] = []
    max_context = min(3, n - 1)
    for context in range(max_context, 0, -1):
        suffix = history[n - context :]
        possible = [
            start for start in range(minimum + context, maximum + 1)
            if all(
                history[start - context + offset][0] == suffix[offset][0]
                and (suffix[offset][0] <= 0 or history[start - context + offset][1] == suffix[offset][1])
                for offset in range(context)
            )
        ]
        if possible:
            break
    if not possible:
        possible = list(range(minimum, maximum + 1))
    seed = (state_key * 0x85EBCA6B) ^ (length * 0xC2B2AE35) ^ sim.trench ^ 0x9E3779B9
    rng = random.Random(seed & 0xFFFFFFFF)
    return [history[start : start + depth] for start in (rng.choice(possible) for _ in range(SCENARIO_TRIALS))]


def portfolio_score(sim: Sim, length: int, action: Action, scenarios: list[list[tuple[int, int]]]) -> float:
    values: list[float] = []
    for scenario in scenarios:
        rolled = sim.clone()
        rolled.place_candidate(length, action)
        for event in scenario:
            rolled.apply_observation(event)
        values.append(float(rolled.trench - sim.trench) + rolled.tail_option_cost())
    return sum(values) / max(1, len(values))


def actual_suffix_cost(sim: Sim, length: int, action: Action, suffix: Iterable[int]) -> int:
    rolled = sim.clone()
    rolled.place_candidate(length, action)
    for command in suffix:
        if command == 0:
            break
        if command > 0:
            rolled.place(command)
        else:
            rolled.remove_pid(-command)
    return rolled.trench - sim.trench


def ranking_accuracy(scores: list[float], actual: list[int]) -> float | None:
    correct = 0.0
    total = 0
    for i in range(len(actual)):
        for j in range(i + 1, len(actual)):
            if actual[i] == actual[j]:
                continue
            total += 1
            if scores[i] == scores[j]:
                correct += 0.5
            elif (scores[i] < scores[j]) == (actual[i] < actual[j]):
                correct += 1.0
    return None if total == 0 else correct / total


def chosen_regret(scores: list[float], actual: list[int]) -> int:
    best = min(range(len(scores)), key=lambda i: (scores[i], i))
    return actual[best] - min(actual)


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def paired_stream_bootstrap(rows: list[dict], samples: int = 20_000) -> dict:
    """Paired percentile bootstrap over informative streams, not state rows."""
    informative = [row for row in rows if row["actual_spread_m"] > 0]
    grouped: dict[str, list[dict]] = {}
    for row in informative:
        grouped.setdefault(row["stream"], []).append(row)
    per_stream: dict[str, dict[str, float]] = {}
    for stream, stream_rows in sorted(grouped.items()):
        pairwise_rows = [row for row in stream_rows if row["baseline_pairwise_accuracy"] is not None]
        per_stream[stream] = {
            "baseline_pairwise_accuracy": sum(row["baseline_pairwise_accuracy"] for row in pairwise_rows) / len(pairwise_rows),
            "portfolio_pairwise_accuracy": sum(row["portfolio_pairwise_accuracy"] for row in pairwise_rows) / len(pairwise_rows),
            "baseline_regret_m": sum(row["baseline_regret_m"] for row in stream_rows) / len(stream_rows),
            "portfolio_regret_m": sum(row["portfolio_regret_m"] for row in stream_rows) / len(stream_rows),
        }
    names = sorted(per_stream)
    accuracy_deltas = [
        per_stream[name]["portfolio_pairwise_accuracy"] - per_stream[name]["baseline_pairwise_accuracy"]
        for name in names
    ]
    regret_deltas = [
        per_stream[name]["portfolio_regret_m"] - per_stream[name]["baseline_regret_m"]
        for name in names
    ]
    rng = random.Random(20261017)

    def interval(values: list[float]) -> list[float]:
        boot = [
            sum(values[rng.randrange(len(values))] for _ in values) / len(values)
            for _ in range(samples)
        ]
        return [percentile(boot, 0.025), percentile(boot, 0.975)]

    return {
        "unit": "informative stream (equal stream weight)",
        "informative_streams": len(names),
        "bootstrap_samples": samples,
        "bootstrap_seed": 20261017,
        "portfolio_minus_baseline_pairwise_accuracy": {
            "mean_delta": sum(accuracy_deltas) / len(accuracy_deltas),
            "percentile_95_ci": interval(accuracy_deltas),
            "streams_improved": sum(value > 0 for value in accuracy_deltas),
            "streams_worsened": sum(value < 0 for value in accuracy_deltas),
            "streams_tied": sum(value == 0 for value in accuracy_deltas),
        },
        "portfolio_minus_baseline_top1_regret_m": {
            "mean_delta": sum(regret_deltas) / len(regret_deltas),
            "percentile_95_ci": interval(regret_deltas),
            "streams_improved": sum(value < 0 for value in regret_deltas),
            "streams_worsened": sum(value > 0 for value in regret_deltas),
            "streams_tied": sum(value == 0 for value in regret_deltas),
        },
        "per_stream": per_stream,
    }


def evaluate_stream(path: Path, binary: Path) -> tuple[list[dict], dict]:
    commands = parse_commands(path)
    outputs = read_solver_outputs(binary, commands)
    sim = Sim()
    rows: list[dict] = []
    output_index = 0
    placements_seen = 0
    checks = 0
    for i, command in enumerate(commands):
        if command == 0:
            break
        if command > 0:
            options, baseline = baseline_action_list(sim, command)
            # Sample at a fixed cadence to avoid selecting states by observed outcome.
            if (i >= 180 and i % 60 == 0 and len(options) >= 2
                    and len(sim.observations) >= 16 and i + 20 < len(commands)):
                scenarios = sample_scenarios(sim, i + 1, command)
                if scenarios:
                    actual = [actual_suffix_cost(sim, command, action, commands[i + 1 :]) for action in options]
                    base_scores = [sim.fit_score(sim.gaps[action.start][0] - action.start, command)
                                   for action in options]
                    pot_scores = [potential_loss(sim, sim.gaps[action.start][0] - action.start, command)
                                  for action in options]
                    portfolio_scores = [portfolio_score(sim, command, action, scenarios) for action in options]
                    rows.append({
                        "stream": path.stem,
                        "command_index": i,
                        "request_length": command,
                        "candidate_count": len(options),
                        "actual_best_growth_m": min(actual),
                        "actual_worst_growth_m": max(actual),
                        "actual_spread_m": max(actual) - min(actual),
                        "baseline_pairwise_accuracy": ranking_accuracy(base_scores, actual),
                        "potential_pairwise_accuracy": ranking_accuracy(pot_scores, actual),
                        "portfolio_pairwise_accuracy": ranking_accuracy(portfolio_scores, actual),
                        "baseline_regret_m": chosen_regret(base_scores, actual),
                        "potential_regret_m": chosen_regret(pot_scores, actual),
                        "portfolio_regret_m": chosen_regret(portfolio_scores, actual),
                        "baseline_action_growth_m": next(
                            actual[j] for j, option in enumerate(options)
                            if (option.start, option.high_side) == (baseline.start, baseline.high_side)
                        ),
                        "baseline_score_choice_growth_m": actual[min(range(len(base_scores)), key=lambda j: (base_scores[j], j))],
                        "potential_choice_growth_m": actual[min(range(len(pot_scores)), key=lambda j: (pot_scores[j], j))],
                        "portfolio_choice_growth_m": actual[min(range(len(portfolio_scores)), key=lambda j: (portfolio_scores[j], j))],
                    })
            digs, start = sim.place(command)
            expected = [digs, start]
            actual_output = outputs[output_index]
            output_index += 1
            if actual_output != expected:
                raise RuntimeError(
                    f"Python baseline diverged from C++ at {path.name}:{i}: "
                    f"expected {expected}, got {actual_output}"
                )
            placements_seen += 1
        else:
            start = sim.remove_pid(-command)
            actual_output = outputs[output_index]
            output_index += 1
            if actual_output != [start]:
                raise RuntimeError(
                    f"Python baseline diverged from C++ at {path.name}:{i}: "
                    f"expected {[start]}, got {actual_output}"
                )
        checks += 1
    return rows, {"stream": path.stem, "commands": checks, "placements": placements_seen,
                  "candidate_states": len(rows), "transcript_matches": True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, default=HERE / "inputs")
    args = parser.parse_args()
    streams = sorted(args.inputs.glob("*.in"))
    all_rows: list[dict] = []
    stream_checks: list[dict] = []
    for stream in streams:
        rows, check = evaluate_stream(stream, args.solver.resolve())
        all_rows.extend(rows)
        stream_checks.append(check)
    out_csv = HERE / "ranking_states.csv"
    if all_rows:
        with out_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]))
            writer.writeheader()
            writer.writerows(all_rows)
    finite_rows = [row for row in all_rows if row["actual_spread_m"] > 0]
    names = ("baseline", "potential", "portfolio")
    summary = {
        "streams": stream_checks,
        "state_count": len(all_rows),
        "informative_state_count": len(finite_rows),
        "scenario_depth": SCENARIO_DEPTH,
        "scenario_trials": SCENARIO_TRIALS,
        "paired_stream_bootstrap": paired_stream_bootstrap(all_rows),
        "metrics": {
            name: {
                "pairwise_accuracy_mean": (
                    sum(row[f"{name}_pairwise_accuracy"] for row in finite_rows
                        if row[f"{name}_pairwise_accuracy"] is not None)
                    / max(1, sum(row[f"{name}_pairwise_accuracy"] is not None for row in finite_rows))
                ),
                "mean_regret_m": sum(row[f"{name}_regret_m"] for row in finite_rows) / max(1, len(finite_rows)),
                "zero_regret_fraction": sum(row[f"{name}_regret_m"] == 0 for row in finite_rows) / max(1, len(finite_rows)),
            }
            for name in names
        },
    }
    (HERE / "ranking_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["metrics"], indent=2))
    print(f"states={len(all_rows)} informative={len(finite_rows)}")


if __name__ == "__main__":
    main()
