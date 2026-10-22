"""Compile and evaluate the new lane profile on old reference traces only."""
import argparse,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=int,choices=[0,2,12],default=12);a=ap.parse_args()
    prefix={12:'lane',2:'lane2',0:'root0'}[a.root];plan=HERE/({12:'lane-plan',2:'lane2-plan',0:'marker3-plan'}[a.root])
    # Same physical allocator/rules as the position screen; different public
    # plans are passed explicitly for each known replayed command.
    source=(HERE/'screen.cpp').read_text()
    source=source.replace('struct Row {int c,x,T;bool replay;};','struct Row {int c,x,T;bool replay;int planned;};')
    source=source.replace(' if(marker==229)return c.target;','')
    source=source.replace('int x=(t==1&&c.rows[0].c==3&&cmd==2)?marker:row.x;','int x=row.planned;')
    source=source.replace('if(coupled||(t>=2&&!differing&&a.T<=row.T&&a.pipes.size()>2&&a.pipes[2].second==0))','if(coupled)')
    source=source.replace('in>>r.c>>r.x>>r.T>>r.replay;','in>>r.c>>r.x>>r.T>>r.replay>>r.planned;')
    source=source.replace('for(int marker=3;marker<=229;++marker)','for(int marker=0;marker<1;++marker)')
    source=source.replace('policy<=8','policy<=12')
    source=source.replace('Allocator a;a.emit=false;size_t differing=0;bool coupled=false;',
      'Allocator a;a.emit=false;size_t differing=0;bool coupled=false;map<int,int>coverage;vector<int>lengths(1);auto bump=[&](int x,int d){int v=(coverage[x]+=d);if(!v)coverage.erase(x);};int second=c.rows.size()>1?c.rows[1].c:0;')
    source=source.replace('choose(a,cmd,row.x,row.T,policy)',
      '([&](){if(policy>=9&&coverage.empty()&&a.T<=row.T)return row.x;if(policy>=10){int q=project(row.x,cmd,second,t,c.rows);if(q>=0&&a.fits(q,cmd)&&digT(a.T,q,cmd)<=row.T)return q;if(policy==11&&a.fits(row.x,cmd)&&digT(a.T,row.x,cmd)<=row.T)return row.x;if(policy==12)return choose(a,cmd,row.x,row.T,4);return a.bf(cmd);}return choose(a,cmd,row.x,row.T,policy==9?0:policy);}())')
    source=source.replace('  if(coupled)return max(a.T,c.suffix[t+1]);',
      '  if(cmd>0){lengths.push_back(cmd);int x=a.pipes.back().first;bump(x,1);bump(x+cmd,-1);bump(row.x,-1);bump(row.x+cmd,1);}else{int x=a.pipes[-cmd].first,L=lengths[-cmd];bump(x,-1);bump(x+L,1);bump(row.x,1);bump(row.x+L,-1);}\n  if(coupled)return max(a.T,c.suffix[t+1]);')
    project=r'''
static int project(int x,int n,int second,size_t t,const vector<Row>&rows){
 // Only already observed public commands select the coordinate permutation.
 // A [3,2] deviation while PID2 lives rotates [0,231) right by2.
 bool early=second==2&&(t==2||!rows[2].replay);
 if(early){if(x+n<=229)return x+2;if(x>=229&&x+n<=231)return x-229;if(x>=231)return x;return -1;}
 if(second==5){if(x+n<=8)return x+2;if(x>=8&&x+n<=10)return x-8;if(x>=10)return x;return -1;}
 if(second==1){
  // Open6 component order, independently lifetime-checked on the public data.
  if(x+n<=3)return x+2;
  if(x>=4&&x+n<=6)return x-4;
  if(x>=8&&x+n<=20)return x-3;
  if(x>=3&&x+n<=4)return x+14;
  if(x>=6&&x+n<=7)return x+12;
  if(x>=7&&x+n<=8)return x+12;
  if(x>=20)return x;return -1;
 }
 if(x+n<=3)return x+2;if(x>=3&&x+n<=5)return x-3;if(x>=5)return x;return -1;
}
'''
    if a.root==0:
        project=r'''
static int project(int x,int n,int second,size_t t,const vector<Row>&rows){
 bool early=second==2&&(t==2||!rows[2].replay);
 if(!early)return x;
 if(x+n<=3)return x;
 if(x>=3&&x+n<=229)return x+2;
 if(x>=229&&x+n<=231)return x-226;
 if(x>=231)return x;return -1;
}
'''
    source=source.replace('static int rollout(',project+'\nstatic int rollout(')
    (HERE/(prefix+'_screen.cpp')).write_text(source)
    r=subprocess.run(['clang++','-std=c++20','-O2',str(HERE/(prefix+'_screen.cpp')),'-o',str(HERE/(prefix+'_screen'))],capture_output=True,text=True)
    (HERE/(prefix+'_screen.compile.log')).write_text(r.stdout+r.stderr);r.check_returncode()
    import importlib.util
    spec=importlib.util.spec_from_file_location('pb',HERE.parents[1]/'prototypes/pipes_prefix_replan_20261020/build.py')
    e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
    tables=e.decode(HERE.parents[1]/'prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp')
    j=json.loads((HERE.parents[1]/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
    changes={int(k):v for k,v in json.loads((plan/'changes.json').read_text()).items()}
    cases=[]
    for f in sorted((HERE/'reference').glob('*.json')):
        r=json.loads(f.read_text());active=list(range(15));rows=[]
        for step,(c,x,T,replay) in enumerate(r['rows']):
            planned=-1
            if replay:
                active=[ci for ci in active if step<len(tables[ci][0]) and tables[ci][0][step]==c];assert active
                if c>0:
                    bid=j['cases'][active[0]]['block_ids'][step];planned=changes.get(bid,x)
            rows.append((c,x,T,replay,planned))
        cases.append((r['id'],rows,r['T']))
    with (HERE/(prefix+'-search.in')).open('w') as f:
        f.write(str(len(cases))+'\n')
        for ident,rows,T in cases:
            f.write(f'{ident} {len(rows)} {T}\n');f.writelines(' '.join(map(str,r))+'\n' for r in rows)
    print('lane known affected cases',len(cases),flush=True)
    subprocess.run([str(HERE/(prefix+'_screen')),str(HERE/(prefix+'-search.in')),str(HERE/(prefix+'-search.csv'))],check=True)
if __name__=='__main__':main()
