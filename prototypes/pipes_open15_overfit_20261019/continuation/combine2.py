import json
from runtime import ROOT,PARENT,e
from export import export
plans={str(i):str(ROOT/'conditioned-plans'/str(i)/'best.txt') for i in range(1,16)}
plans.update({'11':str(PARENT/'future/1/11.txt'),'13':str(ROOT/'case13/positions.txt'),'8':str(ROOT/'refined/8/best.txt'),'15':str(ROOT/'refined/15/best.txt')})
e.save(ROOT/'mapping-v2.json',plans);export(plans,ROOT/'release-v2')
# Prepare one monotone compaction preserving the global prefix graph.
j=json.loads((PARENT/'joint.json').read_text());pos={}
for c in j['cases']:
 vals=iter(map(int,open(plans[str(c['case'])]).read().split()))
 for cmd,bid in zip(c['commands'],c['block_ids']):
  if cmd>0:
   x=next(vals)
   assert bid not in pos or pos[bid]==x;pos[bid]=x
out=ROOT/'joint-compaction-v2';out.mkdir()
with (out/'problem.txt').open('w') as f:
 f.write(f"{len(j['blocks'])} {j['time_count']} {len(j['cases'])}\n")
 for c in j['cases']:f.write(f"{c['weight']} {c['F']}\n")
 for i,b in enumerate(j['blocks']):
  f.write(f"{b['length']} {pos[i]} {b['first']} {len(b['intervals'])}\n")
  for span in b['intervals']:f.write(' '.join(map(str,span))+'\n')
assert e.invoke([str(PARENT/'pack-v2'),str(out/'problem.txt'),str(out/'positions.txt'),'1'],out,'run.log',300)==0
print((out/'run.log').read_text(),flush=True)
