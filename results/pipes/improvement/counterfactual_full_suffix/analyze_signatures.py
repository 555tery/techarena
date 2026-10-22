#!/usr/bin/env python3
"""Reconstruct exact baseline geometry and locate state-similar events."""
from __future__ import annotations

import bisect
import json
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INPUT = ROOT / "data/pipes/open/15.in"
TRACE = ROOT / "results/pipes/final/open-run-size-cohort-lanes/runs/15/judge_output.txt"
ROWS = ROOT / "results/pipes/improvement/counterfactual_full_suffix/case15_120.jsonl"
OUT = ROOT / "results/pipes/improvement/counterfactual_full_suffix/similar_sites.json"


def remove_gap(gaps: dict[int, int], starts: list[int], hist: list[int],
               size_count: Counter[int], start: int) -> int:
    end = gaps.pop(start)
    ix = bisect.bisect_left(starts, start)
    assert ix < len(starts) and starts[ix] == start
    starts.pop(ix)
    length = end - start
    hist[min(length, 40)] -= 1
    size_count[length] -= 1
    if size_count[length] == 0:
        del size_count[length]
    return end


def add_gap(gaps: dict[int, int], starts: list[int], hist: list[int],
            size_count: Counter[int], start: int, end: int) -> None:
    if start >= end:
        return
    ix = bisect.bisect_left(starts, start)
    if ix and gaps[starts[ix - 1]] >= start:
        old_start = starts[ix - 1]
        old_end = remove_gap(gaps, starts, hist, size_count, old_start)
        start = old_start
        end = max(end, old_end)
        ix -= 1
    while ix < len(starts) and starts[ix] <= end:
        old_start = starts[ix]
        old_end = remove_gap(gaps, starts, hist, size_count, old_start)
        end = max(end, old_end)
    gaps[start] = end
    starts.insert(ix, start)
    length = end - start
    hist[min(length, 40)] += 1
    size_count[length] += 1


def find_gap(gaps: dict[int, int], starts: list[int], position: int, length: int):
    ix = bisect.bisect_right(starts, position) - 1
    if ix < 0:
        return None
    start = starts[ix]
    end = gaps[start]
    return (start, end) if start <= position and position + length <= end else None


def main() -> None:
    data = [int(x) for x in INPUT.read_text().split()]
    n = data[1]
    commands = data[2 : 2 + n]
    trace = [line.split() for line in TRACE.read_text().splitlines()]
    if len(commands) != n or len(trace) != n:
        raise SystemExit(f"input/trace size mismatch: {len(commands)=} {len(trace)=}")

    rows = [json.loads(line) for line in ROWS.read_text().splitlines()[1:]]
    winners_by_op = {}
    for row in rows:
        if row["saving_m"] > 0:
            winners_by_op.setdefault(row["op"], row)
    targets = []
    for row in winners_by_op.values():
        targets.append({
            "winner": row,
            "length": row["length"],
            "base_len": row["baseline_gap_length"],
            "alt_len": row["choice_gap_length"],
        })

    gaps: dict[int, int] = {}
    starts: list[int] = []
    gap_hist = [0] * 41
    gap_size_count: Counter[int] = Counter()
    pipes: list[tuple[int, int] | None] = [None]
    history: deque[int] = deque()
    history_hist = [0] * 41
    active_count = 0
    active_length = 0
    trench = 0
    matches = [[] for _ in targets]

    for i, (command, out) in enumerate(zip(commands, trace)):
        if command > 0:
            length = command
            digs, position = map(int, out)
            old_trench = trench
            trench += 20 * digs
            found = find_gap(gaps, starts, position, length)
            if found:
                base_start, base_end = found
                base_len = base_end - base_start
                for ti, target in enumerate(targets):
                    if length != target["length"] or base_len != target["base_len"]:
                        continue
                    alt_len = target["alt_len"]
                    remaining = gap_size_count[alt_len] - (1 if alt_len == base_len else 0)
                    if remaining <= 0:
                        continue
                    gh = tuple(gap_hist)
                    rh = tuple(history_hist)
                    matches[ti].append({
                        "op": i + 1,
                        "length": length,
                        "trench": old_trench,
                        "baseline_position": position,
                        "baseline_gap_start": base_start,
                        "baseline_gap_length": base_len,
                        "baseline_high": position != base_start,
                        "alt_length_available": alt_len,
                        "alt_intervals_count": remaining,
                        "gap_count": len(gaps),
                        "fit_count": sum(gap_size_count[k] for k in range(length, max(gap_size_count.keys(), default=0) + 1)),
                        "eligible40": sum(gap_size_count[k] for k in range(length, length + 41)),
                        "active_count": active_count,
                        "active_length": active_length,
                        "recent_hist": rh,
                        "gap_hist": gh,
                    })

                remove_gap(gaps, starts, gap_hist, gap_size_count, base_start)
                if base_start < position:
                    add_gap(gaps, starts, gap_hist, gap_size_count, base_start, position)
                if position + length < base_end:
                    add_gap(gaps, starts, gap_hist, gap_size_count, position + length, base_end)
            else:
                old_tail = next((s for s in reversed(starts) if gaps[s] == old_trench), None)
                tail_start = old_trench
                if old_tail is not None:
                    tail_start = old_tail
                    remove_gap(gaps, starts, gap_hist, gap_size_count, old_tail)
                if tail_start < position:
                    add_gap(gaps, starts, gap_hist, gap_size_count, tail_start, position)
                if position + length < trench:
                    add_gap(gaps, starts, gap_hist, gap_size_count, position + length, trench)
            pipes.append((position, length))
            active_count += 1
            active_length += length
            history.append(length)
            history_hist[length] += 1
            if len(history) > 2048:
                removed = history.popleft()
                history_hist[removed] -= 1
        else:
            pid = -command
            if pid >= len(pipes) or pipes[pid] is None:
                raise SystemExit(f"bad pid {pid} at op {i + 1}")
            position = int(out[0])
            pstart, length = pipes[pid]
            if position != pstart:
                raise SystemExit(f"trace mismatch at op {i + 1}")
            pipes[pid] = None
            active_count -= 1
            active_length -= length
            add_gap(gaps, starts, gap_hist, gap_size_count, pstart, pstart + length)

    result = {
        "scope": "diagnostic exact-trace state matching; future used only to choose audit sites",
        "eligible_sites": sum(len(x) for x in matches),
        "targets": [],
    }

    def distance(a, b) -> float:
        if (a["length"], a["baseline_gap_length"], a["alt_length_available"]) != (
            b["length"], b["baseline_gap_length"], b["alt_length_available"]
        ):
            return float("inf")
        gh = sum(abs(x - y) for x, y in zip(a["gap_hist"], b["gap_hist"]))
        rh = sum(abs(x - y) for x, y in zip(a["recent_hist"], b["recent_hist"]))
        gc = abs(a["gap_count"] - b["gap_count"])
        ac = abs(a["active_count"] - b["active_count"]) / 100.0
        av = abs(a["active_length"] - b["active_length"]) / 5000.0
        return gh + 0.2 * rh + 0.5 * gc + ac + av

    for target, candidates in zip(targets, matches):
        winner = target["winner"]
        target_site = next((x for x in candidates if x["op"] == winner["op"]), None)
        if target_site is None:
            continue
        ranked = sorted(((distance(target_site, site), site) for site in candidates
                         if site["op"] != winner["op"]), key=lambda z: (z[0], z[1]["op"]))
        nearest = [{"distance": d, **site} for d, site in ranked[:20]]
        exact = [site["op"] for d, site in ranked if d == 0.0]
        result["targets"].append({
            "positive_trial": winner,
            "target_signature": target_site,
            "eligible_similar_sites": len(candidates) - 1,
            "exact_signature_matches": exact,
            "nearest_exact_length_and_gap_shape": nearest,
        })
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {OUT}; positive target signatures={len(targets)}")
    for item in result["targets"]:
        print("target", item["positive_trial"]["op"], "saving", item["positive_trial"]["saving_m"],
              "same base/alt sizes", item["eligible_similar_sites"],
              "exact signature", item["exact_signature_matches"][:8],
              "nearest", [f"{x['op']}:{x['distance']:.1f}" for x in item["nearest_exact_length_and_gap_shape"][:5]])


if __name__ == "__main__":
    main()
