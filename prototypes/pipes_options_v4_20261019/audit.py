"""Coordinator checks with a separate cell-map, no production allocator import."""
import importlib.util
import json
from pathlib import Path
import selectors
import subprocess

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]

def source_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def read_input(path):
    x=path.read_text().split();n=int(x[1]);cmd=list(map(int,x[2:2+n]))
    assert len(cmd)==n and (not x[2+n:] or x[2+n:]==['0'])
    return cmd

def verify(commands,replies):
    cells=[];live={};pid=0
    assert len(commands)==len(replies)
    for i,(c,line) in enumerate(zip(commands,replies)):
        vals=list(map(int,line.split()))
        if c>0:
            assert len(vals)==2,(i,line)
            dig,start=vals;assert dig>=0 and start>=0
            assert dig==(max(0,start+c-len(cells))+19)//20
            cells.extend([0]*(20*dig));pid+=1
            assert start+c<=len(cells) and not any(cells[start:start+c]),(i,line)
            cells[start:start+c]=[pid]*c;live[pid]=(start,c)
        else:
            assert len(vals)==1 and -c in live
            start,l=live.pop(-c);assert vals[0]==start
            assert cells[start:start+l]==[-c]*l
            cells[start:start+l]=[0]*l
    return {'T':len(cells),'F':sum(l for s,l in live.values())}

def data_check(phase):
    manifest=json.loads((ROOT/'data'/f'{phase}.json').read_text())
    parser=source_module('official_parser',REPO/'tools/pipes_harness.py')
    groups={};zero=0
    for r in manifest['records']:
        path=ROOT/'data'/phase/(r['name']+'.in')
        meta=parser.parse_test(path)
        assert meta['test_sha256']==r['sha256']
        assert meta['operation_count']==r['n']
        assert meta['final_occupied_length_m']==r['final_volume']
        assert meta['peak_live_pipe_length_m']==r['peak_volume']
        zero+=r['final_volume']==0
        if r['branch']!='resource':groups.setdefault(r['base'],[]).append(r)
    for base,rows in groups.items():
        assert len(rows)==4 and len({r['branch'] for r in rows})==4
        sequences=[read_input(ROOT/'data'/phase/(r['name']+'.in'))[:24] for r in rows]
        assert all(x==sequences[0] for x in sequences)
    result={'phase':phase,'cases':len(manifest['records']),'matched_quartets':len(groups),'zero_final':zero,'legal':True}
    (ROOT/f'data-audit-{phase}.json').write_text(json.dumps(result,indent=2)+'\n');return result

def solver_check(labels):
    prior=source_module('independent_cells',REPO/'prototypes/pipes_generalization_20261018/audit_baselines.py')
    cases=prior.fixtures()[:28];out={}
    for label in labels:
        binary=ROOT/'builds'/label/'solver'
        for commands in cases:
            r=subprocess.run([str(binary)],input='\n'.join(map(str,commands+[0]))+'\n',text=True,capture_output=True,timeout=5)
            assert r.returncode==0,r.stderr
            replies=r.stdout.splitlines();verify(commands,replies)
            if label in ['bf','kernel_bf','ss']:
                assert replies==prior.oracle(commands,'ss' if label=='ss' else 'bf')
        # No future command, even the stop marker, is available before response.
        commands=cases[3];p=subprocess.Popen([str(binary)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ);replies=[]
        try:
            for c in commands:
                p.stdin.write(str(c)+'\n');p.stdin.flush();assert sel.select(2)
                replies.append(p.stdout.readline().strip())
            p.stdin.write('0\n');p.stdin.flush();p.stdin.close();assert p.wait(timeout=3)==0
            verify(commands,replies)
        finally:
            sel.close()
            if p.poll() is None:p.kill();p.wait()
        out[label]={'streams':len(cases),'commands':sum(map(len,cases)),'valid':True,'immediate_flush':True}
    (ROOT/'solver-audit.json').write_text(json.dumps(out,indent=2)+'\n');return out

if __name__=='__main__':
    import sys
    print(json.dumps(data_check(sys.argv[2]) if sys.argv[1]=='data' else solver_check(sys.argv[2:])))
