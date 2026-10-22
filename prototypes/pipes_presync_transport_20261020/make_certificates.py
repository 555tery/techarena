"""Post-freeze geometric counterexamples, separate from the independent seeded gate.

Keep the moved pipe, remove all others, and fill the original two free intervals.
If no subset of the filler lengths sums to the new left interval length, exact
old capacity is impossible for every continuation preserving that moved pipe.
"""
import hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('build_transport',HERE/'build.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def split(length,width=40):return [width]*(length//width)+([length%width] if length%width else [])
def main():
    freeze=json.loads((HERE/'freeze.json').read_text());assert sha(HERE/freeze['candidate']/'solution.cpp')==freeze['source_sha256']
    tables=b.e.decode(b.PARENT);j=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
    changes={int(k):v for k,v in json.loads((HERE/'tail-changes.json').read_text()).items()}
    folder=HERE/'diagnostics';folder.mkdir(exist_ok=True);cases=[]
    ci=7;commands,positions=tables[ci];live={};pid=T=0
    for step,(c,x,bid) in enumerate(zip(commands,positions,j['cases'][ci]['block_ids'])):
        if c>0:pid+=1;live[pid]=(x,c);T=max(T,20*((x+c+19)//20))
        else:del live[-c]
        if c<=0 or bid not in changes:continue
        new=changes[bid];filler=split(x)+split(T-x-c)
        sums=1
        for length in filler:sums|=sums<<length
        assert ((sums>>new)&1)==0,(bid,new)
        stream=commands[:step+1]+[-i for i in sorted(live) if i!=pid]+filler
        name=f'partition-p{step+1}';path=folder/(name+'.in');path.write_text(f'1 {len(stream)}\n'+'\n'.join(map(str,stream))+'\n')
        cases.append({'name':name,'filename':path.name,'sha256':sha(path),'family':'exact_partition_witness','n':len(stream),
            'public_prefix':step+1,'block_id':bid,'retained_pid':pid,'retained_length':c,'original_x':x,'candidate_x':new,
            'parent_capacity':T,'final_F':T,'filler':filler,'candidate_left_gap_subset_sum_reachable':False,
            'certificate':'At capacity T, volume equals T, so fillers must exactly partition into left gap new_x and right gap T-new_x-L. The subset sum new_x is unreachable. Any policy preserving the new coordinate requires at least T+20.',
            'provenance':'Constructed from public prefix and frozen source changes; targeted diagnostic, not independent validation.'})
    assert len(cases)==4
    # Keep a changed PID alive for the full legal maximum; exercise both helper
    # scan cap and lazy physical-state lifetime. Legal deletions are maintained.
    commands=commands[:67];active=[];pid=0
    for c in commands:
        if c>0:pid+=1;active.append(pid)
        else:active.remove(-c)
    retained=pid
    for step in range(len(commands),200000):
        if step%5==0 and len(active)>1:
            idx=0 if active[0]!=retained else 1;commands.append(-active.pop(idx))
        else:pid+=1;active.append(pid);commands.append(40 if step%7 else 1)
    name='retained-tail-200k';path=folder/(name+'.in');path.write_text(f'1 {len(commands)}\n'+'\n'.join(map(str,commands))+'\n')
    cases.append({'name':name,'filename':path.name,'sha256':sha(path),'family':'retained_changed_pid_scale','n':len(commands)})
    # Separate legal-input audit, including deletion membership and final load.
    for row in cases:
        raw=(folder/row['filename']).read_text().split();n=int(raw[1]);assert len(raw)==n+2 and 1<=n<=200000
        alive={};p=0
        for c in map(int,raw[2:]):
            if c>0:assert c<=40;p+=1;alive[p]=c
            else:assert -c in alive;del alive[-c]
        assert alive;row['validated_final_F']=sum(alive.values())
        if 'final_F' in row:assert row['final_F']==row['validated_final_F']
    (folder/'manifest.json').write_text(json.dumps({'cases':cases,'all_valid':True,'independent':False,'source_sha256':freeze['source_sha256']},indent=2)+'\n')
    print('diagnostics',len(cases),flush=True)
if __name__=='__main__':main()
