#!/usr/bin/env python3
"""Frozen36-input DEVELOPMENT sensitivity corpus, never a hidden-test model.

Public forks:Open12 after155/Open14 after17161,4 strata x3 replicates each:
EOF public cuts+0/31/257; neutral suffix1024/8192/32768; matched equal-length
PID lifetime permutations; scale/hazard shifts. Independent4xN4096/32768/200000.
Seeds/families/cuts were fixed before any outcomes on this corpus.

Only public12.in/14.in and a hash-pinned pure generator component are read.
No solver, replay table, selected answer, archive result, or sealed input is read.
Neutral/permutation pairs use identical structural RNG and legal live-size
counts. They differ only in the choice of active PID among the SAME lengths;
there is no anticipatory constraint on a tested solver's placement.

Public-prefix coordinates are independently constructed by tiny first-fit.
Suffix growth appends, equal-length renewals reuse the actually deleted span.
ALL legacy holes and pending deletions count toward a14% rounded-trench debt
cap; no terminal fill/drain. Long-lived public survivors have a finite cyclic
service rule, but short suffixes necessarily right-censor many Open14 lives.
The witness certifies feasible F/T>=.85; volume bound is not called exact OPT.

Independent cases reuse ONLY development grammars/scheduling from a pinned
microtransaction component and fresh seeds, with new mechanism compositions.
There is no call to its specs()/generate(), nor to any sealed dataset.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import math
import random
import sys
import tempfile
from collections import Counter,defaultdict
from dataclasses import asdict,dataclass
from pathlib import Path

VERSION='selection-sensitivity36-inputonly-v1-20261022'
ROOT=Path('/Users/555tery/techarena')
COMPONENT=Path('/tmp/pipes_async_microtransactions_next_20261022.py')
COMPONENT_SHA256='86c3724450bba7dc483196df5504f0df421eda30cab79990f9bdee2bd938a90c'

@dataclass(frozen=True)
class Spec:
    name:str
    origin:str
    family:str
    seed:int
    replicate:int
    n:int
    public_case:int=0
    fork_after:int=0
    prefix_n:int=0
    suffix_n:int=0
    stream_seed:int=0
    target_positive:float=.65


def specs():
    ss=[]
    families=('natural_eof','neutral','lifetime_permutation','scale_hazard_shift')
    for origin,(case,cut) in enumerate(((12,155),(14,17161))):
        for f,family in enumerate(families):
            for r in range(3):
                seed=0x23A41001+100003*origin+1009*f+97*r
                prefix_n=cut+(0,31,257)[r] if f==0 else cut
                suffix_n=0 if f==0 else (1024,8192,32768)[r]
                # The frozen row seed identifies permutation sampling. Structural
                # RNG is deliberately paired with neutral, preserving signs/L.
                stream_seed=(0x23A41001+100003*origin+1009+97*r) if f==2 else seed
                ss.append(Spec(f'open{case}_{family}_{r}',f'Open{case}',family,seed,r,
                    prefix_n+suffix_n,case,cut,prefix_n,suffix_n,stream_seed,
                    .65 if case==12 else .97))
    independent=('motif_size_hazard_reversal','narrow_popular_renewal',
                 'diffuse_markov','tiny_to_mixed_growth')
    for f,family in enumerate(independent):
        for r,n in enumerate((4096,32768,200000)):
            seed=0x23A43001+1009*f+97*r
            ss.append(Spec(f'independent_{family}_{r}','independent',family,seed,r,n))
    assert len(ss)==36 and len({s.name for s in ss})==36 and len({s.seed for s in ss})==36
    return ss

_COMPONENT=None

def _component():
    global _COMPONENT
    if _COMPONENT is None:
        assert hashlib.sha256(COMPONENT.read_bytes()).hexdigest()==COMPONENT_SHA256,'component changed; review before updating pin'
        name='pipes_sensitivity36_async_component'
        spec=importlib.util.spec_from_file_location(name,COMPONENT)
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module
        spec.loader.exec_module(module);_COMPONENT=module
    return _COMPONENT

@dataclass
class Pipe:
    start:int
    length:int
    pid:int
    born:int

class _PrefixBuild:
    def __init__(self,s,inp,wit):
        self.s=s;self.inp=inp;self.wit=wit
        self.ih=hashlib.sha256();self.wh=hashlib.sha256();self.signature=hashlib.sha256()
        self.r=random.Random(s.stream_seed);self.identity=random.Random(s.seed^0x419D377B)
        self.count=self.pid=self.F=self.peak=self.T=self.raw_end=0
        self.active={};self.by_size=defaultdict(dict);self.pending=defaultdict(list)
        self.holes=[];self.ages=[];self.initial=set();self.initial_deleted=0
        self.pcount=self.dcount=self.suffix_pos=self.suffix_neg=0
        self.last_sign=None;self.run_len=self.max_pos_run=self.max_neg_run=0
        self.service=0;self.next_service=0;self.suffix_positive_run=0
        self.max_debt_fraction=0.;self.profile_hist=None
        self._input(f'1\n{s.n}\n'.encode())

    def _input(self,b):
        self.ih.update(b)
        if self.inp is not None:self.inp.write(b)

    def _answer(self,b):self.wit.write(b);self.wh.update(b)

    def _tick(self,command):
        self.signature.update(f'{command if command>0 else 0}\n'.encode())
        sign=command>0
        if sign==self.last_sign:self.run_len+=1
        else:self.last_sign=sign;self.run_len=1
        if sign:self.max_pos_run=max(self.max_pos_run,self.run_len)
        else:self.max_neg_run=max(self.max_neg_run,self.run_len)
        self.count+=1
        if self.count>self.s.prefix_n:
            self.max_debt_fraction=max(self.max_debt_fraction,(self.T-self.F)/self.T)
            assert self.F/self.T>=.85

    def _place(self,length,start):
        assert self.count<self.s.n and 1<=length<=40 and start>=0
        T=max(self.T,20*((start+length+19)//20));digs=(T-self.T)//20
        self.pid+=1;p=Pipe(start,length,self.pid,self.count)
        self._input(f'{length}\n'.encode());self._answer(f'{digs} {start}\n'.encode())
        self.T=T;self.F+=length;self.peak=max(self.peak,self.F);self.pcount+=1
        self.active[p.pid]=p;self.by_size[length][p.pid]=p
        self._tick(length);return p

    def _remove(self,p):
        assert self.count<self.s.n and self.active.pop(p.pid) is p
        assert self.by_size[p.length].pop(p.pid) is p
        if not self.by_size[p.length]:del self.by_size[p.length]
        self._input(f'{-p.pid}\n'.encode());self._answer(f'{p.start}\n'.encode())
        self.ages.append(self.count-p.born)
        if p.pid in self.initial:self.initial_deleted+=1
        self.F-=p.length;self.dcount+=1;self._tick(-p.pid)

    def _merge(self):
        self.holes.sort();out=[]
        for start,size in self.holes:
            if out and out[-1][0]+out[-1][1]==start:out[-1]=(out[-1][0],out[-1][1]+size)
            else:out.append((start,size))
        self.holes=out

    def _prefix(self):
        path=ROOT/'data/pipes/open'/f'{self.s.public_case}.in'
        source=path.read_bytes();tokens=source.split();official_n=int(tokens[1])
        assert self.s.prefix_n<=official_n
        commands=list(map(int,tokens[2:2+self.s.prefix_n]))
        self.source_sha=hashlib.sha256(source).hexdigest()
        self.prefix_command_sha=hashlib.sha256(' '.join(map(str,commands)).encode()).hexdigest()
        self.profile_hist=Counter(x for x in commands if x>0)
        self.hist_values=sorted(self.profile_hist);self.hist_weights=[self.profile_hist[x] for x in self.hist_values]
        for x in commands:
            if x>0:
                for i,(start,size) in enumerate(self.holes):
                    if size>=x:
                        self.holes.pop(i)
                        if size>x:self.holes.insert(i,(start+x,size-x))
                        self._place(x,start);break
                else:
                    start=self.T;T=20*((start+x+19)//20)
                    self._place(x,start)
                    if T>start+x:self.holes.append((start+x,T-start-x))
            else:
                p=self.active[-x];self._remove(p);self.holes.append((p.start,p.length));self._merge()
        assert self.F+sum(size for start,size in self.holes)==self.T
        self.raw_end=self.T;self.initial=set(self.active)
        self.prefix_F=self.F;self.prefix_T=self.T
        self.initial_size_alphabet=tuple(sorted(self.by_size))
        assert self.F/self.T>=.85,'public prefix requires a stronger independent witness'

    def _new_length(self,j):
        if self.s.family!='scale_hazard_shift':
            # Empirical size frequencies, new stochastic order and short sticky
            # episodes; no source suffix is copied for generated continuations.
            if j%7 in (1,2) and hasattr(self,'last_length'):x=self.last_length
            else:x=self.r.choices(self.hist_values,self.hist_weights,k=1)[0]
        else:
            progress=j/max(1,self.s.suffix_n);r=self.s.replicate
            if r==0:
                x=self.r.choices(self.hist_values,self.hist_weights,k=1)[0] if progress<.25 else self.r.choice((17,23,31,40))
            elif r==1:
                x=self.r.choice((19,27,35,40)) if progress<.25 else self.r.choice((1,2,3))
            else:
                x=self.r.choice((13,21,29,37)) if .25<=progress<.60 else self.r.choices(self.hist_values,self.hist_weights,k=1)[0]
        self.last_length=x;return x

    def _eligible_length(self,j):
        # Eligibility uses only active size counts and a witness debt budget.
        # Counts/volumes are identical on both matched permutations.
        budget=int(.14*self.T)-(self.T-self.F)
        eligible=sorted(x for x,pool in self.by_size.items() if pool and x<=budget)
        if not eligible:return None,False
        service=(self.suffix_neg%7==0)
        if service:
            # Cyclic finite service over every initial size class. Membership in
            # the initial population never constrains a solver's allowed action.
            for offset in range(len(self.initial_size_alphabet)):
                k=(self.service+offset)%len(self.initial_size_alphabet)
                x=self.initial_size_alphabet[k]
                if x in eligible:
                    self.next_service=k+1;return x,True
        phase=int(3*j/max(1,self.s.suffix_n))
        if self.s.family=='scale_hazard_shift':
            weights=[len(self.by_size[x])*(1+(x<9 if phase%2 else x>16)*3) for x in eligible]
        else:weights=[len(self.by_size[x]) for x in eligible]
        return self.r.choices(eligible,weights,k=1)[0],service

    def _identity(self,length,service):
        pool=self.by_size[length]
        candidates=list(pool.values())
        if service:
            old=[p for p in candidates if p.pid in self.initial]
            if old:candidates=old
        if self.s.family=='lifetime_permutation':
            # Separate RNG: changing PID identity cannot perturb signs or L.
            baseline=min(candidates,key=lambda p:p.pid) if service else max(candidates,key=lambda p:p.pid)
            choices=[p for p in candidates if p.pid!=baseline.pid]
            return self.identity.choice(choices or candidates)
        return min(candidates,key=lambda p:p.pid) if service else max(candidates,key=lambda p:p.pid)

    def _suffix(self):
        for j in range(self.s.suffix_n):
            # Renewal/growth are the same ordinary state-based process through
            # the final command; no branch reads remaining commands for filling.
            positive=(self.r.random()<self.s.target_positive)
            # A deterministic finite upper bound on the next deletion attempt
            # makes cyclic service a finite rule, including right-censored lives.
            if self.suffix_positive_run>=(63 if self.s.public_case==12 else 511):positive=False
            length,service=self._eligible_length(j)
            if length is None:positive=True
            if positive:
                pending=sorted(x for x,holes in self.pending.items() if holes)
                debt=(self.T-self.F)/self.T
                refill=pending and (debt>.115 or self.r.random()<.55)
                if refill:
                    x=self.r.choice(pending);start=self.pending[x].pop(0)
                    self._place(x,start)
                else:
                    x=self._new_length(j);start=self.raw_end;self.raw_end+=x;self._place(x,start)
                self.suffix_pos+=1;self.suffix_positive_run+=1
            else:
                p=self._identity(length,service);self._remove(p)
                self.pending[p.length].append(p.start);self.suffix_neg+=1;self.suffix_positive_run=0
                if service:self.service=self.next_service
        assert self.count==self.s.n

    def run(self):
        self._prefix()
        if self.s.suffix_n:self._suffix()
        assert self.count==self.s.n and self.F==sum(p.length for p in self.active.values())
        assert self.F/self.T>=.85
        lower=20*((self.peak+19)//20);ages=sorted(self.ages)
        def q(p):return ages[round((len(ages)-1)*p)] if ages else None
        match=f'Open{self.s.public_case}_neutral_pair_{self.s.replicate}' if self.s.family in ('neutral','lifetime_permutation') else None
        return dict(source=Path(__file__).name,generator_version=VERSION,
            name=self.s.name,split='development',origin=self.s.origin,family=self.s.family,
            stratum=f'{self.s.origin}_{self.s.family}',seed=self.s.seed,n=self.count,
            F=self.F,T=self.T,bound=lower,attainable_KPI=self.F/self.T,
            bound_definition='peak-volume lower bound; witness T is feasible upper bound',
            optimal_trench_interval=[lower,self.T],optimum_exact=lower==self.T,
            theoretical_max_KPI=self.F/self.T if lower==self.T else None,
            sha256=self.ih.hexdigest(),witness_sha256=self.wh.hexdigest(),spec=asdict(self.s),
            match_group=match,matched_signs_positive_lengths_sha256=self.signature.hexdigest(),
            certificate=dict(method='independent-firstfit-prefix-plus-bounded-slot-renewal',
                public_source_sha256=self.source_sha,prefix_commands_sha256=self.prefix_command_sha,
                exact_public_prefix_n=self.s.prefix_n,fork_after=self.s.fork_after,
                prefix_F=self.prefix_F,prefix_T=self.prefix_T,prefix_attainable_KPI=self.prefix_F/self.prefix_T,
                suffix_commands=self.s.suffix_n,suffix_positive=self.suffix_pos,suffix_negative=self.suffix_neg,
                max_suffix_debt_fraction=self.max_debt_fraction,
                max_positive_run=self.max_pos_run,max_negative_run=self.max_neg_run,
                initial_live_pipes=len(self.initial),initial_pipes_deleted=self.initial_deleted,
                initial_pipes_right_censored=sum(pid in self.active for pid in self.initial),
                initial_finite_service_rule='cyclic initial-size-class service every7 deletions; bounded positive gaps; right-censored at EOF',
                deleted_age_q10_q50_q90_q99=[q(p) for p in(.1,.5,.9,.99)],
                final_padding_commands=0,coordinates_in_input=False),
            provenance=dict(public_input_only=True,solver_or_selected_answers_read=False,
                sealed_inputs_or_results_read=False,selection_by_solver_quality=False,
                population_probability_claim=False))


def _independent(s,inp,wit):
    m=_component()
    grammars={
        'motif_size_hazard_reversal':('short_word','alternating_bands','affine_walk','short_word'),
        'narrow_popular_renewal':('hot_three','hot_three','hot_three','hot_three'),
        'diffuse_markov':('affine_walk','alternating_bands','affine_walk','alternating_bands'),
        'tiny_to_mixed_growth':('short_word','short_word','alternating_bands','affine_walk'),
    }
    class Independent(m._Build):
        def _length(self,j,colour):
            if s.family=='tiny_to_mixed_growth' and self._phase()<2:
                return (1,1,2,1,3,2,1)[(j+colour+self.turn//5)%7]
            if s.family=='diffuse_markov' and (j+colour)%5:
                return 1+(self.turn//(7+s.replicate)+colour*3+5*self._phase())%40
            return super()._length(j,colour)
    internal=m.Spec(s.name,'development',s.seed,s.n,s.family,s.replicate,
        (16,24,48)[s.replicate],grammars[s.family],(0.,.27,.55,.79),.65)
    row=Independent(internal,inp,wit).run()
    row.update(source=Path(__file__).name,generator_version=VERSION,spec=asdict(s),
        origin='independent',family=s.family,stratum=f'independent_{s.family}',
        split='development',match_group=None,component_sha256=COMPONENT_SHA256)
    row['provenance'].update(sealed_inputs_or_results_read=False,selection_by_solver_quality=False,
        population_probability_claim=False,component_grammars='development only; fresh composition and seeds')
    return row


def _build(s,inp,wit):
    return _independent(s,inp,wit) if s.origin=='independent' else _PrefixBuild(s,inp,wit).run()


def verify_specs():
    ss=specs();assert sum(s.origin=='independent' for s in ss)==12
    assert all(s.n<=200000 for s in ss)
    for case in (12,14):
        a=[s for s in ss if s.public_case==case];assert len(a)==12
        for r in range(3):
            n=next(s for s in a if s.family=='neutral' and s.replicate==r)
            p=next(s for s in a if s.family=='lifetime_permutation' and s.replicate==r)
            assert n.stream_seed==p.stream_seed and n.prefix_n==p.prefix_n and n.suffix_n==p.suffix_n
    _component()
    return {'cases':36,'Open12':12,'Open14':12,'independent':12,'split':'development'}


def generate(new_dir):
    verify_specs();p=Path(new_dir);p.mkdir(parents=True,exist_ok=False)
    sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();seen=set();matched={}
    with (p/'manifest.jsonl').open('w') as mf,tempfile.TemporaryDirectory(prefix='pipes-sensitivity36-witness-') as td:
        wp=Path(td)/'witness.txt'
        for s in specs():
            ip=p/(s.name+'.in')
            with ip.open('wb') as inp,wp.open('wb') as wit:r=_build(s,inp,wit)
            assert r['sha256'] not in seen,'duplicate frozen input; report, do not resample'
            seen.add(r['sha256']);r.update(input=ip.name,source_sha256=sha)
            if r['match_group']:
                signature=r['matched_signs_positive_lengths_sha256']
                old=matched.setdefault(r['match_group'],signature)
                assert old==signature,'matched controls changed sign/length sequence'
            mf.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n');mf.flush();wp.unlink()
    assert len(matched)==6
    return p/'manifest.jsonl'


def replay_witness(metadata,destination):
    p=Path(destination);s=Spec(**metadata['spec'])
    with p.open('xb') as wit:r=_build(s,None,wit)
    assert r['sha256']==metadata['sha256'] and r['witness_sha256']==metadata['witness_sha256']
    if metadata.get('match_group'):
        assert r['matched_signs_positive_lengths_sha256']==metadata['matched_signs_positive_lengths_sha256']
    return p

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('new_dir')
    print(generate(ap.parse_args().new_dir))
