#!/usr/bin/env python3
"""Event-only descriptors: no placement, score, trench, or solver data."""
import collections
import hashlib
import json
import math
import statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def quantiles(xs):
    if not xs: return None
    xs=sorted(xs)
    return {str(q):xs[int((len(xs)-1)*q)] for q in [0,.25,.5,.75,.95,1]}

def main():
    rows=[]
    for case in range(1,16):
        p=ROOT/'data/pipes/open'/f'{case}.in'
        raw=p.read_bytes(); tokens=raw.split(); commands=list(map(int,tokens[2:-1]))
        live={}; next_pid=1; volume=peak=0; lengths=[]; ages=[]; ranks=[]; lives=[]; runs=[]
        last=None; run=0; batches=[]; sign=None; signrun=0
        for t,c in enumerate(commands):
            if c>0:
                live[next_pid]=(c,t); next_pid+=1; volume+=c; lengths.append(c)
                if c==last:run+=1
                else:
                    if run:runs.append(run)
                    last=c;run=1
            else:
                length,born=live.pop(-c); volume-=length; ages.append(t-born)
                # PID distance is cheap and source-faithful, not an inferred live-age rank.
                ranks.append((next_pid-1)-(-c))
            sg=c>0
            if sg==sign:signrun+=1
            else:
                if signrun:batches.append(signrun)
                sign=sg;signrun=1
            lives.append(len(live));peak=max(peak,volume)
        if run:runs.append(run)
        if signrun:batches.append(signrun)
        hist=collections.Counter(lengths); total=len(lengths)
        entropy=-sum((k/total)*math.log2(k/total) for k in hist.values())
        chunks=[]
        for block in range(8):
            seq=commands[len(commands)*block//8:len(commands)*(block+1)//8]
            add=[c for c in seq if c>0]
            chunks.append({'n':len(seq),'delete_fraction':sum(c<0 for c in seq)/max(1,len(seq)),
                'mean_insert_length':sum(add)/max(1,len(add))})
        rows.append({'case':case,'sha256':hashlib.sha256(raw).hexdigest(),'n':len(commands),
            'insert_count':total,'delete_count':len(ages),'length_histogram':dict(sorted(hist.items())),
            'length_entropy_bits':entropy,'length_quantiles':quantiles(lengths),
            'same_length_insert_run_quantiles':quantiles(runs),'command_sign_run_quantiles':quantiles(batches),
            'deletion_lifetime_commands_quantiles':quantiles(ages),'deletion_pid_distance_quantiles':quantiles(ranks),
            'active_count_quantiles':quantiles(lives),'peak_live_volume':peak,'final_live_volume':volume,
            'final_to_peak_volume':volume/peak,'temporal_eighths':chunks})
    data={'scope':'Official input events only; no solver outputs, scores or placement coordinates',
          'rows':rows,'interpretation_limits':['15 public inputs cannot identify a hidden-test distribution.',
          'PID distance is not live-set age rank; repeated lengths and deletion ages are observable, not evidence of a solver policy.']}
    (HERE/'open15-structure.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps([{'case':r['case'],'n':r['n'],'length_support':len(r['length_histogram']),
        'entropy':round(r['length_entropy_bits'],3),'median_delete_lifetime':None if not r['deletion_lifetime_commands_quantiles'] else r['deletion_lifetime_commands_quantiles']['0.5'],
        'max_equal_insert_run':r['same_length_insert_run_quantiles']['1'],
        'F_peak':round(r['final_to_peak_volume'],3)} for r in rows],indent=2))

if __name__=='__main__':main()
