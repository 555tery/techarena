"""Post-prefix reclamation at a high, certified achievable final load.

These diagnostics attack irreversible reservations, rather than driving the
final numerator to zero. After retiring the old live set, BF's whole trench is
filled, partially replaced in deterministic rounds, then completely filled.
"""
import importlib.util
import json
import random
from build_online_fallback import HERE,ROOT,PREV,e

spec=importlib.util.spec_from_file_location('alloc_sim',PREV/'new_attacks/build_new_attacks.py')
sim=importlib.util.module_from_spec(spec);spec.loader.exec_module(sim)

def main():
    out=HERE/'counterattacks';out.mkdir(exist_ok=True);rows=[]
    tables=e.decode(PREV/'candidate-v3/solution.cpp')
    for case,cut in [(9,127),(12,151),(12,224),(14,17565)]:
        rng=random.Random(771000+case)
        public,positions=tables[case-1];cmd=public[:cut].copy()
        bf=sim.Allocator();target_T=0;ratios=[]
        for c,x in zip(cmd,positions):
            if c>0:bf.place(c);target_T=max(target_T,20*((x+c+19)//20))
            else:bf.remove(-c)
            ratios.append(target_T/bf.trench if bf.trench else 1)
        initial_T=bf.trench
        alive=[i for i,p in enumerate(bf.pipes) if i and p[0] is not None]
        alive.sort(key=lambda i:bf.pipes[i][0])
        if -alive[0]==public[cut]:alive[0],alive[-1]=alive[-1],alive[0]
        assert -alive[0]!=public[cut]
        for pid in alive:cmd.append(-pid);bf.remove(pid)
        def fill():
            while bf.gaps:
                largest=max(b-a for a,b in bf.gaps)
                length=min(largest,rng.randint(1,40));cmd.append(length);bf.place(length)
                assert bf.trench==initial_T
        fill()
        for epoch in range(3):
            alive=[i for i,p in enumerate(bf.pipes) if i and p[0] is not None]
            rng.shuffle(alive)
            for pid in alive[:max(1,len(alive)//12)]:cmd.append(-pid);bf.remove(pid)
            fill()
        assert len(cmd)<=200000
        assert sum(p[1] for p in bf.pipes[1:] if p[0] is not None)==initial_T
        p=out/f'plateau-open{case}-p{cut}.in';p.write_text('1\n'+str(len(cmd))+'\n'+'\n'.join(map(str,cmd))+'\n')
        meta=e.harness.parse_test(p)
        assert meta['final_occupied_length_m']==meta['minimum_trench_lower_bound_m']==initial_T
        rows.append({'file':str(p.relative_to(ROOT)),'sha256':e.sha(p),'open_case':case,'prefix_length':cut,
                     'max_prefix_target_over_BF':max(ratios),'BF_KPI':1,'final_F':initial_T,
                     'mechanism':'retire prefix pipes, saturated BF plateau, three replacement rounds',**meta})
    # A known counterexample to the rejected BF-close Open2 layout; a safety control.
    cmd=tables[1][0][:14]+[5,4,3,1]
    p=out/'control-open2-p14-large-hole.in';p.write_text('1\n'+str(len(cmd))+'\n'+'\n'.join(map(str,cmd))+'\n')
    rows.append({'file':str(p.relative_to(ROOT)),'sha256':e.sha(p),'open_case':2,'prefix_length':14,
                 'mechanism':'known counterexample to an earlier rejected plan; control, not a fresh discovery',**e.harness.parse_test(p)})
    prior={e.sha(p) for p in __import__('validate').old_files()}
    assert not prior&{r['sha256'] for r in rows}
    (out/'manifest.json').write_text(json.dumps({'scope':'post-freeze diagnostic additions, not tuning/holdout','tests':rows},indent=2)+'\n')
    print([(r['file'],r['operation_count']) for r in rows])

if __name__=='__main__':main()
