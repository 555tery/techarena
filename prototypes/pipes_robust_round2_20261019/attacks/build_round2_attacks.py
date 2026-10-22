#!/usr/bin/env python3
"""Create fresh, executable-screened adversarial Pipes streams for candidate-v3.

Candidate KPI measurements are used in the local selection gate but are not
written into the handoff manifest, preserving a blind first comparison for
the coordinator. Causal Best-Fit scores, prefixes, and all provenance are
recorded. No frozen source or prior test suite is modified.
"""
import base64
import concurrent.futures
import hashlib
import importlib.util
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROBUST = REPO / "prototypes/pipes_v5_robust_20261019"
TARGET = ROBUST / "candidate-v3/solver"
SOURCE = ROBUST / "candidate-v3/solution.cpp"
BF = REPO / "prototypes/pipes_prefix_shock_20261019/allocator-probe"
TAPE = REPO / "prototypes/pipes_prefix_shock_20261019/tape.txt"
sys.path.insert(0, str(REPO / "tools"))
from pipes_harness import parse_test


def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(Path(p).read_bytes())


def decode_tables(source):
    start = source.index("static const char* encoded[]={") + len("static const char* encoded[]={")
    end = source.index("};", start)
    tables = []
    for group in source[start:end].split(","):
        blob = base64.b64decode("".join(re.findall(r'"([A-Za-z0-9+/=]*)"', group)))
        offset = 0
        def var():
            nonlocal offset
            value = shift = 0
            while True:
                byte = blob[offset]; offset += 1
                value |= (byte & 127) << shift
                if byte < 128: return value
                shift += 7
        def signed():
            x = var()
            return -(x + 1) // 2 if x & 1 else x // 2
        n = var(); commands = []; positions = []; last = 0
        for _ in range(n):
            c = signed(); commands.append(c)
            if c > 0:
                last += signed(); positions.append(last)
            else: positions.append(None)
        assert offset == len(blob)
        tables.append((commands, positions))
    assert len(tables) == 15
    return tables


def public_commands(case):
    x = (REPO / f"data/pipes/open/{case}.in").read_text().split()
    n = int(x[1])
    return list(map(int,x[2:2+n]))


class Allocator:
    def __init__(self): self.trench = 0; self.gaps = []; self.pipes = [None]
    def clone(self):
        z = Allocator(); z.trench = self.trench; z.gaps = self.gaps.copy(); z.pipes = self.pipes.copy(); return z
    def add_gap(self, l, r):
        if l >= r: return
        out = []
        for a,b in self.gaps:
            if b < l or a > r: out.append((a,b))
            else: l,r=min(l,a),max(r,b)
        out.append((l,r)); self.gaps=sorted(out)
    def place(self, n, planned=None):
        if planned is None:
            fit = sorted((b-a,a) for a,b in self.gaps if b-a >= n)
            if fit: planned=fit[0][1]
            else:
                tail=[a for a,b in self.gaps if b == self.trench]
                planned=tail[-1] if tail else self.trench
        if planned+n > self.trench:
            end=((planned+n+19)//20)*20; self.add_gap(self.trench,end); self.trench=end
        for i,(a,b) in enumerate(self.gaps):
            if a <= planned and planned+n <= b:
                self.gaps.pop(i); self.add_gap(a,planned); self.add_gap(planned+n,b); break
        else: raise ValueError((n,planned,self.gaps[:4]))
        self.pipes.append((planned,n))
    def remove(self, pid):
        x,n=self.pipes[pid]; self.pipes[pid]=(None,0); self.add_gap(x,x+n)


def prefix_state(case, cut, tables, public):
    cs,ps=tables[case-1]; target=Allocator(); bf=Allocator(); active={}; pid=0; ratio=1.0
    for c,x in zip(cs[:cut],ps[:cut]):
        if c>0:
            pid+=1; active[pid]=c; target.place(c,x); bf.place(c)
        else:
            del active[-c]; target.remove(-c); bf.remove(-c)
        ratio=max(ratio,target.trench/bf.trench if bf.trench else 1.0)
    matches=[k for k,v in public.items() if v[:cut]==cs[:cut]]
    nexts={public[k][cut] for k in matches if cut<len(public[k])}
    off=[p for p in sorted(active) if -p not in nexts]
    if not off: return None
    return target,bf,active,ratio,off,matches,nexts


def fill_after_deletions(bf, target, volume, max_additions=32):
    adds=[]
    for _ in range(max_additions):
        differential=[]
        for n in range(1,41):
            nb,nt=bf.clone(),target.clone(); ob,ot=bf.trench,target.trench
            nb.place(n); nt.place(n); db=nb.trench-ob; dt=nt.trench-ot
            if db==0 and dt>0: differential.append((-dt/n,-dt,-n,n,nb,nt))
        if differential:
            _,_,_,n,bf,target=min(differential); volume+=n; adds.append(n); continue
        if bf.trench and volume/bf.trench>=0.96: break
        common=[]
        for n in range(1,41):
            nb,nt=bf.clone(),target.clone(); ob,ot=bf.trench,target.trench
            nb.place(n); nt.place(n)
            if nb.trench==ob and nt.trench==ot: common.append((-n,n,nb,nt))
        if not common: break
        _,n,bf,target=min(common); volume+=n; adds.append(n)
    return bf,target,volume,adds


def encode(commands):
    return "1\n%d\n"%len(commands)+"\n".join(map(str,commands))+"\n"

def commands_of(x):
    return x.get("commands") or (x["prefix"]+x["suffix"])


def batch(path, commands, probe=False):
    argv=[str(path)]
    if probe: argv += ["bestfit",str(TAPE)]
    r=subprocess.run(argv,input="\n".join(map(str,commands+[0]))+"\n",text=True,capture_output=True,check=True,timeout=30)
    lines=r.stdout.splitlines(); assert len(lines)==len(commands),(path,len(lines),len(commands))
    T=F=pid=0; active={}; places={}; trace=[]
    for c,line in zip(commands,lines):
        if c>0:
            digs,x=map(int,line.split()); T+=20*digs; assert x+c<=T,(path,c,line,T)
            # Exhaustive pairwise overlap checks are quadratic; beyond 1k live
            # placements rely on the allocator's own fit guard and the official
            # interactor check, while still validating all PID/remove replies.
            if len(places)<1000:
                assert all(x+c<=a or b<=x for a,b in places.values()),(path,c,line)
            pid+=1; active[pid]=c; places[pid]=(x,x+c); F+=c
        else:
            x=int(line); a,b=places.pop(-c); assert x==a,(path,c,line,a)
            F-=b-a; active.pop(-c)
        trace.append(T)
    return {"T":T,"F":F,"KPI":F/T if T else 0.0,"trace":trace,"stderr":r.stderr.strip()}


def prior_hashes():
    dirs=[
        REPO/"prototypes/pipes_guarded_traps_20261019",
        REPO/"prototypes/pipes_open15_adversary_20261019",
        REPO/"prototypes/pipes_v5_graves_20261019",
        ROBUST/"new_attacks", ROBUST/"counterattacks", ROBUST/"neutral",
    ]
    hashes=set(); inventories=[]
    for d in dirs:
        files=sorted(d.rglob("*.in")) if d.exists() else []
        digests=[sha_file(p) for p in files]
        hashes.update(digests)
        mf=d/"manifest.json"
        if mf.exists():
            try:
                manifest=json.loads(mf.read_text())
                rows=manifest.get("tests",[])
                for row in rows:
                    if isinstance(row,dict):
                        for key in ("input_sha256","test_sha256","sha256"):
                            value=row.get(key)
                            if isinstance(value,str) and re.fullmatch(r"[0-9a-f]{64}",value): hashes.add(value)
            except Exception: pass
        inventories.append({"path":str(d.relative_to(REPO)),"input_files":len(files),
                            "manifest_sha256":sha_file(mf) if mf.exists() else None})
    for p in HERE.glob("*.in"): hashes.add(sha_file(p))
    return hashes,inventories


def main():
    assert sha_file(SOURCE)=="a3d414a4872796fb570753c0e61db5c80dc59c1b8cbd7ec57e95dec345aff53a"
    target_sha="ae7f8ce0ef4902d8a40c6b459990c1b87128c5f0dc015af3b96753d5dde1d06d"
    assert sha_file(TARGET)==target_sha
    tables=decode_tables(SOURCE.read_text()); public={c:public_commands(c) for c in range(1,16)}
    assert all(tables[c-1][0]==public[c] for c in range(1,16))
    excluded,inventories=prior_hashes()

    # Short-prefix geometry families use subset enumeration; late large prefixes
    # use a compact deletion/refill beam so each final input stays independently
    # executable-screened without copying large allocator states repeatedly.
    cut_map={2:[3,4,8,12],3:[4,6,8,10,12],10:[32,128,7691,7692],
             12:[6,12,20,34],14:[128,250,512,17161,17162]}
    pool=[]; seen=set(excluded)
    for case,cuts in cut_map.items():
        cs,_=tables[case-1]
        for cut in cuts:
            if cut>=len(cs): continue
            public_prefix=cs[:cut]
            state=prefix_state(case,cut,tables,public)
            if state is None: continue
            replay0,bf0,active,ratio,off,matches,nexts=state
            ids=sorted(active)
            if len(ids)<=12:
                chosen=ids
                first=off[0]
                ranked=[]
                for mask in range(1<<len(chosen)):
                    deleted=[p for i,p in enumerate(chosen) if mask>>i&1]
                    if first not in deleted or len(deleted)==len(ids): continue
                    bf,replay=bf0.clone(),replay0.clone(); volume=sum(active.values())
                    for p in deleted: bf.remove(p); replay.remove(p); volume-=active[p]
                    maxbg=max((b-a for a,b in bf.gaps),default=0)
                    maxtg=max((b-a for a,b in replay.gaps),default=0)
                    if maxbg>maxtg: ranked.append((maxbg-maxtg,deleted,bf,replay,volume))
                ranked.sort(key=lambda z:(-z[0],len(z[1])))
                for _,deleted,bf,replay,volume in ranked[:16]:
                    b2,t2,v,adds=fill_after_deletions(bf,replay,volume)
                    if not adds or not b2.trench: continue
                    if v/b2.trench < .9 or v/t2.trench >= .9: continue
                    suffix=[-first]+[-p for p in deleted if p!=first]+adds
                    commands=public_prefix+suffix; digest=sha_bytes(encode(commands).encode())
                    if digest in seen: continue
                    seen.add(digest)
                    pool.append({"case":case,"cut":cut,"prefix":public_prefix,"suffix":suffix,
                                 "commands":commands,"first":-first,"matches":matches,
                                 "ratio_sim":ratio,"pred_bf":v/b2.trench,"pred_target":v/t2.trench,
                                 "family":"delete-refill-gap-subset"})
            else:
                # Choose a small, deterministic PID beam spanning early, recent,
                # and size extremes. The first deletion must break every live table.
                cand_ids=sorted(set([off[0],ids[0],ids[-1],*ids[-2:],*ids[:2],*ids[::max(1,len(ids)//4)]]))
                cand_ids=[p for p in cand_ids if p in active and -p not in nexts]
                if off[0] not in cand_ids: cand_ids.insert(0,off[0])
                cand_ids=cand_ids[:4]
                size_set=[1,2,5,10,20,30,40]
                for first in cand_ids:
                    others=[p for p in cand_ids if p!=first]
                    delete_sets=[[first]]+[[first,p] for p in others[:2]]
                    for deleted in delete_sets:
                        # Avoid expensive repeated full-state simulation at very
                        # late cuts; actual frozen binaries score this compact beam.
                        base=[-first]+[-p for p in deleted if p!=first]
                        tail_sets=[[n] for n in size_set]
                        tail_sets += [[a,b] for a,b in [(2,10),(5,20),(10,30),(20,40)]]
                        for tail in tail_sets:
                            suffix=base+tail
                            digest=sha_bytes(encode(public_prefix+suffix).encode())
                            if digest in seen: continue
                            seen.add(digest)
                            pool.append({"case":case,"cut":cut,"prefix":public_prefix,"suffix":suffix,
                                         "first":-first,"matches":matches,
                                         "ratio_sim":ratio,"pred_bf":None,"pred_target":None,
                                         "family":"late-prefix pid/refill beam"})

    # Keep local evaluation modest while preserving late-prefix coverage.
    # Simulation-scored inputs are considered first; the long-prefix beam is
    # spread over the requested Open10 and Open14 neighborhoods.
    pool.sort(key=lambda x:(x["pred_target"] if x["pred_target"] is not None else .95,
                            -(x["pred_bf"] if x["pred_bf"] is not None else 0),len(commands_of(x))))
    buckets={
        "open2":lambda x:x["case"]==2,
        "open3":lambda x:x["case"]==3,
        "open10-late":lambda x:x["case"]==10 and x["cut"]>=32,
        "open14-late":lambda x:x["case"]==14 and x["cut"]>=250,
        "open12":lambda x:x["case"]==12,
    }
    # Build an execution-screen queue, favoring the modeled target but interleave
    # long prefixes so one class cannot exhaust the bounded wall budget.
    queue=[]
    for bucket,pred in buckets.items():
        rows=[x for x in pool if pred(x)]
        if bucket in ("open10-late","open14-late"):
            rows=sorted(rows,key=lambda x:(-x["cut"],x["first"],len(x["suffix"])))
        queue.extend(rows[:(12 if bucket in ("open10-late","open14-late") else 32)])
    # Deduplicate across bucket copies; cap total candidates evaluated.
    unique=[]; keys=set()
    for x in queue:
        key=sha_bytes(encode(commands_of(x)).encode())
        if key not in keys: keys.add(key); unique.append(x)
    unique=unique[:1200]
    print("screen queue",len(unique),{"open2":sum(x["case"]==2 for x in unique),
          "open3":sum(x["case"]==3 for x in unique),"open10":sum(x["case"]==10 for x in unique),
          "open14":sum(x["case"]==14 for x in unique),"open12":sum(x["case"]==12 for x in unique)},flush=True)

    def evaluate(x):
        cmd=commands_of(x)
        cand=batch(TARGET,cmd); bf=batch(BF,cmd,probe=True)
        return x,cand,bf
    evals=[]; errors=[]; gates={"bf":0,"target":0,"fallback":0,"replay":0}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs=[ex.submit(evaluate,x) for x in unique]
        for fut in concurrent.futures.as_completed(futs):
            try:
                x,cand,bf=fut.result()
                if bf["KPI"]<.9: continue
                gates["bf"]+=1
                if cand["KPI"]>=.9: continue
                gates["target"]+=1
                if "fallback=" not in cand["stderr"]: continue
                gates["fallback"]+=1
                if True:
                    # Actual target must have replayed the entire common prefix.
                    m=re.search(r"replay=(\d+)",cand["stderr"])
                    if m and int(m.group(1))>=x["cut"]:
                        x={**x,"_candidate":cand,"_bf":bf}
                        evals.append(x)
                        gates["replay"]+=1
            except Exception as exc:
                if len(errors)<4: errors.append(repr(exc))
                continue
    print("screen results",len(evals),gates,errors,flush=True)

    # Enforce variety and retain ten independent new streams. Prefer late Open10
    # and Open14 attacks, then Open2/3/12 geometry. Candidate KPIs remain in RAM.
    selected=[]; used=set()
    quotas=[("open2",2,lambda x:x["case"]==2),
            ("open3",1,lambda x:x["case"]==3),
            ("open10-late",2,lambda x:x["case"]==10 and x["cut"]>=32),
            ("open14-late",2,lambda x:x["case"]==14 and x["cut"]>=250),
            ("open12",1,lambda x:x["case"]==12)]
    for label,n,pred in quotas:
        rows=sorted((x for x in evals if pred(x)),key=lambda x:(x["_candidate"]["KPI"],-x["_bf"]["KPI"],len(commands_of(x))))
        cuts=set(); got=0
        for x in rows:
            digest=sha_bytes(encode(commands_of(x)).encode())
            if digest in used or (label not in ("open10-late","open14-late") and x["cut"] in cuts): continue
            selected.append(x); used.add(digest); cuts.add(x["cut"]); got+=1
            if got>=n: break
    if len(selected)<6:
        extras=sorted((x for x in evals if sha_bytes(encode(commands_of(x)).encode()) not in used),
                      key=lambda x:(x["_candidate"]["KPI"],-x["_bf"]["KPI"],len(commands_of(x))))
        for x in extras:
            selected.append(x); used.add(sha_bytes(encode(commands_of(x)).encode()))
            if len(selected)>=8: break
    assert len(selected)>=6, (len(pool),len(evals),{k:sum(1 for x in evals if p(x)) for k,p in buckets.items()})
    selected=selected[:8]

    # Re-check each chosen stream with both actual binaries serially, then write
    # only inputs and the blind handoff manifest. Do not persist candidate KPI.
    tests=[]
    for i,x in enumerate(selected,1):
        cmd=commands_of(x)
        cand=batch(TARGET,cmd); bf=batch(BF,cmd,probe=True)
        prefix_target=batch(TARGET,x["prefix"]); prefix_bf=batch(BF,x["prefix"],probe=True)
        ratios=[a/b if b else (1.0 if a==0 else float("inf"))
                for a,b in zip(prefix_target["trace"],prefix_bf["trace"])]
        assert bf["KPI"]>=.9 and cand["KPI"]<.9
        assert max(ratios,default=1.0)<=2.00000001
        name=f"round2-{i:02d}-open{x['case']}-p{x['cut']}.in"
        path=HERE/name; path.write_text(encode(cmd)); assert parse_test(path) is not None
        tests.append({"name":name[:-3],"file":name,"case":x["case"],"cut":x["cut"],
                      "common_prefix":x["prefix"],"suffix":x["suffix"],
                      "first_divergent_command":x["suffix"][0],
                      "expected_table_command_at_cut":tables[x["case"]-1][0][x["cut"]],
                      "matching_open_tables_before_divergence":x["matches"],
                      "max_prefix_ratio_candidate_v3_vs_causal_BF":max(ratios,default=1.0),
                      "prefix_T_target_m":prefix_target["T"],"prefix_T_causal_BF_m":prefix_bf["T"],
                      "causal_BF":{k:bf[k] for k in ["T","F","KPI"]},
                      "input_sha256":sha_file(path),"family":x["family"]})
    source_files=["prototypes/pipes_guarded_traps_20261019/manifest.json",
                  "prototypes/pipes_open15_adversary_20261019/manifest.json",
                  "prototypes/pipes_v5_graves_20261019/manifest.json",
                  "prototypes/pipes_v5_robust_20261019/new_attacks/manifest.json",
                  "prototypes/pipes_v5_robust_20261019/counterattacks/manifest.json",
                  "prototypes/pipes_v5_robust_20261019/neutral/manifest.json"]
    manifest={"title":"Round 2 fresh attack suite for frozen candidate-v3",
              "target_source_sha256":sha_file(SOURCE),"target_binary_sha256":target_sha,
              "causal_bestfit_probe_sha256":sha_file(BF),
              "selection":"New test hashes were excluded against all .in files in the prior attack and neutral catalogs listed below. Pools prioritize quiet Open2/Open3 geometry, delayed Open10/Open14 mismatches, and Open12; Open8/Open11 drain attacks were not generated.",
              "local_screen":"Every selected candidate was run through the actual frozen candidate-v3 batch binary and actual causal Best-Fit probe. Candidate KPI results are intentionally withheld from this handoff for blind first comparison; the per-input gate was BF KPI >= 0.90 and candidate-v3 KPI < 0.90.",
              "official_interactor_validation":"pending root",
              "prior_catalogs":[{"path":p,"sha256":sha_file(REPO/p)} for p in source_files],
              "prior_input_files_excluded":sum(x["input_files"] for x in inventories),
              "tests":tests}
    (HERE/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(f"created {len(tests)} fresh streams; unique={len({t['input_sha256'] for t in tests})}; candidate results withheld")


if __name__=="__main__": main()
