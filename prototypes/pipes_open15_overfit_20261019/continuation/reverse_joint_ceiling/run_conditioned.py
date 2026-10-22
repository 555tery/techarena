#!/usr/bin/env python3
"""Run the existing offline conditioned builder under the task-local usage guard."""
from pathlib import Path
import importlib.util, json, sys, re, hashlib
ROOT=Path(__file__).resolve().parent
REPO=Path(__file__).resolve().parents[4]
CONT=ROOT.parent
sys.path.insert(0,str(CONT))
import runtime
runtime.ROOT=ROOT
runtime.e.ROOT=ROOT
runtime.e.quota=lambda:runtime.e.gate(ROOT,min_remaining_percent=0,max_age_seconds=30)
OUT=ROOT/'conditioned11'
OUT.mkdir(exist_ok=True)
DATA=REPO/'data/pipes/open/11.in'
PINS=ROOT/'pins15_componentpacked.txt'
results=[]
for mode in range(4):
    plan=OUT/f'mode{mode}_positions.txt'; log=OUT/f'mode{mode}.log'
    cmd=[str(CONT/'conditioned'),str(DATA),str(PINS),'4999',str(plan),str(mode)]
    rc=runtime.e.invoke(cmd,OUT,log.name,90)
    text=log.read_text(errors='replace') if log.exists() else ''
    m=re.search(r'(?m)^\s*(\d+)\s*$',text)
    item={'mode':mode,'returncode':rc,'builder_T':int(m.group(1)) if m else None,'log_tail':text[-300:]}
    if plan.exists():item['plan_sha256']=hashlib.sha256(plan.read_bytes()).hexdigest()
    results.append(item)
    print(json.dumps(item))
(ROOT/'conditioned11-runs.json').write_text(json.dumps({'scope':'offline conditioned builder only; no native harness','input':'Open11','prefix_commands':4999,'modes':results},indent=2)+'\n')
