"""Hash-pinned lazy transport candidate; canonical source remains untouched."""
import argparse,datetime,hashlib,importlib.util,json,subprocess
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PARENT=ROOT/'prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp'
spec=importlib.util.spec_from_file_location('encode',ROOT/'prototypes/pipes_prefix_replan_20261020/build.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def with_first(main,name):
    main=main.replace('int main(){',f'int {name}(int first){{',1)
    main=main.replace('  int c;size_t step=0;', '  int c=first;size_t step=0;',1)
    main=main.replace('  while(scanf("%d",&c)==1&&c!=0){','  do{',1)
    main=main.replace('  }\n  planner.report();','  }while(scanf("%d",&c)==1&&c!=0);\n  planner.report();',1)
    return main
def main():
    ap=argparse.ArgumentParser();ap.add_argument('name');ap.add_argument('--profile',choices=['all','instant','joint','exchange','tail','tail-single'],required=True);ap.add_argument('--policy',type=int,choices=range(5),required=True);a=ap.parse_args()
    assert sha(PARENT)=='a843822451c2a7c5e07330daa33268fc77bccfbc08fd196bfaf98a673ae24cfe'
    original=PARENT.read_text();tables=e.decode(PARENT)
    j=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
    changes={int(k):v for k,v in json.loads((ROOT/'prototypes/pipes_prefix_replan_20261020/final/build.json').read_text())['changes'].items() if int(k)!=21532}
    instant={5321,5343,5407,5418,5443,5468,5293,5291};exchange={5499,7242,8517,8518}
    if a.profile=='instant':changes={k:v for k,v in changes.items() if k in instant}
    if a.profile=='joint':changes={k:v for k,v in changes.items() if k not in instant}
    if a.profile=='exchange':changes={k:v for k,v in changes.items() if k in exchange}
    if a.profile in ['tail','tail-single']:
        changes={int(k):v for k,v in json.loads((HERE/'tail-changes.json').read_text()).items()}
        if a.profile=='tail-single':changes={k:v for k,v in changes.items() if k==5321}
    audits=[];patches=[];score=Fraction(0)
    for ci,((commands,xs),case) in enumerate(zip(tables,j['cases'])):
        cells=bytearray(case['lower_T']);live={};pid=T=oldT=F=peak=altered=0
        for step,(c,old,bid) in enumerate(zip(commands,xs,case['block_ids'])):
            if c>0:
                x=changes.get(bid,old)
                if x!=old:patches.append((ci,step,x));altered+=1
                assert x>=0 and x+c<=len(cells) and not any(cells[x:x+c]),(ci,step,x)
                cells[x:x+c]=b'\1'*c;pid+=1;live[pid]=(x,c)
                T=max(T,20*((x+c+19)//20));oldT=max(oldT,20*((old+c+19)//20));assert T<=oldT
                F+=c;peak=max(peak,F)
            else:
                x,L=live.pop(-c);assert all(cells[x:x+L]);cells[x:x+L]=b'\0'*L;F-=L
        assert T==case['lower_T'] and F==case['F'] and peak==case['peak_volume']
        score+=Fraction(str(case['weight']))*F/T
        audits.append({'case':ci+1,'T':T,'F':F,'changed_allocations':altered})
    pos={(ci,s):x for ci,s,x in patches}
    for ci in range(15):
        for cj in range(ci):
            for s,(c,d,x,y) in enumerate(zip(tables[ci][0],tables[cj][0],tables[ci][1],tables[cj][1])):
                if c!=d:break
                if c>0:assert pos.get((ci,s),x)==pos.get((cj,s),y)
    oldmain=original[original.rindex('int main(){'):]
    baseline=with_first(oldmain,'baselineMain')
    physical=with_first(oldmain,'transportMain')
    physical=physical.replace('Allocator state,shadow;shadow.emit=false;',f'Allocator state,shadow;state.emit=false;shadow.emit=false;PhysicalFollower physical({a.policy});')
    physical=physical.replace('int address=-1;bool agrees=true,matched=false;','int address=-1,planned=-1;bool agrees=true,matched=false;')
    physical=physical.replace('int p=tests[i].pos[step];','int p=tests[i].pos[step];int q=patchPosition(int(i),step,p);if(planned>=0&&planned!=q)throw runtime_error("patch prefix conflict");planned=q;')
    physical=physical.replace('if(c>0){state.place(c,address);++replay;}else state.remove(-c);',
      'if(c>0){physical.place(state,c,address,PhysicalFollower::nextT(state.T,address,c),true,planned);state.place(c,address);++replay;}else{physical.remove(-c,state.pipes.at(-c).first,state.T);state.remove(-c);}')
    physical=physical.replace('printf("%lld %lld\\n",(long long)trial->lastDigs,(long long)trial->lastStart);',
      'physical.place(state,c,int(trial->lastStart),int(trial->trenchLength),false);')
    physical=physical.replace('printf("%lld\\n",(long long)x);','physical.remove(-c,int(x),int(online->trenchLength));')
    physical=physical.replace('if(!answered){if(c>0){int x=planner.choose(state,c,state.bf(c));state.place(c,x);}else state.remove(-c);}',
      'if(!answered){if(c>0){int x=planner.choose(state,c,state.bf(c));physical.place(state,c,x,PhysicalFollower::nextT(state.T,x,c),false);state.place(c,x);}else{physical.remove(-c,state.pipes.at(-c).first,state.T);state.remove(-c);}}')
    physical=physical.replace('  planner.report();','  physical.report(online?int(online->trenchLength):state.T);\n  planner.report();')
    physical=physical.replace('(long long)(online?online->trenchLength:state.T),observed.size()', '(long long)physical.T,observed.size()')
    patcher='static int patchPosition(int ci,size_t step,int original){\n'
    for ci,s,x in patches:patcher+=f' if(ci=={ci}&&step=={s})return {x};\n'
    patcher+=' return original;\n}\n'
    source=original[:original.rindex('int main(){')]+(HERE/'theory/local_transport.hpp').read_text().replace('#pragma once','')+'\n'+(HERE/'runtime.hpp').read_text()+'\n'+patcher+baseline+'\n'+physical+'\nint main(){int first;if(scanf("%d",&first)!=1||first==0)return 0;return first==6?transportMain(first):baselineMain(first);}\n'
    out=HERE/a.name;out.mkdir(exist_ok=False);(out/'solution.cpp').write_text(source)
    cmd=['clang++','-std=c++20','-O2','-Wno-unqualified-std-cast-call',str(out/'solution.cpp'),'-o',str(out/'solver')]
    r=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.log').write_text(r.stdout+r.stderr);r.check_returncode()
    meta={'source_sha256':sha(out/'solution.cpp'),'binary_sha256':sha(out/'solver'),'parent_source_sha256':sha(PARENT),
        'built_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'build_command':cmd,'profile':a.profile,'policy':a.policy,
        'changes':changes,'audits':audits,'Open15_score':float(score),'Open15_exact':str(score),'shared_prefix_consistent':True,
        'implementation':'Original fast path for first command!=6; lazy actual geometry only after a changed placement; release maps after identical live PID coordinates; same original reference Planner',
        'guarantee':'After identity and realT<=internal parentT, reference continuation preserves dominance until another public patch. Before identity local reflection is a current-step certificate only.',
        'target_hardware_run':False,'platform_actions':0}
    (out/'build.json').write_text(json.dumps(meta,indent=2)+'\n');print(a.name,meta['source_sha256'],flush=True)
if __name__=='__main__':main()
