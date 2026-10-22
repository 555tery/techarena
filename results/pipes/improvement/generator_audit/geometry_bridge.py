#!/usr/bin/env python3
"""Prequential rank-to-coalescence bridge audit on instrumented baseline runs."""

import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
CASES = [5, 8, 9, 10, 14, 15]
ALPHA = 1.0


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metric(rows, key, eps=1e-12):
    if not rows:
        return {"n": 0, "prevalence": 0.0, "brier": 0.0,
                "logloss": 0.0, "accuracy_at_0_5": 0.0}
    n = len(rows)
    brier = ll = hit = 0.0
    for row in rows:
        p, y = min(1-eps, max(eps, row[key])), row["coal"]
        brier += (p-y)**2
        ll -= y*math.log(p)+(1-y)*math.log(1-p)
        hit += int((p >= .5) == bool(y))
    return {"n": n, "prevalence": sum(r["coal"] for r in rows)/n,
            "brier": brier/n, "logloss": ll/n, "accuracy_at_0_5": hit/n}


def block_ci(rows, fn, width=128, reps=2000, seed=20261017):
    blocks = defaultdict(list)
    for row in rows:
        blocks[(row["op"]-1)//width].append(row)
    groups = list(blocks.values())
    if len(groups) < 8:
        return {"nonempty_blocks": len(groups), "ci95": None}
    stats = [(sum(fn(r) for r in g), len(g)) for g in groups]
    rng = random.Random(seed+len(rows))
    vals = []
    for _ in range(reps):
        chosen = [rng.choice(stats) for _ in range(len(stats))]
        vals.append(sum(s for s, _ in chosen)/sum(n for _, n in chosen))
    vals.sort()
    return {"nonempty_blocks": len(groups),
            "ci95": [vals[int(.025*(reps-1))], vals[int(.975*(reps-1))]]}


def load_case(case):
    path = OUT / "geometry_runs" / "runs" / str(case) / "solver_stderr.txt"
    n = int((ROOT / "data/pipes/open" / f"{case}.in").read_text().split()[1])
    rows = []
    for line in path.read_text().splitlines():
        if not line.startswith("GEOM "):
            continue
        v = list(map(int, line.split()[1:]))
        if len(v) != 16:
            raise ValueError((case, len(v), line[:160]))
        op,pid,perm,age,length,start,lpid,llen,lage,lgap,rpid,rlen,rage,rgap,coal,span = v
        band = min(3, perm*4//1001)
        rows.append({"op":op,"pid":pid,"rank_permille":perm,"band":band,
                     "age":age,"length":length,"start":start,
                     "left_pid":lpid,"left_len":llen,"left_age":lage,"left_gap":lgap,
                     "right_pid":rpid,"right_len":rlen,"right_age":rage,"right_gap":rgap,
                     "coal":coal,"released_span":span})
    if not rows:
        raise ValueError(f"no GEOM rows for {case}")
    return n, rows, path


def band_stats(rows):
    out = []
    for b in range(4):
        g = [r for r in rows if r["band"] == b]
        if not g:
            out.append({"band":b,"n":0})
            continue
        out.append({"band":b,"n":len(g),
                    "coalescence_rate":sum(r["coal"] for r in g)/len(g),
                    "mean_released_span":sum(r["released_span"] for r in g)/len(g),
                    "mean_removed_age_ops":sum(r["age"] for r in g)/len(g),
                    "mean_length_m":sum(r["length"] for r in g)/len(g),
                    "both_neighbor_gaps_positive_rate":sum(r["left_gap"]>0 and r["right_gap"]>0 for r in g)/len(g),
                    "one_or_more_neighbor_gaps_positive_rate":sum(r["left_gap"]>0 or r["right_gap"]>0 for r in g)/len(g),
                    "mean_left_gap_m":sum(r["left_gap"] for r in g)/len(g),
                    "mean_right_gap_m":sum(r["right_gap"] for r in g)/len(g)})
    return out


def evaluate_case(case):
    n, rows, log_path = load_case(case)
    train_cut, val_cut = int(.40*n), int(.60*n)
    rows.sort(key=lambda r:r["op"])
    # Fit rank-to-geometry calibration on first 40%; after that, update only
    # after each deletion has become observable. Markov rank forecast is also
    # prequential and does not inspect the target event.
    band_coal = [[0,0] for _ in range(4)]
    all_coal = [0,0]
    rank_counts = [0]*4
    transitions = [[0]*4 for _ in range(4)]
    previous = None
    scored = []
    train = [r for r in rows if r["op"] <= train_cut]
    val = [r for r in rows if train_cut < r["op"] <= val_cut]
    test = [r for r in rows if r["op"] > val_cut]
    for r in rows:
        if r["op"] > train_cut:
            p_global = (all_coal[1]+ALPHA)/(sum(all_coal)+2*ALPHA)
            if previous is None:
                p_rank = [(rank_counts[b]+ALPHA)/(sum(rank_counts)+4*ALPHA) for b in range(4)]
            else:
                den = sum(transitions[previous])+4*ALPHA
                p_rank = [(transitions[previous][b]+ALPHA)/den for b in range(4)]
            p_rank_to_coal = [(band_coal[b][1]+ALPHA)/(sum(band_coal[b])+2*ALPHA) for b in range(4)]
            p_mapped = sum(p_rank[b]*p_rank_to_coal[b] for b in range(4))
            p_stationary = [(rank_counts[b]+ALPHA)/(sum(rank_counts)+4*ALPHA) for b in range(4)]
            p_stationary_mapped = sum(p_stationary[b]*p_rank_to_coal[b] for b in range(4))
            scored.append({**r,"phase":"validation" if r["op"] <= val_cut else "test",
                           "global":p_global,"markov_mapped":p_mapped,
                           "stationary_mapped":p_stationary_mapped})
        band_coal[r["band"]][0] += 1
        band_coal[r["band"]][1] += r["coal"]
        all_coal[0] += 1
        all_coal[1] += r["coal"]
        if previous is not None:
            transitions[previous][r["band"]] += 1
        rank_counts[r["band"]] += 1
        previous = r["band"]

    phases = {}
    phases["train_0_40"] = band_stats(train)
    phases["validation_40_60"] = band_stats(val)
    phases["test_60_100"] = band_stats(test)
    cuts = [val_cut + (n-val_cut)*q//4 for q in range(5)]
    phases["test_quartiles"] = []
    for q in range(4):
        g = [r for r in test if cuts[q] < r["op"] <= cuts[q+1]]
        phases["test_quartiles"].append({"phase":q+1,"op_range_inclusive":[cuts[q]+1,cuts[q+1]],
                                          "n":len(g),"coalescence_rate":sum(r["coal"] for r in g)/max(1,len(g)),
                                          "by_rank_band":band_stats(g)})
    score = {}
    for split in ("validation","test"):
        g = [r for r in scored if r["phase"] == split]
        score[split] = {m:metric(g,m) for m in ("global","markov_mapped","stationary_mapped")}
        for m in ("markov_mapped","stationary_mapped"):
            gains=[]
            for r in g:
                eps=1e-12
                p0=min(1-eps,max(eps,r["global"]))
                pm=min(1-eps,max(eps,r[m]))
                y=r["coal"]
                gains.append({"op":r["op"],"logloss_gain":(y*math.log(pm)+(1-y)*math.log(1-pm))-(y*math.log(p0)+(1-y)*math.log(1-p0)),
                              "brier_gain":(p0-y)**2-(pm-y)**2})
            score[split][m+"_minus_global"]={
                "mean_logloss_improvement":sum(r["logloss_gain"] for r in gains)/max(1,len(gains)),
                "logloss_improvement_ci95_by_128op_blocks":block_ci(gains,lambda r:r["logloss_gain"],seed=case*100+1),
                "mean_brier_improvement":sum(r["brier_gain"] for r in gains)/max(1,len(gains)),
                "brier_improvement_ci95_by_128op_blocks":block_ci(gains,lambda r:r["brier_gain"],seed=case*100+2)}
    return {"case":case,"operation_count":n,"deletion_count":len(rows),
            "split_ops":{"train":[1,train_cut],"validation":[train_cut+1,val_cut],"test":[val_cut+1,n]},
            "rank_band_geometry_rates":phases,
            "coalescence_forecast":{"scores":score},
            "geometry_log_sha256":sha(log_path)}


def main():
    cases={str(c):evaluate_case(c) for c in CASES}
    agg={}
    for split in ("validation","test"):
        rows=[]
        for c in CASES:
            case_result=cases[str(c)]
            # Aggregate score means weighted by scored events; reconstruct from
            # per-case sufficient metrics/counts, avoiding pooling cases as blocks.
            for model in ("global","markov_mapped","stationary_mapped"):
                item=case_result["coalescence_forecast"]["scores"][split][model]
                agg.setdefault(split,{}).setdefault(model,{"n":0,"brier_sum":0.0,"ll_sum":0.0,"coal_sum":0})
                a=agg[split][model]
                a["n"]+=item["n"]
                a["brier_sum"]+=item["brier"]*item["n"]
                a["ll_sum"]+=item["logloss"]*item["n"]
                a["coal_sum"]+=item["prevalence"]*item["n"]
    for split, models in agg.items():
        for model,a in models.items():
            n=a.pop("n")
            a["n"]=n;a["brier"]=a.pop("brier_sum")/n;a["logloss"]=a.pop("ll_sum")/n;a["prevalence"]=a.pop("coal_sum")/n
    out={"method":"causal replay log of baseline; train 0-40%, validation 40-60%, final heldout 60-100%; rank forecasts prequential; rank-to-coalescence conditional rates Beta(1,1), updated only after outcomes; 128-operation block bootstrap where at least 8 blocks",
         "rank_definition":"rank-from-newest permille, same as final solver; band=min(3,floor(permille*4/1001))",
         "cases":cases,"event_weighted_scores":agg,
         "source_sha256":sha(ROOT/"results/pipes/final/solution.cpp"),
         "instrumented_source_sha256":sha(OUT/"geometry_replay.cpp"),
         "instrumented_binary_sha256":sha(OUT/"geometry_replay"),
         "harness_summary_sha256":sha(OUT/"geometry_runs"/"summary.json"),
         "input_sha256_by_case":{str(c):sha(ROOT/"data/pipes/open"/f"{c}.in") for c in CASES}}
    (OUT/"geometry_bridge.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"event_weighted_scores":agg,
                      "per_case_test":{c:cases[c]["coalescence_forecast"]["scores"]["test"] for c in cases},
                      "case_test_rates":{c:cases[c]["rank_band_geometry_rates"]["test_60_100"] for c in cases}},indent=2))


if __name__=="__main__":
    main()
