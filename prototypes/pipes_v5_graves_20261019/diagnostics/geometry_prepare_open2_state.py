#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'prototypes/pipes_open15_adversary_20261019'))
from construct import decode
plans=decode(ROOT/'prototypes/pipes_v5_graves_20261019/target/solution.cpp')
cmds,poses=plans[1]
probe=ROOT/'prototypes/pipes_prefix_shock_20261019/allocator-probe'
tape=ROOT/'prototypes/pipes_prefix_shock_20261019/tape.txt'
lines=subprocess.run([str(probe),'bestfit',str(tape)],input='\n'.join(map(str,cmds+[0]))+'\n',text=True,capture_output=True,check=True).stdout.splitlines()
active_good={};active_bad={};pid=0;gt=bt=0
for c,g,line in zip(cmds,poses,lines):
 if c>0:
  pid+=1;d,b=map(int,line.split());gt=max(gt,((g+c+19)//20)*20);bt+=20*d
  active_bad[pid]=(c,g);active_good[pid]=(c,b)
 else:
  active_bad.pop(-c);active_good.pop(-c)
assert gt==20 and bt==40
assert len(active_good)==10 and sum(v[0] for v in active_good.values())==20
state=OUT/'geometry_open2_state.txt'
with state.open('w') as f:
 f.write(f'{bt} {gt} 40 {pid} {sum(x[0] for x in active_good.values())} {len(active_good)}\n')
 for ident in sorted(active_good):
  length,bpos=active_good[ident];_,gpos=active_bad[ident]
  f.write(f'{ident} {length} {bpos} {gpos}\n')
print(json.dumps({'state':str(state),'target_T':gt,'BF_T':bt,'live_volume':sum(x[0] for x in active_good.values()),'next_pid':pid,'pipes':len(active_good),'first_prefix':cmds[:18]},indent=2))
