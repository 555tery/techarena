#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,copy,argparse
from generate_checks import generate as general_generate
from generate_lifo_checks import generate as lifo_generate
P=Path(__file__).resolve().parent;D=P/'fresh_checks/lp_sealed'

def plan():
    rows=[]
    for family in ['sealed','lifo_sealed','lifo_large_sealed']:
        old=json.loads((P/'fresh_checks'/family/'design.json').read_text())
        for item in old.get('specs',old.get('cases',[])):
            spec=copy.deepcopy(item);key='id' if 'id' in spec else 'name';spec[key]='lp_'+spec[key]
            spec['seed']^=0x915C742D
            rows.append(dict(generator=('general' if key=='id' else 'lifo'),spec=spec))
    return dict(purpose='Fresh independent seeds for a possible packing-dual candidate; design pinned before its first result. Original heldout now counts as prior evidence, not new confirmation.',cases=rows,generator_sha256={name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in ['generate_checks.py','generate_lifo_checks.py']})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare-only',action='store_true');args=ap.parse_args();D.mkdir(exist_ok=True);m=plan();data=(json.dumps(m,indent=2)+'\n').encode();f=D/'design.json'
    if f.exists():assert f.read_bytes()==data
    else:f.write_bytes(data)
    if args.prepare_only:print(json.dumps(dict(status='design_only',cases=len(m['cases']),sha256=hashlib.sha256(data).hexdigest())));return
    out=[]
    for row in m['cases']:
        spec=row['spec'];name=spec.get('id',spec.get('name'));ops=(general_generate if row['generator']=='general' else lifo_generate)(spec);text='1 '+str(len(ops))+'\n'+'\n'.join(map(str,ops))+'\n0\n';dest=D/(name+'.in');assert not dest.exists();dest.write_text(text);out.append(dict(name=name,sha256=hashlib.sha256(text.encode()).hexdigest()))
    (D/'manifest.json').write_text(json.dumps(dict(design_sha256=hashlib.sha256(data).hexdigest(),cases=out),indent=2)+'\n');print(json.dumps(dict(status='generated',cases=len(out))))
if __name__=='__main__':main()
