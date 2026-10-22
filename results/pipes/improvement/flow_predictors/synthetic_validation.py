#!/usr/bin/env python3
"""Generate independent seeded stream diagnostics, without running an allocator."""
import hashlib, json, random, statistics, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze

ROOT=Path(__file__).resolve().parent
DEST=ROOT/"synthetic"
DEST.mkdir(exist_ok=True)
SEED=20261016
N=15000
PATTERN=(2,7,3,11,5,13,4)


def generate(name,seed):
    rng=random.Random(seed)
    active=[]; ops=[]; next_pid=1
    def add(t):
        nonlocal next_pid
        if name in ("periodic_size_mod2","regime_shift_mod2"):
            length=PATTERN[(next_pid-1)%len(PATTERN)]
        else:
            length=rng.randint(1,40)
        ops.append(length); active.append(next_pid); next_pid+=1
    def remove(t):
        if name=="lifo": idx=len(active)-1
        elif name=="fifo": idx=0
        elif name=="periodic_size_mod2":
            idx=next((j for j,p in enumerate(active) if p%2==1),0)
        elif name=="regime_shift_mod2":
            target=1 if t < int(.62*N) else 0
            idx=next((j for j,p in enumerate(active) if p%2==target),0)
        else:
            idx=rng.randrange(len(active))
        pid=active.pop(idx); ops.append(-pid)
    for t in range(N):
        if len(active)<8 or rng.random()<.58:
            add(t)
        else:
            remove(t)
    inp=DEST/(name+".in")
    body="1.0\n"+str(len(ops))+"\n"+"\n".join(map(str,ops))+"\n"
    inp.write_text(body)
    return ops, hashlib.sha256(inp.read_bytes()).hexdigest()


def trigger_quality(ops):
    n=len(ops); lo=int(.60*n)
    nextpid=1; lengths=[0]; lastpid=-1; lastlen=-1; stride=0; mode=False
    existing=[]; rolling=[]; rolling16=[]; history=[]
    for t,x in enumerate(ops):
        if x>0:
            lengths.append(x); nextpid+=1
            continue
        pid=-x; length=lengths[pid]
        if t>=lo:
            if mode: existing.append(int(pid%2==lastpid%2))
            if len(history)>=12:
                window=history[-12:]
                ones=sum(p%2 for p in window)
                if max(ones,12-ones)>=11:
                    parity=int(ones>=6)
                    rolling.append(int(pid%2==parity))
            if len(history)>=16 and (all(p%2==0 for p in history[-16:]) or
                                     all(p%2==1 for p in history[-16:])):
                parity=history[-1]%2
                rolling16.append(int(pid%2==parity))
        if lastpid>=0 and lastlen==length and pid==lastpid+2:
            stride+=1
        else:
            stride=0; mode=False
        if stride>=7: mode=True
        lastpid,lastlen=pid,length
        history.append(pid)
    return {"existing_stride_predicted":len(existing),
            "existing_stride_accuracy":sum(existing)/len(existing) if existing else None,
            "rolling12_predicted":len(rolling),
            "rolling12_accuracy":sum(rolling)/len(rolling) if rolling else None,
            "rolling16_exact_predicted":len(rolling16),
            "rolling16_exact_accuracy":sum(rolling16)/len(rolling16) if rolling16 else None}


def main():
    scenarios=["lifo","fifo","periodic_size_mod2","regime_shift_mod2","random_churn"]
    out={"seed_base":SEED,"operation_count":N,"scenarios":{}}
    for i,name in enumerate(scenarios):
        ops,sha=generate(name,SEED+i)
        c={"id":100+i,"n":len(ops),"ops":ops}
        # Modulo model uses temporal validation and a later test; the hazard is
        # fitted only on the training prefix and evaluated on unseen events.
        mod=analyze.mod_analysis(c)
        # Existing final rule compared to a simple causal parity-confidence rule.
        q=trigger_quality(ops)
        out["scenarios"][name]={"seed":SEED+i,"n_ops":len(ops),"input_sha256":sha,
             "modulo_validation_test":mod,"causal_parity_trigger_quality_test":q}
    (DEST/"summary.json").write_text(json.dumps(out,indent=2)+"\n")
    for name,x in out["scenarios"].items():
        m=x["modulo_validation_test"]; q=x["causal_parity_trigger_quality_test"]
        print(name,"hash",x["input_sha256"],"k",m.get("selected_k_validation"),
              "test_n",m.get("test_deletions"),"ΔLL",m.get("test_delta_logloss_vs_uniform_active_pid"),
              "exact",q["existing_stride_predicted"],q["existing_stride_accuracy"],
              "roll12",q["rolling12_predicted"],q["rolling12_accuracy"],
              "roll16",q["rolling16_exact_predicted"],q["rolling16_exact_accuracy"])

if __name__=="__main__": main()
