#!/usr/bin/env python3
"""Fresh input-only Openlike renewal grammar; no import-time writes.

96 predetermined cases: development32/sealed_final64, of which64 have200000
commands. No public exact prefix, solver source, replay table, or solver outcome
is used. The public input observations informing this design are documented in
PROVENANCE below. Final differs in grammar, alphabet, hazard, burst scheduler,
and phase switch schedule, not merely seed.

A constructive offline certificate reserves one exact-length physical slot per
birth and renews that slot after deletions. Slots of equal length are deliberately
reordered across births. The emitted input contains no coordinates. Unlike the
older contiguous-exchange generator, there are no zone partitions, adjacent-zone
merges/splits, spatial sweeps, or deletion of a contiguous physical window.

High attainable final KPI follows from a bounded outstanding deletion volume,
not terminal filling. Growth and renewal continue with the same rules until the
Nth command, including in the middle of a deletion burst. No end padding.
The witness T may exceed the volume lower bound: only F/T is certified; exact
OPT is claimed solely when its lower and upper bounds coincide.
"""
from __future__ import annotations
import hashlib
import heapq
import json
import random
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

VERSION = 'openlike-renewal-slot-v2-20261022'
PROVENANCE = {
 'input_only_sources': ['data/pipes/open/1.in..15.in', 'data/pipes/statement.pdf'],
 'observations': ['same-length insertion runs', 'small popular alphabets',
                  'staircase/dyadic size cohorts', 'mostly young deletion',
                  'tiny-size growth', 'mixed short motifs and renewal'],
 'no_solver_inspection': True, 'no_exact_public_prefix': True,
 'witness_is_feasibility_not_solver_policy': True,
}

@dataclass(frozen=True)
class Spec:
    name: str
    split: str
    seed: int
    n: int
    family: str
    variant: int
    phase_cuts: tuple[float, ...]
    grammar: tuple[str, ...]
    growth_ratio: float


def specs() -> list[Spec]:
    rows=[]
    families=('cohort_staircase','offgrid_ladder','popular_renewal','tiny_growth',
              'motif_renewal','age_size_hazard','quality_bursts','sticky_regimes')
    for split, scales, base in (
        ('development',(1200,12000,200000,200000),0x22D092A1),
        ('sealed_final',(1700,19000,200000,200000,200000,200000,200000,200000),0x22F493C7),
    ):
        for k,n in enumerate(scales):
            for f,family in enumerate(families):
                grams=(('ramp','hot3','word5','tiny') if split=='development' else
                       ('folded_ramp','hot4','word11','tiny_dither','skew_ladder'))
                offset=(f+3*k)%len(grams)
                grams=grams[offset:]+grams[:offset]
                growth=(0.65,0.45,0.09,32.,0.80,0.75,0.45,0.6)[f]
                if split=='sealed_final' and family!='tiny_growth': growth*=1.17
                rows.append(Spec(f"{'dev' if split=='development' else 'final'}_{k:02}_{f:02}",
                    split,base+100003*k+7919*f,n,family,k,
                    (0.,.29,.57,.81) if split=='development' else (0.,.13,.38,.64,.89),
                    grams,growth))
    assert len(rows)==96 and sum(s.n==200000 for s in rows)==64
    return rows

@dataclass
class Slot:
    start: int
    length: int
    pid: int=0
    born: int=0
    generation: int=0

class _Done(Exception): pass

class _Build:
    def __init__(self,spec,input_file,witness_file):
        self.s=spec; self.r=random.Random(spec.seed)
        self.inp=input_file; self.wit=witness_file
        self.ih=hashlib.sha256(); self.wh=hashlib.sha256()
        self.slots=[]; self.oldest=[]; self.count=self.pid=self.F=self.peak=self.rawT=self.T=0
        self.turn=self.renewed=self.deleted=self.initial_n=0
        self.max_absence=0; self.max_deleted_age=self.age_sum=0
        self.phase_hist=Counter(); self.lengths=Counter()
        self._input(f'1\n{spec.n}\n'.encode())

    def _input(self,b):
        self.ih.update(b)
        if self.inp is not None:self.inp.write(b)

    def _answer(self,b): self.wit.write(b); self.wh.update(b)

    def _room(self):
        if self.count==self.s.n:raise _Done

    def _phase(self):
        x=self.count/self.s.n
        return max(i for i,c in enumerate(self.s.phase_cuts) if x>=c)

    def _size(self,j):
        """Analogue grammars, never substrings copied from a public input."""
        phase=self._phase(); g=self.s.grammar[phase]; v=self.s.variant
        # Family-specific initial preference, changing to novel compositions.
        if self.s.family=='tiny_growth':g='tiny' if phase%2==0 else ('tiny_dither' if self.s.split=='sealed_final' else 'tiny')
        elif self.s.family=='cohort_staircase' and phase==0:g='ramp' if self.s.split=='development' else 'folded_ramp'
        elif self.s.family=='offgrid_ladder' and phase==0:g='dyadic' if self.s.split=='development' else 'skew_ladder'
        elif self.s.family=='popular_renewal' and phase==0:g='hot3' if self.s.split=='development' else 'hot4'
        elif self.s.family=='motif_renewal' and phase==0:g='word5' if self.s.split=='development' else 'word11'
        # Long homogeneous cohorts use independent run sizes and changed alphabets.
        run=(13+11*v) if self.s.split=='development' else (19+17*v)
        q=(j//run+self.turn//3+phase)
        if g=='ramp': x=1+(q*3+v)%40
        elif g=='folded_ramp':
            z=(q*7+3*v)%78; x=1+(z if z<40 else 78-z)
        elif g=='dyadic':x=(1,2,4,8,16,32)[q%6]
        elif g=='skew_ladder':x=(3,6,11,19,29,37,40)[(q+q//7)%7]
        elif g=='hot3':x=(4+v%3,9+v%4,15+v%5)[(q if self.r.random()<.85 else self.r.randrange(3))%3]
        elif g=='hot4':x=(3+v%4,11+v%5,23+v%3,34+v%6)[(q+q//5+self.r.randrange(2))%4]
        elif g=='tiny':x=1 if self.r.random()<.91 else self.r.choice((2,3,7,19))
        elif g=='tiny_dither':x=self.r.choice((1,1,1,2,2,3,4)) if q%19 else self.r.choice((17,23,31))
        elif g=='word5':x=(3,7,2,7,1)[(j+phase+v)%5]
        elif g=='word11':x=(2,13,5,19,2,29,7,13,3,31,5)[(j+3*(j//11)+v)%11]
        else:raise ValueError(g)
        if self.s.family=='sticky_regimes' and (j//(37+v*7))%3:
            x=1+(7*(phase+v)+11*(j//(37+v*7)))%40
        return max(1,min(40,x))

    def _positive(self,p,new=False):
        self._room()
        oldT=self.T
        if new:
            assert p.start==self.rawT
            self.rawT+=p.length
            self.T=20*((self.rawT+19)//20)
            self.slots.append(p)
        assert p.pid==0 and p.start+p.length<=self.T
        self.pid+=1;p.pid=self.pid;p.born=self.count
        self._input(f'{p.length}\n'.encode());self._answer(f'{(self.T-oldT)//20} {p.start}\n'.encode())
        self.F+=p.length;self.peak=max(self.peak,self.F)
        self.lengths[p.length]+=1;self.phase_hist[self._phase()]+=1
        self.count+=1
        heapq.heappush(self.oldest,(p.born,p.pid,len(self.slots)-1 if new else self.index[id(p)]))

    def _negative(self,p):
        self._room();assert p.pid>0
        self._input(f'{-p.pid}\n'.encode());self._answer(f'{p.start}\n'.encode())
        age=self.count-p.born;self.age_sum+=age;self.max_deleted_age=max(self.max_deleted_age,age)
        self.F-=p.length;p.pid=0;p.generation+=1;self.deleted+=1;self.count+=1
        self.max_absence=max(self.max_absence,self.rawT-self.F)

    def _old(self,excluded):
        while self.oldest:
            born,pid,i=heapq.heappop(self.oldest);p=self.slots[i]
            if p.pid==pid and p.born==born and i not in excluded:return i
        raise AssertionError('no old active slot')

    def _pick(self,q):
        selected=set();popped=set();m=len(self.slots);phase=self._phase()
        # Continuous oldest service retires the initial population; no fixed base.
        guaranteed=max(1,q//3) if self.turn%2==0 else 0
        for _ in range(guaranteed):
            i=self._old(selected);selected.add(i);popped.add(i)
        candidate=self.r.sample(range(m),min(m,max(12,8*q)))
        preferred=self._size(self.turn*97)
        fam=self.s.family
        if fam in ('cohort_staircase','offgrid_ladder','popular_renewal','sticky_regimes'):
            candidate.sort(key=lambda i:(abs(self.slots[i].length-preferred),-self.slots[i].born))
        elif fam=='age_size_hazard':
            candidate.sort(key=lambda i:((self.slots[i].length*(phase+3)+self.slots[i].born//(31+phase*17))%17,-self.slots[i].born))
        elif fam=='quality_bursts':
            width=23 if self.s.split=='development' else 71
            cohort=(self.turn*width)%max(width,self.pid)
            candidate.sort(key=lambda i:(abs(self.slots[i].pid-cohort)//width,-self.slots[i].born))
        else:candidate.sort(key=lambda i:-self.slots[i].born)
        for i in candidate:
            if len(selected)>=q:break
            selected.add(i)
        chosen=list(selected)
        # Capacity limit is independent of the endpoint, so truncating a burst is safe.
        budget=max(40,int(.075*self.rawT));total=0;ans=[]
        for i in chosen:
            if total+self.slots[i].length<=budget:
                ans.append(i);total+=self.slots[i].length
            elif i in popped:
                # Only entries actually removed from the age queue need restoration.
                p=self.slots[i];heapq.heappush(self.oldest,(p.born,p.pid,i))
        assert ans
        return ans

    def _cycle(self):
        # A fixed initial-volume threshold controls section-rounding overhead.
        # This depends on state only, never the remaining command budget.
        if self.rawT<400:
            p=Slot(self.rawT,self._size(self.pid));self.index[id(p)]=len(self.slots)
            self._positive(p,True);self.turn+=1
            return
        m=len(self.slots);phase=self._phase()
        if self.s.split=='development':q=max(1,min(128,m//(43 if self.turn%7==0 else 173)))
        else:q=max(1,min(193,m//(29 if (self.turn%11 in (2,3,7)) else 211)))
        ids=self._pick(q);pipes=[self.slots[i] for i in ids]
        if self.s.split=='development':pipes.sort(key=lambda p:((p.pid//7+self.turn)%3,-p.born))
        else:pipes.sort(key=lambda p:((p.length+phase*11)%7,p.pid%13,-p.born))
        for p in pipes:self._negative(p)
        # Refill permutation differs from deletion and physical order. Same-size
        # slots can have different PIDs over time; the hidden certificate is offline.
        buckets=defaultdict(list)
        for p in pipes:buckets[p.length].append(p)
        for v in buckets.values():self.r.shuffle(v)
        for j in range(len(pipes)):
            want=self._size(self.turn*53+j)
            length=min(buckets,key=lambda k:(abs(k-want),(k+phase*7)%41))
            p=buckets[length].pop()
            if not buckets[length]:del buckets[length]
            self._positive(p);self.renewed+=1
        assert self.F==self.rawT
        # Growth is part of every scheduled cycle, never a final suffix.
        growth=int(len(pipes)*self.s.growth_ratio)
        fraction=len(pipes)*self.s.growth_ratio-growth
        if self.r.random()<fraction:growth+=1
        for j in range(growth):
            p=Slot(self.rawT,self._size(self.pid+j))
            self.index[id(p)]=len(self.slots)
            self._positive(p,True)
        self.turn+=1

    def run(self):
        self.index={}
        initial=(4 if self.s.family=='tiny_growth' else max(24,self.s.n//80))
        try:
            for j in range(initial):
                p=Slot(self.rawT,self._size(j));self.index[id(p)]=len(self.slots)
                self._positive(p,True)
            self.initial_n=len(self.slots)
            while True:self._cycle()
        except _Done:pass
        assert self.count==self.s.n
        assert self.F==sum(p.length for p in self.slots if p.pid)
        assert self.F/self.T>=.85,(self.s,self.F,self.T)
        # Reservation intervals form a partition; at most one pipe per reservation.
        assert self.rawT==sum(p.length for p in self.slots)
        lower=20*((self.peak+19)//20)
        exact=lower==self.T
        return dict(source=Path(__file__).name,generator_version=VERSION,
            name=self.s.name,split=self.s.split,seed=self.s.seed,n=self.count,
            family=self.s.family,stratum=f'{self.s.family}_n{self.s.n}',
            sha256=self.ih.hexdigest(),witness_sha256=self.wh.hexdigest(),spec=asdict(self.s),
            F=self.F,T=self.T,bound=lower,
            bound_definition='20*ceil(peak_live/20), lower bound; witness upper bound is T',
            attainable_KPI=self.F/self.T,optimal_trench_interval=[lower,self.T],
            optimum_exact=exact, theoretical_max_KPI=(self.F/self.T if exact else None),
            certificate=dict(method='exact-length-slot-reservation',peak_live=self.peak,
                final_density=self.F/self.T,max_outstanding_deleted_volume=self.max_absence,
                reservations=len(self.slots),initial_reservations=self.initial_n,
                initial_pipes_still_live=sum(p.generation==0 and p.pid>0 for p in self.slots[:self.initial_n]),
                completed_cycles=self.turn,renewed=self.renewed,deletions=self.deleted,
                max_deleted_lifetime_commands=self.max_deleted_age,
                mean_deleted_lifetime_commands=self.age_sum/max(1,self.deleted),
                length_histogram=dict(sorted(self.lengths.items())),phase_insertions=dict(self.phase_hist),
                final_padding_commands=0,coordinates_in_input=False),
            provenance=PROVENANCE)


def generate(new_dir):
    """Create a new folder with96 inputs and manifest; no persistent witnesses."""
    dest=Path(new_dir);dest.mkdir(parents=True,exist_ok=False)
    source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with (dest/'manifest.jsonl').open('w') as mf,tempfile.TemporaryDirectory(prefix='pipes-openlike-witness-') as td:
        wp=Path(td)/'witness.txt'
        for s in specs():
            p=dest/(s.name+'.in')
            with p.open('wb') as inp,wp.open('wb') as wit:row=_Build(s,inp,wit).run()
            row.update(input=p.name,source_sha256=source_sha)
            mf.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');mf.flush()
            wp.unlink()
    return dest/'manifest.jsonl'


def replay_witness(metadata,destination):
    raw=dict(metadata['spec']);raw['phase_cuts']=tuple(raw['phase_cuts']);raw['grammar']=tuple(raw['grammar'])
    p=Path(destination)
    with p.open('xb') as wit:row=_Build(Spec(**raw),None,wit).run()
    assert row['sha256']==metadata['sha256']
    assert row['witness_sha256']==metadata['witness_sha256']
    return p

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('new_dir')
    print(generate(ap.parse_args().new_dir))
