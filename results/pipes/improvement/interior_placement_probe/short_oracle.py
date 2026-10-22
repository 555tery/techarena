#!/usr/bin/env python3
"""Compare the causal rollout ranking with an exact tiny-suffix oracle."""

from __future__ import annotations

import argparse
import functools
import json
import math
import statistics
from pathlib import Path


def parse_case(path: Path) -> list[int]:
    tokens = path.read_text(encoding="ascii").split()
    return [int(x) for x in tokens[2:]]


def parse_trace(path: Path) -> dict[int, dict]:
    result: dict[int, dict] = {}
    current = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "IPROB":
            _, prev_pid, length, gap, baseline, count, best = fields
            current = {
                "prev_pid": int(prev_pid), "length": int(length),
                "gap": int(gap), "baseline": int(baseline),
                "count": int(count), "best": int(best), "actions": [],
            }
            result[current["prev_pid"]] = current
        elif fields[0] == "IPACT" and current is not None:
            _, index, gap, start, total = fields
            current["actions"].append({
                "index": int(index), "gap": int(gap), "start": int(start),
                "rollout_total_trench": int(total),
            })
    return result


def replay_prefix(commands: list[int], answers: list[str], stop: int):
    trench = 0
    active: dict[int, tuple[int, int]] = {}
    pid = 0
    history: list[int] = []
    for i, command in enumerate(commands[:stop]):
        fields = answers[i].split()
        if command > 0:
            digs, start = map(int, fields)
            trench += 20 * digs
            pid += 1
            active[pid] = (start, command)
            history.append(command)
        else:
            del active[-command]
    return trench, active, pid + 1, history


def exact_rank(commands: list[int], answers: list[str], decision_index: int,
               trace: dict) -> dict:
    command = commands[decision_index]
    if command <= 0:
        raise ValueError("trace decision must refer to a placement")
    trench, active, next_pid, _history = replay_prefix(commands, answers, decision_index)
    actions = trace["actions"]
    suffix = tuple(commands[decision_index + 1:])
    max_total = (sum(length for _, length in active.values()) + command
                 + sum(x for x in suffix if x > 0))
    upper_t = max(trench, 20 * ((max_total + 19) // 20))
    node_counter = [0]

    @functools.lru_cache(maxsize=None)
    def dp(event_index: int, t: int, state: tuple[tuple[int, int, int], ...]) -> int:
        node_counter[0] += 1
        if node_counter[0] > 1_500_000:
            raise RuntimeError("exact oracle state cap exceeded")
        if event_index == len(suffix):
            return t
        cmd = suffix[event_index]
        state_map = {p: (s, length) for p, s, length in state}
        if cmd < 0:
            if -cmd not in state_map:
                raise ValueError(f"invalid suffix deletion {-cmd}")
            del state_map[-cmd]
            packed = tuple(sorted((p, s, length) for p, (s, length) in state_map.items()))
            return dp(event_index + 1, t, packed)

        occupied = sorted((s, s + length) for s, length in state_map.values())
        best = upper_t
        for new_t in range(t, upper_t + 1, 20):
            if new_t >= best:
                break
            latest = new_t - cmd
            for start in range(latest + 1):
                end = start + cmd
                if any(start < right and end > left for left, right in occupied):
                    continue
                state_map[pid_at_event[event_index]] = (start, cmd)
                packed = tuple(sorted((p, s, length) for p, (s, length) in state_map.items()))
                value = dp(event_index + 1, new_t, packed)
                del state_map[pid_at_event[event_index]]
                if value < best:
                    best = value
                    if best == t:
                        return best
            if new_t == upper_t:
                break
        return best

    # Future command PID numbers are deterministic from positive commands.
    pid_at_event: dict[int, int] = {}
    next_future_pid = next_pid + 1
    for i, cmd in enumerate(suffix):
        if cmd > 0:
            pid_at_event[i] = next_future_pid
            next_future_pid += 1

    oracle_values = []
    predicted_values = []
    for action in actions:
        gap_start, start = action["gap"], action["start"]
        # Candidate actions must be fully contained in their reported free gap.
        gaps = []
        cursor = 0
        for _pid, (pipe_start, length) in sorted(active.items(), key=lambda item: item[1][0]):
            if cursor < pipe_start:
                gaps.append((cursor, pipe_start))
            cursor = pipe_start + length
        if cursor < trench:
            gaps.append((cursor, trench))
        gap_end = next((b for a, b in gaps if a == gap_start), None)
        if gap_end is None or start < gap_start or start + command > gap_end:
            raise ValueError(f"invalid trace action {action} for gaps={gaps}")
        state_after = dict(active)
        state_after[next_pid] = (start, command)
        packed = tuple(sorted((p, s, length) for p, (s, length) in state_after.items()))
        oracle_values.append(dp(0, trench, packed))
        predicted_values.append(action["rollout_total_trench"])

    predicted_best = min(range(len(actions)), key=lambda i: (predicted_values[i], i))
    oracle_best = min(range(len(actions)), key=lambda i: (oracle_values[i], i))
    order = sorted(range(len(actions)), key=lambda i: (predicted_values[i], i))
    oracle_best_set = {i for i, x in enumerate(oracle_values) if x == min(oracle_values)}
    predicted_action = trace["best"] if trace["best"] in range(len(actions)) else predicted_best
    return {
        "probe_pid": next_pid,
        "request_length": command,
        "actions": len(actions),
        "predicted_best_index": predicted_action,
        "oracle_best_indices": sorted(oracle_best_set),
        "predicted_best_is_oracle_best": predicted_action in oracle_best_set,
        "oracle_regret_m": oracle_values[predicted_action] - min(oracle_values),
        "spearman_rho": spearman(predicted_values, oracle_values),
        "predicted_rank_of_oracle_best": order.index(oracle_best),
        "oracle_values_m": oracle_values,
        "predicted_rollout_means_m": [x / 12 for x in predicted_values],
        "exact_dp_states": node_counter[0],
    }


def spearman(a: list[int], b: list[int]) -> float:
    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        result = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i + 1
            while j < len(order) and values[order[j]] == values[order[i]]:
                j += 1
            rank = (i + j - 1) / 2.0
            for k in range(i, j):
                result[order[k]] = rank
            i = j
        return result
    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    va = sum((x - ma) ** 2 for x in ra)
    vb = sum((x - mb) ** 2 for x in rb)
    if va == 0 or vb == 0:
        return 1.0 if a == b else 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / math.sqrt(va * vb)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summaries = []
    for input_path in sorted(args.inputs.glob("*.in")):
        run_dir = args.run / "runs" / input_path.stem
        if not run_dir.exists():
            matches = list((args.run / "runs").glob("*/"))
            matches = [item for item in matches if item.name == input_path.stem]
            if len(matches) != 1:
                raise FileNotFoundError(f"cannot resolve harness run for {input_path}")
            run_dir = matches[0]
        commands = parse_case(input_path)
        answers = (run_dir / "judge_output.txt").read_text(encoding="ascii").splitlines()
        trace = parse_trace(run_dir / "solver_stderr.txt")
        decisions = []
        for i, command in enumerate(commands):
            if command > 0:
                prev_pid = sum(1 for x in commands[:i] if x > 0)
                if prev_pid in trace:
                    decisions.append(exact_rank(commands, answers, i, trace[prev_pid]))
        if decisions:
            summaries.extend({"input": input_path.name, **x} for x in decisions)
    args.out.write_text(json.dumps({"decisions": summaries}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision_count": len(summaries),
        "oracle_best_match_rate": statistics.mean(x["predicted_best_is_oracle_best"] for x in summaries) if summaries else None,
        "mean_oracle_regret_m": statistics.mean(x["oracle_regret_m"] for x in summaries) if summaries else None,
        "mean_spearman_rho": statistics.mean(x["spearman_rho"] for x in summaries) if summaries else None,
        "mean_oracle_best_rank": statistics.mean(x["predicted_rank_of_oracle_best"] for x in summaries) if summaries else None,
        "out": str(args.out),
    }, indent=2))


if __name__ == "__main__":
    main()
