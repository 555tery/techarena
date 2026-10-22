#!/usr/bin/env python3
"""Generate an independent, fixed 64-case Pipes transport evaluation set.

This program reads public inputs only and never imports or runs a solver.
Its seed was sampled once with secrets.token_hex(16), before case generation.
No candidate source, score, previous generated case or experiment output is read.
"""

import hashlib
import json
import random
from pathlib import Path


MASTER_SEED = "fbf6bbc2dc5d4ffd228c33bd759c05d2"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def validate(commands):
    assert 1 <= len(commands) <= 200000
    live = {}
    next_pid = 1
    occupied = peak = 0
    for command in commands:
        assert isinstance(command, int) and command != 0
        if command > 0:
            assert 1 <= command <= 40
            live[next_pid] = command
            next_pid += 1
            occupied += command
            peak = max(peak, occupied)
        else:
            assert -command in live
            occupied -= live.pop(-command)
    assert occupied > 0
    return {"final_F": occupied, "peak_P": peak, "placements": next_pid - 1}


def read_public(number):
    path = ROOT / "data" / "pipes" / "open" / f"{number}.in"
    raw = path.read_bytes()
    # The repository's public files contain literal escaped CR/LF sequences.
    tokens = raw.decode("ascii").replace("\\r\\n", "\n").replace("\\n", "\n").split()
    n = int(tokens[1])
    commands = list(map(int, tokens[2:]))
    if len(commands) == n + 1 and commands[-1] == 0:
        commands.pop()
    assert len(commands) == n
    validate(commands)
    return commands, {"path": str(path.relative_to(ROOT)), "sha256": sha256(raw), "n": n}


class Stream:
    def __init__(self, prefix, rng):
        self.commands = []
        self.live = {}
        self.next_pid = 1
        self.rng = rng
        for command in prefix:
            self.put(command)

    def put(self, command):
        if command > 0:
            assert 1 <= command <= 40
            self.live[self.next_pid] = command
            self.next_pid += 1
        else:
            assert -command in self.live
            del self.live[-command]
        self.commands.append(command)

    def remove(self, mode, protected=()):
        pids = [pid for pid in self.live if pid not in protected]
        if not pids:
            return False
        if mode == "fifo":
            pid = pids[0]
        elif mode == "lifo":
            pid = pids[-1]
        elif mode == "parity":
            parity = self.rng.randrange(2)
            preferred = [pid for pid in pids if pid % 2 == parity]
            pid = self.rng.choice(preferred or pids)
        else:
            pid = self.rng.choice(pids)
        self.put(-pid)
        return True

    def fill(self, n, mode, profile="uniform", protected=(), delay=0):
        while len(self.commands) < n:
            step = len(self.commands)
            eligible = len(self.live) - sum(pid in self.live for pid in protected)
            target = 12 + (step // 53) % 67
            delete = step >= delay and eligible > 0 and (
                len(self.live) > target or self.rng.random() < 0.32
            )
            if delete:
                self.remove(mode, protected)
            else:
                if profile == "sizeshift":
                    ranges = ((1, 7), (28, 40), (1, 40), (17, 23))
                    lo, hi = ranges[(step // 47) % len(ranges)]
                    size = self.rng.randint(lo, hi)
                elif profile == "boundary":
                    size = self.rng.choice((1, 2, 3, 18, 19, 20, 21, 22, 38, 39, 40))
                else:
                    size = self.rng.randint(1, 40)
                self.put(size)
        if not self.live:
            assert len(self.commands) < 200000
            self.put(self.rng.randint(1, 40))


def build_case(index, family, public15):
    seed = int(sha256(f"{MASTER_SEED}:{index}:{family}".encode()), 16)
    rng = random.Random(seed)
    prefix_n = 0
    if index < 32:
        prefix_n = 2
        stream = Stream([3, 2], rng)
        j = index
        # Every early case diverges at command 3 while PID 2 is alive.
        # Protection extends through the entire synthetic suffix.
        if j < 8:
            stream.put(-1 if j % 2 == 0 else rng.randint(1, 40))
            stream.fill((29, 73, 157, 389, 947, 1729, 3109, 6311)[j],
                        ("fifo", "lifo", "parity", "random")[j % 4],
                        "boundary" if j % 2 else "uniform", protected=(2,))
        elif j < 20:
            j -= 8
            stream.put(rng.randint(1, 40))
            # Dense packets are defined by occupied volume, independent of layout.
            packet_sizes = (20, 40, 60, 80)
            packet_n = (2, 4, 8)[j // 4]
            for _ in range(packet_n):
                budget = packet_sizes[j % 4]
                while budget:
                    size = rng.randint(1, min(40, budget))
                    stream.put(size)
                    budget -= size
                stream.remove(("fifo", "lifo", "parity", "random")[j % 4], (2,))
            stream.fill(len(stream.commands) + (31, 119, 487)[j // 4],
                        ("fifo", "lifo", "parity", "random")[j % 4],
                        "boundary", protected=(2,))
        else:
            j -= 20
            for block in range(1 + j // 4):
                sizes = list(range(1, 41))
                rng.shuffle(sizes)
                for size in sizes:
                    stream.put(size)
                for _ in range(7 + 3 * block):
                    stream.remove(("fifo", "lifo", "parity", "random")[j % 4], (2,))
            stream.fill(len(stream.commands) + (17, 79, 331)[j // 4],
                        ("fifo", "lifo", "parity", "random")[j % 4],
                        "sizeshift", protected=(2,))
        assert stream.commands[:2] == [3, 2]
        assert stream.commands[2] != -2 and 2 in stream.live
    elif index < 48:
        j = index - 32
        prefix_n = (3, 4, 8, 16, 25, 40, 64, 128)[j // 2]
        stream = Stream(public15[:prefix_n], rng)
        suffix_n = rng.randint(13, 71) if j % 2 == 0 else rng.randint(601, 3071)
        # An explicit changed next command prevents accidental continued copying.
        next_public = public15[prefix_n]
        choices = [size for size in range(1, 41) if size != next_public]
        stream.put(rng.choice(choices))
        stream.fill(prefix_n + suffix_n,
                    ("fifo", "lifo", "parity", "random")[j % 4],
                    "sizeshift" if j % 3 == 0 else "uniform")
    else:
        j = index - 48
        stream = Stream([], rng)
        n = (241, 997, 4093, 16381)[j // 4]
        mode = ("lifo", "fifo", "parity", "random")[j % 4]
        stream.fill(n, mode, "sizeshift" if j >= 8 else "uniform",
                    delay=(n // 5 if j % 4 == 3 else 0))
    return stream.commands, seed, prefix_n


def main():
    public11, meta11 = read_public(11)
    public15, meta15 = read_public(15)
    assert public11[:2] == public15[:2] == [3, 2]
    assert public11[2] == public15[2] == -2
    # All copied prefixes belong to the common public prefix.
    assert public11[:128] == public15[:128]
    out = HERE / "fresh"
    out.mkdir(parents=True, exist_ok=True)
    families = (["early_deletions"] * 8 + ["early_dense_volume"] * 12
                + ["early_size_permutations"] * 12 + ["other_public_prefixes"] * 16
                + ["neutral"] * 16)
    cases = []
    seen = set()
    for index, family in enumerate(families):
        commands, seed, prefix_n = build_case(index, family, public15)
        stats = validate(commands)
        name = f"fresh_{index + 1:02d}"
        filename = f"{name}.in"
        data = (f"1 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n").encode("ascii")
        digest = sha256(data)
        assert digest not in seen
        seen.add(digest)
        (out / filename).write_bytes(data)
        cases.append({"name": name, "filename": filename, "sha256": digest,
                      "family": family, "n": len(commands), "seed": str(seed),
                      "public_prefix_commands": prefix_n, **stats})
    assert len(cases) == 64
    assert len(list(out.glob("*.in"))) == 64
    manifest = {
        "schema": "pipes-independent-fresh-v1",
        "generator": "../generate_fresh.py",
        "generator_sha256": sha256(Path(__file__).read_bytes()),
        "master_seed": MASTER_SEED,
        "provenance": {
            "seed_origin": "One fresh secrets.token_hex(16) draw before generation; never score-conditioned",
            "inputs_read": [meta11, meta15],
            "selection": "Fixed 32 early / 16 other common public prefixes / 16 neutral; no filtering by solver behavior",
            "isolation": "No candidate source, candidate results, old directed inputs, previous fresh round, or current search read; no solvers run",
            "early_prefix_rule": "[3,2] copied; command 3 diverges while PID 2 remains active",
            "reproduction": "Python standard library random.Random, one SHA256-derived seed per case",
        },
        "distribution": {"early_deletions": 8, "early_dense_volume": 12,
                         "early_size_permutations": 12, "other_public_prefixes": 16,
                         "neutral": 16},
        "validation": {"success": True, "case_count": 64, "all_hashes_unique": True,
                       "operation_count_bounds": [1, 200000], "length_bounds": [1, 40],
                       "all_deletions_valid": True, "all_final_F_positive": True},
        "cases": cases,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(cases), "validation_success": True,
                      "manifest_sha256": sha256(manifest_path.read_bytes()),
                      "generator_sha256": manifest["generator_sha256"]}))


if __name__ == "__main__":
    main()
