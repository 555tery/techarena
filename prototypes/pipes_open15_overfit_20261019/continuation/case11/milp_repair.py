#!/usr/bin/env python3
"""Offline-only MILP repair of an Open15 case 11 placement plan.

The model uses all known future deletions. Pipes outside the selected top-K
set retain their source addresses. This is a placement-plan generator, not an
online policy.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_case(path: Path):
    vals = list(map(int, path.read_text().split()))
    width, n = vals[:2]
    cmds = vals[2 : 2 + n]
    if len(cmds) != n:
        raise ValueError(f"expected {n} commands, found {len(cmds)}")
    lens = [0]
    born = [-1]
    died = [n]
    ids_at = [0] * n
    for t, c in enumerate(cmds):
        if c > 0:
            pid = len(lens)
            ids_at[t] = pid
            lens.append(c)
            born.append(t)
            died.append(n)
        elif c < 0:
            pid = -c
            died[pid] = t
            ids_at[t] = pid
    return width, n, cmds, lens, born, died, ids_at


def allowed_intervals(pid, movable, target, lens, born, died, pos):
    max_start = target - lens[pid]
    if max_start < 0:
        return []
    diff = np.zeros(max_start + 2, dtype=np.int32)
    for q in range(1, len(lens)):
        if q in movable:
            continue
        if max(born[pid], born[q]) >= min(died[pid], died[q]):
            continue
        ql = pos[q - 1]
        lo = max(0, ql - lens[pid] + 1)
        hi = min(max_start, ql + lens[q] - 1)
        if lo <= hi:
            diff[lo] += 1
            diff[hi + 1] -= 1
    blocked = np.cumsum(diff[:-1]) > 0
    out = []
    i = 0
    while i <= max_start:
        while i <= max_start and blocked[i]:
            i += 1
        if i > max_start:
            break
        lo = i
        while i + 1 <= max_start and not blocked[i + 1]:
            i += 1
        out.append((lo, i))
        i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--source-positions", type=Path, required=True)
    ap.add_argument("--output-positions", type=Path, required=True)
    ap.add_argument("--target", type=int, default=20760)
    ap.add_argument("--ceiling", type=int, default=None, help="spatial bound; H is minimized within this ceiling")
    ap.add_argument("--movables", type=int, default=150)
    ap.add_argument("--seconds", type=float, default=90)
    ap.add_argument("--fixed-order", action="store_true", help="preserve source spatial order for movable conflicts")
    args = ap.parse_args()
    ceiling = args.ceiling if args.ceiling is not None else args.target
    # Keep any BLAS/OpenMP helpers at one thread; HiGHS is also told explicitly.
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    if hasattr(os, "sched_getaffinity"):
        try:
            os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        except (OSError, ValueError):
            pass

    width, n, cmds, lens, born, died, ids_at = read_case(args.input)
    pos = list(map(int, args.source_positions.read_text().split()))
    if len(pos) != len(lens) - 1:
        raise ValueError(f"source positions={len(pos)}; pipe count={len(lens)-1}")
    src_extent = max(pos[i - 1] + lens[i] for i in range(1, len(lens)))
    if pos[0] != 0:
        raise ValueError("source PID1 is not pinned at coordinate zero")

    # The top-K pipes by right endpoint are movable; all over-target pipes are
    # forcibly included. PID1 remains fixed at zero.
    ranked = sorted(range(2, len(lens)), key=lambda i: (pos[i - 1] + lens[i], pos[i - 1]), reverse=True)
    movable_list = ranked[: args.movables]
    movable_set = set(movable_list)
    for i in range(1, len(lens)):
        if pos[i - 1] + lens[i] > args.target and i != 1:
            movable_set.add(i)
    movable_list = sorted(movable_set)
    m = len(movable_list)
    if not movable_list:
        raise ValueError("empty movable set")

    # Variable blocks: x_i, one-hot allowed-interval selectors, pair-order
    # binaries, and the high-water mark H.
    intv = {}
    interval_lists = {}
    next_var = m
    for local, pid in enumerate(movable_list):
        ranges = allowed_intervals(pid, movable_set, ceiling, lens, born, died, pos)
        # Keep the original coordinate as an explicit singleton if needed; it
        # is guaranteed compatible with every fixed pipe by the source plan.
        original = pos[pid - 1]
        if original <= ceiling - lens[pid] and not any(lo <= original <= hi for lo, hi in ranges):
            ranges.append((original, original))
        if not ranges:
            raise RuntimeError(f"no allowed positions for PID {pid}")
        interval_lists[pid] = ranges
        ids = list(range(next_var, next_var + len(ranges)))
        intv[pid] = ids
        next_var += len(ranges)

    conflicts = []
    for ai, a in enumerate(movable_list):
        for b in movable_list[ai + 1 :]:
            if max(born[a], born[b]) < min(died[a], died[b]):
                y = None if args.fixed_order else next_var
                conflicts.append((a, b, y))
                if y is not None:
                    next_var += 1
    h_var = next_var
    nvars = h_var + 1

    rows, cols, data = [], [], []
    lbs, ubs = [], []
    def add_row(entries, lb=-np.inf, ub=np.inf):
        r = len(lbs)
        for col, val in entries:
            if val:
                rows.append(r); cols.append(col); data.append(float(val))
        lbs.append(lb); ubs.append(ub)

    # Every movable pipe chooses exactly one permitted spatial interval.
    for local, pid in enumerate(movable_list):
        zids = intv[pid]
        add_row([(z, 1) for z in zids], lb=1, ub=1)
        add_row([(local, 1)] + [(z, -interval_lists[pid][k][0]) for k, z in enumerate(zids)], lb=0)
        add_row([(local, 1)] + [(z, -interval_lists[pid][k][1]) for k, z in enumerate(zids)], ub=0)
        add_row([(local, 1), (h_var, -1)], ub=-lens[pid])

    # Pairwise non-overlap disjunction for movable pipes with intersecting
    # lifetimes. y=1 means a is left of b; y=0 means b is left of a.
    big_m = ceiling
    local_of = {pid: i for i, pid in enumerate(movable_list)}
    for a, b, y in conflicts:
        xa, xb = local_of[a], local_of[b]
        if args.fixed_order:
            if pos[a - 1] + lens[a] <= pos[b - 1]:
                add_row([(xa, 1), (xb, -1)], ub=-lens[a])
            else:
                add_row([(xb, 1), (xa, -1)], ub=-lens[b])
        else:
            add_row([(xa, 1), (xb, -1), (y, big_m)], ub=big_m - lens[a])
            add_row([(xb, 1), (xa, -1), (y, -big_m)], ub=-lens[b])

    live = 0
    volume_lb = 0
    for c in cmds:
        if c > 0:
            live += c
        elif c < 0:
            live -= lens[-c]
        volume_lb = max(volume_lb, live)
    fixed_extent = max(
        (pos[i - 1] + lens[i] for i in range(1, len(lens)) if i not in movable_set),
        default=0,
    )
    h_lb = max(volume_lb, fixed_extent)
    # H also respects the fixed part of the layout.
    bounds_lb = np.zeros(nvars)
    bounds_ub = np.full(nvars, np.inf)
    integrality = np.zeros(nvars, dtype=np.uint8)
    for local, pid in enumerate(movable_list):
        bounds_ub[local] = ceiling - lens[pid]
        integrality[local] = 1
        for z in intv[pid]:
            bounds_ub[z] = 1
            integrality[z] = 1
    for _, _, y in conflicts:
        if y is not None:
            bounds_ub[y] = 1
            integrality[y] = 1
    bounds_lb[h_var] = h_lb
    bounds_ub[h_var] = ceiling
    integrality[h_var] = 1
    objective = np.zeros(nvars)
    objective[h_var] = 1
    matrix = coo_matrix((data, (rows, cols)), shape=(len(lbs), nvars)).tocsr()
    print(json.dumps({
        "movables": m, "interval_selectors": sum(map(len, intv.values())),
        "movable_conflicts": len(conflicts), "variables": nvars, "fixed_order": args.fixed_order,
        "constraints": len(lbs), "source_extent": src_extent,
        "fixed_extent": fixed_extent, "volume_lower_bound": volume_lb,
        "target": args.target, "ceiling": ceiling, "input_sha256": sha256(args.input),
        "source_sha256": sha256(args.source_positions),
    }), flush=True)
    result = milp(
        objective,
        integrality=integrality,
        bounds=Bounds(bounds_lb, bounds_ub),
        constraints=LinearConstraint(matrix, np.array(lbs), np.array(ubs)),
        options={"time_limit": args.seconds, "mip_rel_gap": 0.0, "presolve": True, "disp": True, "threads": 1},
    )
    print("MILP_STATUS", result.status, result.message, "objective", result.fun, flush=True)
    if result.x is None:
        return 2
    newpos = pos[:]
    for local, pid in enumerate(movable_list):
        newpos[pid - 1] = int(round(result.x[local]))
    args.output_positions.write_text("".join(f"{p}\n" for p in newpos))
    print(json.dumps({
        "output": str(args.output_positions),
        "extent": max(newpos[i - 1] + lens[i] for i in range(1, len(lens))),
        "pid1": newpos[0], "movables": m,
        "output_sha256": sha256(args.output_positions),
    }), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
