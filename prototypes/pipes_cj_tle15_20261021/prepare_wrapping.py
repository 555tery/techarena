#!/usr/bin/env python3
from pathlib import Path
import re,json,hashlib
HERE=Path(__file__).resolve().parent;s=(HERE/'candidate-io/solution.cj').read_text();lines=s.splitlines(keepends=True)
allowed={'FastIntVector','FastKeyVector','OrderedMap','IntOrderedMap','Ring','IntRing','LengthHistory','Allocator'}
current=None;changed=[];out=[]
for line in lines:
 m=re.match(r'(?:public )?class (\w+)',line)
 if m:current=m[1]
 if current in allowed and re.match(r'    (?:(?:public|private) )?(?:operator )?func ',line):
  if not out or out[-1].strip()!='@OverflowWrapping':
   out.append('    @OverflowWrapping\n');changed.append(dict(class_name=current,method=line.strip().split('{')[0].strip()))
 out.append(line)
s2=''.join(out);d=HERE/'candidate-wrapping';d.mkdir(exist_ok=True);(d/'solution.cj').write_text(s2)
assert s2.replace('    @OverflowWrapping\n','')==s.replace('    @OverflowWrapping\n','')
(d/'source.json').write_text(json.dumps(dict(base_sha256=hashlib.sha256(s.encode()).hexdigest(),source_sha256=hashlib.sha256(s2.encode()).hexdigest(),changes='Function-local integer overflow guards omitted only in bounded numeric allocator/container methods; same explicit validity checks remain. IEEE operations unchanged. Legal domain<=200000 commands, lengths<=40; generated annotation diff only.',annotated_methods=changed),indent=2)+'\n')
print('added',len(changed),'annotations')
