"""Bounded second stage: five explicit offline lifetime packings, prefix-coupled."""
import json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'prototypes/pipes_options_v4_20261019'))
import evaluate as e
e.ROOT=ROOT;e.quota()
j=json.loads((ROOT/'joint.json').read_text());blocks=j['blocks'];cases=j['cases']
assert e.invoke(['/usr/bin/clang++','-O3','-std=c++17',str(ROOT/'future_plans.cpp'),'-o',str(ROOT/'future_plans')],ROOT,'compile-future.log',120)==0
stage=ROOT/'future';stage.mkdir(exist_ok=False)
for mode in range(5):
 e.quota();out=stage/str(mode);out.mkdir();keys=[0]*len(blocks)
 # Longest member supplies priorities for variables shared across public prefixes.
 for case in sorted(cases,key=lambda c:len(c['commands'])):
  target=out/f"{case['case']}.txt"
  assert e.invoke([str(ROOT/'future_plans'),str(REPO/'data/pipes/open'/f"{case['case']}.in"),str(target),str(mode)],out,f"{case['case']}.log",60)==0
  places=iter(map(int,target.read_text().split()))
  for bid in case['block_ids']:
   if bid>=0:keys[bid]=next(places)
 with (out/'problem.txt').open('w') as f:
  print(len(blocks),j['time_count'],15,file=f)
  for c in cases:print(c['weight'],c['F'],file=f)
  for b,x in zip(blocks,keys):
   print(b['length'],x,b['first'],len(b['intervals']),file=f)
   for span in b['intervals']:print(*span,file=f)
 # pack writes raw seed first; always use iteration 0's reconstructed feasible layout.
 # A separate raw-score baseline can be infeasible across shared prefixes, so cannot select it.
 cmd=[str(ROOT/'pack'),str(out/'problem.txt'),str(out/'positions.txt'),'1']
 assert e.invoke(cmd,out,'compaction.log',120)==0
print('Five offline plan orders prepared; independent feasibility verification required.')
