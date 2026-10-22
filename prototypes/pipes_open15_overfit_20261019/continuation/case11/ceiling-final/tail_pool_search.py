"""Exact peak-tail pool layouts plus reverse reconstruction of the prefix.

Offline only: uses known deaths to choose addresses. The 2940 pipes surviving
the peak are packed below the 1242-unit pool; 79 peak-live temporary pipes and
74 post-peak pipes share the pool. Tail packing is forward; the prefix is then
reconstructed backward with explicit collision checks.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from rotation.condition_rotations import INPUT11, read_input, read_positions, replay, sha

H = 20760
SOURCE = HERE.parent / "rotation" / "raw-search-best-h20799.txt"
OUT = HERE


def fits(x, length, active, lengths):
    return all(x + length <= y or y + lengths[q] <= x for q, y in active.items())


def gaps(lo, hi, active, lengths):
    out = []
    cursor = lo
    for pid, x in sorted(active.items(), key=lambda kv: (kv[1], kv[0])):
        y = x + lengths[pid]
        if y <= lo or x >= hi:
            continue
        if x > cursor:
            out.append((cursor, x))
        cursor = max(cursor, y)
    if cursor < hi:
        out.append((cursor, hi))
    return out


def choose(length, free, policy, preferred=-1):
    cand = [(a, b) for a, b in free if b - a >= length]
    if not cand:
        return None
    if policy == "preferred" and preferred >= 0 and any(a <= preferred and preferred + length <= b for a, b in cand):
        return preferred
    if policy in ("first", "preferred"):
        return min(cand)[0]
    if policy == "last":
        return max(cand)[1] - length
    if policy == "best":
        a, b = min(cand, key=lambda ab: (ab[1] - ab[0] - length, ab[0]))
        return a
    if policy == "worst":
        a, b = max(cand, key=lambda ab: (ab[1] - ab[0] - length, -ab[0]))
        return a
    raise ValueError(policy)


def run_tail(tail_policy, prefix_policy, survivor_order, temp_order):
    _, n, cmd, lengths, born, died, pid_at, _ = read_input(INPUT11)
    source = read_positions(SOURCE, len(lengths) - 1)
    volume = peak = cut = 0
    active_at_peak = set()
    for t, c in enumerate(cmd):
        if c > 0:
            volume += c
        else:
            volume -= lengths[-c]
        if volume > peak:
            peak, cut = volume, t
    active_at_peak = {p for p in range(1, len(lengths)) if born[p] <= cut < died[p]}

    if survivor_order == "source":
        perm_key = lambda p: (source[p], p)
    elif survivor_order == "birth-asc":
        perm_key = lambda p: (born[p], source[p], p)
    elif survivor_order == "birth-desc":
        perm_key = lambda p: (-born[p], source[p], p)
    elif survivor_order == "length-desc":
        perm_key = lambda p: (-lengths[p], born[p], source[p], p)
    elif survivor_order == "death-desc":
        perm_key = lambda p: (-died[p], born[p], source[p], p)
    else:
        raise ValueError(survivor_order)
    permanent = sorted((p for p in active_at_peak if died[p] == n), key=lambda p: (p != 1, *perm_key(p)))
    if temp_order == "death-asc":
        temp_key = lambda p: (died[p], source[p], p)
    elif temp_order == "birth-asc":
        temp_key = lambda p: (born[p], source[p], p)
    elif temp_order == "birth-desc":
        temp_key = lambda p: (-born[p], source[p], p)
    elif temp_order == "death-desc":
        temp_key = lambda p: (-died[p], source[p], p)
    else:
        raise ValueError(temp_order)
    initial_temp = sorted((p for p in active_at_peak if died[p] < n), key=temp_key)
    tail_born = sorted((p for p in range(1, len(lengths)) if born[p] > cut), key=lambda p: (born[p], p))
    low_volume = sum(lengths[p] for p in permanent)
    pool_volume = sum(lengths[p] for p in initial_temp)
    if (len(permanent), low_volume, len(initial_temp), pool_volume, len(tail_born), peak) != (2940, 19518, 79, 1241, 74, 20759):
        raise ValueError("peak-tail decomposition differs from the observed case11 profile")
    if H - low_volume < pool_volume:
        return None, {"tail_policy": tail_policy, "prefix_policy": prefix_policy,
                      "survivor_order": survivor_order, "temp_order": temp_order,
                      "failure": "initial pool does not fit"}

    pos = [-1] * len(lengths)
    cursor = 0
    for p in permanent:
        pos[p] = cursor
        cursor += lengths[p]
    if cursor != low_volume or pos[1] != 0 or lengths[1] != 3:
        raise AssertionError("permanent survivor block or PID1 invariant failed")
    cursor = low_volume
    for p in initial_temp:
        pos[p] = cursor
        cursor += lengths[p]
    if cursor != low_volume + pool_volume:
        raise AssertionError("temporary peak block packing mismatch")

    # Simulate the post-peak trace in the 1242-unit upper pool.
    active = {p: pos[p] for p in active_at_peak}
    births_tail = []
    for t in range(cut + 1, n):
        c = cmd[t]
        if c < 0:
            p = -c
            if p not in active:
                raise AssertionError(f"inactive tail deletion at {t}: PID {p}")
            del active[p]
        elif c > 0:
            p = pid_at[t]
            free = gaps(low_volume, H, active, lengths)
            x = choose(c, free, tail_policy)
            if x is None:
                return None, {"tail_policy": tail_policy, "prefix_policy": prefix_policy,
                              "survivor_order": survivor_order, "temp_order": temp_order,
                              "failure": "tail birth does not fit", "command": t, "pid": p,
                              "length": c, "free_gaps": free}
            pos[p] = x
            active[p] = x
            births_tail.append(p)

    expected_final = {p for p in range(1, len(lengths)) if died[p] == n}
    if set(active) != expected_final:
        raise AssertionError("tail forward replay survivor set mismatch")

    # Reconstruct the exact peak state by reversing tail events, keeping every
    # tail-deleted pipe at the address chosen during the forward simulation.
    for t in range(n - 1, cut, -1):
        c = cmd[t]
        if c > 0:
            p = pid_at[t]
            if p not in active:
                raise AssertionError(f"inactive reverse tail birth at {t}: PID {p}")
            del active[p]
        elif c < 0:
            p = -c
            x = pos[p]
            if not fits(x, lengths[p], active, lengths):
                return None, {"tail_policy": tail_policy, "prefix_policy": prefix_policy,
                              "survivor_order": survivor_order, "temp_order": temp_order,
                              "failure": "tail reverse deletion collision", "command": t, "pid": p}
            active[p] = x
    if set(active) != active_at_peak:
        raise AssertionError("reverse tail did not recover peak-active set")

    # Undo the prefix. A forward deletion reintroduces one pipe into any gap;
    # a forward birth removes it again. Several standard gap policies are tried.
    for t in range(cut, -1, -1):
        c = cmd[t]
        if c > 0:
            p = pid_at[t]
            if p not in active:
                raise AssertionError(f"inactive prefix reverse birth at {t}: PID {p}")
            del active[p]
        elif c < 0:
            p = -c
            free = gaps(0, H, active, lengths)
            x = choose(lengths[p], free, prefix_policy, source[p])
            if x is None:
                return None, {"tail_policy": tail_policy, "prefix_policy": prefix_policy,
                              "survivor_order": survivor_order, "temp_order": temp_order,
                              "failure": "prefix pipe does not fit", "command": t, "pid": p,
                              "length": lengths[p], "free_gaps": free[:30],
                              "active_intervals": [[q, active[q], active[q] + lengths[q]]
                                                   for q in sorted(active, key=lambda z: active[z])]
                              if t >= cut - 12 else None}
            pos[p] = x
            active[p] = x
    if active:
        raise AssertionError(f"reverse prefix left {len(active)} active pipes")
    if any(x < 0 for x in pos[1:]):
        raise AssertionError("unassigned pipe remains")

    report = replay(INPUT11, pos)
    if report["extent"] > H or pos[1] != 0:
        raise AssertionError(f"replay violates ceiling or PID1 pin: {report}, pid1={pos[1]}")
    return pos, {"tail_policy": tail_policy, "prefix_policy": prefix_policy,
                 "survivor_order": survivor_order, "temp_order": temp_order,
                 "peak_command_zero_based": cut, "peak_volume": peak,
                 "permanent_count": len(permanent), "permanent_volume": low_volume,
                 "initial_temp_count": len(initial_temp), "initial_temp_volume": pool_volume,
                 "tail_birth_count": len(tail_born), "tail_births_placed": len(births_tail),
                 "peak_active_count": len(active_at_peak), "extent": report["extent"],
                 "T": report["trench_score"], "replay": report}


def main():
    attempts = []
    for survivor_order in ("birth-asc", "birth-desc", "source"):
      for temp_order in ("birth-asc", "death-asc", "birth-desc", "death-desc"):
       for tail_policy in ("first", "best", "last", "worst"):
        for prefix_policy in ("last", "first", "best", "preferred", "worst"):
            pos, record = run_tail(tail_policy, prefix_policy, survivor_order, temp_order)
            attempts.append(record)
            print(json.dumps({k: record.get(k) for k in ("survivor_order", "temp_order", "tail_policy", "prefix_policy", "failure", "command", "pid", "extent", "T")}), flush=True)
            if pos is not None:
                dest = OUT / "positions.txt"
                dest.write_text("".join(f"{pos[p]}\n" for p in range(1, len(pos))))
                record.update({"status": "verified", "positions": str(dest), "positions_sha256": sha(dest),
                               "input_sha256": sha(INPUT11), "source_sha256": sha(SOURCE), "attempts": attempts})
                (OUT / "report.json").write_text(json.dumps(record, indent=2) + "\n")
                print(json.dumps(record, indent=2), flush=True)
                return 0
    (OUT / "tail-pool-attempts.json").write_text(json.dumps(attempts, indent=2) + "\n")
    print(json.dumps({"status": "no witness", "attempts": len(attempts)}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
