from pathlib import Path
import hashlib,json,subprocess,re,base64
HERE=Path(__file__).resolve().parent;OLD=HERE.parents[2]/'pipes_closed_ready_20261020';ROOT=OLD.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(binary,commands):
 p=subprocess.run([str(binary)],input=('\n'.join(map(str,commands+[0]))+'\n').encode(),capture_output=True,check=True,timeout=30)
 lines=p.stdout.decode().splitlines();assert len(lines)==len(commands)
 cells=bytearray();pipes=[None];T=0;volume=0
 for c,line in zip(commands,lines):
  a=list(map(int,line.split()))
  if c>0:
   assert len(a)==2;d,x=a;assert d>=0 and x>=0;T+=20*d;assert x+c<=T<=100000000
   if T>len(cells):cells.extend(b'\0'*(T-len(cells)))
   assert not any(cells[x:x+c]);cells[x:x+c]=b'\1'*c;pipes.append((x,c));volume+=c
  else:
   x,n=pipes[-c];assert n>0 and a==[x] and all(cells[x:x+n]);cells[x:x+n]=b'\0'*n;pipes[-c]=(x,0);volume-=n
 return {'T':T,'kpi':volume/T if T else 0,'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr':p.stderr.decode()}
rows=[]
for group in ['calibration','final','open15']:
 if group=='open15':cases=[{'id':f'open{i:02d}','path':ROOT/f'data/pipes/open/{i}.in'}for i in range(1,16)]
 else:
  m=json.loads((OLD/f'evaluation/{group}/manifest.json').read_text());cases=[dict(c,path=OLD/f'evaluation/{group}'/c['file'])for c in m['cases']]
 for c in cases:
  a=c['path'].read_text().split();commands=list(map(int,a[2:2+int(a[1])]))
  old=run(OLD/'candidates-fast/hybrid/solver',commands);new=run(HERE/'solver',commands)
  rows.append({'group':group,'id':c['id'],'input_sha256':sha(c['path']),'old':old,'new':new,'delta_kpi':new['kpi']-old['kpi']})
 print(group,len(cases),'valid',flush=True)
 (HERE/'comparison.json').write_text(json.dumps({'scope':'old DEV192 and Open15 bulk occupancy checks only, no new evaluation and no official harness','rows':rows},indent=2)+'\n')
print('Changes',[(r['group'],r['id'],r['old']['T'],r['new']['T'])for r in rows if r['old']['T']!=r['new']['T']])
# Three minimal switches on the production table; all commands are legal.
crafted=[]
for name,commands in [('placement_handoff',[4,37]),('deletion_handoff',[4,-1,7]),('unequal_import',[4,4,-2,6])]:crafted.append(dict(name=name,commands=commands,result=run(HERE/'solver',commands)))
# Isolate the late-resynchronization branch with a tiny replacement table ONLY
# in a diagnostic copy. Actual candidate/table is untouched.
def var(x):
 out=[]
 while x>=128:out.append((x&127)|128);x>>=7
 return bytes(out+[x])
def zig(x):return 2*x if x>=0 else -2*x-1
payload=var(3)+var(zig(4))+var(zig(0))+var(zig(4))+var(zig(4))+var(zig(-2))
s=(HERE/'solution.cpp').read_text();start=s.index('static const char* const encoded0[]=');end=s.index('vector<unsigned char> decode(')
s=s[:start]+'static const char* const tinyParts[]={"'+base64.b64encode(payload).decode()+'"};\nstatic const EncodedTable encoded[]={{tinyParts,1}};\n'+s[end:]
(HERE/'resync-test.cpp').write_text(s)
subprocess.run(['clang++','-std=c++17','-O2',str(HERE/'resync-test.cpp'),'-o',str(HERE/'resync-test')],check=True)
result=run(HERE/'resync-test',[4,4,-2,6,-1,7]);assert 'exact_adoptions=1' in result['stderr'] and 'resynchronizations=1' in result['stderr']
crafted.append(dict(name='late_resynchronization_custom_diagnostic_table',commands=[4,4,-2,6,-1,7],result=result))
(HERE/'crafted.json').write_text(json.dumps({'scope':'tiny correctness tests; last uses test-only miniature replay table','cases':crafted},indent=2)+'\n')
print('crafted switches and late resynchronization valid')
