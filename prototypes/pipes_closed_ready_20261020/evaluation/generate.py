#!/usr/bin/env python3
"""Predeclared, solver-independent causal streams; no solver imports or runs."""
import collections
import hashlib
import heapq
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FAMILIES = ["iid_churn", "fifo", "lifo", "random_lifetime", "cohort_lifetimes",
            "waves", "rising_trend", "broken_trend", "alternating_sizes",
            "dense_fragmentation", "bimodal", "size_lifetime_correlation",
            "size_lifetime_inversion", "bursty_arrivals", "retained_background",
            "cyclic_profiles"]
SUFFIXES = ["retained_anchors", "lifetime_inversion", "stop_after_prefix",
            "fills", "bursts", "churn", "near_public_perturbation", "cohort_replacement"]


class Stream:
    def __init__(self, rng):
        self.rng = rng
        self.commands = []
        self.live = {}
        self.ids = []
        self.pos = {}
        self.order = collections.deque()
        self.stack = []
        self.deadlines = []
        self.next_pid = 1
        self.volume = self.peak = self.peak_count = 0
        self.anchors = set()

    def emit(self, command):
        assert command != 0
        if command > 0:
            assert command <= 40
            pid = self.next_pid
            self.next_pid += 1
            self.live[pid] = command
            self.pos[pid] = len(self.ids)
            self.ids.append(pid)
            self.order.append(pid)
            self.stack.append(pid)
            self.volume += command
            # Lifetimes are sampled on arrival, independently of placement.
            deadline = len(self.commands) + self.rng.randint(20, 350)
            heapq.heappush(self.deadlines, (deadline, pid))
        else:
            pid = -command
            assert pid in self.live, (len(self.commands), command)
            self.volume -= self.live.pop(pid)
            idx = self.pos.pop(pid)
            last = self.ids.pop()
            if idx < len(self.ids):
                self.ids[idx] = last
                self.pos[last] = idx
        self.commands.append(command)
        self.peak = max(self.peak, self.volume)
        self.peak_count = max(self.peak_count, len(self.live))

    def deletion(self, policy="random", protect=False):
        if len(self.live) <= 1:
            return None
        if policy in ("fifo", "lifo") and not protect:
            seq = self.order if policy == "fifo" else self.stack
            while seq and (seq[0] if policy == "fifo" else seq[-1]) not in self.live:
                seq.popleft() if policy == "fifo" else seq.pop()
            return seq[0] if policy == "fifo" else seq[-1]
        if policy == "deadline" and not protect:
            while self.deadlines and self.deadlines[0][1] not in self.live:
                heapq.heappop(self.deadlines)
            return self.deadlines[0][1]
        candidates = [self.ids[self.rng.randrange(len(self.ids))] for _ in range(16)]
        if protect:
            candidates = [p for p in candidates if p not in self.anchors]
            if not candidates:
                return None
        if policy == "short":
            return min(candidates, key=lambda p: (self.live[p], p))
        if policy == "long":
            return max(candidates, key=lambda p: (self.live[p], -p))
        return candidates[0]


def event(s, family, t, n):
    r = s.rng
    phase = t / max(1, n)
    prob, policy, protect = .43, "random", False
    length = r.randint(1, 40)
    if family == "fifo": prob, policy = .46, "fifo"
    elif family == "lifo": prob, policy = .46, "lifo"
    elif family == "random_lifetime":
        prob, policy = (.18 if len(s.live) < 100 else .55), "deadline"
    elif family == "cohort_lifetimes":
        prob, policy = (.12 if t % 230 < 130 else .79), "fifo"
        length = r.choice([7, 11, 19, 23, 31])
    elif family == "waves":
        prob = .13 if t % 400 < 230 else .83
    elif family == "rising_trend":
        length = max(1, min(40, int(2 + 35 * phase) + r.randint(-3, 3)))
        prob, policy = .35, "fifo"
    elif family == "broken_trend":
        trend = phase * 2 if phase < .5 else 2 - phase * 2
        length = max(1, min(40, int(3 + 34 * trend) + r.randint(-4, 4)))
        prob, policy = .41, ("fifo" if phase < .55 else "lifo")
    elif family == "alternating_sizes":
        length = r.randint(1, 6) if t % 2 == 0 else r.randint(31, 40)
        prob, policy = .44, "short"
    elif family == "dense_fragmentation":
        length = r.randint(1, 5) if t % 300 < 210 else r.randint(15, 40)
        prob, policy = (.30 if t % 300 < 150 else .60), "random"
    elif family == "bimodal":
        length = r.randint(2, 9) if r.random() < .63 else r.randint(28, 40)
        prob, policy = .40, "random"
    elif family == "size_lifetime_correlation":
        prob, policy = .43, "short"
        length = r.choice([3, 8, 17, 29, 38])
    elif family == "size_lifetime_inversion":
        prob, policy = .43, "long"
        length = r.choice([2, 9, 18, 27, 39])
    elif family == "bursty_arrivals":
        prob, policy = (.04 if t % 173 < 87 else .86), "random"
        length = r.randint(1, 12) if (t // 173) % 2 else r.randint(21, 40)
    elif family == "retained_background":
        if t == 120: s.anchors.update(s.live)
        prob, protect = .44, True
        length = r.randint(2, 9) if r.random() < .75 else r.randint(30, 40)
    elif family == "cyclic_profiles":
        band = (t // 113) % 3
        length = r.randint(*[(1, 10), (11, 24), (25, 40)][band])
        prob, policy = [.26, .55, .38][band], ["fifo", "lifo", "random"][band]
    pid = s.deletion(policy, protect) if r.random() < prob else None
    s.emit(-pid if pid is not None else length)


def ordinary(seed, n, index, final=False):
    s = Stream(random.Random(seed))
    a = FAMILIES[index % 16]
    rep = index // 16
    b = FAMILIES[(index % 16 + 5 + 3 * rep) % 16]
    for t in range(n):
        family = a
        if final:
            if rep == 0: family = a if t < n * .43 else b
            elif rep == 1: family = a if (t // 127) % 2 else b
            elif rep == 2: family = a if s.rng.random() < .65 else b
            else: family = a if t < n * .31 or t > n * .76 else b
        event(s, family, t, n)
    return s, (f"{a}+{b}/composition{rep}" if final else a)


def prefix_stream(seed, index, final=False):
    r = random.Random(seed)
    case = index % 15 + 1
    long = final and index in (62, 63)
    if long: case = 14 if index == 62 else 15
    path = ROOT / "data/pipes/open" / f"{case}.in"
    raw = path.read_bytes()
    tokens = raw.split()
    allcmds = [int(x) for x in tokens[2:-1]]
    assert len(allcmds) == int(tokens[1]) and int(tokens[-1]) == 0
    if long: plen = 18031 if case == 14 else 18439
    elif len(allcmds) <= 32: plen = max(1, len(allcmds) - 1 - index % 3)
    else: plen = r.randint(17, min(3800, len(allcmds) - 1))
    suffix = SUFFIXES[(index + (3 if final else 0)) % len(SUFFIXES)]
    if suffix == "stop_after_prefix" and len(allcmds) >= 1002:
        plen = max(plen, min(len(allcmds)-1, 1100 + index*3))
    if suffix == "stop_after_prefix" and plen < 500: suffix = "fills"
    s = Stream(r)
    for c in allcmds[:plen]: s.emit(c)
    # A stop is a true EOF at a nonempty legal public prefix.
    if suffix == "stop_after_prefix":
        while not s.live:
            s.emit(allcmds[plen]); plen += 1
        target = plen
    else:
        target = plen + (2200 if long else r.randint(900, 2050))
        if suffix == "retained_anchors":
            s.anchors.update(p for p in s.live if r.random() < .35)
        for j in range(target - plen):
            pid = None
            length = r.randint(1, 40)
            if suffix == "retained_anchors":
                if r.random() < .47: pid = s.deletion("random", True)
            elif suffix == "lifetime_inversion":
                if r.random() < .56: pid = s.deletion("lifo" if j < 500 else "long")
                length = r.randint(1, 10) if j % 4 else r.randint(25, 40)
            elif suffix == "fills":
                if r.random() < .09: pid = s.deletion("random")
            elif suffix == "bursts":
                if r.random() < (.86 if j % 181 > 87 else .03): pid = s.deletion("fifo")
                length = r.randint(24, 40) if (j // 181) % 2 else r.randint(1, 11)
            elif suffix == "churn":
                if r.random() < .58: pid = s.deletion("random")
            elif suffix == "near_public_perturbation":
                # Continue original causal removals if still legal; perturb sizes
                # occasionally and replace stale removals by legal live choices.
                c = allcmds[(plen + j) % len(allcmds)]
                if c > 0:
                    length = max(1, min(40, c + (r.choice([-2, -1, 1, 2]) if r.random() < .16 else 0)))
                elif -c in s.live and len(s.live) > 1: pid = -c
                else: pid = s.deletion("random")
            elif suffix == "cohort_replacement":
                if r.random() < (.72 if j % 241 < 100 else .22): pid = s.deletion("fifo")
                length = r.choice([5, 12, 18, 26, 35])
            s.emit(-pid if pid is not None else length)
    info = {"case": case, "source": str(path.relative_to(ROOT)),
            "source_sha256": hashlib.sha256(raw).hexdigest(), "prefix_n": plen,
            "prefix_commands_sha256": hashlib.sha256(("\n".join(map(str, allcmds[:plen])) + "\n").encode()).hexdigest(),
            "source_command_count": len(allcmds), "suffix": suffix, "suffix_n": target-plen}
    return s, "public_prefix/" + suffix, info


def audit(commands):
    live = {}; pid = 1; volume = peak = peak_count = 0
    assert 1 <= len(commands) <= 200000
    for c in commands:
        if c > 0:
            assert 1 <= c <= 40
            live[pid] = c; pid += 1; volume += c
        else:
            assert c < 0 and -c in live
            volume -= live.pop(-c)
        peak = max(peak, volume); peak_count = max(peak_count, len(live))
    assert len(live) >= 1 and volume > 0
    return volume, peak, len(live), peak_count


def save(split, index, s, family, stratum, seed, public=None):
    stats = audit(s.commands)
    assert stats == (s.volume, s.peak, len(s.live), s.peak_count)
    name = f"case-{index:03d}.in"
    raw = (f"1 {len(s.commands)}\n" + "\n".join(map(str, s.commands)) + "\n0\n").encode("ascii")
    folder = HERE / split
    folder.mkdir(exist_ok=True)
    (folder / name).write_bytes(raw)
    return {"id": f"{split}-{index:03d}", "file": name, "family": family,
            "stratum": stratum, "seed": seed, "n": len(s.commands),
            "final_live_volume": stats[0], "peak_live_volume": stats[1],
            "final_live_count": stats[2], "peak_live_count": stats[3],
            "sha256": hashlib.sha256(raw).hexdigest(), "public_prefix": public}


def main():
    allrows = []
    manifests = {}
    for split, half, base in [("calibration", 32, 2026102001000), ("final", 64, 2026102009000)]:
        rows = []
        for i in range(half):
            seed = base + i
            n = 1000 + (i * 977 + (371 if half == 64 else 0)) % 5001
            if i in ((0, 19, 37, 58) if half == 64 else (7, 29)): n = 14921 + i * 3
            s, family = ordinary(seed, n, i, half == 64)
            rows.append(save(split, len(rows), s, family, "ordinary", seed))
        for i in range(half):
            seed = base + 1000 + i
            s, family, public = prefix_stream(seed, i, half == 64)
            rows.append(save(split, len(rows), s, family, "prefix", seed, public))
        manifests[split] = {"schema_version": 1, "split": split, "weight": 1,
            "selection_status": "predeclared_before_any_candidate_results", "cases": rows}
        allrows.extend(rows)
    rows = []
    for i, family in enumerate(["max_alive", "heavy_churn", "regime_switches"]):
        seed = 2026102090000 + i
        s = Stream(random.Random(seed))
        for t in range(200000):
            if i == 0: s.emit(s.rng.randint(1, 40))
            elif i == 1:
                pid = s.deletion("random") if len(s.live) > 120 or (len(s.live) > 50 and s.rng.random() < .52) else None
                s.emit(-pid if pid is not None else s.rng.randint(1, 40))
            else:
                event(s, ["waves", "lifo", "dense_fragmentation", "size_lifetime_inversion", "rising_trend"][min(4,t//40000)], t % 40000, 40000)
        rows.append(save("stress", i, s, family, "stress", seed))
    manifests["stress"] = {"schema_version": 1, "split": "stress", "weight": 1, "cases": rows}
    allrows.extend(rows)
    hashes = [r["sha256"] for r in allrows]
    assert len(set(hashes)) == len(hashes), "new input duplicates"
    # Read only SHA-like byte strings, never parse any solver metrics/results.
    known_paths = ["data/pipes/synthetic/final-holdout-v2/manifest.json",
        "prototypes/pipes_baseline_router_v1/data/manifest.json",
        "prototypes/pipes_baseline_router_v1/data/final_validation/manifest.json",
        "prototypes/pipes_architecture_v2_20261018/data/train/manifest.json",
        "prototypes/pipes_architecture_v2_20261018/data/dev/manifest.json",
        "prototypes/pipes_architecture_v2_20261018/data/final/manifest.json",
        "prototypes/pipes_prefix_shock_20261019/manifest.json",
        "prototypes/pipes_g5420_cpu_20261020/tests/manifest.json",
        "shinka-pipes/search-v3/task/data/search/manifest.json",
        "shinka-pipes/search-v3/stress/data/manifest.json",
        "shinka-pipes/search-v3-1/task/data/search/manifest.json",
        "shinka-pipes/search-v3-1/stress/data/manifest.json"]
    checked = []; known = set()
    for rel in known_paths:
        p = ROOT / rel
        if p.exists():
            found = {x.decode().lower() for x in re.findall(rb"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])", p.read_bytes())}
            known.update(found)
            checked.append({"path": rel, "sha256_tokens": len(found)})
    overlap = sorted(set(hashes) & known)
    assert not overlap, "duplicate of a known hash"
    for split, manifest in manifests.items():
        (HERE / split / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    summary = {"schema_version": 1, "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "counts": {k: len(v["cases"]) for k,v in manifests.items()},
        "ordinary_base_families": FAMILIES, "final_design": "64 causal compositions of two mechanisms; four composition schedules; different seeds and sizes",
        "public_prefix_coverage": {k: sorted({r["public_prefix"]["case"] for r in v["cases"] if r["public_prefix"]}) for k,v in manifests.items() if k != "stress"},
        "all_new_inputs_unique": True, "known_hash_overlap": overlap, "known_manifests_checked": checked,
        "known_sha256_tokens": len(known), "validation": {"legal_deletes": True, "lengths_1_to_40": True, "commands_le_200000": True, "positive_final_live_volume": True, "independent_second_pass": True},
        "independence_constraints": ["No candidate solver code was read or modified by this generator design.",
            "No candidates were run; no candidate scores or outcomes were inspected.",
            "No platform access; no recursive agents.",
            "Parameters fixed by formulas and seeds, never selected using score.",
            "Only official public streams are reused as declared prefixes; ordinary streams do not depend on them.",
            "Public-prefix stratum deliberately shares known events; it is not an independent unseen-prefix distribution.",
            "Final mechanism compositions differ from calibration; final outcomes must remain unseen until candidate freeze.",
            "Hash comparison is finite and limited to the listed available manifests, not a complete repository deduplication.",
            "Synthetic robustness evidence does not establish hidden-test generalization."],
        "manifests": {k: {"path": f"{k}/manifest.json", "sha256": hashlib.sha256((HERE/k/"manifest.json").read_bytes()).hexdigest()} for k in manifests}}
    (HERE / "generation-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"counts": summary["counts"], "manifests": summary["manifests"], "unique": True, "known_overlap": overlap}, indent=2))


if __name__ == "__main__":
    main()
