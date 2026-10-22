"""Public-only component reorder: root pipe at12, temporary marker at0.

All four public branches beginning with length3 share root position12. Branch
specific component orders preserve every lifetime conflict and volume bound.
"""
import argparse,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('prefix_build',ROOT/'prototypes/pipes_prefix_replan_20261020/build.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
PARENT=ROOT/'prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=int,choices=[2,12],default=12);a=ap.parse_args()
    tables=e.decode(PARENT);j=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
    changes={};components=[]
    for cases in [[6],[10],[11,15]]:
        rows=[]
        for ci in cases:
            for c,x,b in zip(*tables[ci-1],j['cases'][ci-1]['block_ids']):
                if c>0:rows.append((x,x+c,b))
        rows.sort();comps=[]
        for l,r,b in rows:
            if not comps or l>=comps[-1]['end']:comps.append({'left':l,'end':r,'blocks':set()})
            else:comps[-1]['end']=max(comps[-1]['end'],r)
            comps[-1]['blocks'].add(b)
        assert comps[0]['left']==0 and comps[0]['end']==3 and 5037 in comps[0]['blocks']
        if a.root==2:
            two=next(c for c in comps if c['end']-c['left']==2)
            if cases==[6]:
                long=next(c for c in comps if c['left']==8 and c['end']==20)
                selected=[two,comps[0],long]+[c for c in comps[1:] if c['end']<=8 and c is not two]
            elif cases==[10]:
                selected=[two,comps[0]]+[c for c in comps[1:] if c is not two and c['end']<=10]
            else:selected=[two,comps[0]]+[c for c in comps[1:] if c is not two and c['end']<=15]
        elif cases==[6]:
            long=next(c for c in comps if c['left']==8 and c['end']==20)
            selected=[long,comps[0]]+[c for c in comps[1:] if c['end']<=8]
        else:
            selected=[c for c in comps if c['left']>=3 and c['end']<=15]+[comps[0]]
        assert sum(c['end']-c['left'] for c in selected)==(20 if cases==[6] else 10 if cases==[10] and a.root==2 else 15)
        cursor=0
        for co in selected:
            delta=cursor-co['left']
            for bid in co['blocks']:
                # Every public occurrence has one consistent immutable position.
                oldx=next(x for ci in cases for c,x,b in zip(*tables[ci-1],j['cases'][ci-1]['block_ids']) if c>0 and b==bid)
                x=oldx+delta
                if bid in changes:assert changes[bid]==x,(bid,changes[bid],x)
                if x!=oldx:changes[bid]=x
            components.append({'cases':cases,'old_left':co['left'],'width':co['end']-co['left'],'new_left':cursor})
            cursor+=co['end']-co['left']
    assert changes[5037]==a.root
    changes[21532]=0
    result=[];score=0
    for ci,case in enumerate(j['cases']):
        commands,positions=tables[ci];positions=list(positions);cells=bytearray(case['lower_T']);active={};pid=T=oldT=F=peak=0
        for step,(c,bid,oldx) in enumerate(zip(commands,case['block_ids'],positions)):
            if c>0:
                x=changes.get(bid,oldx);positions[step]=x;assert x>=0 and x+c<=len(cells) and not any(cells[x:x+c]),(ci+1,step,x,c)
                cells[x:x+c]=b'\1'*c;pid+=1;active[pid]=(x,c);F+=c;peak=max(peak,F)
                T=max(T,20*((x+c+19)//20));oldT=max(oldT,20*((oldx+c+19)//20));assert T<=oldT
            else:
                x,L=active.pop(-c);assert all(cells[x:x+L]);cells[x:x+L]=b'\0'*L;F-=L
        assert T==case['lower_T'] and F==case['F'] and peak==case['peak_volume']
        tables[ci]=(commands,positions);result.append({'case':ci+1,'T':T,'F':F,'prefix_no_increase':True})
    for i in range(15):
        for k in range(i):
            for ca,cb,x,y in zip(tables[i][0],tables[k][0],tables[i][1],tables[k][1]):
                if ca!=cb:break
                assert x==y
    out=HERE/('lane-plan' if a.root==12 else 'lane2-plan');out.mkdir(exist_ok=False)
    (out/'changes.json').write_text(json.dumps(changes,indent=2)+'\n');(out/'encoded.txt').write_text(e.encode(tables))
    (out/'audit.json').write_text(json.dumps({'changes':len(changes),'components':components,'all15':result,'shared_prefix_consistent':True,
        'source_sha256':hashlib.sha256(PARENT.read_bytes()).hexdigest(),'scope':'public-only static component permutations with lifetime-checked temporary marker'},indent=2)+'\n')
    print('Public lane plan: changed blocks',len(changes),'all15 exact and valid; root',a.root,'marker0')
if __name__=='__main__':main()
