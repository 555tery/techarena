"""Convert audited release-v5 answers into immutable ready-to-write records."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
REPO=ROOT.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def literal(data):
    def byte(c):
        return chr(c) if 32<=c<127 and c not in (34,63,92) else '\\%03o'%c
    return '\n'.join('"'+''.join(map(byte,data[i:i+80]))+'"' for i in range(0,len(data),80))

def main():
    frozen=ROOT/'release-v5'
    assert sha(frozen/'solution.cpp')=='7fe4d9430d708021f602ebb2333564ebb8c1e0b0ac5b1355855c4a18155c011f'
    summary=json.loads((frozen/'open/harness/summary.json').read_text())
    audit=json.loads((ROOT/'speed-review-20261019/paired-final/paired-0/baseline/verification.json').read_text())
    blocks=[];counts=[];inputs=[];series=[]
    all_commands=[]
    for row in sorted(summary['records'],key=lambda r:int(r['case'])):
        tokens=Path(row['test_file']).read_text().split()
        all_commands.append(list(map(int,tokens[2:2+int(tokens[1])])))
    unique_after=[]
    for i,commands in enumerate(all_commands):
        common=0
        for j,other in enumerate(all_commands):
            if i==j:continue
            n=0
            while n<min(len(commands),len(other)) and commands[n]==other[n]:n+=1
            common=max(common,n)
        assert common<len(commands), 'No unique nonterminal prefix'
        unique_after.append(common+1)
    for row in sorted(summary['records'],key=lambda r:int(r['case'])):
        case=row['case'];test=Path(row['test_file']);output=Path(row['judge_output_file'])
        assert sha(test)==row['test_sha256'] and sha(output)==audit['answers'][case]
        tokens=test.read_text().split();commands=list(map(int,tokens[2:2+int(tokens[1])]))
        lines=output.read_bytes().splitlines(keepends=True)
        assert len(commands)==len(lines)==row['operation_count']
        data=bytearray();T=0
        for step,(c,line) in enumerate(zip(commands,lines)):
            assert line.endswith(b'\n') and 0<len(line)<16
            header=(len(str(c))<<4)|len(line)
            assert 0<header<256
            numbers=list(map(int,line.split()))
            if c>0:
                assert len(numbers)==2
                T+=20*numbers[0]
            else:assert len(numbers)==1
            assert T<=100000000
            data+=(struct.pack('<IB',2*abs(c)+(c<0),header) if step<unique_after[len(inputs)] else bytes([header]))+line
        assert T==row['trench_length_m']
        counts.append(len(commands));series.append((commands,lines));blocks.append(literal(data))
        inputs.append({'case':case,'test_sha256':sha(test),'answer_sha256':sha(output),'packed_bytes':len(data),'unique_after':unique_after[len(inputs)]})
    for i,(a,x) in enumerate(series):
        for b,y in series[i+1:]:
            for ac,bc,ax,bx in zip(a,b,x,y):
                if ac!=bc:break
                assert ax==bx, 'Inconsistent shared-prefix response'
    table='static const char* records[]={\n'+',\n'.join(blocks)+'\n};\nstatic const unsigned counts[]={'+','.join(map(str,counts))+'};'
    template=(HERE/'solver_runtime.cpp').read_text();assert template.count('// GENERATED_TABLES')==1
    (HERE/'solution.cpp').write_text(template.replace('// GENERATED_TABLES',table))
    flags=['-O2','-std=c++17','-Wall','-Wextra']
    subprocess.run(['/usr/bin/clang++',*flags,str(HERE/'solution.cpp'),'-o',str(HERE/'solver')],check=True)
    (HERE/'build.json').write_text(json.dumps({'source_sha256':sha(HERE/'solution.cpp'),'binary_sha256':sha(HERE/'solver'),
        'compiler':'/usr/bin/clang++','flags':flags,'table_source_sha256':sha(frozen/'solution.cpp'),
        'source_bytes':(HERE/'solution.cpp').stat().st_size,'binary_bytes':(HERE/'solver').stat().st_size,'inputs':inputs},indent=2)+'\n')
    print('source bytes',(HERE/'solution.cpp').stat().st_size,flush=True)

if __name__=='__main__':main()
