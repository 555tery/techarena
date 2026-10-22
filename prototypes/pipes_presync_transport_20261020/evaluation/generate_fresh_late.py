#!/usr/bin/env python3
"""Independent retained-prefix continuations; no solver or score access."""

import hashlib
import json
import random
from pathlib import Path


MASTER_SEED = "515ef5010543f2d6ec732b0ae4df9084"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LANDMARKS = (14, 17, 67, 109, 233, 255, 303, 352, 397, 402)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate(commands):
    assert 1 <= len(commands) <= 200000
    live = {}
    allocated = 0
    occupied = peak = 0
    for command in commands:
        if command > 0:
            assert 1 <= command <= 40
            allocated += 1
            live[allocated] = command
            occupied += command
            peak = max(peak, occupied)
        else:
            assert command < 0 and -command in live
            occupied -= live.pop(-command)
    assert occupied > 0
    return {"final_F": occupied, "peak_P": peak, "placements": allocated}


def public(number):
    path = ROOT / "data" / "pipes" / "open" / f"{number}.in"
    raw = path.read_bytes()
    tokens = raw.decode("ascii").replace("\\r\\n", "\n").replace("\\n", "\n").split()
    n = int(tokens[1])
    commands = list(map(int, tokens[2:]))
    if len(commands) == n + 1 and commands[-1] == 0:
        commands.pop()
    assert len(commands) == n
    validate(commands)
    return commands, {"path": str(path.relative_to(ROOT)), "sha256": digest(raw), "n": n}


class Stream:
    def __init__(self, prefix, rng):
        self.commands = []
        self.live = {}
        self.next_pid = 1
        self.volume = 0
        self.rng = rng
        for command in prefix:
            self.put(command)

    def put(self, command):
        if command > 0:
            assert 1 <= command <= 40
            self.live[self.next_pid] = command
            self.next_pid += 1
            self.volume += command
        else:
            assert -command in self.live
            self.volume -= self.live.pop(-command)
        self.commands.append(command)

    def delete(self, protected, policy):
        options = [pid for pid in self.live if pid != protected]
        if not options:
            return False
        if policy == "fifo":
            pid = options[0]
        elif policy == "lifo":
            pid = options[-1]
        elif policy == "parity":
            parity = self.rng.randrange(2)
            same_parity = [pid for pid in options if pid % 2 == parity]
            pid = self.rng.choice(same_parity or options)
        else:
            pid = self.rng.choice(options)
        self.put(-pid)
        return True


def generate(number, landmark, variant, index, commands):
    seed = int(digest(f"{MASTER_SEED}:{number}:{landmark}:{variant}".encode()), 16)
    rng = random.Random(seed)
    prefix_n = landmark
    # A public landmark may be a deletion. Use the immediately preceding
    # allocation so that the copied prefix always ends at an allocation.
    while commands[prefix_n - 1] < 0:
        prefix_n -= 1
    stream = Stream(commands[:prefix_n], rng)
    target_pid = stream.next_pid - 1
    assert target_pid in stream.live
    suffix_n = (241, 359, 631, 997)[index % 4] + rng.randrange(101)
    retained_n = suffix_n * (2 if variant else 3) // 5
    release = index % 3 == 0
    family = ("retained_deletions", "retained_bursts", "retained_capacity_fill", "retained_mixed")[index % 4]
    policy = ("fifo", "lifo", "parity", "random")[(index // 4) % 4]
    next_public = commands[prefix_n]
    stream.put(rng.choice([size for size in range(1, 41) if size != next_public]))
    released_at = None
    fill_budget = 0
    while len(stream.commands) < prefix_n + suffix_n:
        step = len(stream.commands) - prefix_n
        if release and step >= retained_n and released_at is None:
            assert target_pid in stream.live
            stream.put(-target_pid)
            released_at = step + 1
            continue
        protected = target_pid if target_pid in stream.live else None
        if family == "retained_deletions":
            delete = step % 11 < 6
        elif family == "retained_bursts":
            delete = step % 41 >= 25
        elif family == "retained_capacity_fill":
            delete = step % 29 < 10
        else:
            delete = rng.random() < 0.43
        if delete and stream.delete(protected, policy):
            fill_budget = 0
        else:
            if family == "retained_capacity_fill":
                # Exactly refill a volume boundary in multiples of 20,
                # independently of any solver's actual trench geometry.
                if fill_budget == 0:
                    fill_budget = ((stream.volume + 19) // 20 + 1 + index % 3) * 20 - stream.volume
                size = rng.randint(1, min(40, fill_budget))
                fill_budget -= size
            elif family == "retained_bursts":
                size = rng.choice((1, 2, 3, 17, 19, 20, 21, 23, 38, 39, 40))
            elif family == "retained_mixed":
                lo, hi = ((1, 8), (24, 40), (1, 40))[(step // 37) % 3]
                size = rng.randint(lo, hi)
            else:
                size = rng.randint(1, 40)
            stream.put(size)
    assert stream.commands[:prefix_n] == commands[:prefix_n]
    assert stream.commands[prefix_n] != commands[prefix_n]
    assert -target_pid not in stream.commands[prefix_n:prefix_n + retained_n]
    if release:
        assert released_at is not None and released_at > retained_n
    else:
        assert target_pid in stream.live
    if not stream.live:
        stream.put(rng.randint(1, 40))
    return stream.commands, {
        "family": family, "seed": str(seed), "public_test": number,
        "landmark_command": landmark, "public_prefix_commands": prefix_n,
        "target_pid": target_pid, "target_length": commands[prefix_n - 1],
        "protected_suffix_commands": retained_n, "target_release_suffix_command": released_at,
        "variant": variant,
    }


def main():
    sources = {number: public(number) for number in (8, 13)}
    specifications = [(number, step, 0) for number in (8, 13) for step in LANDMARKS]
    specifications += [(number, step, 1) for number in (8, 13) for step in LANDMARKS[:6]]
    assert len(specifications) == 32
    out = HERE / "fresh-late"
    out.mkdir(parents=True, exist_ok=True)
    cases = []
    seen = set()
    for index, (number, landmark, variant) in enumerate(specifications):
        commands, metadata = generate(number, landmark, variant, index, sources[number][0])
        stats = validate(commands)
        name = f"fresh_late_{index + 1:02d}"
        filename = f"{name}.in"
        raw = (f"1 {len(commands)}\n" + "\n".join(map(str, commands)) + "\n").encode("ascii")
        sha = digest(raw)
        assert sha not in seen
        seen.add(sha)
        (out / filename).write_bytes(raw)
        cases.append({"name": name, "filename": filename, "sha256": sha,
                      "n": len(commands), **metadata, **stats})
    assert len(list(out.glob("*.in"))) == 32
    manifest = {
        "schema": "pipes-independent-fresh-retained-prefix-v1",
        "generator": "../generate_fresh_late.py",
        "generator_sha256": digest(Path(__file__).read_bytes()),
        "master_seed": MASTER_SEED,
        "provenance": {
            "seed_origin": "One independent secrets.token_hex(16) draw before generation; no score conditioning",
            "inputs_read": [sources[number][1] for number in (8, 13)],
            "selection": "All 10 predeclared landmarks in Open8/Open13, plus independent variants of the first six per source",
            "landmark_rule": "1-based public command index; a deletion landmark uses its immediately preceding allocation",
            "isolation": "No candidate, results, current search, previous directed inputs, or existing fresh64 read; no solver executed",
            "fresh_gate": "Append these 32 cases to the separately frozen fresh64; no tuning after gate opening",
        },
        "validation": {"success": True, "case_count": 32, "all_hashes_unique": True,
                       "operation_count_bounds": [1, 200000], "length_bounds": [1, 40],
                       "all_deletions_valid": True, "all_final_F_positive": True,
                       "retained_prefix_and_next_command_divergence": True,
                       "target_survives_declared_suffix": True},
        "cases": cases,
    }
    path = out / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case_count": 32, "validation_success": True,
                      "generator_sha256": manifest["generator_sha256"],
                      "manifest_sha256": digest(path.read_bytes())}))


if __name__ == "__main__":
    main()
