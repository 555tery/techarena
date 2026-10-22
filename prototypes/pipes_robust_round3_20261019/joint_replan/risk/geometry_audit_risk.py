#!/usr/bin/env python3
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent; REPO=HERE.parents[3]
prov=json.loads((HERE/'geometry_risk_provenance.json').read_text())
pair=json.loads((HERE.parent/'geometry_pair_provenance.json').read_text())
ids=pair['block_ids']; dense={b:i for i,b in enumerate(ids)}
pos=list(map(int,(HERE/'geometry_risk.positions').read_text().split())); assert len(pos)==len(ids)
j=json.loads((REPO/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
trace=[]
with (HERE/'geometry_pair_risk.trace').open() as f:
 assert int(f.readline())==2
 for _ in range(2):
  n=int(f.readline());trace.append([tuple(map(int,f.readline().split())) for __ in range(n)])
results=[];allocfiles={}
for ci,goal in [(7,4640),(12,3220)]:
 c=j['cases'][ci]; active={}; occupied=set();pid=0;peak=0;alloc=[]; overlaps=[]
 for ti,(cmd,bid) in enumerate(zip(c['commands'],c['block_ids'])):
  if cmd>0:
   pid+=1; assert bid in dense
   x=pos[dense[bid]]
   for y in range(x,x+cmd):
    if y in occupied:overlaps.append((ti,pid,y))
    occupied.add(y)
   active[pid]=(x,cmd,bid);peak=max(peak,x+cmd);alloc.append(x)
  else:
   q=-cmd;assert q in active,(ci,ti,q)
   x,n,_=active.pop(q)
   for y in range(x,x+n):assert y in occupied,(ci,ti,q,y);occupied.remove(y)
 T=20*((peak+19)//20);assert not overlaps and T==goal,(ci,T,goal,overlaps[:1])
 out=HERE/f'geometry_risk_open{ci+1}.positions';out.write_text('\n'.join(map(str,alloc))+'\n');allocfiles[str(ci+1)]={'path':str(out.relative_to(REPO)),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'allocations':len(alloc)}
 # Full per-command cumulative risk using precomputed causal BF trace.
 T=0;maxr=0.;sumr=0.;summ=0;peakrow=None;traj=[]
 for step,(item,bfrow) in enumerate(zip(c['commands'],trace[0 if ci==7 else 1]),1):
  block,size,bfT=bfrow
  if item>0:
   assert block==dense[c['block_ids'][step-1]] and size==item
   T=max(T,20*((pos[block]+size+19)//20))
  else: assert block==-1 and size==0
  r=T/bfT;traj.append((T,bfT,r));sumr+=max(0.,r-1.);summ+=max(0,T-bfT)
  if r>maxr:maxr=r;peakrow={'step':step,'command':item,'T':T,'BF_T':bfT,'ratio':r}
 results.append({'case':ci+1,'target_T':goal,'candidate_T':T,'peak_endpoint':peak,'max_full_cumulative_T_over_BF':maxr,'at':peakrow,'integrated_positive_ratio_excess':sumr,'integrated_positive_meter_excess':summ,'physical_replay_valid':True,'remaining_live_pipes':len(active),'positions_file':allocfiles[str(ci+1)]})
# Common-prefix identity and positions.
assert j['cases'][7]['commands'][:388]==j['cases'][12]['commands'][:388]
common_alloc=0
for ti in range(388):
 if j['cases'][7]['commands'][ti]>0:
  a=j['cases'][7]['block_ids'][ti];b=j['cases'][12]['block_ids'][ti];assert a==b and pos[dense[a]]==pos[dense[b]];common_alloc+=1
assert common_alloc==210
shared_excess=0.;T=0
for item,(block,size,bfT) in zip(j['cases'][7]['commands'][:388],trace[0][:388]):
 if item>0:T=max(T,20*((pos[block]+size+19)//20))
 shared_excess+=max(0.,T/bfT-1.)
dedup=sum(r['integrated_positive_ratio_excess'] for r in results)-shared_excess
old=prov['before_risk_metrics'];src=prov['release_source_metrics']
report={'candidate_positions':str((HERE/'geometry_risk.positions').relative_to(REPO)),'candidate_sha256':hashlib.sha256((HERE/'geometry_risk.positions').read_bytes()).hexdigest(),'pair':[8,13],'common_prefix_commands':388,'common_prefix_allocations':common_alloc,'first_five_shared_positions':[pos[dense[j['cases'][7]['block_ids'][i]]] for i,c in enumerate(j['cases'][7]['commands']) if i<388 and c>0][:5],'previous_candidate_first_five':[20,0,2144,26,522],'source_table_first_five':{'decoded':[688,3064,2124,0,496],'solver_stdout_positions':[688,3064,2124,0,496]},'source_global_max_full_ratio':src['global_max_ratio'],'previous_candidate_global_max_full_ratio':old['global_max_ratio'],'candidate_global_max_full_ratio':max(r['max_full_cumulative_T_over_BF'] for r in results),'integrated_ratio_excess_shared_prefix_counted_once':dedup,'previous_candidate_integrated_ratio_excess_shared_prefix_once':old['integrated_ratio_excess_shared_prefix_once'],'candidate_integrated_meter_excess_pair_sum':sum(r['integrated_positive_meter_excess'] for r in results),'previous_candidate_integrated_meter_excess_pair_sum':old['integrated_meter_excess_pair_sum'],'cases':results,'ranking':'200 trials; exact T required; min max full-stream T/BF, then integrated positive ratio excess with shared 388-command prefix counted once, then integrated meter excess, then early shared coordinates.','official_harness_not_run':True,'scope':'Full physical and BF-risk replay for Open8/Open13 only; all other 13 tests not checked.'}
(HERE/'geometry_risk_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
