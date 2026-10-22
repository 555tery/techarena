"""Post-freeze residual counterexamples with a certified attainable KPI of 1."""
import json
import random
import subprocess
from common import HERE,ROOT,e,BF,known_files

def main():
    info={}
    for path in [HERE/'components/audit.json',*sorted((HERE/'components').glob('pair-*/audit.json'))]:
        data=json.loads(path.read_text())
        for r in data['audits']:info[r['case']]=r
    tables=e.decode(HERE/'candidate/solution.cpp');rows=[]
    out=HERE/'counterattacks';out.mkdir(exist_ok=True)
    for case in [8,9,11,12,13,14]:
        cut=info[case]['worst_step'];public=tables[case-1][0];cmd=public[:cut].copy()
        run=subprocess.run(BF,input='\n'.join(map(str,cmd+[0]))+'\n',text=True,capture_output=True,check=True)
        active={};pid=T=0
        for c,line in zip(cmd,run.stdout.splitlines()):
            if c>0:
                digs,x=map(int,line.split());T+=20*digs;pid+=1;active[pid]=(x,c)
            else:del active[-c]
        expected={commands[cut] for commands,poses in tables if commands[:cut]==cmd and len(commands)>cut}
        alive=sorted(active,key=lambda i:active[i][0]);first=next(i for i in alive if -i not in expected)
        delete=[first]+[i for i in alive if i!=first]
        cmd.extend(-i for i in delete)
        fill=[40]*(T//40)+([T%40] if T%40 else [])
        cmd.extend(fill);fill_ids=list(range(pid+1,pid+len(fill)+1))
        # Exact-size replacements keep BF full without needing any future oracle.
        rng=random.Random(773000+case);replaced=rng.sample(range(len(fill)),min(12,len(fill)))
        for index in replaced:cmd.extend([-fill_ids[index],fill[index]])
        path=out/f'residual-open{case}-p{cut}.in'
        path.write_text('1\n'+str(len(cmd))+'\n'+'\n'.join(map(str,cmd))+'\n')
        meta=e.harness.parse_test(path)
        assert meta['final_occupied_length_m']==meta['minimum_trench_lower_bound_m']==T
        rows.append({'file':str(path.relative_to(ROOT)),'case':case,'prefix_length':cut,'sha256':e.sha(path),
                     'mechanism':'retire observed pipes, fill the entire BF trench, then exact-size replacements',
                     'attainable_KPI':1,'public_plan_prefix_max_ratio':info[case]['ratio'],**meta})
    excluded={e.sha(p) for p in known_files()}|{e.sha(p) for p in (HERE/'attacks').glob('*.in')}
    assert not excluded&{r['sha256'] for r in rows}
    (out/'manifest.json').write_text(json.dumps({'scope':'post-freeze diagnostic attacks; never used for tuning candidate','candidate_source_sha256':e.sha(HERE/'candidate/solution.cpp'),'tests':rows},indent=2)+'\n')
    print([(r['case'],r['prefix_length'],r['operation_count']) for r in rows])

if __name__=='__main__':main()
