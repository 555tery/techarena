#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
prov=json.loads((HERE/'geometry_pair_provenance.json').read_text())
pos_file=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'geometry_tie.positions'
if not pos_file.is_absolute(): pos_file=REPO/pos_file
ids=prov['block_ids']; xs=list(map(int,pos_file.read_text().split()))
assert len(ids)==len(xs)
byid=dict(zip(ids,xs))
j=json.loads((REPO/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
results=[]
for ci,target in [(7,4640),(12,3220)]:
 c=j['cases'][ci]; cmds=c['commands']; bids=c['block_ids']; active={}; pid=0; used=set(); peak=0; overlaps=[]; allocrows=[]
 for t,(cmd,bid) in enumerate(zip(cmds,bids)):
  if cmd>0:
   pid+=1; assert bid in byid,(ci,t,bid)
   x=byid[bid]; assert x>=0
   for y in range(x,x+cmd):
    if y in used: overlaps.append((t,pid,y))
    used.add(y)
   active[pid]=(x,cmd,bid); peak=max(peak,x+cmd)
   allocrows.append((t,cmd,x,bid))
  else:
   q=-cmd; assert q in active,(ci,t,q)
   x,size,b=active.pop(q)
   for y in range(x,x+size):
    assert y in used,(ci,t,q,y)
    used.remove(y)
 # Final live allocations are permitted in the input; retain their occupancy for peak validation.
 T=20*((peak+19)//20)
 assert not overlaps,(ci,overlaps[:5])
 assert T==target,(ci,T,target)
 results.append({'case':ci+1,'allocations':len(allocrows),'peak_end':peak,'T':T,'target_T':target,'valid_physical_replay':True,'first_alloc_positions':[x[2] for x in allocrows[:5]],'allocation_position_sha256':hashlib.sha256((' '.join(str(x[2]) for x in allocrows)).encode()).hexdigest()})
ca,cb=[j['cases'][x] for x in [7,12]]
assert ca['commands'][:388]==cb['commands'][:388]
common=[]
for idx in range(388):
 if ca['commands'][idx]>0:
  ida,idb=ca['block_ids'][idx],cb['block_ids'][idx]
  assert ida==idb,(idx,ida,idb)
  assert byid[ida]==byid[idb]
  common.append((ida,byid[ida]))
assert len(common)==210
report={'candidate_positions':str(pos_file.relative_to(REPO)),'candidate_sha256':hashlib.sha256(pos_file.read_bytes()).hexdigest(),'pair':[8,13],'common_prefix_commands':388,'common_prefix_allocations':len(common),'prefix_allocations_shared_positions':True,'first_two_common_positions':[common[0][1],common[1][1]],'original_first_two_positions':prov['seeds'][:2],'reduction_second_allocation':prov['seeds'][1]-common[1][1],'cases':results,'method':'independent physical byte-occupancy replay from full Open8/Open13 command streams; lifetime conflict model separately enforced by pair packer','official_harness_not_run':True}
(HERE/'geometry_pair_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
