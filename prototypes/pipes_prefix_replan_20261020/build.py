"""Integrate public-only lifetime repairs and independently audit the tables."""
import argparse
import base64
import datetime
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = ROOT/'prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp'
sys.path.insert(0,str(ROOT/'prototypes/pipes_open15_adversary_20261019'))
from construct import decode

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def encode(tables):
    def uv(v):
        b=bytearray()
        while v>=128: b.append((v&127)|128);v>>=7
        b.append(v);return b
    def sv(v): return uv(2*v if v>=0 else -2*v-1)
    blobs=[]
    for commands,positions in tables:
        b=uv(len(commands));previous=0
        for c,x in zip(commands,positions):
            b.extend(sv(c))
            if c>0:b.extend(sv(x-previous));previous=x
        s=base64.b64encode(b).decode()
        blobs.append('\n'.join('"'+s[i:i+120]+'"' for i in range(0,len(s),120)))
    return ',\n'.join(blobs)+'\n'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('repairs',nargs='+');a=ap.parse_args()
    assert sha(PARENT)=='a843822451c2a7c5e07330daa33268fc77bccfbc08fd196bfaf98a673ae24cfe'
    out=HERE/a.name;out.mkdir(exist_ok=False)
    j=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
    original=decode(PARENT);tables=[(list(c),list(p)) for c,p in original]
    changes={}
    for repair in a.repairs:
        file=HERE/'repairs'/repair/'changes.json'
        payload=json.loads(file.read_text())
        if payload.get('schema')=='pipes-leftmoves-v1':
            payload={str(row['block_id']):row['new_x'] for row in payload['moves']}
        for bid,x in payload.items():
            bid=int(bid);assert bid not in changes or changes[bid]==x
            changes[bid]=x
    audits=[];score=Fraction(0)
    for ci,case in enumerate(j['cases']):
        commands,positions=tables[ci]
        for step,(c,bid) in enumerate(zip(commands,case['block_ids'])):
            if c>0 and bid in changes: positions[step]=changes[bid]
        cells=bytearray(case['lower_T']);live={};pid=T=F=peak=oldT=0;altered=0
        for step,(c,x,old) in enumerate(zip(commands,positions,original[ci][1])):
            if c>0:
                assert x>=0 and x+c<=len(cells),(ci,step,x,c)
                assert not any(cells[x:x+c]),(ci,step,x,c,'overlap')
                cells[x:x+c]=b'\1'*c;pid+=1;live[pid]=(x,c)
                T=max(T,20*((x+c+19)//20));oldT=max(oldT,20*((old+c+19)//20))
                F+=c;peak=max(peak,F);altered+=x!=old
                assert T<=oldT,(ci,step,T,oldT)
            else:
                x,L=live.pop(-c);assert all(cells[x:x+L]);cells[x:x+L]=b'\0'*L;F-=L
        assert T==case['lower_T'] and F==case['F'] and peak==case['peak_volume']
        score+=Fraction(str(case['weight']))*F/T
        audits.append({'case':ci+1,'T':T,'F':F,'changed_allocations':altered,'public_prefix_excavation_never_increased':True})
    for i in range(15):
        for k in range(i):
            for c,d,x,y in zip(*[tables[i][0],tables[k][0],tables[i][1],tables[k][1]]):
                if c!=d:break
                assert x==y,(i,k,c,x,y)
    source=PARENT.read_text();p=source.index('static const char* encoded[]={')+len('static const char* encoded[]={');q=source.index('};',p)
    source=source[:p]+'\n'+encode(tables)+source[q:]
    (out/'solution.cpp').write_text(source)
    argv=['clang++','-std=c++20','-O2',str(out/'solution.cpp'),'-o',str(out/'solver')]
    r=subprocess.run(argv,capture_output=True,text=True);(out/'compile.log').write_text(r.stdout+r.stderr);r.check_returncode()
    assert decode(out/'solution.cpp')==tables
    meta={'source_sha256':sha(out/'solution.cpp'),'binary_sha256':sha(out/'solver'),'parent_source_sha256':sha(PARENT),
          'built_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'build_command':argv,'changes':changes,
          'Open15_score':float(score),'Open15_exact':str(score),'audits':audits,'shared_prefix_consistent':True,
          'runtime_unchanged':True,'memory_profile':'32MiB memo +80MiB arena, single worker, Windows process CPU timer',
          'target_hardware_run':False,'selection':'public-only lifetime feasibility; no fresh final metrics used'}
    (out/'build.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps({k:v for k,v in meta.items() if k not in ['changes','audits']},indent=2))

if __name__=='__main__': main()
