"""Independently verify exact public plans, then export an explicitly marked solver."""
import base64,json,hashlib,sys
from fractions import Fraction
from pathlib import Path
from runtime import ROOT,PARENT,e
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def var(x):
 a=bytearray()
 while x>=128:a.append((x&127)|128);x>>=7
 a.append(x);return a
def signed(x):return var(2*x if x>=0 else -2*x-1)
def export(plans,out):
 e.quota();out.mkdir(exist_ok=False);j=json.loads((PARENT/'joint.json').read_text());prefix={};strings=[];rows=[];exact=Fraction()
 for c in j['cases']:
  p=Path(plans[str(c['case'])]);positions=list(map(int,p.read_text().split()));assert len(positions)==sum(x>0 for x in c['commands'])
  cells=bytearray();live={};pid=0;high=0;F=0;data=var(len(c['commands']));last=0;values=iter(positions)
  for cmd,bid in zip(c['commands'],c['block_ids']):
   data.extend(signed(cmd))
   if cmd>0:
    x=next(values);assert x>=0
    if bid in prefix:assert prefix[bid]==x,('prefix mismatch',c['case'],pid+1,bid)
    prefix[bid]=x;end=x+cmd
    if end>len(cells):cells.extend(bytes(end-len(cells)))
    assert not any(cells[x:end]),('overlap',c['case'],pid+1,x)
    cells[x:end]=bytes([1])*cmd;pid+=1;live[pid]=(x,cmd);F+=cmd;high=max(high,end);data.extend(signed(x-last));last=x
   else:
    x,n=live.pop(-cmd);assert cells[x:x+n]==bytes([1])*n;cells[x:x+n]=bytes(n);F-=n
  T=20*((high+19)//20);assert F==c['F'];s=Fraction(str(c['weight']))*F/T;exact+=s
  rows.append({'case':c['case'],'F':F,'T':T,'lower_T':c['lower_T'],'weighted_score':float(s),'plan':str(p),'plan_sha256':sha(p),'input_sha256':c['input_sha256']})
  text=base64.b64encode(data).decode();strings.append('\n'.join('"'+text[k:k+120]+'"' for k in range(0,len(text),120)))
 source=(ROOT/'solver_runtime.cpp').read_text().replace('// GENERATED_TABLES','static const char* encoded[]={\n'+',\n'.join(strings)+'\n};')
 (out/'solution.cpp').write_text(source)
 e.save(out/'plan-audit.json',{'weighted_score':float(exact),'exact_fraction':str(exact),'cases':rows,'public_prefixes_consistent':True,'independent_cell_replay':True,'source_sha256':sha(out/'solution.cpp'),'source_bytes':(out/'solution.cpp').stat().st_size,'generalization_claim':False,'uses_public_future':True})
 assert e.invoke(['/usr/bin/clang++','-O2','-std=c++17','-Wall','-Wextra',str(out/'solution.cpp'),'-o',str(out/'solver')],out,'compile.log',120)==0
 e.save(out/'build.json',{'source_sha256':sha(out/'solution.cpp'),'binary_sha256':sha(out/'solver')})
 print(json.dumps({'out':str(out),'score':float(exact),'source_bytes':len(source)}),flush=True)
if __name__=='__main__':
 if len(sys.argv)==3:plans=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2])
 else:plans={str(i):str(ROOT/'conditioned-plans'/str(i)/'best.txt') for i in range(1,16)};out=ROOT/'release-v1'
 export(plans,out)
