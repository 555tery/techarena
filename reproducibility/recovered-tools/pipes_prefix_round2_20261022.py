#!/usr/bin/env python3
"""Directed prefix24 input-only generator, with constructive offline witnesses.

8 development +16 sealed_final, 14 streams with 200000 commands. Every case
starts with an exact common Open11/15 or Open8/13 prefix, diverges immediately,
then runs repeated volume-preserving renewal with changing size grammars.
The prefix witness uses causal best-fit, never a replay table or solver answer.
Later witness coordinates only certify feasibility and are absent from inputs.
No import-time writes. generate() must be called after the CPU worker is free.
"""
from __future__ import annotations
import hashlib
import json
import random
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

VERSION='directed-prefix-renewal-v2-20261022'
ROOT=Path('/Users/555tery/techarena')
PROVENANCE={
 'input_only_sources':['data/pipes/open/8.in','data/pipes/open/11.in',
                       'data/pipes/open/13.in','data/pipes/open/15.in'],
 'mechanism':'shared public prefix; immediate mismatch; sustained renewable repartitions',
 'prefix_witness':'causal best-fit, without replay coordinates',
 'no_solver_response_read':True,'no_solver_execution':True,
 'no_terminal_padding':True,'no_fixed_forever_background':True,
 'optimum_claim':'rounded peak volume is only a lower bound; T is a feasible upper bound',
}

@dataclass(frozen=True)
class Spec:
    name:str
    split:str
    seed:int
    n:int
    public_pair:tuple[int,int]
    prefix_cut:int
    family:str
    arena:int
    zone_target:int
    phase_cuts:tuple[float,...]
    grammar:tuple[str,...]
    variant:int


def specs():
    rows=[]
    for split,cuts,base in (
        ('development',(2,18,63,127),0x22D04D71),
        ('sealed_final',(2,7,18,31,63,127,31,127),0x22F04D71),
    ):
        for g,pair in enumerate(((11,15),(8,13))):
            for j,cut in enumerate(cuts):
                long=j>=2 if split=='development' else j>=3
                n=200000 if long else ((12000,28000)[j%2] if split=='development' else (17000,37000,61000)[j])
                arena=((2560,5120,10240,20480)[j%4] if split=='development' else (3200,6400,12800,25600)[j%4])
                grams=(('stair','dyadic','word','plateau') if split=='development' else
                       ('offgrid','antiphase','palindrome','tiny_large','residue'))
                shift=(g+3*j)%len(grams);grams=grams[shift:]+grams[:shift]
                family=('cohort_permute','age_fold')[g] if split=='development' else ('braided_cohorts','phase_reversal')[g]
                rows.append(Spec(f"{'dev' if split=='development' else 'final'}_{g:02d}_{j:02d}",
                    split,base+65537*g+1009*j,n,pair,cut,family,arena,
                    (128+32*(j%3)) if split=='development' else (173+38*(j%4)),
                    (0.,.24,.53,.79) if split=='development' else (0.,.12,.36,.62,.87),
                    grams,j))
    assert len(rows)==24
    assert sum(s.split=='development' for s in rows)==8
    assert sum(s.n==200000 for s in rows)==14
    assert {s.prefix_cut for s in rows}=={2,7,18,31,63,127}
    return rows

@dataclass
class Pipe:
    start:int
    length:int
    pid:int=0
    born:int=0

@dataclass
class Zone:
    start:int
    length:int
    pipes:list[Pipe]
    served:int=-1

class _Done(Exception):pass


def _prefix(spec):
    """Read only cut+1 public commands; no historical solver outputs."""
    rows=[]
    for number in spec.public_pair:
        tokens=[]
        with (ROOT/f'data/pipes/open/{number}.in').open() as f:
            for line in f:
                tokens.extend(map(int,line.split()))
                if len(tokens)>=spec.prefix_cut+3:break
        assert len(tokens)>=spec.prefix_cut+3
        rows.append(tokens[2:spec.prefix_cut+3])
    assert rows[0][:spec.prefix_cut]==rows[1][:spec.prefix_cut]
    return rows[0][:spec.prefix_cut],{x[spec.prefix_cut] for x in rows}


class _Build:
    def __init__(self,spec,input_file,witness_file):
        self.s=spec;self.r=random.Random(spec.seed);self.inp=input_file;self.wit=witness_file
        self.ih=hashlib.sha256();self.wh=hashlib.sha256();self.occupied=bytearray()
        self.active={};self.pid=self.count=self.F=self.peak=self.T=0
        self.turn=self.deletions=self.renewed=self.age_sum=self.max_age=0
        self.max_absence=0;self.lengths=Counter();self.phases=Counter();self.zone_visits=Counter()
        self.initial=set();self.zones=[];self.prefix_end_T=0
        self._input(f'1\n{spec.n}\n'.encode())

    def _input(self,b):
        self.ih.update(b)
        if self.inp is not None:self.inp.write(b)

    def _answer(self,b):self.wit.write(b);self.wh.update(b)
    def _room(self):
        if self.count==self.s.n:raise _Done

    def _phase(self):
        x=self.count/self.s.n
        return max(i for i,c in enumerate(self.s.phase_cuts) if x>=c)

    def _size(self,j):
        phase=self._phase();g=self.s.grammar[phase];v=self.s.variant
        # Both run order and size alphabets change on the held-out split.
        run=(11+7*v) if self.s.split=='development' else (17+13*v)
        q=j//run+self.turn//(3 if self.s.split=='development' else 5)+phase
        if g=='stair':return (3,6,9,12,15,18,21,24,27,30,33,36)[q%12]
        if g=='dyadic':return (2,4,8,16,32)[q%5]
        if g=='word':return (3,7,3,11,19,5,13)[(j+phase)%7]
        if g=='plateau':return 1+(7*q+5*v)%40
        if g=='offgrid':return (6,11,17,23,29,37)[(q+q//6)%6]
        if g=='antiphase':return (31,5,27,9,23,13,19,17)[(j+3*(j//8)+phase)%8]
        if g=='palindrome':return (4,10,18,28,38,28,18,10)[q%8]
        if g=='tiny_large':return (1,2,3,1,2,37,39)[(j+q)%7]
        if g=='residue':return (7,12,19,26,33,40)[(q+phase)%6]
        raise ValueError(g)

    def _positive(self,length,start):
        self._room();assert 1<=length<=40 and start>=0
        oldT=self.T;end=start+length
        self.T=max(self.T,20*((end+19)//20))
        if self.T>oldT:self.occupied.extend(b'\0'*(self.T-oldT))
        assert not any(self.occupied[start:end]),('witness overlap',self.count,start,length)
        self.occupied[start:end]=b'\1'*length
        self.pid+=1;p=Pipe(start,length,self.pid,self.count);self.active[p.pid]=p
        self._input(f'{length}\n'.encode());self._answer(f'{(self.T-oldT)//20} {start}\n'.encode())
        self.F+=length;self.peak=max(self.peak,self.F);self.lengths[length]+=1
        self.phases[self._phase()]+=1;self.count+=1
        return p

    def _negative(self,p):
        self._room();assert self.active.pop(p.pid) is p
        a,b=p.start,p.start+p.length
        assert all(self.occupied[a:b]);self.occupied[a:b]=b'\0'*p.length
        self._input(f'{-p.pid}\n'.encode());self._answer(f'{p.start}\n'.encode())
        age=self.count-p.born;self.age_sum+=age;self.max_age=max(self.max_age,age)
        self.F-=p.length;self.deletions+=1;self.count+=1
        self.max_absence=max(self.max_absence,self.T-self.F)

    def _gaps(self):
        gaps=[];i=0
        while i<self.T:
            if self.occupied[i]:i+=1;continue
            a=i
            while i<self.T and not self.occupied[i]:i+=1
            gaps.append((a,i))
        return gaps

    def _bestfit(self,n):
        gaps=self._gaps();fit=[(b-a,a) for a,b in gaps if b-a>=n]
        if fit:return min(fit)[1]
        return gaps[-1][0] if gaps and gaps[-1][1]==self.T else self.T

    def _warmup(self):
        prefix,forbidden=_prefix(self.s)
        for c in prefix:
            if c>0:self._positive(c,self._bestfit(c))
            else:self._negative(self.active[-c])
        self.prefix_end_T=self.T
        # A legal positive size immediately differs from both public successors.
        mismatch=1+(13*self.s.variant+7*self.s.public_pair[0]+17)%40
        while mismatch in forbidden:mismatch=mismatch%40+1
        self.divergence=mismatch
        self._positive(mismatch,self._bestfit(mismatch))
        target=max(self.s.arena,self.T+400);target=20*((target+19)//20)
        # Fill all holes, then extend the small live arena. This is initialization,
        # followed by thousands of renewal commands; there is no terminal suffix.
        for a,b in self._gaps():
            while a<b:
                n=min(self._size(self.pid),b-a);self._positive(n,a);a+=n
        while self.T<target:
            a=self.T;n=min(40,target-a);self._positive(n,a)
        for a,b in self._gaps():
            while a<b:
                n=min(self._size(self.pid),b-a);self._positive(n,a);a+=n
        assert self.F==self.T and all(self.occupied)
        self.initial=set(self.active);self.initial_count=len(self.initial)
        # Boundaries follow existing pipes, so no prefix pipe is split/moved.
        group=[];a=0;end=0
        for p in sorted(self.active.values(),key=lambda p:p.start):
            assert p.start==end;group.append(p);end=p.start+p.length
            if end-a>=self.s.zone_target:
                self.zones.append(Zone(a,end-a,group));a=end;group=[]
        if group:self.zones.append(Zone(a,end-a,group))
        assert max(z.length for z in self.zones)<=self.T//10
        assert sum(z.length for z in self.zones)==self.T
        self.warmup_commands=self.count;self.renewal_floor=self.T

    def _choose(self):
        phase=self._phase();budget=self.T//10
        # Start with oldest zone every cycle. Additional zones alter cohort/PID
        # composition; no initial background survives a complete zone service.
        order=sorted(range(len(self.zones)),key=lambda i:(self.zones[i].served,(i*37+self.turn*11)%101))
        ids=[order[0]];volume=self.zones[ids[0]].length
        assert volume<=budget
        candidates=list(range(len(self.zones)));self.r.shuffle(candidates)
        if self.s.split=='development':
            candidates.sort(key=lambda i:((i+self.turn)%3,(i+phase)%7))
        else:
            candidates.sort(key=lambda i:((i*11+self.turn//3+phase)%7,(i^self.turn)%13))
        limit=(1+(self.turn%3)) if self.s.split=='development' else (2+((self.turn//2+phase)%4))
        for i in candidates:
            if len(ids)>=limit:break
            if i not in ids and volume+self.zones[i].length<=budget:
                ids.append(i);volume+=self.zones[i].length
        return ids

    def _cycle(self):
        phase=self._phase();ids=self._choose();old=[]
        for i in ids:old.extend(self.zones[i].pipes)
        # Different deletion and insertion orders hide physical contiguity.
        if self.s.split=='development':old.sort(key=lambda p:(p.pid&1,p.pid if self.turn%2 else -p.pid))
        else:old.sort(key=lambda p:((p.pid//(3+phase))%5,-p.born,p.pid%17))
        for p in old:self._negative(p)
        plans=[]
        for i in ids:
            z=self.zones[i];a=z.start;end=a+z.length;pieces=[]
            while a<end:
                n=min(self._size(self.pid+len(plans)+len(pieces)),end-a)
                pieces.append((a,n));a+=n
            self.zones[i].pipes=[]
            for j,(a,n) in enumerate(pieces):plans.append((i,a,n,j))
        if self.s.split=='development':plans.sort(key=lambda p:(p[2],(p[3]+self.turn)%7,p[0]))
        else:
            # Alternate whole-size runs with interleaved off-grid motifs.
            if (self.turn+phase)%2:plans.sort(key=lambda p:(-p[2],p[3]%11,-p[0]))
            else:plans.sort(key=lambda p:((p[3]+3*p[0]+phase)%13,p[2],-p[1]))
        for i,a,n,j in plans:
            p=self._positive(n,a);self.zones[i].pipes.append(p);self.renewed+=1
        for i in ids:self.zones[i].served=self.turn;self.zone_visits[i]+=1
        assert self.F==self.T and all(self.occupied)
        self.turn+=1

    def run(self):
        try:
            self._warmup()
            while True:self._cycle()
        except _Done:pass
        assert self.count==self.s.n and self.turn>0
        assert self.F==sum(p.length for p in self.active.values())
        assert self.F/self.T>=.85,(self.s,self.F,self.T)
        initial_survivors=len(self.initial.intersection(self.active))
        assert initial_survivors==0,('fixed background was not fully retired',self.s,initial_survivors)
        lower=20*((self.peak+19)//20);exact=lower==self.T
        return dict(source=Path(__file__).name,generator_version=VERSION,
            name=self.s.name,split=self.s.split,seed=self.s.seed,n=self.count,
            family=self.s.family,stratum=f'public_pair_{self.s.public_pair[0]}_{self.s.public_pair[1]}_n{self.s.n}',
            sha256=self.ih.hexdigest(),witness_sha256=self.wh.hexdigest(),spec=asdict(self.s),
            F=self.F,T=self.T,bound=lower,
            bound_definition='20*ceil(peak_live/20), lower bound; witness upper bound is T',
            attainable_KPI=self.F/self.T,optimal_trench_interval=[lower,self.T],
            optimum_exact=exact,theoretical_max_KPI=self.F/self.T if exact else None,
            certificate=dict(method='causal-bestfit-prefix then renewable zone repartition',
                prefix_cut=self.s.prefix_cut,public_pair=list(self.s.public_pair),
                immediate_divergence_command=self.divergence,prefix_witness_trench=self.prefix_end_T,
                warmup_commands=self.warmup_commands,initial_pipes=self.initial_count,
                initial_pipes_still_live=initial_survivors,completed_cycles=self.turn,
                zones=len(self.zones),distinct_zones_renewed=len(self.zone_visits),
                minimum_completed_zone_visits=min(self.zone_visits.values()),
                renewed=self.renewed,deletions=self.deletions,peak_live=self.peak,
                final_density=self.F/self.T,max_outstanding_deleted_volume=self.max_absence,
                max_deleted_lifetime_commands=self.max_age,
                mean_deleted_lifetime_commands=self.age_sum/max(1,self.deletions),
                length_histogram=dict(sorted(self.lengths.items())),phase_insertions=dict(self.phases),
                final_padding_commands=0,coordinates_in_input=False),provenance=PROVENANCE)


def generate(new_dir):
    """Create exactly24 new inputs and a raw manifest; temporary witnesses only."""
    dest=Path(new_dir);dest.mkdir(parents=True,exist_ok=False)
    source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();hashes=set()
    with (dest/'manifest.jsonl').open('w') as mf,tempfile.TemporaryDirectory(prefix='pipes-prefix24-witness-') as td:
        wp=Path(td)/'witness.txt'
        for s in specs():
            p=dest/(s.name+'.in')
            with p.open('wb') as inp,wp.open('wb') as wit:row=_Build(s,inp,wit).run()
            assert row['sha256'] not in hashes;hashes.add(row['sha256'])
            row.update(input=p.name,source_sha256=source_sha)
            mf.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');mf.flush();wp.unlink()
    return dest/'manifest.jsonl'


def replay_witness(metadata,destination):
    raw=dict(metadata['spec'])
    for key in ('public_pair','phase_cuts','grammar'):raw[key]=tuple(raw[key])
    p=Path(destination)
    with p.open('xb') as wit:row=_Build(Spec(**raw),None,wit).run()
    assert row['sha256']==metadata['sha256'] and row['witness_sha256']==metadata['witness_sha256']
    return p

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('new_dir')
    print(generate(ap.parse_args().new_dir))
