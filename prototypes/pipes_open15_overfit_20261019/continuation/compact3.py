import json
from runtime import ROOT,PARENT,e
plans=json.loads((ROOT/"mapping-v3.json").read_text())
# Prepare one monotone compaction preserving the global prefix graph.
j=json.loads((PARENT/'joint.json').read_text());pos={}
for c in j['cases']:
 vals=iter(map(int,open(plans[str(c['case'])]).read().split()))
 for cmd,bid in zip(c['commands'],c['block_ids']):
  if cmd>0:
   x=next(vals)
   assert bid not in pos or pos[bid]==x;pos[bid]=x
out=ROOT/'joint-compaction-v3';out.mkdir()
with (out/'problem.txt').open('w') as f:
 f.write(f"{len(j['blocks'])} {j['time_count']} {len(j['cases'])}\n")
 for c in j['cases']:f.write(f"{c['weight']} {c['F']}\n")
 for i,b in enumerate(j['blocks']):
  f.write(f"{b['length']} {pos[i]} {b['first']} {len(b['intervals'])}\n")
  for span in b['intervals']:f.write(' '.join(map(str,span))+'\n')
assert e.invoke([str(PARENT/'pack-v2'),str(out/'problem.txt'),str(out/'positions.txt'),'1'],out,'run.log',300)==0
print((out/'run.log').read_text(),flush=True)
