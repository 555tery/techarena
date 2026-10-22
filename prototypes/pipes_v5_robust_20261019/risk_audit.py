"""Check maximum excavation ratios over every common-prefix step, not its end."""
import json
import subprocess
import sys
from experiment import HERE, ROOT, BASE, decode, harness, sha

BF=[str(ROOT/'prototypes/pipes_prefix_shock_20261019/allocator-probe'),'bestfit',str(ROOT/'prototypes/pipes_prefix_shock_20261019/tape.txt')]

def main():
    name=sys.argv[1] if len(sys.argv)>1 else 'candidate-v2'
    old=decode(BASE/'target/solution.cpp');new=decode(HERE/name/'solution.cpp')
    rows=[]
    for case,((cmd,p),(cmd2,q)) in enumerate(zip(old,new),1):
        assert cmd==cmd2
        out=subprocess.run(BF,input='\n'.join(map(str,cmd+[0]))+'\n',text=True,capture_output=True,check=True)
        bt=ot=nt=0;live=peak=0;pid=0;pipes={};entry={'case':case,'baseline_max_ratio':1,'candidate_max_ratio':1}
        trace=[]
        for i,(c,x,y,line) in enumerate(zip(cmd,p,q,out.stdout.splitlines()),1):
            if c>0:
                bt+=20*int(line.split()[0]);ot=max(ot,20*((x+c+19)//20));nt=max(nt,20*((y+c+19)//20))
                pid+=1;pipes[pid]=c;live+=c;peak=max(peak,live)
            else:live-=pipes.pop(-c)
            for name,t in [('baseline',ot),('candidate',nt)]:
                ratio=t/bt if bt else 1
                if ratio>entry[name+'_max_ratio']:
                    entry[name+'_max_ratio']=ratio;entry[name+'_worst_step']=i
            if c<0:initial=False
            trace.append((bt,ot,nt))
        entry.update(BF_final_T=bt,baseline_final_T=ot,candidate_final_T=nt)
        rows.append(entry)
        print(entry,flush=True)
        # Three additional early reservations outside the former four cases.
        if case in [5,7,9]:
            first_delete=next(i for i,c in enumerate(cmd) if c<0)
            limit=min(first_delete,300)
            cut=max(range(1,limit+1),key=lambda k:(trace[k-1][1]/trace[k-1][0],-k))
            prefix=cmd[:cut]
            first=40 if cmd[cut]!=40 else 39
            total=sum(prefix)+first
            suffix=[first]+[1]*((-total)%20)
            data=prefix+suffix
            path=HERE/'new_attacks'/f'attack-extra-open{case}-p{cut}.in'
            path.write_text('1\n'+str(len(data))+'\n'+'\n'.join(map(str,data))+'\n')
            mpath=HERE/'new_attacks/extra-manifest.json'
            extra=json.loads(mpath.read_text()) if mpath.exists() else {'tests':[]}
            row={'file':str(path.relative_to(ROOT)),'case':case,'cut':cut,'prefix':prefix,'suffix':suffix,
                 'sha256':sha(path),'scope':'extra diagnostics after candidate freeze; no drain; all original pipes remain',
                 'max_prefix_ratio':max(t[1]/t[0] for t in trace[:cut]),**harness.parse_test(path)}
            extra['tests']=[x for x in extra['tests'] if x['case']!=case]+[row]
            mpath.write_text(json.dumps(extra,indent=2)+'\n')
    (HERE/'cumulative-risk-audit.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':main()
