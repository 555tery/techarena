"""Replay a Pipes input/output trace and extract causal snapshots and labels."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from pathlib import Path

from pipes_common import HORIZON, Pair, Pipe, adjacent_disjoint_pairs


@dataclass(frozen=True)
class LabeledPair:
    pair: Pair
    y_left: int
    y_right: int


@dataclass(frozen=True)
class Snapshot:
    command_index: int
    active: tuple[Pipe, ...]
    pairs: tuple[LabeledPair, ...]


def extract_snapshots(
    input_path: Path,
    reply_path: Path,
    *,
    horizon: int = HORIZON,
) -> list[Snapshot]:
    input_lines = input_path.read_text(encoding="ascii").splitlines()
    if not input_lines:
        raise ValueError(f"empty input trace: {input_path}")
    header = input_lines[0].split()
    if len(header) != 2:
        raise ValueError("Pipes input header must contain weight and command count")
    command_count = int(header[1])
    command_tokens = [int(token) for line in input_lines[1:] for token in line.split()]
    if len(command_tokens) != command_count + 1 or command_tokens[-1] != 0:
        raise ValueError("input command count or zero terminator is invalid")
    commands = command_tokens[:-1]
    replies = reply_path.read_text(encoding="ascii").splitlines()
    if len(replies) != command_count:
        raise ValueError("there must be exactly one solver response per nonzero command")

    active: dict[int, Pipe] = {}
    starts: list[int] = []
    pipes_by_start: dict[int, Pipe] = {}
    removed_at: dict[int, int] = {}
    length_occurrences = [0] * 41
    next_pid = 1
    trench_length = 0
    active_snapshots: list[tuple[int, tuple[Pipe, ...]]] = []

    for step, (command, reply) in enumerate(zip(commands, replies), start=1):
        fields = reply.split()
        if command > 0:
            if not 1 <= command <= 40 or len(fields) != 2:
                raise ValueError(f"malformed placement at command {step}")
            digs, start = map(int, fields)
            if digs < 0 or start < 0:
                raise ValueError(f"negative placement data at command {step}")
            trench_length += 20 * digs
            parity = length_occurrences[command] % 2
            length_occurrences[command] += 1
            pipe = Pipe(next_pid, command, start, step, parity)
            position = bisect_left(starts, start)
            if position > 0:
                previous = pipes_by_start[starts[position - 1]]
                if previous.start + previous.length > start:
                    raise ValueError(f"placement overlaps prior pipe at command {step}")
            if position < len(starts):
                following = pipes_by_start[starts[position]]
                if start + command > following.start:
                    raise ValueError(f"placement overlaps following pipe at command {step}")
            if start + command > trench_length:
                raise ValueError(f"placement exceeds trench at command {step}")
            starts.insert(position, start)
            pipes_by_start[start] = pipe
            active[next_pid] = pipe
            next_pid += 1
        elif command < 0:
            if len(fields) != 1:
                raise ValueError(f"malformed removal at command {step}")
            pid = -command
            pipe = active.pop(pid, None)
            if pipe is None or int(fields[0]) != pipe.start:
                raise ValueError(f"invalid removal response at command {step}")
            removed_at[pid] = step
            position = bisect_left(starts, pipe.start)
            if position >= len(starts) or starts[position] != pipe.start:
                raise ValueError(f"active-coordinate index is inconsistent at command {step}")
            starts.pop(position)
            del pipes_by_start[pipe.start]
        else:
            raise ValueError("zero command appeared before the declared end")

        if step % horizon == 0 and step + horizon <= command_count:
            active_snapshots.append((step, tuple(active.values())))

    snapshots: list[Snapshot] = []
    for command_index, active_at_snapshot in active_snapshots:
        pairs = adjacent_disjoint_pairs(active_at_snapshot)
        labeled: list[LabeledPair] = []
        upper = command_index + horizon
        for pair in pairs:
            deleted_left = removed_at.get(pair.left.pid)
            deleted_right = removed_at.get(pair.right.pid)
            y_left = int(deleted_left is not None and command_index < deleted_left <= upper)
            y_right = int(deleted_right is not None and command_index < deleted_right <= upper)
            labeled.append(LabeledPair(pair, y_left, y_right))
        snapshots.append(Snapshot(command_index, active_at_snapshot, tuple(labeled)))
    return snapshots
