#!/usr/bin/env python3
"""Causal feature audit on a chronological split of the sealed holdout-v2 streams.

The early half of each sequence supplies training data only. The later half is
used only for retrospective scoring of predictions made from that early data.
No allocator candidate is constructed here.
"""
from __future__ import annotations
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / 'data/pipes/synthetic/final-holdout-v2'
OUTPUTS = ROOT / 'results/pipes/final/holdout-run-size-cohort-lanes/runs'
OUT = Path(__file__).resolve().parent
HORIZON = 128
MIN_LENGTH_SUPPORT = 8

class Node:
    __slots__ = ('key','pid','length','born','priority','left','right')
    def __init__(self,key,pid,length,born,priority):
        self.key,self.pid,self.length,self.born,self.priority=key,pid,length,born,priority
        self.left=self.right=None

def split(node,key):
    if node is None: return None,None
    if node.key < key:
        a,b=split(node.right,key); node.right=a; return node,b
    a,b=split(node.left,key); node.left=b; return a,node

def merge(a,b):
    if a is None: return b
    if b is None: return a
    if a.priority < b.priority:
        a.right=merge(a.right,b); return a
    b.left=merge(a,b.left); return b

def insert(node,item):
    if node is None: return item
    if item.priority < node.priority:
        item.left,item.right=split(node,item.key); return item
    if item.key < node.key: node.left=insert(node.left,item)
    else: node.right=insert(node.right,item)
    return node

def erase(node,key):
    if node is None: raise KeyError(key)
    if key==node.key: return merge(node.left,node.right)
    if key<node.key: node.left=erase(node.left,key)
    else: node.right=erase(node.right,key)
    return node

def predecessor(node,key):
    best=None
    while node:
        if node.key<key: best=node; node=node.right
        else: node=node.left
    return best

def successor(node,key):
    best=None
    while node:
        if node.key>=key: best=node; node=node.left
        else: node=node.right
    return best

def parse_case(path):
    vals=path.read_text().split()
    n=int(vals[1]); ops=list(map(int,vals[2:2+n]))
    assert len(ops)==n
    return ops

def parse_answers(ops,path):
    ans=list(map(int,path.read_text().split())); out=[]; i=0
    for op in ops:
        k=2 if op>0 else 1
        out.append(tuple(ans[i:i+k])); i+=k
    assert i==len(ans),(path,i,len(ans))
    return out

def replay(casepath, outpath):
    ops=parse_case(casepath); answers=parse_answers(ops,outpath)
    n=len(ops); cut=n//2
    pipes=[None]; rows=[]; tree=None; trench=0; placement_count=0
    rng=0x9e3779b97f4a7c15
    def priority():
        nonlocal rng
        rng ^= (rng << 13) & ((1<<64)-1); rng ^= rng >> 7; rng ^= (rng << 17) & ((1<<64)-1)
        return rng & ((1<<64)-1)
    ai=0
    for opidx,cmd in enumerate(ops,1):
        response=answers[opidx-1]
        if cmd>0:
            digs,start=response; trench += digs*20; length=cmd
            left=predecessor(tree,start)
            right=successor(tree,start+length)
            pid=len(pipes)
            row={'pid':pid,'op':opidx,'placement':placement_count+1,'length':length,
                 'start':start,'left_pid':left.pid if left else 0,
                 'left_length':left.length if left else 0,'left_born':left.born if left else 0,
                 'left_start':left.key if left else 0,'left_end':left.key+left.length if left else 0,
                 'right_pid':right.pid if right else 0,
                 'right_length':right.length if right else 0,'right_born':right.born if right else 0,
                 'right_start':right.key if right else 0,
                 'death':None}
            rows.append(row)
            pipes.append({'pid':pid,'length':length,'born':opidx,'death':None,'start':start})
            tree=insert(tree,Node(start,pid,length,opidx,priority()))
            placement_count+=1
        elif cmd<0:
            pid=-cmd; pipe=pipes[pid]
            assert pipe and pipe['death'] is None
            pipe['death']=opidx
            # Fill the matching row with its eventual label after replay.
            rows[pid-1]['death']=opidx
            tree=erase(tree,pipe['start'])
        else: raise ValueError('unexpected zero terminator inside declared operations')
    assert len(rows)==placement_count
    train_life=defaultdict(list)
    for p in pipes[1:]:
        if p['born']<=cut and p['death'] is not None and p['death']<=cut:
            train_life[p['length']].append(p['death']-p['born'])
    train_all=[x for xs in train_life.values() for x in xs]
    global_median=statistics.median(train_all) if train_all else 1.0
    med={l:(statistics.median(xs) if len(xs)>=MIN_LENGTH_SUPPORT else global_median)
         for l,xs in train_life.items()}
    def median_for(length):
        xs=train_life.get(length,())
        return statistics.median(xs) if len(xs)>=MIN_LENGTH_SUPPORT else global_median
    val=[]
    for r in rows:
        if r['op']<=cut or r['op']+HORIZON>n: continue
        if not (r['left_pid'] and r['right_pid']): continue
        incoming_death=r['death']
        left_death=pipes[r['left_pid']]['death']; right_death=pipes[r['right_pid']]['death']
        if incoming_death is None or left_death is None or right_death is None: continue
        incoming_actual=incoming_death-r['op']
        left_actual=left_death-r['op']; right_actual=right_death-r['op']
        # We require all three outcomes within the fixed horizon for an unbiased
        # paired comparison of edge choices.
        if max(incoming_actual,left_actual,right_actual)>HORIZON: continue
        in_pred=median_for(r['length'])
        global_prior=global_median
        left_pred=max(0,median_for(r['left_length'])-(r['op']-r['left_born']))
        right_pred=max(0,median_for(r['right_length'])-(r['op']-r['right_born']))
        actual_left_err=abs(incoming_actual-left_actual)
        actual_right_err=abs(incoming_actual-right_actual)
        pred_left_err=abs(in_pred-left_pred)
        pred_right_err=abs(in_pred-right_pred)
        same_left=(r['pid']%2)==(r['left_pid']%2)
        same_right=(r['pid']%2)==(r['right_pid']%2)
        left_age=r['op']-r['left_born']; right_age=r['op']-r['right_born']
        used_side=('left' if r['start']==r['left_end'] and r['start']+r['length']!=r['right_start'] else ('right' if r['start']+r['length']==r['right_start'] and r['start']!=r['left_end'] else 'tie'))
        # Control policy with no length-conditioned lifetime model: use the
        # completed-training global median and current neighbor ages only.
        # On a tie, preserve the observed baseline edge if it is unambiguous;
        # otherwise use a fixed left tie-break.
        age_left_err=abs(global_prior-max(0,global_prior-left_age))
        age_right_err=abs(global_prior-max(0,global_prior-right_age))
        age_side=('left' if age_left_err<age_right_err else 'right' if age_right_err<age_left_err else (used_side if used_side in ('left','right') else 'left'))
        pred_side=('left' if pred_left_err<pred_right_err else 'right' if pred_right_err<pred_left_err else (used_side if used_side in ('left','right') else 'left'))
        val.append({'case':casepath.stem,'pid':r['pid'],'op':r['op'],
                    'incoming_actual':incoming_actual,'left_actual':left_actual,'right_actual':right_actual,
                    'actual_left_error':actual_left_err,'actual_right_error':actual_right_err,
                    'pred_left_error':pred_left_err,'pred_right_error':pred_right_err,
                    'predicted_side':'left' if pred_left_err<pred_right_err else ('right' if pred_right_err<pred_left_err else 'tie'),
                    'predicted_decision_side':pred_side,
                    'predicted_side_gain':(actual_right_err-actual_left_err) if pred_left_err<pred_right_err else ((actual_left_err-actual_right_err) if pred_right_err<pred_left_err else 0),
                    'same_left':same_left,'same_right':same_right,
                    'used_side':used_side,'age_only_side':age_side,
                    'age_left_error':age_left_err,'age_right_error':age_right_err,
                    'predicted_actual_mismatch':actual_left_err if pred_side=='left' else actual_right_err,
                    'age_only_actual_mismatch':actual_left_err if age_side=='left' else actual_right_err,
                    'baseline_actual_mismatch':actual_left_err if used_side=='left' else actual_right_err if used_side=='right' else None,
                    'model_minus_age_mismatch':(actual_left_err if pred_side=='left' else actual_right_err)-(actual_left_err if age_side=='left' else actual_right_err),
                    'same_parity_error':actual_left_err if same_left else actual_right_err if same_right else None,
                    'opposite_parity_error':actual_left_err if not same_left and same_right else actual_right_err if not same_right and same_left else None})
    return {'case':casepath.stem,'operations':n,'cut_op':cut,'train_completed_count':len(train_all),
            'supported_lengths':sum(len(xs)>=MIN_LENGTH_SUPPORT for xs in train_life.values()),
            'global_median_lifetime':global_median,'eligible_validation_pairs':len(val)}, val

def main():
    per_case=[]; all_rows=[]
    for path in sorted(DATA.glob('*.in')):
        key=path.stem
        out=OUTPUTS/key/'judge_output.txt'
        assert out.exists(),out
        summary,rows=replay(path,out)
        per_case.append(summary); all_rows.extend(rows)
    parity=[r for r in all_rows if r['same_parity_error'] is not None and r['opposite_parity_error'] is not None]
    pred=[r for r in all_rows if r['predicted_side']!='tie']
    same_wins=sum(r['same_parity_error']<r['opposite_parity_error'] for r in parity)
    same_ties=sum(r['same_parity_error']==r['opposite_parity_error'] for r in parity)
    pred_wins=sum(r['predicted_side_gain']>0 for r in pred)
    pred_ties=sum(r['predicted_side_gain']==0 for r in pred)
    case_detail=[]
    for c in per_case:
        rs=[r for r in all_rows if r['case']==c['case']]
        ps=[r for r in rs if r['same_parity_error'] is not None and r['opposite_parity_error'] is not None]
        # Paired policy comparisons use identical placements on both sides.
        ds=rs
        baseline_pairs=[r for r in ds if r['used_side'] in ('left','right')]
        pred_actual=[r['predicted_actual_mismatch'] for r in ds]
        age_actual=[r['age_only_actual_mismatch'] for r in ds]
        baseline_actual=[r['baseline_actual_mismatch'] for r in baseline_pairs]
        model_age_deltas=[r['model_minus_age_mismatch'] for r in ds]
        model_baseline_deltas=[r['predicted_actual_mismatch']-r['baseline_actual_mismatch'] for r in baseline_pairs]
        case_detail.append({**c,'neighbor_parity_pairs':len(ps),
            'same_parity_closer_fraction':sum(r['same_parity_error']<r['opposite_parity_error'] for r in ps)/len(ps) if ps else None,
            'mean_same_minus_opposite_error':statistics.mean(r['same_parity_error']-r['opposite_parity_error'] for r in ps) if ps else None,
            'lifetime_edge_pairs':len(ds),
            'predicted_edge_win_fraction':sum(r['predicted_side_gain']>0 for r in ds)/len(ds) if ds else None,
            'mean_predicted_edge_gain_commands':statistics.mean(r['predicted_side_gain'] for r in ds) if ds else None,
            'predicted_model_mean_actual_mismatch':statistics.mean(pred_actual) if pred_actual else None,
            'age_only_mean_actual_mismatch':statistics.mean(age_actual) if age_actual else None,
            'baseline_side_pairs':len(baseline_pairs),
            'baseline_side_mean_actual_mismatch':statistics.mean(baseline_actual) if baseline_actual else None,
            'mean_model_minus_age_mismatch':statistics.mean(model_age_deltas) if model_age_deltas else None,
            'model_beats_age_fraction':sum(x<0 for x in model_age_deltas)/len(model_age_deltas) if model_age_deltas else None,
            'baseline_side_pairs':len(baseline_pairs),
            'baseline_side_mean_actual_mismatch':statistics.mean(baseline_actual) if baseline_actual else None,
            'mean_model_minus_baseline_mismatch':statistics.mean(model_baseline_deltas) if model_baseline_deltas else None,
            'model_beats_baseline_fraction':sum(x<0 for x in model_baseline_deltas)/len(model_baseline_deltas) if model_baseline_deltas else None})
    # Equally weight cases with at least 20 paired observations to avoid letting
    # one long synthetic stream dominate the temporal transfer diagnosis.
    usable=[r for r in case_detail if r['neighbor_parity_pairs']>=20]
    usable_edge=[r for r in case_detail if r['lifetime_edge_pairs']>=20]
    def cluster_bootstrap_ci(values, seed=20261017, draws=20000):
        import random
        if not values: return None
        rng=random.Random(seed); samples=[]; m=len(values)
        for _ in range(draws): samples.append(statistics.mean(values[rng.randrange(m)] for _ in range(m)))
        samples.sort()
        return [samples[int(0.025*draws)],samples[int(0.975*draws)]]
    parity_case_deltas=[r['mean_same_minus_opposite_error'] for r in usable]
    edge_case_gains=[r['mean_predicted_edge_gain_commands'] for r in usable_edge]
    edge_age_gains=[r['mean_model_minus_age_mismatch'] for r in usable_edge]
    edge_base_gains=[r['mean_model_minus_baseline_mismatch'] for r in usable_edge if r['mean_model_minus_baseline_mismatch'] is not None]
    # Cluster bootstrap over cases, not individual placements. This avoids
    # treating highly dependent events from one stream as independent draws.
    summary={
      'dataset':'final-holdout-v2; each stream split chronologically at command 50%; early completed events train, late events validate',
      'baseline_source_sha256':hashlib.sha256((ROOT/'results/pipes/final/solution.cpp').read_bytes()).hexdigest(),
      'horizon_commands':HORIZON,'min_completed_train_support_per_length':MIN_LENGTH_SUPPORT,
      'cases':case_detail,
      'neighbor_parity':{'paired_validation_samples':len(parity),'same_parity_wins':same_wins,'ties':same_ties,
        'same_parity_win_fraction_excluding_ties':same_wins/max(1,len(parity)-same_ties),
        'mean_same_minus_opposite_actual_lifetime_error_commands':statistics.mean(r['same_parity_error']-r['opposite_parity_error'] for r in parity) if parity else None,
        'cases_with_ge20_pairs':len(usable),'positive_case_count':sum(r['mean_same_minus_opposite_error']<0 for r in usable),
        'equal_case_weighted_mean_delta_commands':statistics.mean(parity_case_deltas) if parity_case_deltas else None,
        'equal_case_weighted_bootstrap_95pct_ci':cluster_bootstrap_ci(parity_case_deltas)},
      'predicted_lifetime_edge':{'paired_validation_samples':len(pred),'predicted_side_wins':pred_wins,'ties':pred_ties,
        'win_fraction_excluding_ties':pred_wins/max(1,len(pred)-pred_ties),
        'mean_predicted_choice_gain_commands':statistics.mean(r['predicted_side_gain'] for r in pred) if pred else None,
        'cases_with_ge20_pairs':len(usable_edge),'positive_case_count':sum(r['mean_predicted_edge_gain_commands']>0 for r in usable_edge),
        'equal_case_weighted_model_minus_age_mismatch':statistics.mean(edge_age_gains) if edge_age_gains else None,
        'equal_case_weighted_model_minus_age_bootstrap_95pct_ci':cluster_bootstrap_ci(edge_age_gains,seed=20261018),
        'baseline_side_comparison_case_count':len(edge_base_gains),
        'equal_case_weighted_model_minus_baseline_mismatch':statistics.mean(edge_base_gains) if edge_base_gains else None,
        'equal_case_weighted_model_minus_baseline_bootstrap_95pct_ci':cluster_bootstrap_ci(edge_base_gains,seed=20261019)},
      'limits':'Retrospective paired scoring is conditional on the baseline-chosen hole and pipes later removed within 128 commands. It is a feature-transfer diagnostic, not a counterfactual allocator score. Holdout-v2 had prior use for finalist comparisons; this analysis was not used to train or tune allocator code.'}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'temporal_holdout_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    fields=list(case_detail[0].keys())
    with (OUT/'temporal_holdout_per_case.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(case_detail)
    print(json.dumps(summary['neighbor_parity'],indent=2)); print(json.dumps(summary['predicted_lifetime_edge'],indent=2))
    print('PER CASE')
    for r in case_detail: print(r)
if __name__=='__main__': main()
