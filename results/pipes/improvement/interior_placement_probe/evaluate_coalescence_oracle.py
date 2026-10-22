#!/usr/bin/env python3
"""Exact tiny-suffix evaluation for preregistered state-only coalescence cases."""
from __future__ import annotations
import functools
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASE_DIR = ROOT / "coalescence_cases"


def read_trace(path: Path) -> list[dict]:
    blocks: list[dict] = []
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "IPROB":
            current = {"pid": int(fields[1]), "length": int(fields[2]),
                       "baseline_gap": int(fields[3]), "baseline_start": int(fields[4]),
                       "best_index": int(fields[6]), "actions": []}
            blocks.append(current)
        elif fields[0] == "IPACT" and current is not None:
            current["actions"].append({"index": int(fields[1]), "gap": int(fields[2]),
                                       "start": int(fields[3]), "predicted_sum": int(fields[4])})
    return blocks


def oracle(case: dict, current_start: int) -> tuple[int, int]:
    trench = case["trench"]
    left_start = case["left_fill"] + case["left_ext"]
    right_start = left_start + case["left_anchor"] + case["target_gap"]
    right_fill_start = right_start + case["right_anchor"] + case["right_ext"]
    active0 = ((1, 0, case["left_fill"]),
               (2, left_start, case["left_anchor"]),
               (3, right_start, case["right_anchor"]),
               (4, right_fill_start, case["right_fill"]))
    current = (5, current_start, case["probe_length"])
    future = case["future_length"]
    suffix = (-2, future, -3, future)
    total_bound = sum(x[2] for x in active0) + case["probe_length"] + sum(x for x in suffix if x > 0)
    upper_t = max(trench, 20 * ((total_bound + 19) // 20))
    future_pid = {}
    next_pid = 6
    for i, cmd in enumerate(suffix):
        if cmd > 0:
            future_pid[i] = next_pid
            next_pid += 1
    nodes = 0

    @functools.lru_cache(maxsize=None)
    def dp(i: int, t: int, state: tuple[tuple[int, int, int], ...]) -> int:
        nonlocal nodes
        nodes += 1
        if nodes > 1_500_000:
            raise RuntimeError(f"state cap exceeded for seed {case['seed']}")
        if i == len(suffix):
            return t
        cmd = suffix[i]
        pipes = {pid: (start, length) for pid, start, length in state}
        if cmd < 0:
            if -cmd not in pipes:
                raise ValueError(f"missing PID {-cmd} in suffix for seed {case['seed']}")
            del pipes[-cmd]
            packed = tuple(sorted((pid, s, length) for pid, (s, length) in pipes.items()))
            return dp(i + 1, t, packed)
        occupied = sorted((s, s + length) for s, length in pipes.values())
        best = upper_t
        for new_t in range(t, upper_t + 1, 20):
            for start in range(new_t - cmd + 1):
                end = start + cmd
                if any(start < right and end > left for left, right in occupied):
                    continue
                pipes[future_pid[i]] = (start, cmd)
                packed = tuple(sorted((pid, s, length) for pid, (s, length) in pipes.items()))
                value = dp(i + 1, new_t, packed)
                del pipes[future_pid[i]]
                if value < best:
                    best = value
                    if best == t:
                        return best
        return best

    init = tuple(sorted(active0 + (current,)))
    return dp(0, trench, init), nodes


def evaluate_group(split: str, cases: list[dict], trace: list[dict], selected: dict[int, int]) -> dict:
    rows = []
    for case, block in zip(cases, trace, strict=True):
        target_start = case["left_fill"] + case["left_ext"] + case["left_anchor"]
        target_end = target_start + case["target_gap"]
        probe = case["probe_length"]
        legal_starts = list(range(target_start, target_end - probe + 1))
        all_values = {}
        total_states = 0
        for start in legal_starts:
            value, states = oracle(case, start)
            all_values[start] = value
            total_states += states
        candidate_values = [all_values[action["start"]] for action in block["actions"]]
        best_idx = block["best_index"]
        chosen_start = selected[case["seed"]]
        oracle_best = min(all_values.values())
        baseline_start = target_end - probe
        opposite_start = target_start
        center_start = target_start + (case["target_gap"] - probe) // 2
        rows.append({
            "seed": case["seed"], "split": split,
            "parameters": {k: case[k] for k in ("trench", "left_ext", "left_anchor", "target_gap", "probe_length", "future_length")},
            "candidate_actions": len(block["actions"]),
            "baseline_right_edge_T": all_values[baseline_start],
            "opposite_left_edge_T": all_values[opposite_start],
            "center_T": all_values[center_start],
            "causal_rollout_best_index": best_idx,
            "causal_rollout_best_start": block["actions"][best_idx]["start"],
            "causal_rollout_best_exact_T": all_values[block["actions"][best_idx]["start"]],
            "actual_selected_start": chosen_start,
            "actual_selected_exact_T": all_values[chosen_start],
            "all_position_oracle_best_T": oracle_best,
            "all_position_oracle_best_starts": [s for s, v in all_values.items() if v == oracle_best],
            "exact_values_by_candidate": candidate_values,
            "rollout_sums_by_candidate": [a["predicted_sum"] for a in block["actions"]],
            "causal_regret_m": all_values[chosen_start] - oracle_best,
            "oracle_states_evaluated": total_states,
        })
    return {
        "split": split,
        "n": len(rows),
        "mc_best_matches_all_position_oracle": sum(r["causal_rollout_best_exact_T"] == r["all_position_oracle_best_T"] for r in rows),
        "actual_policy_matches_oracle": sum(r["causal_regret_m"] == 0 for r in rows),
        "mean_actual_regret_m": statistics.mean(r["causal_regret_m"] for r in rows),
        "edge_baseline_strictly_worse_than_center": sum(r["baseline_right_edge_T"] > r["center_T"] for r in rows),
        "edge_opposite_strictly_worse_than_center": sum(r["opposite_left_edge_T"] > r["center_T"] for r in rows),
        "rows": rows,
    }


def read_cases(split: str) -> list[dict]:
    manifest = json.loads((CASE_DIR / "manifest.json").read_text())
    cases = [dict(zip(manifest["keys"], row, strict=True)) for row in manifest["cases"]]
    return [case for case in cases if case["split"] == split]


def read_selected(path: Path) -> dict[int, int]:
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if fields and fields[0] == "CASE":
            result[int(fields[1])] = int(fields[3])
    return result


def main() -> None:
    result = {}
    for split in ("train", "holdout"):
        cases = read_cases(split)
        blocks = read_trace(CASE_DIR / f"{split}.trace")
        if len(cases) != len(blocks):
            raise ValueError(f"{split}: cases={len(cases)} trace blocks={len(blocks)}")
        result[split] = evaluate_group(split, cases, blocks,
                                       read_selected(CASE_DIR / f"{split}.stdout"))
    out = ROOT / "coalescence_oracle_results.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for split, summary in result.items():
        print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    print(f"out={out}")


if __name__ == "__main__":
    main()
