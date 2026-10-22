from pathlib import Path
import hashlib,json,random,sys
sys.path.insert(0,'/tmp');import pipes_o0_evaluate_20261022 as ev
E=Path('/Users/555tery/techarena/prototypes/pipes_guard_generalization_20261022');P=E/'input_manifest.jsonl'
def sha(b):return hashlib.sha256(b).hexdigest()
specs=[dict(public=p,prefix=plen,n=n,seed=202610228100+4*i+j)for i,p in enumerate([11,8,5,9])for j,(plen,n)in enumerate([(2,200000),(8,1201),(97,10007),(509,200000)])]
known=[json.loads(s)for s in P.open()];assert not any(r.get('type')=='prefix_final_extension_freeze'for r in known)
with P.open('a')as f:f.write(json.dumps(dict(type='prefix_final_extension_freeze',specs=specs,generator_sha256=sha(Path(__file__).read_bytes()),generator_code=Path(__file__).read_text(),role='final-only, no solver evaluations; declared after calibration inputs were observed but before policy selection/final freeze; no changes to policy candidates or gates',no_terminal_fill=True,mechanism='public command prefix then steady multiset renewal, total live volume preserved over each complete delete/add block; length200k can have tiny working set'))+'\n')
hashes={r['command_sha256']for r in known if r.get('type')=='input'}
pubs={r['public_number']:r for r in ev.rows if r.get('public_number')}
for i,spec in enumerate(specs):
 rng=random.Random(spec['seed']);meta=pubs[spec['public']];data=Path(meta['test_file']).read_bytes().split();prefix=list(map(int,data[2:2+spec['prefix']]))
 commands=[];active={};nextpid=0;volume=peak=0
 def add(n):
  global nextpid,volume,peak
  nextpid+=1;active[nextpid]=n;volume+=n;peak=max(peak,volume);commands.append(n)
 def delete(p):
  global volume
  n=active.pop(p);volume-=n;commands.append(-p);return n
 for c in prefix:
  if c>0:add(c)
  else:delete(-c)
 target=max(200,peak)+80
 while volume<target:add(rng.choice([2,3,5,7,11,19,29,37]))
 # Initial steady-operation population is followed by renewal throughout,
 # rather than any padding appended to the end of a low-load stream.
 steady_volume=volume;renew=0
 while len(commands)<spec['n']:
  remain=spec['n']-len(commands)
  if remain==1:add(rng.choice([3,13,31]));break
  batch=min([1,3,5,7][i%4],remain//2,max(1,len(active)-1))
  pool=[p for p in active if p>2]or list(active)
  batch=min(batch,len(pool));chosen=(sorted(pool)[:batch]if renew%3==0 else rng.sample(pool,batch))
  lengths=[delete(p)for p in chosen];rng.shuffle(lengths)
  for n in lengths:add(n)
  assert volume==steady_volume;renew+=1
 assert len(commands)==spec['n'];rounded=20*((peak+19)//20);assert volume/rounded>=.85
 pid=live=maxlive=0;check={}
 for c in commands:
  if c>0:pid+=1;check[pid]=c;live+=c;maxlive=max(maxlive,live)
  else:live-=check.pop(-c)
 assert (live,maxlive)==(volume,peak)
 body=('\n'.join(map(str,commands))+'\n').encode();h=sha(body);assert h not in hashes;hashes.add(h)
 ident=f'final-prefix-renewal-{i+1:02d}';path=E/'inputs'/f'{ident}.in';raw=('1\n'+str(len(commands))+'\n').encode()+body;path.write_bytes(raw)
 row=dict(type='input',id=ident,split='final',stratum='public_prefix',family='bounded_working_set_renewal',seed=spec['seed'],test_file=str(path),test_sha256=sha(raw),command_sha256=h,weight=1.,operation_count=len(commands),placement_count=pid,final_occupied_length_m=volume,peak_live_pipe_length_m=peak,minimum_trench_lower_bound_m=rounded,kpi_upper_bound_from_live_volume=volume/rounded,parameters=dict(**spec,steady_volume=steady_volume,renewal_blocks=renew,prefix_exactly_preserved=True))
 with P.open('a')as f:f.write(json.dumps(row)+'\n')
print('FROZEN16 additional final-only prefix renewal inputs;8have200kcommands',flush=True)
