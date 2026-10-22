#!/usr/bin/env python3
"""Fresh gradually growing Pipes streams with finite, changing lifetime hazards.

No inputs are created on import. No solver, public input, answer, or external
file is read by this generator. generate(new_dir) writes48 inputs+manifest only.
Witnesses are temporary. replay_witness(record,path) recreates one certificate.

Offline bands are opened gradually. A band contains small contiguous cohorts,
but their insertions and later multi-band renewals are interleaved. Renewal
repartitions the released spans using a different size grammar: no fixed exact
length slots. Finite cohort due dates depend on size AND current hazard regime;
the same size becomes long- or short-lived in different phases. Initial cohorts
have explicit deadlines <=.42N (service may lag under the deletion-volume cap).

Every completed band/renewal densely packs its own spans. A transaction reserves
or deletes at most7.5% of existing arena volume (40m allowance only at startup).
Thus arbitrary endpoint truncation has witness KPI>=.85 once arena>=400m;
startup finishes far before the minimum12000-command horizon. There is no final
padding, time-horizon drain, fixed background, or adaptation to solver results.
The witness is an upper bound on OPT trench, not an exact OPT claim.
"""
from __future__ import annotations
import hashlib
import heapq
import json
import random
import tempfile
from collections import Counter
from dataclasses import asdict,dataclass,field
from pathlib import Path

VERSION='gradual-bands-finite-size-hazards-v1-20261022'

@dataclass(frozen=True)
class Spec:
    name:str
    split:str
    seed:int
    n:int
    family:str
    variant:int
    switches:tuple[float,...]
    grammar:tuple[str,...]
    target_positive:float=.65


def specs():
    out=[]
    fs=('interleaved_words','shifted_popular_sets','layered_quality_bursts','mixed_markov')
    for split,ns,base in (
        ('development',(12000,45000,200000,200000),0x22D6A9C1),
        ('sealed_final',(19000,67000,200000,200000,200000,200000,200000,200000),0x22F8B3D7),
    ):
        for k,n in enumerate(ns):
            for f,family in enumerate(fs):
                gs=(('word5','triad','bimodal','walk') if split=='development' else
                    ('word11','four_modes','residue_braid','sparse_ladder','renewal_ring'))
                j=(k+f)%len(gs);gs=gs[j:]+gs[:j]
                out.append(Spec(f"{'dev' if split=='development' else 'final'}_{k:02}_{f:02}",
                    split,base+100003*k+8191*f,n,family,k,
                    (0.,.23,.51,.78) if split=='development' else (0.,.11,.34,.63,.86),gs))
    assert len(out)==48 and sum(s.n==200000 for s in out)==32
    return out

@dataclass
class Pipe:
    start:int
    length:int
    pid:int=0
    born:int=0

@dataclass
class Cohort:
    start:int
    length:int
    colour:int
    pipes:list[Pipe]=field(default_factory=list)
    version:int=0
    due:int=0
    initial:bool=False
    renewals:int=0
    index:int=-1

class _Done(Exception):pass

class _Build:
    def __init__(self,s,inp,wit):
        self.s=s;self.r=random.Random(s.seed);self.inp=inp;self.wit=wit
        self.ih=hashlib.sha256();self.wh=hashlib.sha256()
        self.count=self.pid=self.F=self.peak=self.T=self.arena=0
        self.positive=self.negative=self.turn=self.band_count=0
        self.groups=[];self.queue=[];self.live={};self.ages=[]
        self.max_debt=0;self.phases=Counter();self.sizes=Counter()
        self.hazard_roles=Counter();self.initial_ids=set();self.initial_deleted=0
        self._input(f'1\n{s.n}\n'.encode())

    def _input(self,b):
        self.ih.update(b)
        if self.inp is not None:self.inp.write(b)

    def _answer(self,b):self.wit.write(b);self.wh.update(b)

    def _room(self):
        if self.count==self.s.n:raise _Done

    def _phase(self):
        return max(i for i,x in enumerate(self.s.switches) if self.count/self.s.n>=x)

    def _size(self,j,colour):
        p=self._phase();g=self.s.grammar[p];v=self.s.variant;r=self.r
        # Markov state is a slowly moving regime, not a repeated public prefix.
        if self.s.family=='mixed_markov' and (self.turn//(3+v%3)+colour)%3==0:
            g='walk' if self.s.split=='development' else 'renewal_ring'
        if self.s.family=='shifted_popular_sets':
            g='triad' if self.s.split=='development' else 'four_modes'
        if self.s.family=='interleaved_words' and (colour+p)%3==0:
            g='word5' if self.s.split=='development' else 'word11'
        if g=='word5':x=(2,7,3,11,5)[(j+colour*2+p)%5]
        elif g=='triad':x=(2+2*p+v%2,7+3*p,16+p)[(j//(2+colour%4)+colour)%3]
        elif g=='bimodal':x=r.choice((1,2,3,4)) if (colour+p)%2 else r.choice((17,21,29,35))
        elif g=='walk':x=1+(j*(1+colour%3)+self.turn//3+7*p+v)%23
        elif g=='word11':x=(3,17,2,9,23,5,11,2,31,7,13)[(j+3*colour+2*p+j//11)%11]
        elif g=='four_modes':x=(3+v%3,9+2*p,19+p,33-p)[(j//(3+colour%5)+colour+p)%4]
        elif g=='residue_braid':x=(1,4,7,10,13,22,28,37)[(j*3+colour*5+p)%8]
        elif g=='sparse_ladder':x=(2,5,11,19,29,38)[(j//(3+p)+colour+j//17)%6]
        elif g=='renewal_ring':x=(2,3,5,8,13,21,34)[(j*(1+colour%2)+self.turn//5+p)%7]
        else:raise ValueError(g)
        # Hidden cohort offsets overlap in size, so size alone is not a label.
        if (colour+self.turn+p)%5==0:x+=r.choice((-2,-1,0,1,2))
        return max(1,min(40,x))

    def _partition(self,start,length,colour,old_count=None):
        arr=[];remain=length;j=0
        while remain:
            size=min(remain,self._size(j+self.turn*17,colour))
            arr.append(Pipe(start+length-remain,size));remain-=size;j+=1
        # Limit count explosions after grammar shifts without forcing an exact
        # histogram. Positive fraction is controlled by ordinary ongoing growth.
        if old_count and len(arr)>max(old_count+2,int(1.65*old_count)):
            target=max(old_count+2,int(1.65*old_count));arr=[]
            width,extra=divmod(length,target)
            if width>=1:
                pos=start
                for j in range(target):
                    size=width+(j<extra);assert 1<=size<=40
                    arr.append(Pipe(pos,size));pos+=size
        assert sum(p.length for p in arr)==length
        return arr

    def _place(self,p):
        self._room();assert p.pid==0
        required=20*((p.start+p.length+19)//20);newT=max(self.T,required)
        self.pid+=1;p.pid=self.pid;p.born=self.count
        self._input(f'{p.length}\n'.encode());self._answer(f'{(newT-self.T)//20} {p.start}\n'.encode())
        self.T=newT;self.F+=p.length;self.peak=max(self.peak,self.F)
        self.live[p.pid]=p;self.positive+=1;self.count+=1
        self.sizes[p.length]+=1;self.phases[self._phase()]+=1

    def _remove(self,p):
        self._room();assert self.live.pop(p.pid) is p
        self._input(f'{-p.pid}\n'.encode());self._answer(f'{p.start}\n'.encode())
        self.ages.append(self.count-p.born)
        if p.pid in self.initial_ids:self.initial_deleted+=1
        p.pid=0;self.F-=p.length;self.negative+=1;self.count+=1
        self.max_debt=max(self.max_debt,self.arena-self.F)

    def _schedule(self,g):
        mean=g.length/max(1,len(g.pipes));phase=self._phase()
        # The size->hazard relationship explicitly reverses after a phase change.
        if phase%3==0:role=2 if mean<8 else (0 if mean>15 else 1)
        elif phase%3==1:role=0 if mean<8 else (2 if mean>15 else 1)
        else:role=(int(mean)+g.colour+self.turn)%3
        # Colour introduces overlapping lifetimes within the same size profile.
        if (g.colour+self.turn)%5==0:role=(role+1)%3
        if self.s.split=='development':
            delay=(self.r.randint(11,101),self.r.randint(350,2700),self.r.randint(max(600,self.s.n//12),max(1200,self.s.n*2//5)))[role]
        else:
            delay=(self.r.randint(17,173),self.r.randint(670,4700),self.r.randint(max(850,self.s.n//9),max(1600,self.s.n*7//16)))[role]
        g.due=self.count+delay
        if g.initial and g.renewals==0:g.due=min(g.due,int(.42*self.s.n))
        assert g.due>self.count
        g.version+=1;self.hazard_roles[(phase,role)]+=1
        heapq.heappush(self.queue,(g.due,g.index,g.index,g.version))

    def _new_band(self,initial=False):
        # Small startup bands avoid any large filled initial arena. Later band
        # size remains <=7.5% of pre-existing arena, even if truncated mid-fill.
        cap=max(20,min(1600,int(.07*self.arena)))
        units=max(1,cap//20)
        total=20*self.r.randint(max(1,units//2),units)
        k=min(total//20,(3 if self.s.split=='development' else 5))
        cuts=[20]*k
        for _ in range(total//20-k):cuts[self.r.randrange(k)]+=20
        pos=self.arena;new=[]
        for j,length in enumerate(cuts):
            g=Cohort(pos,length,(self.band_count*7+j*11)%19,initial=initial,index=len(self.groups)+len(new))
            g.pipes=self._partition(pos,length,g.colour);new.append(g);pos+=length
        self.arena=pos;self.groups.extend(new);self.band_count+=1
        # Deliberately interleave finite lifetime cohorts in the arrival order.
        arriving=[(g,p) for g in new for p in g.pipes]
        if self.s.split=='development':
            self.r.shuffle(arriving)
        else:
            arriving.sort(key=lambda z:((z[1].length+self.turn+z[0].colour)%7,-z[0].colour,z[1].start%11))
        for g,p in arriving:
            self._place(p)
            if initial:self.initial_ids.add(p.pid)
        assert self.F==self.arena
        for g in new:self._schedule(g)

    def _pick_due(self):
        budget=max(0,int(.075*self.arena))
        selected=[];volume=0;deferred=[]
        want=(1+self.turn%3) if self.s.split=='development' else (2+(self.turn*7)%5)
        while self.queue and len(selected)<want:
            due,seq,i,version=heapq.heappop(self.queue);g=self.groups[i]
            if g.version!=version:continue
            if due>self.count:
                deferred.append((due,seq,i,version));break
            if g.length+volume<=budget:
                selected.append(g);volume+=g.length
            else:
                deferred.append((due,seq,i,version))
                if len(deferred)>20:break
        for e in deferred:heapq.heappush(self.queue,e)
        return selected

    def _renew(self,gs):
        old=[p for g in gs for p in g.pipes]
        if self.s.family=='layered_quality_bursts':
            old.sort(key=lambda p:((p.pid//(11 if self.s.split=='development' else 29))%5,-p.born))
        elif self.s.split=='development':self.r.shuffle(old)
        else:old.sort(key=lambda p:((p.length+self.turn)%11,-p.born,p.pid%17))
        for p in old:self._remove(p)
        arriving=[]
        for g in gs:
            g.pipes=self._partition(g.start,g.length,g.colour,old_count=len(g.pipes));g.renewals+=1
            arriving.extend((g,p) for p in g.pipes)
        # Two splits use different arrival shuffles and different grammar lengths.
        if self.s.split=='development':self.r.shuffle(arriving)
        else:arriving.sort(key=lambda z:((z[1].length*3+z[0].colour+self.turn)%13,z[1].start%7))
        for g,p in arriving:self._place(p)
        assert self.F==self.arena
        for g in gs:self._schedule(g)
        self.turn+=1

    def run(self):
        try:
            self._new_band(initial=True)
            while True:
                # Ongoing growth balances *commands*, giving ~65% positives.
                # No condition here reads remaining N or a desired final KPI.
                ratio=self.positive/max(1,self.positive+self.negative)
                if self.arena<400 or ratio<self.s.target_positive:
                    self._new_band();continue
                due=self._pick_due()
                if due:self._renew(due)
                else:self._new_band()
        except _Done:pass
        assert self.count==self.s.n
        assert self.arena>=400
        assert self.F==sum(p.length for p in self.live.values())
        assert self.F/self.T>=.85,(self.s,self.F,self.T,self.arena)
        assert not any(pid in self.live for pid in self.initial_ids),'initial finite cohorts were not serviced'
        lower=20*((self.peak+19)//20)
        ages=sorted(self.ages)
        def q(x):return ages[round((len(ages)-1)*x)] if ages else None
        return dict(source=Path(__file__).name,generator_version=VERSION,name=self.s.name,
            split=self.s.split,seed=self.s.seed,n=self.count,family=self.s.family,
            stratum=f'{self.s.family}_n{self.s.n}',spec=asdict(self.s),
            sha256=self.ih.hexdigest(),witness_sha256=self.wh.hexdigest(),
            F=self.F,T=self.T,bound=lower,attainable_KPI=self.F/self.T,
            bound_definition='peak-volume lower bound; witness T is a feasible upper bound',
            optimal_trench_interval=[lower,self.T],optimum_exact=lower==self.T,
            theoretical_max_KPI=self.F/self.T if lower==self.T else None,
            certificate=dict(method='gradual-hidden-bands-repartitioned-finite-cohorts',
                bands=self.band_count,cohorts=len(self.groups),renewal_rounds=self.turn,
                positive_commands=self.positive,negative_commands=self.negative,
                positive_fraction=self.positive/self.count,target_positive_fraction=self.s.target_positive,
                peak_live_volume=self.peak,final_live_count=len(self.live),
                max_unfilled_reserved_volume=self.max_debt,
                initial_pipes=len(self.initial_ids),initial_pipes_deleted=self.initial_deleted,
                initial_pipes_still_live=sum(pid in self.live for pid in self.initial_ids),
                initial_deadline_limit=int(.42*self.s.n),
                finite_due_dates=True,hazard_changes_at=list(self.s.switches[1:]),
                deleted_age_q10_q50_q90_q99=[q(x) for x in(.1,.5,.9,.99)],
                size_histogram=dict(sorted(self.sizes.items())),phase_insertions=dict(self.phases),
                scheduled_hazard_counts={f'{a}:{b}':v for (a,b),v in self.hazard_roles.items()},
                final_padding_commands=0,coordinates_in_input=False),
            provenance=dict(public_commands_copied=0,solver_inspected=False,
                baseline_results_used=False,heldout_results_used=False,
                model_limit='synthetic lifetime stress; no closed-distribution or exact-OPT claim'))


def generate(new_dir):
    p=Path(new_dir);p.mkdir(parents=True,exist_ok=False)
    sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();seen=set()
    with (p/'manifest.jsonl').open('w') as mf,tempfile.TemporaryDirectory(prefix='pipes-growing-witness-') as td:
        wp=Path(td)/'witness.txt'
        for s in specs():
            ip=p/(s.name+'.in')
            with ip.open('wb') as inp,wp.open('wb') as wit:r=_Build(s,inp,wit).run()
            assert r['sha256'] not in seen,'deterministic duplicate input'
            seen.add(r['sha256']);r.update(input=ip.name,source_sha256=sha)
            mf.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n');mf.flush();wp.unlink()
    return p/'manifest.jsonl'


def replay_witness(metadata,destination):
    raw=dict(metadata['spec']);raw['switches']=tuple(raw['switches']);raw['grammar']=tuple(raw['grammar'])
    p=Path(destination)
    with p.open('xb') as wit:r=_Build(Spec(**raw),None,wit).run()
    assert r['sha256']==metadata['sha256'] and r['witness_sha256']==metadata['witness_sha256']
    return p

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('new_dir')
    print(generate(a.parse_args().new_dir))
