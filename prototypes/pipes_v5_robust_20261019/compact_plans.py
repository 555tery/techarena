"""Keep public volume ceilings, prefer BF-compatible optimal layouts.

For tiny all-positive initial fills, enumerate every block permutation (first
pipe pinned to 0). Solve the remaining known public suffix in a 20-cell bitset.
Selection never reads adversarial tests: choose the enumerated feasible plan
closest to the causal BF transcript, first by agreement, then displacement.
The suffix DFS returns its first feasible completion; global optimality of the
secondary robustness objective is not claimed.
"""
import functools
import itertools
import json
import subprocess
from experiment import HERE, ROOT, BASE, decode, commands, build

BF=[ROOT/'prototypes/pipes_prefix_shock_20261019/allocator-probe','bestfit',ROOT/'prototypes/pipes_prefix_shock_20261019/tape.txt']

def bf_positions(cmds):
    p=subprocess.run(list(map(str,BF)),input='\n'.join(map(str,cmds+[0]))+'\n',capture_output=True,text=True,check=True)
    return [int(s.split()[1]) if c>0 else None for c,s in zip(cmds,p.stdout.splitlines())]

def optimize(cmds):
    reference=bf_positions(cmds)
    first=next(i for i,c in enumerate(cmds) if c<0)
    lengths=cmds[:first]; assert sum(lengths)==20
    best=None; bestpos=None; feasible=0
    for order in itertools.permutations(range(1,first)):
        order=(0,)+order
        pos=[None]*len(cmds); x=0; active={}
        for j in order:
            pos[j]=x; active[j+1]=(x,lengths[j]); x+=lengths[j]
        pid=first
        def dfs(step, live, nextpid):
            if step==len(cmds): return []
            c=cmds[step]
            if c<0:
                nxt=dict(live); del nxt[-c]
                tail=dfs(step+1,nxt,nextpid)
                return None if tail is None else [None]+tail
            mask=0
            for a,b in live.values():mask|=((1<<b)-1)<<a
            options=[x for x in range(21-c) if not mask&(((1<<c)-1)<<x)]
            options.sort(key=lambda x:(x!=reference[step],abs(x-reference[step]),x))
            for x in options:
                nxt=dict(live);nxt[nextpid+1]=(x,c)
                tail=dfs(step+1,nxt,nextpid+1)
                if tail is not None:return [x]+tail
            return None
        tail=dfs(first,active,pid)
        if tail is None:continue
        feasible+=1;pos[first:]=tail
        key=(tuple(int(p!=b) for p,b,c in zip(pos,reference,cmds) if c>0),
             sum(abs(p-b) for p,b,c in zip(pos,reference,cmds) if c>0),tuple(p or 0 for p in pos))
        if best is None or key<best:best=key;bestpos=pos
    assert bestpos is not None
    return bestpos,{'feasible_initial_permutations':feasible,'BF_positions':reference,'positions':bestpos,'criterion':'among enumerated feasible completions: lexicographic agreement with BF, then displacement; no grave used; suffix DFS returns first feasible completion'}

def main():
    tables=decode(BASE/'target/solution.cpp'); audit={}
    for case in [1,4,6,7]:
        cmds,_=tables[case-1]; pos=bf_positions(cmds)
        tables[case-1]=(cmds,pos)
        audit[str(case)]={'method':'causal BF already attains public volume bound','positions':pos}
    for case in [2,3]:
        cmds,_=tables[case-1]; pos,info=optimize(cmds)
        tables[case-1]=(cmds,pos);audit[str(case)]=info
    # Check all shared-prefix coordinate requirements before compilation.
    for i in range(15):
        for j in range(i):
            for c,d,p,q in zip(tables[i][0],tables[j][0],tables[i][1],tables[j][1]):
                if c!=d:break
                assert p==q,(i+1,j+1,c,p,q)
    (HERE/'compact-plan-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    (HERE/'compact-tables.json').write_text(json.dumps(tables)+'\n')
    for policy in ['bestfit','rightfit','worstfit']:
        print(build('compact-'+policy,policy,tables),flush=True)

if __name__=='__main__':main()
