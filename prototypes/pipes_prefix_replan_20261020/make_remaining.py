"""Post-freeze diagnostic counterexamples; never used to select the candidate."""
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'prototypes/pipes_open15_adversary_20261019'))
from construct import decode

def main():
    source=HERE/'final/solution.cpp';tables=decode(source)
    out=HERE/'evaluation/remaining';out.mkdir(parents=True,exist_ok=False);rows=[]
    for case in [8,11]:
        commands,positions=tables[case-1]
        result=subprocess.run([str(ROOT/'prototypes/pipes_prefix_shock_20261019/allocator-probe'),'bestfit',str(ROOT/'prototypes/pipes_prefix_shock_20261019/tape.txt')],
                              input='\n'.join(map(str,commands+[0]))+'\n',text=True,capture_output=True,check=True)
        bf=T=pid=0;live=set();best=None
        for step,(c,x,line) in enumerate(zip(commands,positions,result.stdout.splitlines()),1):
            if c>0:
                bf+=20*int(line.split()[0]);T=max(T,20*((x+c+19)//20));pid+=1;live.add(pid)
            else:live.remove(-c)
            count=(bf+39)//40
            if step+len(live)+count>200000 or not live or step==len(commands):continue
            key=(40*count/max(T,40*count),step)
            if best is None or key<best[0]:best=(key,step,T,bf,sorted(live),count)
        key,cut,T,bf,live,count=best
        stream=commands[:cut]+[-p for p in live]+[40]*count
        name=f'remaining-open{case}-p{cut}';path=out/(name+'.in')
        path.write_text('1\n'+str(len(stream))+'\n'+'\n'.join(map(str,stream))+'\n')
        rows.append({'id':name,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'case':case,'prefix':cut,'prefix_T':T,'prefix_BF_T':bf,'predicted_KPI':key[0],
                     'construction':'delete every live PID, refill rounded BF trench with40m pipes',
                     'scope':'post-freeze candidate-targeted diagnostic, not independent confirmation'})
    (out/'manifest.json').write_text(json.dumps({'tests':rows,'selection_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'used_in_selection':False},indent=2)+'\n')
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
