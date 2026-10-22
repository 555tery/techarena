#!/usr/bin/env python3
"""Turn the bounded Open2 geometry beam result into a reproducible test."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'prototypes/pipes_open15_adversary_20261019'))
sys.path.insert(0,str(ROOT/'tools'))
from construct import decode
from pipes_harness import parse_test
TARGET=ROOT/'prototypes/pipes_v5_graves_20261019/target'
BEAM=OUT/'geometry_beam_search_open2'
STATE=OUT/'geometry_open2_state.txt'
PROBE=ROOT/'prototypes/pipes_prefix_shock_20261019/allocator-probe'
SEED_TAPE=ROOT/'prototypes/pipes_prefix_shock_20261019/tape.txt'
PLAN_TAPE=OUT/'geometry_open2_plan.tape'
TEST=OUT/'geometry_quiet_open2_beam.in'
PROV=OUT/'geometry_quiet_open2_beam.json'
RESULT=OUT/'geometry_open2_beam_result.txt'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def probe(mode,tape,commands):
 p=subprocess.run([str(PROBE),mode,str(tape)],input='\n'.join(map(str,commands+[0]))+'\n',text=True,capture_output=True,check=True,timeout=30)
 return p.stdout.splitlines(),p.stderr.strip()
def main():
 plans=decode(TARGET/'solution.cpp')
 prefix,positions=plans[1]
 assert len(prefix)==18
 matching=[i+1 for i,(c,_) in enumerate(plans) if c[:len(prefix)]==prefix]
 assert matching==[2]
 search=subprocess.run([str(BEAM),str(STATE),'128','500','55'],text=True,capture_output=True,check=True,timeout=15)
 RESULT.write_text(search.stdout+'\n--- search progress ---\n'+search.stderr,encoding='utf-8')
 best=int(re.search(r'best_target_T=(\d+)',search.stdout).group(1))
 suffix=list(map(int,re.search(r'suffix=\[([^]]*)\]',search.stdout).group(1).split(',')))
 commands=prefix+suffix
 TEST.write_text('1\n'+str(len(commands))+'\n'+'\n'.join(map(str,commands))+'\n',encoding='ascii')
 testmeta=parse_test(TEST)
 assert testmeta['final_occupied_length_m']==40
 assert best>80
 with PLAN_TAPE.open('w') as f:
  f.write(str(len(prefix))+'\n')
  for c,pos in zip(prefix,positions): f.write(f'{c} {-1 if pos is None else pos}\n')
 bf_lines,_=probe('bestfit',SEED_TAPE,commands)
 target_lines,target_err=probe('guarded',PLAN_TAPE,commands)
 def trench(lines,seq):
  T=0; trace=[]
  for c,line in zip(seq,lines):
   if c>0:
    digs,pos=map(int,line.split());T+=20*digs
    trace.append({'command':c,'placement_m':pos,'T_m':T})
   else: trace.append({'command':c,'T_m':T})
  return T,trace
 bfT,bftrace=trench(bf_lines,commands)
 targetT,targettrace=trench(target_lines,commands)
 assert targetT==best and bfT==40,(targetT,best,bfT)
 ratio=[];bt=tt=0
 for i,(c,pos,line) in enumerate(zip(prefix,positions,bf_lines),1):
  if c>0:
   digs,_=map(int,line.split());bt+=20*digs
   tt=max(tt,((pos+c+19)//20)*20)
  ratio.append({'step':i,'T_target_m':tt,'T_plain_BF_m':bt,'ratio':tt/bt if bt else 1})
 maxratio=max(x['ratio'] for x in ratio)
 assert maxratio<=1.25
 payload={
  "title": "Cumulative-quiet Open2 geometry grave for release-v5",
  "scope": "Local diagnostic only; frozen target and platform untouched.",
  "target": {
   "version": "release-v5",
   "source": str((TARGET/"solution.cpp").relative_to(ROOT)),
   "source_sha256": sha(TARGET/"solution.cpp"),
   "binary": str((TARGET/"solver").relative_to(ROOT)),
   "binary_sha256": sha(TARGET/"solver"),
   "runtime_guard": "At first command beyond all matching Open15 tapes, replay is invalidated; subsequent additions use Best-Fit from current physical state."
  },
  "test": {"file": str(TEST.relative_to(ROOT)), "sha256": sha(TEST), **testmeta, "commands": commands},
  "shared_prefix": {
   "open_case": 2,
   "open_input": "data/pipes/open/2.in",
   "open_input_sha256": sha(ROOT/"data/pipes/open/2.in"),
   "prefix_length": len(prefix),
   "commands": prefix,
   "decoded_target_positions_m": positions,
   "matching_open_tables": matching,
   "first_suffix_command": suffix[0] if suffix else None,
   "max_T_target_over_plain_BF": maxratio,
   "per_step": ratio
  },
  "beam": {
   "source": str((OUT/"geometry_beam_search_open2.cpp").relative_to(ROOT)),
   "source_sha256": sha(OUT/"geometry_beam_search_open2.cpp"),
   "configuration": {"beam_width": 128, "depth_limit": 500, "time_limit_s": 55},
   "state_file": str(STATE.relative_to(ROOT)),
   "state_file_sha256": sha(STATE),
   "result_file": str(RESULT.relative_to(ROOT)),
   "result_file_sha256": sha(RESULT),
   "optimized_target_T_m": best,
   "beam_suffix_command_count": len(suffix)
  },
  "expected_comparison_from_causal_allocator_probe": {
   "probe": str(PROBE.relative_to(ROOT)),
   "probe_sha256": sha(PROBE),
   "plain_best_fit": {
    "final_trench_m": bfT,
    "final_live_volume_m": testmeta["final_occupied_length_m"],
    "KPI": testmeta["final_occupied_length_m"]/bfT,
    "trace": bftrace
   },
   "release_v5_replay_then_fallback": {
    "final_trench_m": targetT,
    "final_live_volume_m": testmeta["final_occupied_length_m"],
    "KPI": testmeta["final_occupied_length_m"]/targetT,
    "trace": targettrace,
    "probe_stderr": target_err
   },
   "target_KPI_ratio_to_plain_BF": bfT/targetT
  },
  "mechanism": "Open2 target tape ends at T=20 with a tightly packed 20 m layout. Causal BF on the same 18-command prefix is at T=40 with different free-gap geometry. The bounded suffix keeps BF at T=40 while exact-prefix replay has already fallen back; cumulative prefix T ratio remains <=1.25.",
  "verification_boundary": "Command validity and KPI were checked with pipes_harness.parse_test and the causal diagnostic allocator probe. Coordinating agent performs official-interactor final verification."
 }
 PROV.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'test':str(TEST),'test_sha256':sha(TEST),'provenance':str(PROV),'commands':len(commands),'prefix_max_ratio':maxratio,'plain_BF_T':bfT,'target_T':targetT,'BF_KPI':testmeta['final_occupied_length_m']/bfT,'target_KPI':testmeta['final_occupied_length_m']/targetT,'last_target_response':targettrace[-1]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
