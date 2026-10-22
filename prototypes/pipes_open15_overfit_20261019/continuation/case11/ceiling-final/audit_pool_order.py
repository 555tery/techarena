"""Independent cell-owner replay of the parent pool-order candidate."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[5]
SRC = REPO / "prototypes/pipes_open15_overfit_20261019/continuation/pool-order/best.txt"
IN11 = REPO / "data/pipes/open/11.in"
IN15 = REPO / "data/pipes/open/15.in"
BOUND = 20760
PREFIX = 4999


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(path):
    vals = list(map(int, path.read_text().split()))
    width, n = vals[:2]
    commands = vals[2:2+n]
    if len(commands) != n or vals[2+n:] not in ([], [0]):
        raise ValueError(f"malformed input {path}")
    lengths = [0]
    born = [-1]
    died = [n]
    pid_at = [0] * n
    for t, c in enumerate(commands):
        if c > 0:
            pid = len(lengths)
            lengths.append(c)
            born.append(t)
            died.append(n)
            pid_at[t] = pid
        elif c < 0:
            pid = -c
            if pid <= 0 or pid >= len(lengths) or died[pid] != n:
                raise ValueError(f"invalid deletion at {t}, PID {pid}")
            died[pid] = t
    return width, n, commands, lengths, born, died, pid_at


def replay(commands, lengths, pid_at, positions, label):
    owner = [0] * BOUND
    live = {}
    volume = peak = insertions = deletions = 0
    active_after_prefix = None
    for t, c in enumerate(commands):
        if c > 0:
            pid = pid_at[t]
            x = positions[pid]
            end = x + c
            if x < 0 or end > BOUND:
                raise ValueError(f"{label}: out of bound at command {t}, PID {pid}, [{x},{end})")
            for z in range(x, end):
                if owner[z]:
                    raise ValueError(f"{label}: collision at {t}, PID {pid} with PID {owner[z]}, cell {z}")
            for z in range(x, end):
                owner[z] = pid
            live[pid] = (x, c)
            volume += c
            peak = max(peak, volume)
            insertions += 1
        elif c < 0:
            pid = -c
            if pid not in live:
                raise ValueError(f"{label}: deleting inactive PID {pid} at command {t}")
            x, length = live.pop(pid)
            if any(owner[z] != pid for z in range(x, x + length)):
                raise ValueError(f"{label}: owner-map mismatch for PID {pid} at command {t}")
            for z in range(x, x + length):
                owner[z] = 0
            volume -= length
            deletions += 1
        if t == PREFIX - 1:
            active_after_prefix = dict(live)
    return {"insertions": insertions, "deletions": deletions,
            "survivors": len(live), "peak_volume": peak,
            "active_after_prefix": active_after_prefix}


def main():
    _, n, cmd11, lengths, born, died, pid_at = parse(IN11)
    _, n15, cmd15, lengths15, _, _, _ = parse(IN15)
    raw = list(map(int, SRC.read_text().split()))
    if len(raw) != len(lengths) - 1:
        raise ValueError(f"candidate has {len(raw)} positions, expected {len(lengths)-1}")
    positions = [0] + raw
    extent = max(positions[p] + lengths[p] for p in range(1, len(lengths)))
    if cmd11[:PREFIX] != cmd15[:PREFIX] or lengths[:4007] != lengths15[:4007]:
        raise ValueError("Open11/Open15 shared command or PID prefix mismatch")
    if n != 9999 or n15 < PREFIX:
        raise ValueError(f"unexpected command counts {n}, {n15}")
    if lengths[1] != 3 or born[1] != 0 or died[1] != n or positions[1] != 0:
        raise ValueError(f"PID1 invariant failed: len/born/death/pos={lengths[1],born[1],died[1],positions[1]}")

    audit = replay(cmd11, lengths, pid_at, positions, "Open11")
    prefix_pids = [p for p in range(1, len(lengths)) if born[p] < PREFIX]
    prefix_max = max(positions[p] + lengths[p] for p in prefix_pids)
    prefix_min = min(positions[p] for p in prefix_pids)
    active = audit.pop("active_after_prefix")
    active_extent = max((positions[p] + length for p, (x, length) in active.items()), default=0)
    if len(prefix_pids) != 4006:
        raise ValueError(f"expected 4006 common-prefix births, got {len(prefix_pids)}")

    report = {
        "status": "verified",
        "candidate_source": str(SRC.relative_to(REPO)),
        "candidate_source_sha256": sha(SRC),
        "input11_sha256": sha(IN11),
        "input15_sha256": sha(IN15),
        "positions_count": len(raw),
        "positions_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
        "bound": BOUND,
        "extent": extent,
        "T": 20 * ((extent + 19) // 20),
        "pid1": {"position": positions[1], "length": lengths[1],
                 "birth_zero_based": born[1], "death_zero_based": died[1], "immortal": died[1] == n},
        "independent_cell_replay": audit,
        "common_prefix": {
            "commands": PREFIX, "identical_commands": True, "births": len(prefix_pids),
            "min_position": prefix_min, "max_assignment_end": prefix_max,
            "assignment_span": prefix_max - prefix_min,
            "active_after_prefix": len(active), "active_after_prefix_extent": active_extent,
        },
    }
    dest = HERE / "positions.txt"
    dest.write_text("".join(f"{positions[p]}\n" for p in range(1, len(positions))))
    report["positions_file"] = str(dest)
    report["positions_file_sha256"] = sha(dest)
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
