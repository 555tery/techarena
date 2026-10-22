#!/usr/bin/env python3
"""Read-only, prequential diagnostic of deletion-rank signal in public traces.

No solver is run and no future fate labels are used as model features. At each
delete event, the normalized rank is observed; the next rank is predicted from
only earlier observed ranks. This tests whether a causal rank-regime signal is
available, not whether a placement policy improves trench length.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter, deque
from pathlib import Path


CAMPAIGN = Path("/Users/555tery/techarena/research-campaigns/20261018T141843+0700-autonomous")
WINDOW = 128
WARMUP = 64
N_BINS = 10


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tokens(path: Path):
    with path.open("r", encoding="ascii") as f:
        for line in f:
            yield from line.split()


def summarize(test_path: Path) -> dict:
    it = iter(tokens(test_path))
    weight = float(next(it))
    operation_count = int(next(it))
    lengths = [0]
    alive = [False]
    capacity = operation_count + 2
    fenwick = [0] * (capacity + 1)
    live_count = 0
    delete_bins: list[int] = []
    delete_lengths: list[int] = []
    delete_ops: list[int] = []
    recent_delete_ranks: deque[int] = deque(maxlen=64)
    recent_lengths: deque[int] = deque(maxlen=2048)
    lifo_lane_disabled_for_scale = False
    observed_lifo_gate_placements = 0
    observed_lifo_gate_long = 0
    observed_lifo_gate_short = 0
    observed_lifo_gate_segments = 0
    previous_placement_gate = False
    first_gate_op = None
    last_gate_op = None
    legacy_side_lane_placements = 0

    def add(index: int, delta: int) -> None:
        while index <= capacity:
            fenwick[index] += delta
            index += index & -index

    def prefix(index: int) -> int:
        total = 0
        while index > 0:
            total += fenwick[index]
            index -= index & -index
        return total

    placements = 0
    for op_index in range(operation_count):
        command = int(next(it))
        if command > 0:
            if live_count > 4096:
                lifo_lane_disabled_for_scale = True
            rank_gate = (live_count >= 128 and len(recent_delete_ranks) >= 48 and
                         sum(rank <= 50 for rank in recent_delete_ranks) * 100 >=
                         len(recent_delete_ranks) * 80)
            if rank_gate:
                observed_lifo_gate_placements += 1
                if command > 8:
                    observed_lifo_gate_long += 1
                else:
                    observed_lifo_gate_short += 1
                if not previous_placement_gate:
                    observed_lifo_gate_segments += 1
                if first_gate_op is None:
                    first_gate_op = op_index + 1
                last_gate_op = op_index + 1
            previous_placement_gate = rank_gate
            short_placements = sum(length <= 8 for length in recent_lengths)
            legacy_side_lane = (
                not lifo_lane_disabled_for_scale and live_count >= 128 and
                4 < command <= 8 and len(recent_delete_ranks) >= 48 and
                sum(rank <= 50 for rank in recent_delete_ranks) * 100 >=
                len(recent_delete_ranks) * 80 and len(recent_lengths) >= 64 and
                short_placements * 100 >= len(recent_lengths) * 90
            )
            if legacy_side_lane:
                legacy_side_lane_placements += 1
            placements += 1
            lengths.append(command)
            alive.append(True)
            live_count += 1
            add(placements, 1)
            recent_lengths.append(command)
            continue
        pid = -command
        if pid <= 0 or pid >= len(lengths) or not alive[pid]:
            raise ValueError(f"invalid delete at operation {op_index + 1}: pid={pid}")
        newer = live_count - prefix(pid)
        rank = 0 if live_count <= 1 else (newer * 1000) // (live_count - 1)
        delete_bins.append(min(N_BINS - 1, rank // 100))
        delete_lengths.append(lengths[pid])
        delete_ops.append(op_index + 1)
        recent_delete_ranks.append(rank)
        alive[pid] = False
        live_count -= 1
        add(pid, -1)

    # Prequential comparison: each prediction uses only the previous WINDOW
    # observed rank bins. Laplace smoothing avoids zero-probability events.
    markov_losses: list[float] = []
    marginal_losses: list[float] = []
    for i in range(WARMUP, len(delete_bins)):
        lo = max(0, i - WINDOW)
        train = delete_bins[lo:i]
        prior = delete_bins[i - 1]
        global_counts = Counter(train)
        row = Counter((train[j - 1], train[j]) for j in range(1, len(train)))
        row_total = sum(row[(prior, b)] for b in range(N_BINS))
        bin_value = delete_bins[i]
        p_global = (global_counts[bin_value] + 1) / (len(train) + N_BINS)
        p_markov = (row[(prior, bin_value)] + 1) / (row_total + N_BINS)
        marginal_losses.append(-math.log2(p_global))
        markov_losses.append(-math.log2(p_markov))

    counts = Counter(delete_bins)
    transition_same = sum(a == b for a, b in zip(delete_bins, delete_bins[1:]))
    transition_n = max(0, len(delete_bins) - 1)
    expected_same_probability = sum((counts[b] / max(1, len(delete_bins))) ** 2
                                    for b in range(N_BINS))
    top_bottom = sum(1 for b in delete_bins if b in (0, N_BINS - 1))
    run_lengths: list[int] = []
    if delete_bins:
        run = 1
        for a, b in zip(delete_bins, delete_bins[1:]):
            if a == b:
                run += 1
            else:
                run_lengths.append(run)
                run = 1
        run_lengths.append(run)

    by_time_quartile = []
    for q in range(4):
        begin = len(delete_bins) * q // 4
        end = len(delete_bins) * (q + 1) // 4
        part = delete_bins[begin:end]
        by_time_quartile.append({
            "quartile": q + 1,
            "n_deletes": len(part),
            "rank_bin_counts": [part.count(b) for b in range(N_BINS)],
            "edge_rank_fraction": sum(b in (0, N_BINS - 1) for b in part) / max(1, len(part)),
        })

    return {
        "test": str(test_path),
        "test_sha256": sha256(test_path),
        "weight": weight,
        "operation_count": operation_count,
        "placement_count": placements,
        "deletion_count": len(delete_bins),
        "rank_gate_coverage": {
            "definition": "live_count>=128, >=48 recent delete ranks, and >=80% rank<=50/1000; no size or lifetime condition",
            "placement_count_active": observed_lifo_gate_placements,
            "fraction_of_placements": observed_lifo_gate_placements / max(1, placements),
            "active_placements_length_1_to_8": observed_lifo_gate_short,
            "active_placements_length_9_to_40": observed_lifo_gate_long,
            "active_segments_over_placement_events": observed_lifo_gate_segments,
            "first_active_operation": first_gate_op,
            "last_active_operation": last_gate_op,
            "legacy_high_side_lane_placements": legacy_side_lane_placements,
            "legacy_lane_scope": "length 5..8, recent-length window >=64 and >=90% <=8, rank gate, and not scale-disabled after live_count>4096",
        },
        "rank_definition": "floor(1000 * newer_live_count / (live_count - 1)); 0=newest, 1000=oldest",
        "rank_bins": {"count": N_BINS, "counts": [counts[b] for b in range(N_BINS)]},
        "edge_rank_fraction": top_bottom / max(1, len(delete_bins)),
        "same_bin_transition_fraction": transition_same / max(1, transition_n),
        "same_bin_transition_expected_from_marginal": expected_same_probability,
        "same_bin_transition_lift": (transition_same / max(1, transition_n)) / max(1e-12, expected_same_probability),
        "same_bin_run_max": max(run_lengths, default=0),
        "same_bin_run_p90": sorted(run_lengths)[math.ceil(0.9 * len(run_lengths)) - 1] if run_lengths else 0,
        "prequential_prediction": {
            "history_window_deletions": WINDOW,
            "warmup_deletions": WARMUP,
            "scored_deletions": len(markov_losses),
            "marginal_logloss_bits_per_delete": sum(marginal_losses) / max(1, len(marginal_losses)),
            "first_order_markov_logloss_bits_per_delete": sum(markov_losses) / max(1, len(markov_losses)),
            "markov_minus_marginal_bits_per_delete": (sum(markov_losses) - sum(marginal_losses)) / max(1, len(markov_losses)),
        },
        "time_quartiles": by_time_quartile,
        "causality_scope": "rank prediction is strictly prequential; no lifetime or future-survivor labels; no allocator placements are simulated",
        "inference_limit": "rank predictability alone does not establish that a placement policy can co-locate eventual deletions or improve trench length",
    }


def main() -> int:
    open_dir = Path("/Users/555tery/techarena/data/pipes/open")
    inputs = [open_dir / "11.in", open_dir / "15.in"]
    output = Path(__file__).with_name("rank_signal.json")
    results = [summarize(path) for path in inputs]
    output.write_text(json.dumps({
        "campaign": str(CAMPAIGN),
        "analysis": "causal availability screen for rank-regime signal",
        "baseline_source_sha256": sha256(CAMPAIGN / "seeds" / "baseline.cpp"),
        "public_best_source_sha256": sha256(CAMPAIGN / "seeds" / "public_best.cpp"),
        "method": "single-pass trace parser + Fenwick order-statistics; no candidate solver/evaluator run",
        "results": results,
    }, indent=2) + "\n", encoding="utf-8")
    print(output)
    for row in results:
        pre = row["prequential_prediction"]
        print(f"{Path(row['test']).name}: n_del={row['deletion_count']} "
              f"edge={row['edge_rank_fraction']:.3f} "
              f"same-bin lift={row['same_bin_transition_lift']:.3f} "
              f"Markov-minus-marginal={pre['markov_minus_marginal_bits_per_delete']:.4f} bits/delete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
