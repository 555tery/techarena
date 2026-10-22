from pathlib import Path
import hashlib,inspect,json,random,sys
sys.path.insert(0,'/tmp')
import pipes_o0_evaluate_20261022 as ev
from pipes_o0_fresh_20261022 import generate
specs=[dict(profile=profile,warmup=warmup,seed=2026102281+index*2+side) for index,profile in enumerate(['uniform_fifo','uniform_random','phase_fifo_lifo','heavy_tail_lifetimes']) for side,warmup in enumerate([1024,65536])]
code=inspect.getsource(generate).replace('def generate(profile,seed):','def generate(profile,seed,warmup=20000):').replace('range(20000)','range(warmup)').replace('range(90000)','range((200000-warmup)//2)').replace('len(active)==20000','len(active)==warmup')
ns={'random':random};exec(compile(code,'frozen-holdout-generator','exec'),ns)
E=ev.EXP;known=[json.loads(s) for s in(E/'records.jsonl').open()]
metas=[r['meta']for r in known if r.get('type')=='holdout_input']
if not metas:
 out=E/'holdout';out.mkdir(exist_ok=True)
 with(E/'records.jsonl').open('a')as f:f.write(json.dumps(dict(type='holdout_protocol',role='final independent validation; freeze exact424b... and balancedf309... before reading holdout responses; no subsequent policy tuning',specs=specs,generator_code=code))+'\n')
 for i,spec in enumerate(specs):
  commands,meta=ns['generate'](**spec);path=out/f'{i+1:02d}-{spec["profile"]}-{spec["warmup"]}.in';path.write_text('1\n200000\n'+'\n'.join(map(str,commands))+'\n')
  meta.update(id=f'holdout-o0-{i+1:02d}',family=spec['profile'],seed=spec['seed'],warmup=spec['warmup'],test_file=str(path),test_sha256=hashlib.sha256(path.read_bytes()).hexdigest());metas.append(meta)
  with(E/'records.jsonl').open('a')as f:f.write(json.dumps(dict(type='holdout_input',meta=meta))+'\n')
 print('HOLDOUT_FROZEN',len(metas),flush=True)
if sys.argv[1:]==['generate']:sys.exit()
for i,meta in enumerate(metas):
 refs=[r for r in known if r.get('type')=='evaluation'and r.get('suite')=='final-holdout'and r.get('kind')=='baseline'and r.get('id')==meta['id']]
 reference=refs[-1]if refs else ev.run(meta,'baseline','final-holdout')
 meta['response_sha256']=reference['response_sha256'];meta['kpi']=reference['kpi'];meta['trench_length_m']=reference['trench_length_m']
 kinds=sys.argv[1:]or['exact','paced-balanced']
 for kind in(kinds if i%2==0 else list(reversed(kinds))):
  if any(r.get('type')=='evaluation'and r.get('suite')=='final-holdout'and r.get('kind')==kind and r.get('id')==meta['id']for r in known):continue
  ev.run(meta,kind,'final-holdout')
