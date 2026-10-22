#!/usr/bin/env python3
"""Create reproducible online allocator streams independent of the open tests."""
from collections import deque
from pathlib import Path
import random

OUT = Path(__file__).resolve().parent / "generated"
OUT.mkdir(exist_ok=True)


def stream(name, target_live, operations, length_sampler, deletion, seed):
    rng = random.Random(seed)
    cmds, alive = [], deque()
    next_pid = 0
    for _ in range(operations):
        should_insert = not alive or len(alive) < target_live and rng.random() < 0.57
        if should_insert:
            next_pid += 1
            cmds.append(length_sampler(rng, next_pid))
            alive.append(next_pid)
        else:
            if deletion == "fifo":
                pid = alive.popleft()
            elif deletion == "lifo":
                pid = alive.pop()
            elif deletion == "shortest":
                pid = min(alive, key=lambda p: length_by_pid[p])
                alive.remove(pid)
            elif deletion == "longest":
                pid = max(alive, key=lambda p: length_by_pid[p])
                alive.remove(pid)
            else:
                j = rng.randrange(len(alive))
                alive.rotate(-j)
                pid = alive.popleft()
                alive.rotate(j)
            cmds.append(-pid)
        if cmds[-1] > 0:
            length_by_pid[next_pid] = cmds[-1]
    path = OUT / f"{name}.in"
    path.write_text(f"1\n{len(cmds)}\n" + "\n".join(map(str, cmds)) + "\n", encoding="ascii")
    return path


length_by_pid = {}


def uniform(rng, pid):
    return rng.randint(1, 40)


def short_skew(rng, pid):
    return rng.randint(1, 5) if rng.random() < 0.8 else rng.randint(6, 40)


def long_skew(rng, pid):
    return rng.randint(30, 40) if rng.random() < 0.8 else rng.randint(1, 29)


def bimodal(rng, pid):
    return 1 if rng.random() < 0.5 else 40


def cycle(rng, pid):
    return 1 + ((pid * 17 + pid // 13) % 40)


def make_burst(name, seed):
    rng = random.Random(seed)
    cmds=[]; live=[]; lengths={}; pid=0
    for _round in range(40):
        added=[]
        for _ in range(500):
            pid+=1; length=rng.randint(1,40); lengths[pid]=length
            cmds.append(length); added.append(pid); live.append(pid)
        # Recycle a pseudo-random third of the current cohort; commands are
        # generated without reference to any candidate placement strategy.
        rng.shuffle(added)
        for dead in added[:300]:
            cmds.append(-dead); live.remove(dead)
    # Keep all streams valid and nonempty at completion.
    return write(name, cmds)


def write(name, cmds):
    path=OUT/f"{name}.in"
    path.write_text(f"1\n{len(cmds)}\n"+"\n".join(map(str,cmds))+"\n",encoding="ascii")
    return path


def make_fragmentation():
    cmds=[]; pid=0
    # Repeated independent waves create mixed-size gaps and then make larger
    # requests compete with them. The sequence is fixed before any policy runs.
    for wave in range(50):
        cohort=[]
        for j in range(240):
            pid+=1
            length=1 if (j+wave)%2==0 else 39
            cmds.append(length); cohort.append(pid)
        # Delete every other member in alternating parity across waves.
        for idx,dead in enumerate(cohort):
            if (idx+wave)%2==0:
                cmds.append(-dead)
        for j in range(120):
            pid+=1
            cmds.append(40 if j%3==0 else 20)
    return write("fragmentation_waves",cmds)


def main():
    specs = [
        ("uniform_rand_20k", 800, 20_000, uniform, "random", 1101),
        ("uniform_rand_100k", 2_000, 100_000, uniform, "random", 1102),
        ("uniform_fifo_100k", 2_000, 100_000, uniform, "fifo", 1103),
        ("uniform_lifo_100k", 2_000, 100_000, uniform, "lifo", 1104),
        ("short_skew_rand_100k", 1_800, 100_000, short_skew, "random", 1105),
        ("long_skew_rand_100k", 1_400, 100_000, long_skew, "random", 1106),
        ("bimodal_rand_100k", 1_500, 100_000, bimodal, "random", 1107),
        ("cyclic_fifo_100k", 2_000, 100_000, cycle, "fifo", 1108),
        ("cyclic_lifo_100k", 2_000, 100_000, cycle, "lifo", 1109),
        ("delete_shortest_100k", 1_500, 100_000, uniform, "shortest", 1110),
        ("delete_longest_100k", 1_500, 100_000, uniform, "longest", 1111),
    ]
    paths=[]
    for spec in specs:
        length_by_pid.clear()
        paths.append(stream(*spec))
    paths.extend([make_burst("burst_delete_40x500", 2201), make_fragmentation()])
    for path in paths:
        print(path.name, path.stat().st_size)


if __name__ == "__main__":
    main()
