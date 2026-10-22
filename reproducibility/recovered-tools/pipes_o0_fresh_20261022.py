from pathlib import Path
import hashlib,json,random,sys
sys.path.insert(0,'/tmp')
import pipes_o0_evaluate_20261022 as ev
PROFILES=['uniform_fifo','uniform_random','short_fifo','long_fifo','alternating_ends','phase_fifo_lifo','bimodal_long_survive','bimodal_short_survive','coalescing_blocks','size_bursts','heavy_tail_lifetimes','uniform_lifo']
def generate(profile,seed):
 rng=random.Random(seed);commands=[];lengths=[0];active=[];position={};oldest=1;occupied=0;peak=0;pending=[]
 def new_length():
  pid=len(lengths)
  if profile=='short_fifo':return rng.randint(1,12)
  if profile=='long_fifo':return rng.randint(24,40)
  if profile.startswith('bimodal_'):return rng.choice([8,32])
  if profile=='size_bursts':return 1+(pid//256)%40
  return rng.randint(1,40)
 def add(length):
  nonlocal occupied,peak
  pid=len(lengths);lengths.append(length);position[pid]=len(active);active.append(pid);commands.append(length);occupied+=length;peak=max(peak,occupied)
 for _ in range(20000):
  size=32 if profile=='bimodal_long_survive' else 8 if profile=='bimodal_short_survive' else new_length()
  add(size)
 for cycle in range(90000):
  if profile in ['uniform_fifo','short_fifo','long_fifo'] or profile=='phase_fifo_lifo' and (cycle//15000)%3==0 or profile=='alternating_ends' and (cycle//128)%2==0:
   while oldest not in position:oldest+=1
   pid=oldest
  elif profile=='uniform_lifo' or profile=='phase_fifo_lifo' and (cycle//15000)%3==1 or profile=='alternating_ends' or profile=='heavy_tail_lifetimes' and rng.random()<0.9:
   pid=len(lengths)-1
   while pid not in position:pid-=1
  elif profile.startswith('bimodal_'):
   choices=[rng.choice(active) for _ in range(8)]
   pid=min(choices,key=lambda p:lengths[p]) if profile=='bimodal_long_survive' else max(choices,key=lambda p:lengths[p])
  elif profile=='coalescing_blocks':
   while pending and pending[-1] not in position:pending.pop()
   if not pending:
    center=rng.choice(active);pending=sorted((p for p in range(max(1,center-64),min(len(lengths),center+65)) if p in position),reverse=True)
   pid=pending.pop()
  else:pid=rng.choice(active)
  commands.append(-pid);occupied-=lengths[pid]
  index=position.pop(pid);last=active.pop()
  if index<len(active):active[index]=last;position[last]=index
  add(new_length())
 assert len(commands)==200000 and len(active)==20000
 minimum=((peak+19)//20)*20;bound=occupied/minimum
 assert bound>=0.85,(profile,bound)
 return commands,dict(operation_count=200000,weight=1.0,placement_count=len(lengths)-1,peak_live_pipe_length_m=peak,minimum_trench_lower_bound_m=minimum,final_occupied_length_m=occupied,kpi_upper_bound_from_live_volume=bound)
if __name__=='__main__':
 exp=ev.EXP;out=exp/'fresh';out.mkdir(exist_ok=True)
 known=[json.loads(s) for s in (exp/'records.jsonl').open()]
 metas=[r['meta'] for r in known if r.get('type')=='fresh_input']
 if not metas:
  with(exp/'records.jsonl').open('a')as f:f.write(json.dumps(dict(type='fresh_protocol',operations=200000,live_count=20000,profiles=PROFILES,seeds=[2026102201+i for i in range(len(PROFILES))],independent_of='no Open15 prefixes, source code, responses or placements used',generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))+'\n')
  for i,profile in enumerate(PROFILES):
   seed=2026102201+i;commands,meta=generate(profile,seed);path=out/f'{i+1:02d}-{profile}.in';path.write_text('1\n200000\n'+'\n'.join(map(str,commands))+'\n')
   meta.update(id=f'fresh-o0-{i+1:02d}',family=profile,seed=seed,test_file=str(path),test_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
   metas.append(meta)
   with(exp/'records.jsonl').open('a')as f:f.write(json.dumps(dict(type='fresh_input',meta=meta))+'\n')
  print('FROZEN',len(metas),flush=True)
 if sys.argv[1:] and sys.argv[1]=='generate':sys.exit()
 for i,meta in enumerate(metas):
  references=[r for r in known if r.get('type')=='evaluation' and r.get('suite')=='new-independent' and r.get('kind')=='baseline' and r.get('id')==meta['id']]
  if references:
   reference=references[-1]
  elif sys.argv[1:]==['generate']:continue
  else:reference=ev.run(meta,'baseline','new-independent')
  meta['response_sha256']=reference['response_sha256'];meta['kpi']=reference['kpi'];meta['trench_length_m']=reference['trench_length_m']
  kinds=[k for k in (sys.argv[1:] or ['combined']) if k!='baseline']
  for kind in (kinds if i%2==0 else list(reversed(kinds))):
   if any(r.get('type')=='evaluation' and r.get('suite')=='new-independent' and r.get('kind')==kind and r.get('id')==meta['id'] for r in known):continue
   ev.run(meta,kind,'new-independent')
