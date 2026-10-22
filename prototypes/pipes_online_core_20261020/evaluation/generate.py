#!/usr/bin/env python3
"""New causal workloads, declared without reading solver code or outcomes."""
import collections
import hashlib
import heapq
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FAMILIES = ["stable_short_then_long", "stable_long_then_short", "young_then_old_deaths",
            "old_then_young_deaths", "random_mortality", "batch_mortality",
            "equal_runs_odd_breaks", "equal_runs_jittered_breaks", "uniform_window_lifetimes",
            "two_scale_lifetimes", "heavy_tail_lifetimes", "lifetime_reversal",
            "old_background_size_shift", "renewal_bursts", "longrun_capacity", "longrun_fill"]
SUFFIXES = ["retained_background_reversal", "death_age_reversal", "random_deaths",
            "batch_deaths", "equal_run_breaks", "lifetime_resampling", "terminal_fill",
            "near_public_perturbation", "stop_after_prefix"]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Stream:
    def __init__(self, rng):
        self.rng = rng
        self.commands, self.ids = [], []
        self.live, self.positions = {}, {}
        self.order = collections.deque()
        self.stack, self.deadlines = [], []
        self.next_pid = 1
        self.volume = self.peak = self.peak_count = 0
        self.anchors = set()
        self.run_size = rng.randint(7, 34)
        self.run_period = rng.randint(259, 521)
        self.batch_remaining = 0

    def emit(self, command, life=1000000):
        if command > 0:
            assert command <= 40
            pid = self.next_pid
            self.next_pid += 1
            self.live[pid] = command
            self.positions[pid] = len(self.ids)
            self.ids.append(pid)
            self.order.append(pid)
            self.stack.append(pid)
            heapq.heappush(self.deadlines, (len(self.commands) + life, pid))
            self.volume += command
        else:
            assert command < 0 and -command in self.live
            pid = -command
            self.volume -= self.live.pop(pid)
            idx = self.positions.pop(pid)
            last = self.ids.pop()
            if idx < len(self.ids):
                self.ids[idx] = last
                self.positions[last] = idx
        self.commands.append(command)
        self.peak = max(self.peak, self.volume)
        self.peak_count = max(self.peak_count, len(self.live))

    def choose(self, policy="random", protect=False):
        if len(self.live) <= 1:
            return None
        if policy in ("oldest", "newest") and not protect:
            seq = self.order if policy == "oldest" else self.stack
            while seq and (seq[0] if policy == "oldest" else seq[-1]) not in self.live:
                seq.popleft() if policy == "oldest" else seq.pop()
            return seq[0] if policy == "oldest" else seq[-1]
        candidates = [self.ids[self.rng.randrange(len(self.ids))] for _ in range(24)]
        if protect:
            candidates = [p for p in candidates if p not in self.anchors]
            if not candidates:
                return None
        if policy == "young": return max(candidates)
        if policy == "old": return min(candidates)
        return candidates[0]

    def due(self):
        while self.deadlines and self.deadlines[0][1] not in self.live:
            heapq.heappop(self.deadlines)
        if len(self.live) > 1 and self.deadlines and self.deadlines[0][0] <= len(self.commands):
            return self.deadlines[0][1]
        return None


def event(s, family, t, duration):
    r = s.rng
    phase = t / max(1, duration)
    reverse = phase >= .57
    length = r.randint(1, 40)
    life, prob, policy, protect = 1000000, .39, "random", False
    pid = None
    if family.startswith("stable_"):
        short = not reverse if family == "stable_short_then_long" else reverse
        length = r.randint(3, 10) if short else r.randint(27, 38)
        prob, policy = .42, ("young" if short else "old")
    elif family in ("young_then_old_deaths", "old_then_young_deaths"):
        first_young = family == "young_then_old_deaths"
        policy = "young" if first_young != reverse else "old"
        prob = .48 if phase < .74 else .32
        if t == 90: s.anchors.update(s.live)
        protect = True
        length = r.randint(1, 16) if reverse else r.randint(17, 40)
    elif family == "random_mortality":
        prob = .24 if t < 170 else .48
        length = r.choice([4, 6, 13, 21, 28, 37])
    elif family == "batch_mortality":
        if t % 331 == 227:
            s.batch_remaining = min(max(0, len(s.live)-1), r.randint(35, 105))
        if s.batch_remaining:
            pid = s.choose("old" if (t // 331) % 2 else "random")
            s.batch_remaining -= 1
        prob = .06 if pid is None else 0
        length = r.randint(2, 18) if t % 331 < 190 else r.randint(19, 40)
    elif family in ("equal_runs_odd_breaks", "equal_runs_jittered_breaks"):
        period = s.run_period + (0 if family == "equal_runs_odd_breaks" else (t // s.run_period) % 7)
        offset = t % period
        length = s.run_size
        if offset in (0, 1, period-1):
            length = max(1, min(40, s.run_size + r.choice([-5, -2, 1, 3, 7])))
        prob, policy = (.18 if offset < period * .53 else .58), ("oldest" if (t//period)%2 else "newest")
    elif family in ("uniform_window_lifetimes", "two_scale_lifetimes", "heavy_tail_lifetimes", "lifetime_reversal"):
        if family == "uniform_window_lifetimes": life = r.randint(80, 420)
        elif family == "two_scale_lifetimes": life = r.randint(15, 50) if r.random() < .65 else r.randint(650, 1600)
        elif family == "heavy_tail_lifetimes": life = min(7000, int(23 * r.paretovariate(1.25)))
        else: life = r.randint(20, 100) if reverse else r.randint(700, 2000)
        pid = s.due()
        prob = 0
        length = r.randint(1, 8) if life > 600 else r.randint(9, 40)
    elif family == "old_background_size_shift":
        if t == 135: s.anchors.update(s.live)
        protect = True
        prob = .43
        length = r.randint(3, 9) if not reverse else r.randint(23, 40)
    elif family == "renewal_bursts":
        offset = t % 503
        prob, policy = (.02 if offset < 270 else .83), ("old" if reverse else "young")
        length = r.randint(4, 15) if (t // 503) % 2 else r.randint(21, 39)
    elif family == "longrun_capacity":
        prob = .12 if phase < .24 else (.47 if phase < .83 else .20)
        length = r.randint(11, 23) if phase < .63 else r.randint(1, 40)
        policy = "oldest"
    elif family == "longrun_fill":
        prob, policy = (.49 if phase < .62 else 0), "random"
        length = r.randint(1, 12) if phase < .62 else r.randint(23, 40)
    if pid is None and r.random() < prob:
        pid = s.choose(policy, protect)
    s.emit(-pid if pid is not None else length, life)


def ordinary(seed, n, index, final):
    s = Stream(random.Random(seed))
    a = FAMILIES[index % 16]
    rep = index // 16
    b = FAMILIES[(index % 16 + 7 + rep * 2) % 16]
    c = FAMILIES[(index % 16 + 3 + rep * 3) % 16]
    # Fixed terminal fill is a workload mechanism, never a rejection filter.
    terminal_fill = index % 4 == 1 if final else index % 8 == 3
    for t in range(n):
        family = a
        if final:
            if rep == 0: family = a if t < .36*n else (b if t < .77*n else c)
            elif rep == 1: family = [a, b, c, b][(t // 191) % 4]
            elif rep == 2: family = a if s.rng.random() < .56 else b
            else: family = a if t < .29*n or t >= .71*n else c
        if terminal_fill and t >= n * .68:
            s.emit(s.rng.randint(22, 40))
        else:
            event(s, family, t, n)
    label = f"{a}+{b}+{c}/schedule{rep}" if final else a
    return s, label, terminal_fill


def prefix_stream(seed, index, final):
    r = random.Random(seed)
    case = index % 15 + 1
    long = final and index in (62, 63)
    if long: case = 14 if index == 62 else 15
    path = ROOT / "data/pipes/open" / f"{case}.in"
    raw = path.read_bytes()
    tokens = raw.split()
    public = list(map(int, tokens[2:-1]))
    assert len(public) == int(tokens[1]) and tokens[-1] == b"0"
    if long: plen = 17629 if case == 14 else 17947
    elif len(public) <= 32: plen = max(1, len(public) - 1 - (index % 4))
    else: plen = r.randint(31, min(3600, len(public)-1))
    suffix = SUFFIXES[(index + (4 if final else 0)) % 9]
    if suffix == "stop_after_prefix":
        if len(public) < 1002: suffix = "terminal_fill"
        else: plen = max(plen, min(len(public)-1, 1231 + index * 5))
    if long: suffix = "terminal_fill" if case == 14 else "retained_background_reversal"
    s = Stream(r)
    for command in public[:plen]: s.emit(command)
    while not s.live:
        s.emit(public[plen]); plen += 1
    target = plen if suffix == "stop_after_prefix" else plen + (2300 if long else r.randint(1000, 2200))
    if suffix == "retained_background_reversal":
        s.anchors.update(p for p in s.live if r.random() < .45)
    for j in range(target-plen):
        length, pid = r.randint(1, 40), None
        if suffix == "retained_background_reversal":
            length = r.randint(1, 11) if j < (target-plen)*.46 else r.randint(25, 40)
            if r.random() < .44: pid = s.choose("young" if j < 500 else "old", True)
        elif suffix == "death_age_reversal":
            if r.random() < .48: pid = s.choose("old" if j < (target-plen)*.53 else "young")
        elif suffix == "random_deaths":
            if r.random() < (.58 if j % 401 < 190 else .29): pid = s.choose()
        elif suffix == "batch_deaths":
            if j % 281 == 0: s.batch_remaining = min(max(0,len(s.live)-1), r.randint(40,110))
            if s.batch_remaining: pid = s.choose("oldest"); s.batch_remaining -= 1
            length = r.choice([3, 11, 17, 28, 39])
        elif suffix == "equal_run_breaks":
            length = s.run_size if j % 379 not in (0, 1, 378) else r.randint(1,40)
            if r.random() < .36: pid = s.choose("newest" if j//379 % 2 else "oldest")
        elif suffix == "lifetime_resampling":
            event(s, "two_scale_lifetimes" if j < 620 else "heavy_tail_lifetimes", j, target-plen)
            continue
        elif suffix == "terminal_fill":
            length = r.randint(16, 40)
        elif suffix == "near_public_perturbation":
            command = public[(plen+j) % len(public)]
            if command > 0:
                length = max(1,min(40,command + (r.choice([-3,-1,1,3]) if r.random()<.23 else 0)))
            else:
                pid = -command if -command in s.live and len(s.live)>1 else s.choose()
        s.emit(-pid if pid is not None else length)
    info = {"case": case, "source": str(path.relative_to(ROOT)), "source_sha256": digest(raw),
        "source_command_count": len(public), "prefix_n": plen,
        "prefix_commands_sha256": digest(("\n".join(map(str,public[:plen]))+"\n").encode()),
        "suffix": suffix, "suffix_n": target-plen}
    return s, "public_prefix/"+suffix, info


def save(split, index, s, family, stratum, seed, public=None, terminal_fill=False):
    assert 1 <= len(s.commands) <= 200000 and s.volume > 0 and s.live
    file = f"case-{index:03d}.in"
    commands_raw = ("\n".join(map(str,s.commands))+"\n").encode()
    raw = f"1 {len(s.commands)}\n".encode()+commands_raw+b"0\n"
    folder = HERE/split
    folder.mkdir(exist_ok=True)
    (folder/file).write_bytes(raw)
    return {"id": f"{split}-{index:03d}", "file": file, "family": family, "stratum": stratum,
        "seed": seed, "n": len(s.commands), "sha256": digest(raw), "commands_sha256": digest(commands_raw),
        "final_live_volume": s.volume, "peak_live_volume": s.peak, "final_live_count": len(s.live),
        "peak_live_count": s.peak_count, "final_to_peak_volume": s.volume/s.peak,
        "predeclared_terminal_fill": terminal_fill, "public_prefix": public}


def main():
    manifests = {}
    for split, half, base in [("calibration",32,867530910000), ("final",64,867530990000)]:
        rows = []
        for i in range(half):
            seed = base+i
            n = 1111 + (i * 853 + (257 if split=="final" else 0)) % 4801
            s, family, fill = ordinary(seed,n,i,split=="final")
            rows.append(save(split,len(rows),s,family,"ordinary",seed,terminal_fill=fill))
        for i in range(half):
            seed = base+1000+i
            s,family,public = prefix_stream(seed,i,split=="final")
            rows.append(save(split,len(rows),s,family,"prefix",seed,public,public["suffix"]=="terminal_fill"))
        manifests[split] = {"schema_version":1,"split":split,"weight":1,
            "selection_status":"predeclared_without_solver_outcomes","cases":rows}
    rows=[]
    for i,family in enumerate(["max_alive","heavy_churn","regime_switches"]):
        seed = 867539990000+i
        s = Stream(random.Random(seed))
        for t in range(200000):
            if i==0: s.emit(s.rng.randint(1,40))
            elif i==1:
                pid=s.choose() if len(s.live)>180 or (len(s.live)>70 and s.rng.random()<.53) else None
                s.emit(-pid if pid is not None else s.rng.randint(1,40))
            else:
                event(s,["stable_long_then_short","two_scale_lifetimes","batch_mortality","equal_runs_jittered_breaks","longrun_fill"][min(4,t//40000)],t%40000,40000)
        rows.append(save("stress",i,s,family,"stress",seed))
    manifests["stress"]={"schema_version":1,"split":"stress","weight":1,"cases":rows}
    rows=[r for m in manifests.values() for r in m["cases"]]
    hashes={r["sha256"] for r in rows}
    assert len(hashes)==len(rows)
    assert len({r["commands_sha256"] for r in rows})==len(rows)
    previous=ROOT/"prototypes/pipes_closed_ready_20261020/evaluation"
    known_paths=[str((previous/s/"manifest.json").relative_to(ROOT)) for s in ("calibration","final","stress")]
    prior_summary=json.loads((previous/"generation-summary.json").read_text())
    known_paths += [x["path"] for x in prior_summary["known_manifests_checked"]]
    known=set(); checked=[]
    for rel in known_paths:
        path=ROOT/rel
        if path.exists():
            tokens={t.decode().lower() for t in re.findall(rb"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])",path.read_bytes())}
            known.update(tokens); checked.append({"path":rel,"sha256_tokens":len(tokens)})
    open_hashes={digest((ROOT/"data/pipes/open"/f"{i}.in").read_bytes()) for i in range(1,16)}
    known.update(open_hashes)
    assert not hashes & known
    for split,manifest in manifests.items():
        (HERE/split/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    summary={"schema_version":1,"generator_sha256":digest(Path(__file__).read_bytes()),
        "counts":{k:len(m["cases"]) for k,m in manifests.items()},"ordinary_base_families":FAMILIES,
        "final_design":"three mechanism compositions with four schedules; new seeds; fixed terminal-fill assignments",
        "no_rejection_sampling":True,"all_new_input_and_commands_hashes_unique":True,
        "known_hash_overlap":[],"known_manifests_checked":checked,"known_sha256_tokens":len(known),
        "open15_source_hashes_checked":sorted(open_hashes),
        "final_to_peak_volume_diagnostics":{k:{"count_ge_0_9":sum(r["final_to_peak_volume"]>=.9 for r in m["cases"]),
            "min":min(r["final_to_peak_volume"] for r in m["cases"]),"max":max(r["final_to_peak_volume"] for r in m["cases"])} for k,m in manifests.items()},
        "independence_constraints":["No new candidates or their outcomes read, no solver runs, no platform access, no subagents.",
            "No input selection or parameter changes based on score, KPI or solver behavior.",
            "Lifetime and workload transitions depend only on past/current events, seeded randomness and declared schedules.",
            "Terminal fill selected by fixed index rule before generation; F/peak is reported, not optimized by rejection.",
            "Previous 195 inputs and Open15 are known; exact file hashes excluded. Hash search also covers listed historical input manifests.",
            "Shared public-prefix stratum intentionally reuses public events; it is not unseen-prefix evidence.",
            "Final compositions and schedules differ from calibration; final outcomes must be sealed until candidate freeze.",
            "Synthetic tests do not establish official hidden-test generalization; some terminal volumes can be low by mechanism design."],
        "manifests":{k:{"path":f"{k}/manifest.json","sha256":digest((HERE/k/"manifest.json").read_bytes())} for k in manifests}}
    (HERE/"generation-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps({"counts":summary["counts"],"manifests":summary["manifests"],"volume":summary["final_to_peak_volume_diagnostics"]},indent=2))


if __name__=="__main__": main()
