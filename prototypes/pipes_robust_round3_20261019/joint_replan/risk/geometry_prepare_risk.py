#!/usr/bin/env python3
import sys
sys.dont_write_bytecode=True
import json,subprocess,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
# Reuse the project's established table decoder without changing its cache.
sys.path.insert(0,str(REPO/'prototypes/pipes_open15_adversary_20261019'))
from construct import decode
SRC=REPO/'prototypes/pipes_robust_round2_20261019/final/solution.cpp'
BIN=REPO/'prototypes/pipes_robust_round2_20261019/final/solver'
J=json.loads((REPO/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
PROV=json.loads((HERE.parent/'geometry_pair_provenance.json').read_text())
block_ids=PROV['block_ids']; dense={bid:i for i,bid in enumerate(block_ids)}
old=list(map(int,(HERE/'geometry_before_risk.positions').read_text().split()))
assert len(old)==len(block_ids)
tables=decode(SRC)
traces={};actual_positions={};first_allocations={};source_byid={}
for ci in (7,12):
 case=J['cases'][ci]; commands=case['commands']; alloc_positions=tables[ci][1]
 assert tables[ci][0]==commands
 assert case['input_sha256']==hashlib.sha256((REPO/f"data/pipes/open/{ci+1}.in").read_bytes()).hexdigest()
 # Run the frozen source binary directly on the raw operation stream and compare its physical outputs with the decoded table.
 out=subprocess.run([str(BIN)],input='\n'.join(map(str,commands+[0]))+'\n',text=True,capture_output=True,check=True,timeout=20)
 lines=out.stdout.splitlines(); assert len(lines)==len(commands),(ci,len(lines),len(commands))
 pids=0; seen=[]
 for ti,(cmd,line,decoded_pos) in enumerate(zip(commands,lines,alloc_positions)):
  parts=list(map(int,line.split()))
  if cmd>0:
   assert len(parts)==2
   pids+=1; x=parts[1]; assert x==decoded_pos,(ci,pids,x,decoded_pos)
   bid=case['block_ids'][ti]; assert bid in dense
   if bid in source_byid: assert source_byid[bid]==x,(bid,source_byid[bid],x)
   source_byid[bid]=x
   seen.append(x)
  else: assert len(parts)==1 and decoded_pos is None
 actual_positions[ci+1]=seen
 # Causal BF traces from the existing bestfit probe. Only allocations change T.
 inp='\n'.join(map(str,commands+[0]))+'\n'
 bf=subprocess.run([str(REPO/'prototypes/pipes_prefix_shock_20261019/allocator-probe'),'bestfit',str(REPO/'prototypes/pipes_prefix_shock_20261019/tape.txt')],input=inp,text=True,capture_output=True,check=True,timeout=30)
 bl=bf.stdout.splitlines(); assert len(bl)==len(commands)
 Tbf=0; rows=[]
 for cmd,bid,line in zip(commands,case['block_ids'],bl):
  if cmd>0:
   assert bid in dense
   Tbf+=20*int(line.split()[0]); rows.append((dense[bid],cmd,Tbf))
  else: rows.append((-1,0,Tbf))
 traces[ci+1]=rows
 first_allocations[ci+1]={'decoded_first5': [x for c,x in zip(commands,alloc_positions) if c>0][:5], 'source_stdout_first5':seen[:5], 'source_stderr':out.stderr.strip()}
# shared first 388 operation rows coincide including BF timeline and single joint coordinates
assert J['cases'][7]['commands'][:388]==J['cases'][12]['commands'][:388]
assert traces[8][:388]==traces[13][:388]
for t in range(388):
 if J['cases'][7]['commands'][t]>0:
  assert J['cases'][7]['block_ids'][t]==J['cases'][12]['block_ids'][t]
# Serialize risk traces: number of cases, then number of steps, then block-index,size,BF-T rows.
riskfile=HERE/'geometry_pair_risk.trace'
with riskfile.open('w') as f:
 f.write('2\n')
 for case in (8,13):
  f.write(str(len(traces[case]))+'\n')
  for row in traces[case]:f.write('%d %d %d\n'%row)

def metrics(pos):
 report={};allrat=[];percase=[]
 for case in (8,13):
  T=0;maxr=0.;sumr=0.;summ=0;peakrow=None
  for step,(bid,size,bfT) in enumerate(traces[case],1):
   if bid>=0:T=max(T,20*((pos[bid]+size+19)//20))
   ratio=T/bfT
   if ratio>maxr:maxr=ratio;peakrow={'step':step,'T':T,'BF_T':bfT,'ratio':ratio}
   sumr+=max(0.,ratio-1.);summ+=max(0,T-bfT)
  report[str(case)]={'max_ratio':maxr,'integrated_ratio_excess':sumr,'integrated_meter_excess':summ,'at':peakrow,'final_T':T}
  allrat.append(maxr);percase.append((sumr,summ))
 shared=sum(max(0., (lambda T,bf:T/bf-1)(0,1)) for _ in [])
 # Integrated risk counts shared prefix once.
 shared_sum=0.;T=0
 for bid,size,bfT in traces[8][:388]:
  if bid>=0:T=max(T,20*((pos[bid]+size+19)//20))
  shared_sum+=max(0.,T/bfT-1.)
 dedup=sum(x[0] for x in percase)-shared_sum
 return {'cases':report,'global_max_ratio':max(allrat),'integrated_ratio_excess_pair_sum':sum(x[0] for x in percase),'integrated_ratio_excess_shared_prefix_once':dedup,'integrated_meter_excess_pair_sum':sum(x[1] for x in percase)}
oldm=metrics(old)
source_positions=[source_byid[bid] for bid in block_ids]
source_metrics=metrics(source_positions)
meta={'source':str(SRC.relative_to(REPO)),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'binary':str(BIN.relative_to(REPO)),'binary_sha256':hashlib.sha256(BIN.read_bytes()).hexdigest(),'cases':{str(c):{'input_sha256':J['cases'][c-1]['input_sha256'],'first_allocations':first_allocations[c]} for c in (8,13)},'common_prefix':{'commands':388,'allocations':210,'BF_traces_identical':True},'risk_trace':str(riskfile.relative_to(REPO)),'risk_trace_sha256':hashlib.sha256(riskfile.read_bytes()).hexdigest(),'before_risk_positions_sha256':hashlib.sha256((HERE/'geometry_before_risk.positions').read_bytes()).hexdigest(),'release_source_metrics':source_metrics,'before_risk_metrics':oldm,'ranking':'min global max T/BF over every command in both full cases; then integrated positive ratio excess counting the shared 388-command prefix once; then integrated meter excess; then early shared allocation coordinates.'}
(HERE/'geometry_risk_provenance.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({'first_allocations':meta['cases'],'release_source_metrics':source_metrics,'before_risk_metrics':oldm},indent=2))
