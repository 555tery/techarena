#!/usr/bin/env python3
"""Small, preselected continuation-mode check for the compact Open15 prefix."""
from pathlib import Path
import sys,json,re,hashlib
ROOT=Path(__file__).resolve().parent; REPO=Path(__file__).resolve().parents[4]; CONT=ROOT.parent
sys.path.insert(0,str(CONT)); import runtime
runtime.ROOT=ROOT; runtime.e.ROOT=ROOT
runtime.e.quota=lambda:runtime.e.gate(ROOT,min_remaining_percent=0,max_age_seconds=30)
OUT=ROOT/'conditioned11'; DATA=REPO/'data/pipes/open/11.in'; PINS=ROOT/'pins15_componentpacked.txt'
tests=[('reverse',CONT/'conditioned_reverse',m) for m in (0,1,2,3,4,5)] + [('knapsack',CONT/'conditioned_knapsack',m) for m in (2000,2001)]
results=[]
for family,binary,mode in tests:
  label=f'{family}_{mode}'; plan=OUT/f'{label}_positions.txt'; log=OUT/f'{label}.log'
  cmd=[str(binary),str(DATA),str(PINS),'4999',str(plan),str(mode)]
  rc=runtime.e.invoke(cmd,OUT,log.name,90)
  text=log.read_text(errors='replace') if log.exists() else ''
  m=re.search(r'(?m)^\s*(\d+)\s*$',text)
  item={'family':family,'mode':mode,'returncode':rc,'builder_T':int(m.group(1)) if m else None,'log_tail':text[-200:]}
  if plan.exists():item['plan_sha256']=hashlib.sha256(plan.read_bytes()).hexdigest()
  results.append(item); print(json.dumps(item))
(ROOT/'conditioned11-more-runs.json').write_text(json.dumps({'scope':'bounded offline continuation variants; no native harness','prefix_commands':4999,'runs':results},indent=2)+'\n')
