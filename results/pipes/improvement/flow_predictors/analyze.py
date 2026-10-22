#!/usr/bin/env python3
"""Chronological diagnostics on official Pipes inputs; analysis only."""
import json, math, random, statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
EPS = 1e-12


def load(path):
    a = path.read_text().split()
    n, ops = int(a[1]), list(map(int, a[2:2+int(a[1])]))
    births, lens, deaths = [None], [0], [None]
    alive = [False]
    for t, x in enumerate(ops):
        if x > 0:
            births.append(t); lens.append(x); deaths.append(None); alive.append(True)
        elif x < 0:
            pid = -x
            if pid >= len(alive) or not alive[pid]:
                raise ValueError((path, t, pid))
            alive[pid] = False; deaths[pid] = t
    return {"id": int(path.stem), "n": n, "ops": ops,
            "birth": births, "length": lens, "death": deaths}


def dist(counts, alpha=1.0):
    total = sum(counts); d = len(counts)
    return [(x+alpha)/(total+alpha*d) for x in counts]


def score_probs(rows):
    if not rows: return {"n": 0}
    n = len(rows); brier = ll = hit = 0.0
    for p, y in rows:
        brier += sum((p[j] - (1.0 if y == j else 0.0))**2 for j in range(len(p)))
        ll -= math.log(max(EPS, p[y]))
        hit += max(range(len(p)), key=lambda j: p[j]) == y
    return {"n": n, "accuracy": hit/n, "brier": brier/n, "logloss": ll/n}


def ci_blocks(xs, width=128, reps=1200, seed=19):
    if len(xs) < 512: return None
    blocks = [xs[i:i+width] for i in range(0, len(xs), width)]
    if len(blocks) < 8: return None
    rng = random.Random(seed+len(xs)); vals=[]
    for _ in range(reps):
        q=[]
        while len(q)<len(xs): q.extend(rng.choice(blocks))
        vals.append(sum(q[:len(xs)])/len(xs))
    vals.sort()
    return [vals[int(.025*(reps-1))], vals[int(.975*(reps-1))]]


def length_predictions(c):
    n, ops = c["n"], c["ops"]
    adds = [(t,x) for t,x in enumerate(ops) if x>0]
    cut = int(.60*n)
    tr = [x for t,x in adds if t<cut]
    te = [(t,x) for t,x in adds if t>=cut]
    if len(tr)<64 or len(te)<32:
        return {"status":"too_small","train_adds":len(tr),"test_adds":len(te)}
    prior = dist([tr.count(x) for x in range(1,41)])
    lagmatch=[]
    maxlag=min(64,len(tr)//4)
    for lag in range(1,maxlag+1):
        hits=sum(tr[i]==tr[i-lag] for i in range(lag,len(tr)))
        lagmatch.append((hits/(len(tr)-lag),lag))
    selected=max(lagmatch,key=lambda z:(z[0],-z[1]))[1]
    trans={1:[[0]*40 for _ in range(40)], selected:[[0]*40 for _ in range(40)]}
    for i in range(1,len(tr)): trans[1][tr[i-1]-1][tr[i]-1]+=1
    for i in range(selected,len(tr)): trans[selected][tr[i-selected]-1][tr[i]-1]+=1
    def rowprob(row):
        s=sum(row)
        return [(row[j]+8*prior[j])/(s+8) for j in range(40)]
    names=("stationary","markov1","best_lag","recent128")
    pred={k:[] for k in names}; dll={k:[] for k in names if k!="stationary"}
    hist=list(tr)
    for _,y0 in te:
        y=y0-1
        ps={"stationary":prior,
            "markov1":rowprob(trans[1][hist[-1]-1]),
            "best_lag":rowprob(trans[selected][hist[-selected]-1]) if len(hist)>=selected else prior}
        recent=hist[-128:]; count=[recent.count(x) for x in range(1,41)]
        ps["recent128"]=[(count[j]+16*prior[j])/(len(recent)+16) for j in range(40)]
        for name,p in ps.items():
            pred[name].append((p,y))
            if name!="stationary":
                dll[name].append(math.log(max(EPS,p[y]))-math.log(max(EPS,prior[y])))
        hist.append(y0)
    metrics={k:score_probs(v) for k,v in pred.items()}
    half=len(te)//2
    return {"status":"ok","train_adds":len(tr),"test_adds":len(te),"cut_op":cut,
            "train_selected_lag":selected,"train_best_lag_match":max(lagmatch)[0],
            "test":metrics,
            "test_delta_logloss_improvement_ci_block128":{k:ci_blocks(v,128,seed=c["id"]*37) for k,v in dll.items()},
            "test_halves":{"first":{k:score_probs(v[:half]) for k,v in pred.items()},
                           "second":{k:score_probs(v[half:]) for k,v in pred.items()}}}


def modulo_fit(ops,k,end):
    counts=[0]*k; active=0; pidnext=1; obs=[0.0]*k; exp=[0.0]*k
    for t,x in enumerate(ops[:end]):
        if x>0:
            counts[pidnext%k]+=1; active+=1; pidnext+=1
        elif x<0:
            r=(-x)%k
            if active:
                for j in range(k): exp[j]+=counts[j]/active
                obs[r]+=1
            counts[r]-=1; active-=1
    return [(o+4)/(e+4) for o,e in zip(obs,exp)],sum(obs)


def modulo_score(ops,k,lo,hi,rates):
    counts=[0]*k; active=0; pidnext=1; scores=[]
    for t,x in enumerate(ops[:hi]):
        if x>0:
            counts[pidnext%k]+=1; active+=1; pidnext+=1
        elif x<0:
            r=(-x)%k
            if lo<=t<hi and active:
                den=sum(counts[j]*rates[j] for j in range(k))
                p=rates[r]/den; p0=1/active
                pc=[counts[j]*rates[j]/den for j in range(k)]
                pbase=[z/active for z in counts]
                b0=sum((pbase[j]-(j==r))**2 for j in range(k))
                b1=sum((pc[j]-(j==r))**2 for j in range(k))
                scores.append((math.log(max(EPS,p/p0),), b0-b1,active))
            counts[r]-=1; active-=1
    return scores


def mod_analysis(c):
    ops,n=c["ops"],c["n"]; tr=int(.40*n); va=int(.60*n)
    val={}
    for k in range(2,17):
        rate,ne=modulo_fit(ops,k,tr)
        rows=modulo_score(ops,k,tr,va,rate)
        if rows: val[k]=sum(r[0] for r in rows)/len(rows)
    if not val:
        return {"status":"no_pretest_deletions","train_ops":tr,"validation_ops":va-tr,"test_ops":n-va}
    k0=max(val,key=lambda k:(val[k],-k))
    rate,_=modulo_fit(ops,k0,va)
    test=modulo_score(ops,k0,va,n,rate)
    dll=[z[0] for z in test]; db=[z[1] for z in test]
    top=sorted(val.items(),key=lambda z:(z[1],-z[0]),reverse=True)[:5]
    return {"status":"ok","train_ops":tr,"validation_ops":va-tr,"test_ops":n-va,
            "selected_k_validation":k0,"validation_delta_logloss":val[k0],
            "top_validation_k":[{"k":k,"delta_ll":v} for k,v in top],
            "test_deletions":len(test),
            "test_delta_logloss_vs_uniform_active_pid":statistics.mean(dll) if dll else None,
            "test_delta_logloss_95ci_block256":ci_blocks(dll,256,seed=100+c["id"]),
            "test_modulo_brier_improvement":statistics.mean(db) if db else None,
            "test_modulo_brier_95ci_block256":ci_blocks(db,256,seed=200+c["id"]),
            "test_mean_active":statistics.mean(z[2] for z in test) if test else None,
            "fitted_rate_ratios":rate}


def age_horizon_rows(c,h):
    n=c["n"]; fit_end=int(.40*n); val_end=int(.60*n)
    split={"train":[],"val":[],"test":[]}
    offsets=[0]+[h*(2**j) for j in range(10)]
    for pid in range(1,len(c["birth"])):
        born=c["birth"][pid]; dead=c["death"][pid]; length=c["length"][pid]
        for age in offsets:
            t=born+age
            if t+h>=n: continue
            if dead is not None and dead<=t: break
            y=int(dead is not None and dead<=t+h)
            if t+h<fit_end: s="train"
            elif t>=fit_end and t+h<val_end: s="val"
            elif t>=val_end: s="test"
            else: continue
            ab=min(10,int(math.log2(age//h+1)))
            split[s].append((t,length,ab,pid,y))
    return split


def fit_age(rows,k=None,alpha=50):
    glob=sum(r[4] for r in rows)/max(1,len(rows))
    base=defaultdict(lambda:[0,0]); mod=defaultdict(lambda:[0,0])
    for t,l,a,pid,y in rows:
        base[l,a][0]+=y; base[l,a][1]+=1
        if k: mod[l,a,pid%k][0]+=y; mod[l,a,pid%k][1]+=1
    pb={g:(p+alpha*glob)/(n+alpha) for g,(p,n) in base.items()}
    pm={}
    if k:
        for g,(p,n) in mod.items():
            parent=(g[0],g[1]); prior=pb.get(parent,glob)
            pm[g]=(p+alpha*prior)/(n+alpha)
    return glob,pb,pm


def age_predict(row,model,k=None):
    glob,pb,pm=model; t,l,a,pid,y=row
    p=pm.get((l,a,pid%k),pb.get((l,a),glob)) if k else pb.get((l,a),glob)
    return min(1-EPS,max(EPS,p))


def age_metrics(rows,model,k=None):
    if not rows:return {"n":0}
    b=ll=ece=0.; n=len(rows); cal=[[] for _ in range(10)]
    for r in rows:
        p=age_predict(r,model,k); y=r[4]
        b+=(p-y)**2; ll-=y*math.log(p)+(1-y)*math.log(1-p)
        cal[min(9,int(p*10))].append((p,y))
    details=[]
    for i,group in enumerate(cal):
        if group:
            mp=sum(x for x,_ in group)/len(group); obs=sum(y for _,y in group)/len(group)
            ece+=len(group)/n*abs(mp-obs)
            details.append({"decile":i,"n":len(group),"pred":mp,"observed":obs})
    return {"n":n,"prevalence":sum(r[4] for r in rows)/n,"brier":b/n,"logloss":ll/n,
            "ece10":ece,"calibration":details}


def survival_age_analysis(c,h):
    rows=age_horizon_rows(c,h)
    if min(map(len,rows.values()))<100:return {"status":"too_few_rows","counts":{x:len(y) for x,y in rows.items()}}
    baseval=age_metrics(rows["val"],fit_age(rows["train"]))
    val_scores={}
    for k in range(2,17):
        val_scores[k]=age_metrics(rows["val"],fit_age(rows["train"],k),k)["brier"]
    k0=min(val_scores,key=lambda k:(val_scores[k],k))
    fit=rows["train"]+rows["val"]
    bmodel=fit_age(fit); mmodel=fit_age(fit,k0)
    base=age_metrics(rows["test"],bmodel); mod=age_metrics(rows["test"],mmodel,k0)
    return {"status":"ok","train_rows":len(rows["train"]),"validation_rows":len(rows["val"]),
            "test_rows":len(rows["test"]),"selected_modulo_k_validation":k0,
            "validation_base_brier":baseval["brier"],"validation_mod_brier":val_scores[k0],
            "validation_brier_improvement":baseval["brier"]-val_scores[k0],
            "test_length_age":base,"test_length_age_plus_pidmod":mod,
            "test_brier_improvement":base["brier"]-mod["brier"],
            "age_offsets_horizon_units":[0]+[2**j for j in range(10)],
            "note":"Rows are repeated age snapshots of pipes; interval labels are fully inside temporal split, but observations within a pipe are dependent."}


def survival_descriptive(c):
    out={}
    for h in (128,1024,8192):
        groups=defaultdict(lambda:[0,0]); total=events=0
        for pid in range(1,len(c["birth"])):
            b=c["birth"][pid]; d=c["death"][pid]
            if b+h>=c["n"]:continue
            y=int(d is not None and d<=b+h)
            groups[c["length"][pid]][0]+=y;groups[c["length"][pid]][1]+=1
            total+=1;events+=y
        out[str(h)]={"pipes_with_full_horizon":total,"removed_within_h":events,
                     "survival_probability":(total-events)/total if total else None,
                     "length_rates":{str(l):round(e/n,4) for l,(e,n) in sorted(groups.items()) if n>=20}}
    bylen=defaultdict(list)
    for pid in range(1,len(c["birth"])):
        d=c["death"][pid]
        if d is not None:bylen[c["length"][pid]].append(d-c["birth"][pid])
    out["completed_lifetime_median_ops"]={str(l):statistics.median(v) for l,v in bylen.items() if len(v)>=20}
    return out


def main():
    cases=[load(p) for p in sorted((ROOT/"data/pipes/open").glob("*.in"),key=lambda p:int(p.stem))]
    results={}
    for c in cases:
        results[str(c["id"])]={"n_ops":c["n"],"placements":len(c["birth"])-1,
          "deletions":sum(x<0 for x in c["ops"]),
          "length_prediction":length_predictions(c),"pid_modulo":mod_analysis(c),
          "survival_descriptive":survival_descriptive(c),
          "age_conditioned_survival":{str(h):survival_age_analysis(c,h) for h in (128,1024,8192)}}
    doc={"protocol":{
      "length":"first 60% of operation rows train, final 40% test; test forecasts are prequential and use only earlier observed insertion lengths; best lag chosen on train.",
      "pid_modulo":"first 40% operations fit rate ratios by PID mod k with active-risk-set exposure; 40-60% chooses k; final 40% is independent test. Baseline is uniform choice among currently active PIDs.",
      "age_survival":"per-pipe snapshots at ages 0,H,2H,4H,...; train future windows end before 40%, validation windows lie in 40-60%, test windows begin after 60%; models predict removal in next H conditioned on current age and length; PID mod k selected on validation only.",
      "uncertainty":"paired moving-block bootstrap over test event order for length and modulo log-loss/Brier changes. Age metrics are calibrated/Brier-scored but repeated snapshots within each pipe are dependent; small row counts are suppressed.",
      "limitations":"These 15 fixed public inputs were already explored; chronological splits reduce direct event-row reuse but do not establish hidden-test generalization. Phase boundaries are descriptive."
    },"cases":results}
    path=OUT/"metrics.json";path.write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n")
    print(path)
    for cid,r in results.items():
        l=r["length_prediction"];m=r["pid_modulo"]
        print(cid,"length",l.get("test_adds"),l.get("train_selected_lag"),
              "base/lags",[(k,round(v.get("brier",0),4)) for k,v in l.get("test",{}).items()],
              "pidmod",m.get("selected_k_validation"),m.get("test_deletions"),m.get("test_delta_logloss_vs_uniform_active_pid"))
        for h,z in r["age_conditioned_survival"].items():
            if z.get("status")=="ok": print("  age",h,z["test_length_age"]["brier"],z["test_length_age_plus_pidmod"]["brier"],z["test_brier_improvement"])


if __name__=="__main__":main()
