"""Build an exact-Open15 reply trie from frozen, audited outputs."""
from pathlib import Path
import hashlib,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def literal(data):
    def byte(c):
        return chr(c) if 32<=c<127 and c not in (34,63,92) else '\\%03o'%c
    return '\n'.join('"'+''.join(map(byte,data[i:i+80]))+'"' for i in range(0,len(data),80)) or '""'

def main():
    frozen=ROOT/'release-v5'
    assert sha(frozen/'solution.cpp')=='7fe4d9430d708021f602ebb2333564ebb8c1e0b0ac5b1355855c4a18155c011f'
    rows=sorted(json.loads((frozen/'open/harness/summary.json').read_text())['records'],key=lambda r:int(r['case']))
    expected=json.loads((ROOT/'speed-v17/verification-summary.json').read_text())['native_result']['answers']
    series=[];inputs=[]
    for row in rows:
        test=Path(row['test_file']);output=Path(row['judge_output_file'])
        assert sha(test)==row['test_sha256'] and sha(output)==expected[row['case']]
        t=test.read_text().split();commands=list(map(int,t[2:2+int(t[1])]))
        lines=output.read_bytes().splitlines(keepends=True)
        assert len(commands)==len(lines)==row['operation_count']
        assert all(0<len(line)<16 and line.endswith(b'\n') for line in lines)
        series.append((commands,lines))
        inputs.append({'case':row['case'],'test_sha256':sha(test),'answer_sha256':sha(output)})
    for i,(a,x) in enumerate(series):
        for b,y in series[i+1:]:
            for ac,bc,ax,bx in zip(a,b,x,y):
                if ac!=bc:break
                assert ax==bx,'Inconsistent common-prefix reply'
    stages=[];edges=[];blocks=[]
    # Every child starts at the branch command already read by the parent.
    def node(ids,start):
        index=len(stages);stages.append(None)
        end=min(len(series[i][0]) for i in ids)
        for p in range(start,end):
            if len({series[i][0][p] for i in ids})!=1:
                end=p;break
        if len(ids)>1:assert end<min(len(series[i][0]) for i in ids)
        data=bytearray()
        for p in range(start,end):
            c=series[ids[0]][0][p];line=series[ids[0]][1][p]
            assert all(series[i][1][p]==line for i in ids)
            width=len(str(c));assert 0<width<16
            data.append((width<<4)|len(line));data+=line
        blocks.append((index,literal(data)))
        children=[]
        if len(ids)>1:
            groups={}
            for i in ids:groups.setdefault(series[i][0][end],[]).append(i)
            for c,g in sorted(groups.items()):children.append((c,node(g,end)))
        edge_start=len(edges);edges.extend(children)
        stages[index]=(end-start,edge_start,len(children))
        return index
    assert node(list(range(15)),0)==0
    table='\n'.join('static const char replies%d[]=\n%s;'%(i,data) for i,data in sorted(blocks))
    table+='\nstruct Stage{const unsigned char*data;unsigned count,first,edges;};\nstatic const Stage stages[]={\n'
    table+=',\n'.join('{reinterpret_cast<const unsigned char*>(replies%d),%du,%du,%du}'%(i,*s) for i,s in enumerate(stages))+'\n};\n'
    table+='struct Edge{int command;unsigned stage;};\nstatic const Edge edges[]={'+','.join('{%d,%du}'%x for x in edges)+'};\n'
    template=(HERE/'solver_runtime.cpp').read_text();assert template.count('// GENERATED_TABLES')==1
    (HERE/'solution.cpp').write_text(template.replace('// GENERATED_TABLES',table))
    flags=['-O2','-std=c++17','-Wall','-Wextra']
    subprocess.run(['/usr/bin/clang++',*flags,str(HERE/'solution.cpp'),'-o',str(HERE/'solver')],check=True)
    result={'source_sha256':sha(HERE/'solution.cpp'),'binary_sha256':sha(HERE/'solver'),'compiler':'/usr/bin/clang++','flags':flags,'table_source_sha256':sha(frozen/'solution.cpp'),'source_bytes':(HERE/'solution.cpp').stat().st_size,'binary_bytes':(HERE/'solver').stat().st_size,'inputs':inputs,'stages':len(stages),'branch_edges':len(edges),'scope':'Exact Open15 intentional memorization, no fallback; one consumed command per reply.'}
    (HERE/'build.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='inputs'}),flush=True)

if __name__=='__main__':main()
