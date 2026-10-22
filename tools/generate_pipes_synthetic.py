#!/usr/bin/env python3
"""Create deterministic, valid synthetic Pipes command streams."""

import argparse
import random
from pathlib import Path


def sample_length(rng, profile):
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
    raise ValueError("unknown length profile: " + profile)


def generate(seed, operations, length_profile, churn, batch, deletion_policy):
    if operations < 1 or operations > 200000:
        raise ValueError("operations must be in [1, 200000]")
    rng = random.Random(seed)
    commands = []
    live = []
    lengths = {}
    next_pid = 1
    # The batch target periodically drives the live set up and then drains it,
    # producing fragmentation without encoding any open-test sequence.
    drain_phase = False
    phase_count = 0
    for operation_index in range(operations):
        # Keep one live pipe at EOF so generated KPI comparisons are not
        # degenerate (the official interactor requires a nonempty trench).
        if operation_index == operations - 1:
            length = sample_length(rng, length_profile)
            commands.append(length)
            live.append(next_pid)
            lengths[next_pid] = length
            next_pid += 1
            continue
        if live and drain_phase:
            index = choose_delete_index(rng, live, lengths, deletion_policy)
            pid = live.pop(index)
            commands.append(-pid)
            del lengths[pid]
            phase_count -= 1
            if phase_count <= 0:
                drain_phase = False
                phase_count = 0
            continue

        should_remove = bool(live) and rng.random() < churn
        if should_remove:
            index = choose_delete_index(rng, live, lengths, deletion_policy)
            pid = live.pop(index)
            commands.append(-pid)
            del lengths[pid]
        else:
            length = sample_length(rng, length_profile)
            commands.append(length)
            live.append(next_pid)
            lengths[next_pid] = length
            next_pid += 1
            if batch > 0 and len(live) >= batch and not drain_phase:
                drain_phase = True
                phase_count = max(1, (batch * 3) // 4)
    return commands


def choose_delete_index(rng, live, lengths, policy):
    if policy == "random":
        return rng.randrange(len(live))
    if policy == "oldest":
        return 0
    if policy == "newest":
        return len(live) - 1
    if policy == "shortest":
        return min(range(len(live)), key=lambda i: (lengths[live[i]], live[i]))
    if policy == "longest":
        return max(range(len(live)), key=lambda i: (lengths[live[i]], -live[i]))
    raise ValueError("unknown deletion policy: " + policy)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True, help="deterministic PRNG seed")
    parser.add_argument("--operations", type=int, default=20000)
    parser.add_argument("--length-profile", choices=("uniform", "short-heavy", "long-heavy"), default="uniform")
    parser.add_argument("--churn", type=float, default=0.42, help="probability of deletion when live set is nonempty")
    parser.add_argument("--batch", type=int, default=500, help="live-set threshold for periodic drain; 0 disables it")
    parser.add_argument("--deletion-policy", choices=("random", "oldest", "newest", "shortest", "longest"), default="random")
    parser.add_argument("--weight", type=float, default=1.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    if not 0.0 <= args.churn < 1.0:
        parser.error("--churn must be in [0,1)")
    if args.batch < 0:
        parser.error("--batch cannot be negative")
    commands = generate(args.seed, args.operations, args.length_profile, args.churn, args.batch,
                        args.deletion_policy)
    lines = ["%s %d" % (args.weight, len(commands))]
    lines.extend(map(str, commands))
    lines.append("0")
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    print("wrote %d commands from seed %d to %s" % (len(commands), args.seed, path))


if __name__ == "__main__":
    main()
