from pathlib import Path
import json,csv,subprocess,hashlib
HERE=Path(__file__).resolve().parent;OLD=HERE.parents[1]/'pipes_online_core_20261020';losses=json.load(open(HERE/'losses.json'));checks=[]
for c in losses:
 tokens=Path(c['input_path']).read_text().split();commands=list(map(int,tokens[2:2+int(tokens[1])]))
 for name in ['baseline','current','no_dp','mc_off_dp','fresh','legacy_tie']:
  rows=list(csv.DictReader(open(HERE/f"{c['id']}-{name}.csv")));cells=bytearray();pipes=[None];T=0;replies=[]
  for cmd,row in zip(commands,rows):
   if cmd>0:
    x,d=int(row['x']),int(row['dig']);assert d>=0 and x>=0;T+=d;assert x+cmd<=T<=100000000
    if T>len(cells):cells.extend(b'\0'*(T-len(cells)))
    assert not any(cells[x:x+cmd]),(c['id'],name,row)
    cells[x:x+cmd]=b'\1'*cmd;pipes.append((x,cmd));replies.append(f'{d//20} {x}')
   else:
    x,n=pipes[-cmd];assert n>0 and all(cells[x:x+n]);cells[x:x+n]=b'\0'*n;pipes[-cmd]=(x,0);replies.append(str(x))
   assert T==int(row['T'])
  assert len(rows)==len(commands)
  parity=None
  if name in ['baseline','current']:
   binary=OLD/('candidates/baseline/solver'if name=='baseline'else'candidates/primal_recent/solver')
   result=subprocess.run([str(binary)],input=('\n'.join(map(str,commands+[0]))+'\n').encode(),capture_output=True,check=True)
   assert result.stdout==('\n'.join(replies)+'\n').encode(),(c['id'],name,'instrumentation changed output')
   parity=True
  checks.append({'case':c['id'],'diagnostic':name,'occupancy_valid':True,'original_stdout_byte_parity':parity})
(HERE/'verification.json').write_text(json.dumps({'n':len(checks),'all_valid':True,'original_parity_runs':46,'scope':'23 observed losses, six diagnostic variants, no official harness','checks':checks},indent=2)+'\n')
print('138 occupancy trajectories valid; 46 original baseline/current stdout byte parity checks passed')
