from pathlib import Path
import hashlib,json,random,sys
sys.path.insert(0,'/tmp');from pipes_reservations_20261022 import Stream
E=Path('/Users/555tery/techarena/prototypes/pipes_guard_generalization_20261022');P=E/'input_manifest.jsonl'
def sha(b):return hashlib.sha256(b).hexdigest()
specs=[dict(split=split,index=i,block=b,seed=202610227100+(100 if split=='final'else 0)+i)for split,bs in [('calibration',[157,683,2137,5189]),('final',[239,919,3301,7121])]for i,b in enumerate(bs)]
with P.open('a')as f:f.write(json.dumps(dict(type='small_reserve_generation_freeze',specs=specs,generator_sha256=sha(Path(__file__).read_bytes()),generator_code=Path(__file__).read_text(),before_any_solver_evaluation=True,note='M denotes block count; background2*M placements20m, not 100000; final has3..5 preparation stages, oddcounts and deletions during interrupted reserve; no future or outputs read'))+'\n')
known=[json.loads(s)for s in P.open()];hashes={r['test_sha256']for r in known if r.get('type')=='input'};cmdhashes={r['command_sha256']for r in known if r.get('type')=='input'}
for spec in specs:
 final=spec['split']=='final';i=spec['index'];b=spec['block'];rng=random.Random(spec['seed']);s=Stream()
 for _ in range(2*b):s.add(20)
 start=[3,4,5,7][i];step=[1,2,1,3][i];stages=(3+i%3)if final else 2
 for stage in range(stages):s.run(start+step*stage,b,parity=0)
 n=start+step*stages;assert n<=40
 partial=[1,2,3,b-1][i]
 added=[]
 for _ in range(partial):added.append(s.add(n))
 if final and i==2:
  s.delete(added[0]);s.add(n);s.add(n)
 if i%2==0:
  excursion=min(40,n+2)
  for _ in range(29 if final else 17):s.add(excursion)
  if final:s.add(n)
 commands=s.commands;op=len(commands);assert op<=200000 and s.occupied/(20*((s.peak+19)//20))>=.85
 raw=('1\n'+str(op)+'\n'+'\n'.join(map(str,commands))+'\n').encode();h=sha(raw);ch=sha(('\n'.join(map(str,commands))+'\n').encode());assert h not in hashes and ch not in cmdhashes
 pid=0;active={};live=peak=0
 for c in commands:
  if c>0:pid+=1;active[pid]=c;live+=c;peak=max(peak,live)
  else:live-=active.pop(-c)
 assert (live,peak)==(s.occupied,s.peak)
 ident=f'{spec["split"]}-small-reserve-{i+1:02d}';path=E/'inputs'/f'{ident}.in';path.write_bytes(raw)
 row=dict(type='input',id=ident,split=spec['split'],stratum='small_reserve',family='causal_partial_cohort_reserve',seed=spec['seed'],test_file=str(path),test_sha256=h,command_sha256=ch,weight=1.,operation_count=op,placement_count=len(s.lengths)-1,final_occupied_length_m=s.occupied,peak_live_pipe_length_m=s.peak,minimum_trench_lower_bound_m=20*((s.peak+19)//20),kpi_upper_bound_from_live_volume=s.occupied/(20*((s.peak+19)//20)),parameters=dict(block=b,initial_background_count=2*b,preparation_stages=stages,interrupted_length=n,partial_count=partial))
 with P.open('a')as f:f.write(json.dumps(row)+'\n')
 hashes.add(h);cmdhashes.add(ch)
print('ADDED small reserve4calibration+4final; total inputs',len(hashes),flush=True)
