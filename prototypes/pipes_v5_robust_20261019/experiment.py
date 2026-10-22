"""Bounded local robustness pilot; never modifies the frozen release."""
import base64
import concurrent.futures
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'prototypes/pipes_v5_graves_20261019'
spec = importlib.util.spec_from_file_location('old_construct', ROOT / 'prototypes/pipes_open15_adversary_20261019/construct.py')
construct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(construct)
decode = construct.decode
sys.path.insert(0, str(ROOT / 'tools'))
import pipes_harness as harness

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def commands(path):
    t = Path(path).read_text().split()
    return list(map(int, t[2:2+int(t[1])]))

def encode(tables):
    def uv(x):
        out = bytearray()
        while x >= 128:
            out.append((x & 127) | 128); x >>= 7
        out.append(x)
        return out
    def sv(x): return uv(2*x if x >= 0 else -2*x-1)
    blobs=[]
    for cmds, positions in tables:
        b = uv(len(cmds)); prev = 0
        for c, x in zip(cmds, positions):
            b.extend(sv(c))
            if c > 0:
                b.extend(sv(x-prev)); prev=x
        text=base64.b64encode(b).decode()
        blobs.append('\n'.join('"'+text[i:i+120]+'"' for i in range(0,len(text),120)))
    return ',\n'.join(blobs)+'\n'

def build(name, policy='bestfit', tables=None):
    source=(BASE/'target/solution.cpp').read_text()
    if tables is not None:
        a=source.index('static const char* encoded[]={')+len('static const char* encoded[]={')
        b=source.index('};',a)
        source=source[:a]+'\n'+encode(tables)+source[b:]
    old='int bf(int n){auto it=sizes.lower_bound({n,-1});if(it!=sizes.end())return it->second;if(!g.empty()&&prev(g.end())->second==T)return prev(g.end())->first;return T;}'
    policies={
        'bestfit':old,
        'rightfit':'int bf(int n){auto it=sizes.lower_bound({n,-1});if(it!=sizes.end())return g.at(it->second)-n;if(!g.empty()&&prev(g.end())->second==T)return prev(g.end())->first;return T;}',
        'firstfit':'int bf(int n){for(auto q:g)if(q.second-q.first>=n)return q.first;if(!g.empty()&&prev(g.end())->second==T)return prev(g.end())->first;return T;}',
        'firstfit-fast':'int bf(int n){int x=INT_MAX;for(int d=n;d<=40;++d)if(!starts[d].empty())x=min(x,*starts[d].begin());if(x!=INT_MAX)return x;if(!g.empty()&&prev(g.end())->second==T)return prev(g.end())->first;return T;}',
        'worstfit':'int bf(int n){if(!sizes.empty()&&sizes.rbegin()->first>=n)return sizes.rbegin()->second;if(!g.empty()&&prev(g.end())->second==T)return prev(g.end())->first;return T;}',
        'lastfit':'int bf(int n){for(auto it=g.rbegin();it!=g.rend();++it)if(it->second-it->first>=n)return it->second-n;if(!g.empty()&&prev(g.end())->second==T)return prev(g.end())->first;return T;}',
    }
    assert old in source
    source=source.replace(old,policies[policy])
    if policy=='firstfit-fast':
        source=source.replace('switches to Best Fit from','switches to First Fit from')
        source=source.replace('int T=0;map<int,int>g;', 'array<set<int>,41> starts; int T=0;map<int,int>g;')
        source=source.replace('void erase(map<int,int>::iterator it){', 'void erase(map<int,int>::iterator it){starts[min(40,it->second-it->first)].erase(it->first);')
        source=source.replace('g[l]=r;sizes.insert({r-l,l});','g[l]=r;sizes.insert({r-l,l});starts[min(40,r-l)].insert(l);')
    folder=HERE/'variants'/name; folder.mkdir(parents=True,exist_ok=True)
    path=folder/'solution.cpp'; path.write_text(source)
    subprocess.run(['clang++','-std=c++20','-O2',str(path),'-o',str(folder/'solver')],check=True,capture_output=True)
    metadata={'name':name,'policy':policy,'source_sha256':sha(path),'binary_sha256':sha(folder/'solver'),
              'baseline_source_sha256':sha(BASE/'target/solution.cpp'),'table_changes':tables is not None}
    (folder/'build.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return folder/'solver'

def screen(argv, path):
    cmds=commands(path)
    run=subprocess.run(list(map(str,argv)),input='\n'.join(map(str,cmds+[0]))+'\n',capture_output=True,text=True,check=True,timeout=20)
    lines=run.stdout.splitlines(); assert len(lines)==len(cmds),(path,len(lines),len(cmds))
    T=0; pipes={}; pid=0; trace=[]; volume=peak=0
    for c,line in zip(cmds,lines):
        if c>0:
            digs,x=map(int,line.split()); assert digs>=0 and x>=0
            T+=20*digs; assert x+c<=T
            assert all(x+c<=a or a+b<=x for a,b in pipes.values()),(path,c,line)
            pid+=1; pipes[pid]=(x,c); volume+=c; peak=max(peak,volume)
        else:
            x,n=pipes.pop(-c); assert int(line)==x; volume-=n
        trace.append(T)
    return {'T':T,'F':volume,'peak':peak,'KPI':volume/T if T else 0,'trace':trace,'stderr':run.stderr}

def main():
    results={}
    tests=sorted((BASE/'suite').glob('*.in'))
    for policy in ['bestfit','rightfit','firstfit','worstfit','lastfit']:
        solver=build('fallback-'+policy,policy)
        results[policy]={p.stem:{k:v for k,v in screen([solver],p).items() if k!='trace'} for p in tests}
    (HERE/'fallback-screen.json').write_text(json.dumps(results,indent=2)+'\n')
    for name,rows in results.items():
        print(name,{k:round(v['KPI'],4) for k,v in rows.items()})

if __name__=='__main__':main()
