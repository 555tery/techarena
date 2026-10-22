#!/usr/bin/env python3
"""Causal next-deletion parity diagnostic for baseline and rolling-16 trigger."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import analyze
ROOT=Path(__file__).resolve().parents[4]
result={'protocol':'At each deletion, score parity prediction from state after previous deletion; test is final 40% by operation time. This is an event-prediction diagnostic, not allocator KPI.' ,'cases':{}}
for cid in (5,9,15):
 c=analyze.load(ROOT/f'data/pipes/open/{cid}.in');ops=c['ops'];n=c['n'];cut=int(.60*n)
 lastpid=-1;lastlen=-1;stride=0;exact=False;exactpar=1
 hist=[]; stats={'test_deletions':0,'existing_predictions':0,'existing_correct':0,'rolling_only_predictions':0,'rolling_only_correct':0,'union_predictions':0,'union_correct':0,'rolling_any_predictions':0,'rolling_any_correct':0}
 for t,x in enumerate(ops):
  if x>0: continue
  pid=-x
  if t>=cut:
   stats['test_deletions']+=1
   if exact:
    stats['existing_predictions']+=1; stats['existing_correct']+=int((pid&1)==exactpar)
   roll=(len(hist)>=16 and all((z&1)==(hist[-1]&1) for z in hist[-16:]))
   if roll:
    stats['rolling_any_predictions']+=1;stats['rolling_any_correct']+=int((pid&1)==(hist[-1]&1))
    if not exact:
     stats['rolling_only_predictions']+=1;stats['rolling_only_correct']+=int((pid&1)==(hist[-1]&1))
   if exact or roll:
    stats['union_predictions']+=1
    pred=exactpar if exact else hist[-1]&1
    stats['union_correct']+=int((pid&1)==pred)
  length=c['length'][pid]
  if lastpid>=0 and lastlen==length and pid==lastpid+2: stride+=1
  else: stride=0;exact=False
  if stride>=7: exact=True;exactpar=pid&1
  lastpid,lastlen=pid,length
  hist.append(pid)
 for key,predkey in [('existing_accuracy','existing_predictions'),('rolling_only_accuracy','rolling_only_predictions'),('union_accuracy','union_predictions'),('rolling_any_accuracy','rolling_any_predictions')]:
  npr=stats[predkey]; corr=stats[{'existing_accuracy':'existing_correct','rolling_only_accuracy':'rolling_only_correct','union_accuracy':'union_correct','rolling_any_accuracy':'rolling_any_correct'}[key]]
  stats[key]=corr/npr if npr else None
 result['cases'][str(cid)]={'input_sha256':hashlib.sha256((ROOT/f'data/pipes/open/{cid}.in').read_bytes()).hexdigest(),**stats}
path=Path(__file__).resolve().parent/'trigger_audit.json';path.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
