#!/usr/bin/env python3
"""Hindsight lower bound on continuation space for a fixed observed prefix.
This is a diagnostic certificate, never an online policy or a bound on all
possible prefix layouts. No holdout/validation input is read.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,math
ROOT=Path(__file__).resolve().parents[4]
CAMPAIGN=Path(__file__).resolve().parents[2]
INPUT=ROOT/'data/pipes/open/15.in'
REPLIES=CAMPAIGN/'evaluations/baseline-open15/harness/runs/15/judge_output.txt'
POINT=100000

def main():
    tokens=INPUT.read_text().split()
    weight=float(tokens[0]); n=int(tokens[1]); ops=list(map(int,tokens[2:]))
    assert ops[-1]==0 and len(ops)==n+1
    ops=ops[:-1]; replies=REPLIES.read_text().splitlines()
    assert len(replies)==len(ops)
    active={}; pid=0; trench=0
    for index,(command,line) in enumerate(zip(ops,replies),1):
        if command>0:
            pid+=1; digs,start=map(int,line.split())
            assert digs>=0 and start>=0
            trench+=20*digs
            assert start+command<=trench
            active[pid]=(start,start+command,command,index)
        else:
            assert int(line)==active[-command][0]
            del active[-command]
        if index==POINT: prefix=dict(active); prefix_trench=trench
    survivors={pid:pipe for pid,pipe in prefix.items() if pid in active}
    new_final={pid:pipe for pid,pipe in active.items() if pipe[3]>POINT}
    gaps=[]; cursor=0
    for start,end,length,index in sorted(survivors.values()):
        assert start>=cursor
        if start>cursor:gaps.append((cursor,start,start-cursor))
        cursor=end
    # Deliberately exclude the tail after the last surviving barrier: it can
    # connect to future trench extension and therefore is not permanently lost.
    bounds=[]
    for cut in range(2,41):
        gap_m=sum(gap[2] for gap in gaps if gap[2]<cut)
        supply_m=sum(pipe[2] for pipe in new_final.values() if pipe[2]<cut)
        bounds.append(dict(cut=cut,bounded_gap_m=gap_m,
            new_final_small_pipe_volume_m=supply_m,
            unfillable_m_lower_bound=max(0,gap_m-supply_m)))
    best=max(bounds,key=lambda row:row['unfillable_m_lower_bound'])
    final_volume=sum(pipe[2] for pipe in active.values())
    lb=math.ceil((final_volume+best['unfillable_m_lower_bound'])/20)*20
    summary=json.loads((CAMPAIGN/'evaluations/baseline-open15/harness/summary.json').read_text())
    rec=next(row for row in summary['records'] if row['case']=='15')
    assert rec['trench_length_m']==trench and rec['occupied_length_m']==final_volume
    result=dict(diagnostic_only_uses_future_survival_labels=True,prefix_operations=POINT,
        prefix_T=prefix_trench,prefix_active_count=len(prefix),
        final_prefix_survivor_count=len(survivors),
        new_final_pipe_size_histogram=dict(sorted(Counter(v[2] for v in new_final.values()).items())),
        best_capacity_bound=best,bounds=bounds,final_volume=final_volume,
        continuation_trench_lower_bound_from_immutable_survivor_barriers=lb,
        observed_final_T=trench,remaining_possible_saving_at_same_prefix_m=trench-lb,
        maximum_possible_whole_score_at_same_prefix=summary['weighted_score_sum']+weight*final_volume/lb-rec['weighted_score'],
        above_projection_holds_other_14_cases_at_baseline=True,
        conditional_whole_score_upper_if_other_14_cases_volume_optimal=sum(r['weight']*r['kpi_upper_bound_from_live_volume'] for r in summary['records'])-weight*rec['kpi_upper_bound_from_live_volume']+weight*final_volume/lb,
        input_sha256=hashlib.sha256(INPUT.read_bytes()).hexdigest(),
        transcript_sha256=hashlib.sha256(REPLIES.read_bytes()).hexdigest(),
        baseline_source_sha256=hashlib.sha256((CAMPAIGN/'baseline/solution.cpp').read_bytes()).hexdigest(),
        proof='Surviving prefix pipes cannot move or disappear. In bounded gaps shorter than cut, only new final pipes shorter than cut can fit. Their entire volume is an upper bound on how much of those gaps can be occupied. Thus at least gap_m minus supply_m is unused at EOF, requiring trench >= final volume + unused volume. Round up to 20m.')
    (Path(__file__).parent/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['best_capacity_bound','continuation_trench_lower_bound_from_immutable_survivor_barriers','maximum_possible_whole_score_at_same_prefix']}))
if __name__=='__main__':main()
