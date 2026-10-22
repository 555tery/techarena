from pathlib import Path
from types import SimpleNamespace
import hashlib,importlib.util,json,math,os,statistics,subprocess,sys,tempfile
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_guards_20261022 as e
R=e.R;PARENT=e.E;PR=e.rows();E=R/'prototypes/pipes_virtual_dig_20261022';REC=E/'records.jsonl'
E.mkdir(exist_ok=True);(E/'bin').mkdir(exist_ok=True)
META={m['id']:m for m in e.ev.rows}
META.update({m['id']:m for m in e.inputs('calibration')+e.inputs('final')})
BASE={r['id']:r for r in PR if r['type']=='evaluation'and r['suite']in['archive-production','calibration-production']and r['kind']=='production'}
BASE.update({r['id']:r for r in PR if r['type']=='interactive_evaluation'and r['suite']=='unseen-final'and r['kind']=='production'})
assert len(META)==len(BASE)==2765
EAGER_REF={r['id']:r for r in PR if r['type']=='evaluation'and r['suite']=='archive-same-policy-oldcore'}
EAGER_REF.update({r['id']:r for r in PR if r['type']=='evaluation'and r['suite']=='final'and r['kind']=='same-policy-oldcore'})
e.E=E;e.REC=REC;e.EVAL_CACHE={(r['suite'],r['kind'],r['id'],r['binary_sha256']):r for r in e.rows()if r['type']=='evaluation'}

def build():
 p=Path('/tmp/pipes_guard_generalization.cpp');s=p.read_text();patches=[]
 def patch(a,b,count=1):
  nonlocal s
  assert s.count(a)==count,(a[:90],s.count(a));s=s.replace(a,b);patches.append([a,b])
 patch('''    std::vector<Pipe> pipes{Pipe{}};  // PID is the vector index.
    std::int64_t trenchLength = 0;''','''    std::vector<Pipe> pipes{Pipe{}};  // PID is the vector index.
    std::int64_t trenchLength = 0;
    // Reporting only: never read by the placement policy or its RNG.
    std::int64_t emittedTrenchLength = 0;''')
 patch('printPlacement(digs, start);','printPlacement(digs, start, length);',2)
 patch('''    void printPlacement(std::int64_t digs, std::int64_t start) {
        if (emit) fastio::answer(digs, start);
    }''','''    void printPlacement(std::int64_t digs, std::int64_t start, int length) {
        if (!emit) return;
        if (EMIT_ONLY_NEEDED) {
            const auto missing = start + length - emittedTrenchLength;
            const auto actualDigs = missing > 0 ? (missing + kDigLength - 1) / kDigLength : 0;
            emittedTrenchLength += actualDigs * kDigLength;
            fastio::answer(actualDigs, start);
        } else {
            emittedTrenchLength = trenchLength;
            fastio::answer(digs, start);
        }
    }''')
 patch(' out.trenchLength=actual.T;',' out.trenchLength=actual.T;out.emittedTrenchLength=actual.T;')
 patch('  if(online) cerr<<"reclaimed_reservation_m="','  if(online) cerr<<"emitted_T="<<online->emittedTrenchLength<<" virtual_T="<<online->trenchLength<<"\\n";\n  if(online) cerr<<"reclaimed_reservation_m="')
 cpp=Path('/tmp/pipes_virtual_dig_20261022.cpp');cpp.write_text(s)
 e.record(dict(type='protocol',current_cj=str(PARENT/'release/solution.cj'),current_sha256=e.sha((PARENT/'release/solution.cj').read_bytes()),base_cpp_sha256=e.sha(p.read_bytes()),cpp_sha256=e.sha(cpp.read_bytes()),patches=patches,variants={'eager':dict(lazy=0,emission=0),'virtual-eager':dict(lazy=0,emission=1),'virtual-lazy':dict(lazy=1,emission=1)},guard=5,theorem='Output-only wrapper leaves virtual decision state and every coordinate/removal unchanged; physical T=max(initial imported T,ceil20 max placed end)<=virtual original T. KPI>=same address policy without wrapper for any normally completing valid finite input.',independent_auditor='/root/online_loss_diagnosis',acceptance='all valid; addresses of virtual candidates equal parent; actualT<=parent every step; against current: old archive min delta>=-0.01, all-provenance macro mean>=0, no declared scenario loss>0.05 total points; development mean>=0; Open15>=current; final mean>=0,min>=-0.01, no post-final refit; actual Cj1.0.5 O0 CPU<5s/RSS<256MiB, single worker. Choose max minimum scenario total-score change after gates, ties prefer virtual-eager, virtual-lazy, current.',fresh_design='independent sealed generator with constructive official-checker witness F/T>=0.85; no terminal filler; explicit final grammar changes; final not read during selection',no_platform=True))
 for k,lazy,emit in [('eager',0,0),('virtual-eager',0,1),('virtual-lazy',1,1)]:
  b=E/'bin'/k;q=subprocess.run(['clang++','-O2','-std=c++17','-DRESERVATION_POLICY=1',f'-DLAZY_SLAB={lazy}','-DREPLAY_GUARD=5',f'-DEMIT_ONLY_NEEDED={emit}',str(cpp),'-o',str(b)],capture_output=True,text=True)
  e.record(dict(type='build',kind=k,binary_sha256=e.sha(b.read_bytes())if q.returncode==0 else None,status=q.returncode,stderr=q.stderr[-2000:]));assert q.returncode==0,q.stderr;print('BUILT',k,flush=True)
 (E/'bin/current').symlink_to(PARENT/'bin/edge-local')

def inputs(split):
 return [json.loads(s)for s in(E/'input_manifest.jsonl').open()if json.loads(s).get('type')=='input'and json.loads(s)['split']==split]

def evaluate(m,kind,suite):return e.batch(m,kind,suite)

def oldpanel():
 for i,m in enumerate(META.values()):
  for k in ['virtual-eager','virtual-lazy']:
   x=evaluate(m,k,'old')
   if k=='virtual-lazy':assert x['response_sha256']==BASE[m['id']]['response_sha256'],(m['id'],'current has nonminimal digs?',x['kpi'],BASE[m['id']]['kpi'])
   ref=EAGER_REF.get(m['id'])if k=='virtual-eager'else BASE[m['id']]
   if ref:assert x['kpi']>=ref['kpi']-1e-12,(m['id'],k,'dominance failed')
  if(i+1)%128==0 or i+1==len(META):print('OLD',i+1,len(META),flush=True)

def verify_trace(m):
 """Both complete traces are checked independently plus pointwise simulation."""
 tokens=Path(m['test_file']).read_bytes().split();commands=list(map(int,tokens[2:2+m['operation_count']]))
 raw=('\n'.join(map(str,commands))+'\n0\n').encode();outs=[]
 for k in ['eager','virtual-eager']:
  q=subprocess.run([str(E/'bin'/k)],input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'cjProcessorNum':'1'},timeout=120);assert q.returncode==0,q.stderr[-1000:];outs.append(q.stdout)
 lines=[x.splitlines()for x in outs];assert len(lines[0])==len(lines[1])==len(commands)
 ts=[0,0];ends=0;addresses=hashlib.sha256()
 for cmd,a,b in zip(commands,*lines):
  aa,bb=list(map(int,a.split())),list(map(int,b.split()))
  assert aa[-1]==bb[-1],(m['id'],cmd,aa,bb)
  addresses.update(str(aa[-1]).encode()+b'\n')
  if cmd>0:
   ts[0]+=20*aa[0];ts[1]+=20*bb[0];ends=max(ends,bb[1]+cmd)
   assert ts[1]<=ts[0]and ts[1]==20*((ends+19)//20),(m['id'],ts,ends)
 for kind,out in zip(['eager','virtual-eager'],outs):
  x=evaluate(m,kind,'trace-reference');assert x['response_sha256']==e.sha(out)
 e.record(dict(type='pointwise_trace_certificate',id=m['id'],test_sha256=m['test_sha256'],commands=len(commands),addresses_sha256=addresses.hexdigest(),equal_all_addresses_and_removals=True,physical_minimal_every_step=True,physical_never_above_eager=True,eager_final_T=ts[0],physical_final_T=ts[1]))
 return ts

def invariants():
 known=e.rows();vm={r['id']:r for r in known if r['type']=='evaluation'and r['suite']=='old'and r['kind']=='virtual-eager'}
 chosen=[i for i,r in vm.items()if i not in EAGER_REF or r['response_sha256']!=EAGER_REF[i]['response_sha256']]
 # In addition to all changes, exercise each public path and largest streams.
 chosen=list(dict.fromkeys(chosen+[m['id']for m in META.values()if m.get('public_number')]+[m['id']for m in list(META.values())[-104:]if m['operation_count']==200000]))
 for j,i in enumerate(chosen):
  verify_trace(META[i])
  if(j+1)%8==0 or j+1==len(chosen):print('TRACE',j+1,len(chosen),flush=True)

if __name__=='__main__':
 {'build':build,'old':oldpanel,'invariants':invariants}[sys.argv[1]]()
