#!/usr/bin/env python3
"""Order-statistics equivalent of the local Pipes synthetic generator."""
from __future__ import annotations

import argparse
import heapq
import random
from pathlib import Path


def sample_length(rng: random.Random, profile: str) -> int:
    if profile == "uniform":
        return rng.randint(1, 40)
    if profile == "short-heavy":
        pick = rng.random()
        if pick < 0.65:
            return rng.randint(1, 5)
        if pick < 0.90:
            return rng.randint(6, 20)
        return rng.randint(21, 40)
    if profile == "long-heavy":
        pick = rng.random()
        if pick < 0.10:
            return rng.randint(1, 5)
        if pick < 0.35:
            return rng.randint(6, 20)
        return rng.randint(21, 40)
    raise ValueError(f"unknown length profile: {profile}")


class Fenwick:
    def __init__(self, size: int):
        self.size = size
        self.tree = [0] * (size + 1)

    def add(self, index: int, delta: int) -> None:
        while index <= self.size:
            self.tree[index] += delta
            index += index & -index

    def find_by_order(self, order: int) -> int:
        """Return the 1-based position of the zero-based active-item rank."""
        target = order + 1
        index = 0
        bit = 1 << (self.size.bit_length() - 1)
        while bit:
            next_index = index + bit
            if next_index <= self.size and self.tree[next_index] < target:
                target -= self.tree[next_index]
                index = next_index
            bit >>= 1
        return index + 1


def generate(seed: int, operations: int, length_profile: str, churn: float,
             batch: int, deletion_policy: str) -> list[int]:
    if operations < 1 or operations > 200_000:
        raise ValueError("operations must be in [1, 200000]")
    if not 0.0 <= churn < 1.0:
        raise ValueError("churn must be in [0, 1)")
    if batch < 0:
        raise ValueError("batch must be nonnegative")
    rng = random.Random(seed)
    commands: list[int] = []
    lengths = [0] * (operations + 2)
    alive = bytearray(operations + 2)
    active = Fenwick(operations + 1)
    shortest: list[tuple[int, int]] = []
    longest: list[tuple[int, int]] = []
    live_count = 0
    next_pid = 1
    drain_phase = False
    phase_count = 0

    def add_pipe(length: int) -> None:
        nonlocal live_count, next_pid
        pid = next_pid
        next_pid += 1
        lengths[pid] = length
        alive[pid] = 1
        active.add(pid, 1)
        heapq.heappush(shortest, (length, pid))
        heapq.heappush(longest, (-length, pid))
        live_count += 1
        commands.append(length)

    def delete_pipe() -> None:
        nonlocal live_count
        if deletion_policy == "random":
            rank = rng.randrange(live_count)
            pid = active.find_by_order(rank)
        elif deletion_policy == "oldest":
            pid = active.find_by_order(0)
        elif deletion_policy == "newest":
            pid = active.find_by_order(live_count - 1)
        elif deletion_policy == "shortest":
            while shortest and not alive[shortest[0][1]]:
                heapq.heappop(shortest)
            pid = shortest[0][1]
            heapq.heappop(shortest)
        elif deletion_policy == "longest":
            while longest and not alive[longest[0][1]]:
                heapq.heappop(longest)
            pid = longest[0][1]
            heapq.heappop(longest)
        else:
            raise ValueError(f"unknown deletion policy: {deletion_policy}")
        alive[pid] = 0
        active.add(pid, -1)
        live_count -= 1
        commands.append(-pid)

    for operation_index in range(operations):
        if operation_index == operations - 1:
            add_pipe(sample_length(rng, length_profile))
            continue
        if live_count and drain_phase:
            delete_pipe()
            phase_count -= 1
            if phase_count <= 0:
                drain_phase = False
                phase_count = 0
            continue

        should_remove = bool(live_count) and rng.random() < churn
        if should_remove:
            delete_pipe()
        else:
            add_pipe(sample_length(rng, length_profile))
            if batch > 0 and live_count >= batch and not drain_phase:
                drain_phase = True
                phase_count = max(1, (batch * 3) // 4)
    return commands


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--operations", type=int, default=20_000)
    parser.add_argument("--length-profile", choices=("uniform", "short-heavy", "long-heavy"), default="uniform")
    parser.add_argument("--churn", type=float, default=0.42)
    parser.add_argument("--batch", type=int, default=500)
    parser.add_argument("--deletion-policy", choices=("random", "oldest", "newest", "shortest", "longest"), default="random")
    parser.add_argument("--weight", type=float, default=1.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    commands = generate(args.seed, args.operations, args.length_profile, args.churn,
                        args.batch, args.deletion_policy)
    lines = [f"{args.weight} {len(commands)}", *(str(c) for c in commands), "0"]
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"wrote {len(commands)} commands from seed {args.seed} to {path}")


if __name__ == "__main__":
    main()
