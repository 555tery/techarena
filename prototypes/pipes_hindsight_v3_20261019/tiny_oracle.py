"""Exact bounded offline interval packing for tiny fixtures, diagnostic only.

All integer starts are enumerated. Fixed past placements cannot move. A result
is exact only if search completes; timeout/node exhaustion is reported, never
converted into infeasibility. This file is not linked into the causal solver.
"""
from functools import lru_cache

def optimal(commands, fixed=None, lower=0, upper=200, node_cap=200000):
    fixed=fixed or {};pipes=[];alive={};volume=peak=0
    for t,c in enumerate(commands):
        if c>0:
            pipes.append([c,t,len(commands)+1]);pid=len(pipes)-1;alive[pid]=c
            volume+=c;peak=max(peak,volume)
        else:
            pid=-c-1;pipes[pid][2]=t;volume-=alive.pop(pid)
    conflicts=[[max(a[1],b[1])<min(a[2],b[2]) for b in pipes] for a in pipes]
    nodes=0
    for height in range(max(lower,20*((peak+19)//20)),upper+1,20):
        starts=dict(fixed)
        if any(p<0 or p+pipes[i][0]>height for i,p in starts.items()):continue
        if any(conflicts[i][j] and not (p+pipes[i][0]<=q or q+pipes[j][0]<=p)
               for i,p in starts.items() for j,q in starts.items() if i<j):continue
        def choices(i):
            length=pipes[i][0]
            return [s for s in range(height-length+1)
                    if all(not conflicts[i][j] or s+length<=p or p+pipes[j][0]<=s
                           for j,p in starts.items())]
        def search():
            nonlocal nodes
            nodes+=1
            if nodes>node_cap:raise TimeoutError('node cap, not infeasibility')
            if len(starts)==len(pipes):return dict(starts)
            pending=[(choices(i),i) for i in range(len(pipes)) if i not in starts]
            positions,i=min(pending,key=lambda x:(len(x[0]),-sum(conflicts[x[1]]),-pipes[x[1]][0],x[1]))
            for s in positions:
                starts[i]=s;r=search()
                if r is not None:return r
                del starts[i]
            return None
        try:r=search()
        except TimeoutError:return {'complete':False,'nodes':nodes,'tested_height':height}
        if r is not None:return {'complete':True,'optimum':height,'starts':r,'nodes':nodes,'peak':peak}
    return {'complete':True,'infeasible_up_to':upper,'nodes':nodes}

if __name__=='__main__':
    import json
    cases=[[5,5,1,-1,9,-2,11], [7,7,6,-2,5,-1,-3,15],
           [10,10,-1,6,4,-2,10], [8,5,7,-2,3,-1,12]]
    print(json.dumps([{'commands':c,**optimal(c,upper=60)} for c in cases]))
