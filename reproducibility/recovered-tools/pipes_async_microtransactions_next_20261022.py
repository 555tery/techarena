#!/usr/bin/env python3
"""Next-round pure Pipes generator: asynchronous small-span transactions.

36 predetermined cases,12 development/24 sealed_final;24 cases haveN200000.
No public inputs, solver source, replay, or outcomes are read. Importing only
creates definitions. generate(new_dir) explicitly writes inputs and a manifest;
replay_witness(record,path) recreates only the hidden offline certificate.

A transaction deletes1..5 adjacent old pipes within a small span, gradually and
interleaved with other transactions. Once its old pipes are removed, it inserts
a new2..10-part composition of exactly that span. New growing spans are mixed
into the positive packets. Positive/negative runs are bounded by11/5 commands.
Each packet completes one small transaction but can also advance other ones.
There is no global clearing phase and no fixed exact-length reservations.

Specs request16..64 simultaneous transactions; early populations naturally
have fewer. All potential missing volume, including not-yet-deleted transaction
spans and unfinished growth, is reserved under a10% arena cap once arena>=400m.
This stronger cap implies actual missing volume<=11%. Startup uses at most40m
of pending reservations, and reaches400m early through ordinary ongoing growth.
Thus arbitrary endpoints have certified F/T>=.85 without final filling/drain.
Finite size-dependent due dates reverse their hazard relation between phases.
The initially created pipes must all be deleted before return.

This is a constructed stress distribution, not a closed-test model. A witness
T is feasible; OPT remains in[peak-volume lower bound,T] unless they coincide.
"""
from __future__ import annotations
import hashlib
import heapq
import json
import math
import random
import tempfile
from collections import Counter
from dataclasses import asdict,dataclass,field
from pathlib import Path

VERSION='asynchronous-microspan-growth-v1a-20261022'

@dataclass(frozen=True)
class Spec:
    name:str
    split:str
    seed:int
    n:int
    family:str
    variant:int
    concurrency:int
    grammar:tuple[str,...]
    switches:tuple[float,...]
    target_positive:float=.65


def specs():
    rows=[]
    families=('asynchronous_motif_hazards','cohort_size_hazard_reversal','bursty_multilevel_renewal')
    for split,ns,base in (
        ('development',(16000,200000,200000,200000),0x22DA67C1),
        ('sealed_final',(23000,51000,87000,200000,200000,200000,200000,200000),0x22FEC8D3),
    ):
        for k,n in enumerate(ns):
            for f,fam in enumerate(families):
                gs=(('short_word','hot_three','alternating_bands','affine_walk') if split=='development' else
                    ('braided_word','skew_four','dithered_residues','prime_stair','nested_ring'))
                shift=(k+f)%len(gs);gs=gs[shift:]+gs[:shift]
                rows.append(Spec(f"{'dev' if split=='development' else 'final'}_{k:02}_{f:02}",
                    split,base+100019*k+6151*f,n,fam,k,
                    (16,24,32,48)[(k+f)%4] if split=='development' else (24,32,48,64)[(k+2*f)%4],
                    gs,(0.,.27,.55,.79) if split=='development' else (0.,.12,.37,.61,.87)))
    assert len(rows)==36 and sum(s.n==200000 for s in rows)==24
    return rows

@dataclass
class Pipe:
    start:int
    length:int
    pid:int=0
    born:int=0

@dataclass
class Group:
    start:int
    width:int
    colour:int
    index:int
    pipes:list[Pipe]=field(default_factory=list)
    busy:bool=False
    version:int=0
    due:int=0

@dataclass
class Txn:
    group:int
    start:int
    width:int
    old:list[Pipe]
    new:list[Pipe]
    growth:bool=False
    removed:int=0
    placed:int=0
    sequence:int=0

    def deletable(self):return self.removed<len(self.old)
    def ready(self):return self.removed==len(self.old) and self.placed<len(self.new)
    def done(self):return self.removed==len(self.old) and self.placed==len(self.new)

class _Done(Exception):pass

class _Build:
    def __init__(self,s,inp,wit):
        self.s=s;self.r=random.Random(s.seed);self.inp=inp;self.wit=wit
        self.ih=hashlib.sha256();self.wh=hashlib.sha256()
        self.count=self.pid=self.F=self.peak=self.arena=self.T=0
        self.pos=self.neg=self.reserved=self.turn=0
        self.groups=[];self.pending=[];self.queue=[];self.free_min=[];self.live={}
        self.initial=set();self.initial_deleted=0;self.ages=[]
        self.hist=Counter();self.hazards=Counter();self.phases=Counter()
        self.max_pending=self.max_debt=0;self.max_debt_fraction=0.
        self.max_pos_run=self.max_neg_run=self.run_len=0;self.last_sign=None
        self.completed_renewals=self.completed_growth=self.forced_hazard=0
        self.txn_sequence=0
        self.initial_fill_commands=None
        self._input(f'1\n{s.n}\n'.encode())

    def _input(self,b):
        self.ih.update(b)
        if self.inp is not None:self.inp.write(b)

    def _answer(self,b):self.wit.write(b);self.wh.update(b)

    def _room(self):
        if self.count==self.s.n:raise _Done

    def _phase(self):
        return max(i for i,x in enumerate(self.s.switches) if self.count/self.s.n>=x)

    def _cap(self):return max(40,int(.10*self.arena))

    def _record(self,positive):
        if positive==self.last_sign:self.run_len+=1
        else:self.last_sign=positive;self.run_len=1
        if positive:self.max_pos_run=max(self.max_pos_run,self.run_len)
        else:self.max_neg_run=max(self.max_neg_run,self.run_len)
        assert self.max_pos_run<=11 and self.max_neg_run<=5
        if self.arena>=400:
            assert self.reserved<=int(.11*self.arena)
            debt=self.arena-self.F
            assert debt<=self.reserved
            self.max_debt_fraction=max(self.max_debt_fraction,debt/self.arena)
            if self.initial_fill_commands is None:self.initial_fill_commands=self.count
        self.max_debt=max(self.max_debt,self.arena-self.F)
        self.max_pending=max(self.max_pending,len(self.pending))

    def _length(self,j,colour):
        phase=self._phase();g=self.s.grammar[phase];r=self.r;v=self.s.variant
        if self.s.family=='cohort_size_hazard_reversal' and (colour+phase)%3==0:
            g='hot_three' if self.s.split=='development' else 'skew_four'
        if g=='short_word':x=(2,7,3,11,5,1,9)[(j+2*colour+phase)%7]
        elif g=='hot_three':x=(3+v%3,9+2*phase,18+phase)[(j//3+colour)%3]
        elif g=='alternating_bands':x=r.randint(1,5) if (colour+phase)%2 else r.randint(17,35)
        elif g=='affine_walk':x=1+(5*j+7*colour+self.turn//3+phase)%27
        elif g=='braided_word':x=(3,17,2,11,29,5,13,7,23,2,19)[(j+3*colour+j//11+phase)%11]
        elif g=='skew_four':x=(2+v%4,11+phase,23-phase,34+v%5)[(j//2+colour+phase)%4]
        elif g=='dithered_residues':x=(1,4,7,10,16,22,31,37)[(j*3+colour+phase)%8]+r.choice((-1,0,1))
        elif g=='prime_stair':x=(2,5,11,19,29,37)[(j//3+colour+j//17+phase)%6]
        elif g=='nested_ring':x=(1,3,6,10,15,21,28,36)[(j+colour*3+self.turn//7+phase)%8]
        else:raise ValueError(g)
        return max(1,min(40,x))

    def _partition(self,start,width,colour,old_count=None):
        lo=max(1,(width+39)//40);hi=min(10,width)
        if old_count is None:
            mean=max(3,self._length(self.turn+colour,colour))
            k=max(lo,min(hi,max(2,round(width/mean))))
        else:k=max(lo,min(hi,old_count+self.r.choice((-1,0,0,0,1))))
        # Exact bounded composition, allowing size changes and shifted boundaries.
        out=[];left=width;pos=start
        for j in range(k):
            rest=k-j-1;low=max(1,left-40*rest);high=min(40,left-rest)
            x=max(low,min(high,self._length(j+self.turn*13,colour)))
            out.append(Pipe(pos,x));pos+=x;left-=x
        assert left==0 and 1<=len(out)<=10 and sum(p.length for p in out)==width
        return out

    def _place(self,p):
        self._room();assert p.pid==0
        T=max(self.T,20*((p.start+p.length+19)//20))
        self.pid+=1;p.pid=self.pid;p.born=self.count
        self._input(f'{p.length}\n'.encode());self._answer(f'{(T-self.T)//20} {p.start}\n'.encode())
        self.T=T;self.F+=p.length;self.peak=max(self.peak,self.F);self.pos+=1
        self.live[p.pid]=p;self.hist[p.length]+=1;self.phases[self._phase()]+=1
        if not self.initial and len(self.groups)==1:self.initial.add(p.pid)
        elif len(self.groups)==1 and self.completed_growth==0:self.initial.add(p.pid)
        self.count+=1;self._record(True)

    def _remove(self,p):
        self._room();assert self.live.pop(p.pid) is p
        self._input(f'{-p.pid}\n'.encode());self._answer(f'{p.start}\n'.encode())
        self.ages.append(self.count-p.born)
        if p.pid in self.initial:self.initial_deleted+=1
        p.pid=0;self.F-=p.length;self.neg+=1;self.count+=1;self._record(False)

    def _schedule(self,g):
        assert not g.busy and g.pipes
        mean=g.width/len(g.pipes);phase=self._phase()
        if phase%3==0:role=2 if mean<8 else (0 if mean>16 else 1)
        elif phase%3==1:role=0 if mean<8 else (2 if mean>16 else 1)
        else:role=(int(mean)+g.colour+self.turn)%3
        if (g.colour+self.turn)%7==0:role=(role+1)%3
        if self.s.split=='development':
            delay=(self.r.randint(1,35),self.r.randint(180,2100),self.r.randint(max(400,self.s.n//13),max(900,self.s.n*2//5)))[role]
        else:
            delay=(self.r.randint(2,61),self.r.randint(370,3900),self.r.randint(max(600,self.s.n//10),max(1300,self.s.n*7//16)))[role]
        g.due=self.count+delay
        # Initial pipes have actual finite service targets, never a fixed base.
        if any(p.pid in self.initial for p in g.pipes):
            g.due=min(g.due,self.count+max(20,self.s.n//150),int(.42*self.s.n))
            if g.due<=self.count:g.due=self.count+1
        g.version+=1;self.hazards[(phase,role)]+=1
        heapq.heappush(self.queue,(g.due,g.index,g.version))
        heapq.heappush(self.free_min,(min(p.length for p in g.pipes),g.index,g.version))

    def _min_free_group(self):
        while self.free_min:
            length,i,version=self.free_min[0];g=self.groups[i]
            if g.busy or g.version!=version:heapq.heappop(self.free_min);continue
            return length,g
        return None

    def _growth(self,first=False):
        if len(self.pending)>=self.s.concurrency:return None
        free=self._cap()-self.reserved
        if not first and not any(t.deletable() for t in self.pending):
            # Leave both a transaction slot and enough volume to emit the next
            # short negative packet while a new span is only partly populated.
            if len(self.pending)>=self.s.concurrency-1:return None
            smallest=self._min_free_group()
            if smallest is None:return None
            free-=smallest[0]
        maxwidth=40 if first else min(160,free//20*20)
        if maxwidth<20:return None
        if first:width=40
        else:
            alphabet=(20,40,60,80,100,120,160) if self.s.split=='development' else (20,60,100,140,160)
            choices=[x for x in alphabet if x<=maxwidth]
            width=self.r.choice(choices)
        start=self.arena
        g=Group(start,width,(len(self.groups)*11+3)%29,len(self.groups),busy=True)
        g.pipes=self._partition(start,width,g.colour,old_count=4 if first else None)
        self.groups.append(g);self.arena+=width
        self.txn_sequence+=1
        tx=Txn(g.index,start,width,[],list(g.pipes),growth=True,sequence=self.txn_sequence)
        self.r.shuffle(tx.new);self.pending.append(tx);self.reserved+=width
        assert self.reserved<=self._cap()
        return tx

    def _make_renewal(self,g,free):
        if g.busy or free<1:return None
        pipes=sorted(g.pipes,key=lambda p:p.start)
        # Prefer a finite-lifetime old pipe; neighbouring survivors can remain.
        centre=min(range(len(pipes)),key=lambda i:(pipes[i].born,pipes[i].pid))
        want=1+self.r.randrange(min(5,len(pipes)))
        a=max(0,min(centre-want//2,len(pipes)-want));b=a+want
        selected=pipes[a:b]
        while len(selected)>1 and sum(p.length for p in selected)>free:
            # Shrink around the old anchor when the reservation cap is tight.
            if selected[0] is pipes[centre]:selected.pop()
            else:selected.pop(0)
        if sum(p.length for p in selected)>free:
            # The just-completed transaction always supplies a fitting pipe.
            fitting=[p for p in pipes if p.length<=free]
            if not fitting:return None
            selected=[min(fitting,key=lambda p:(p.born,p.pid))]
        start=selected[0].start;width=sum(p.length for p in selected)
        new=self._partition(start,width,g.colour,old_count=len(selected))
        old=list(selected)
        if self.s.split=='development':self.r.shuffle(old);self.r.shuffle(new)
        else:
            old.sort(key=lambda p:((p.pid+self.turn)%7,-p.born))
            new.sort(key=lambda p:((p.length*3+g.colour+self.turn)%11,p.start%13))
        self.txn_sequence+=1
        tx=Txn(g.index,start,width,old,new,sequence=self.txn_sequence)
        g.busy=True;g.version+=1
        self.pending.append(tx);self.reserved+=width
        assert self.reserved<=self._cap()
        return tx

    def _open_renewal(self,forced=False):
        if len(self.pending)>=self.s.concurrency:return None
        free=self._cap()-self.reserved
        if not forced:
            # Keep ongoing growth possible while the population is small.
            free-=min(160,max(20,self._cap()//3))
        if free<=0:return None
        hold=[];chosen=None
        while self.queue:
            due,i,version=heapq.heappop(self.queue);g=self.groups[i]
            if g.busy or g.version!=version:continue
            if due>self.count and not forced:
                hold.append((due,i,version));break
            tx=self._make_renewal(g,free)
            if tx:
                chosen=tx
                if due>self.count:self.forced_hazard+=1
                break
            hold.append((due,i,version))
            if len(hold)>=64:break
        for e in hold:heapq.heappush(self.queue,e)
        if chosen is None and forced:
            # A completed span releases capacity and a non-busy group. This
            # deterministic fallback guarantees a short negative packet exists.
            smallest=self._min_free_group()
            if smallest is not None and smallest[0]<=free:
                tx=self._make_renewal(smallest[1],free)
                if tx:self.forced_hazard+=1;return tx
        return chosen

    def _finish(self,tx):
        if not tx.done():return
        g=self.groups[tx.group]
        if not tx.growth:
            dead={id(p) for p in tx.old}
            g.pipes=[p for p in g.pipes if id(p) not in dead]+list(tx.new)
            g.pipes.sort(key=lambda p:p.start)
            self.completed_renewals+=1
        else:self.completed_growth+=1
        # The group is fully packed without overlaps at every completed txn.
        pos=g.start
        for p in g.pipes:
            assert p.pid and p.start==pos
            pos+=p.length
        assert pos==g.start+g.width
        g.busy=False;self.pending.remove(tx);self.reserved-=tx.width
        self._schedule(g)

    def _positive_packet(self):
        self._room()
        ready=[t for t in self.pending if t.ready()]
        if not ready:
            tx=self._growth()
            assert tx is not None,'no positive work after completed negative packet'
            ready=[tx]
        primary=min(ready,key=lambda t:t.sequence)
        need=len(primary.new)-primary.placed
        want=math.ceil((self.s.target_positive*self.count-self.pos)/(1-self.s.target_positive))
        limit=max(need,min(11,max(1,want)))
        # Growth is an ongoing state-dependent action, not an endpoint suffix.
        if want>need or self.turn%37==0:self._growth()
        for j in range(limit):
            self._room()
            candidates=[t for t in self.pending if t.ready()]
            if not candidates:
                if self.pos/max(1,self.count)>=self.s.target_positive:break
                fresh=self._growth()
                if fresh is None:break
                candidates=[fresh]
            must_finish=(primary in self.pending and len(primary.new)-primary.placed>=limit-j)
            tx=primary if must_finish else self.r.choice(candidates)
            p=tx.new[tx.placed];self._place(p);tx.placed+=1;self._finish(tx)
            if self.count<self.s.n and tx.done() and (want>need or self.turn%37==0):self._growth()
        assert primary.done()

    def _negative_packet(self):
        self._room()
        while len(self.pending)<self.s.concurrency:
            if self._open_renewal() is None:break
        deletable=[t for t in self.pending if t.deletable()]
        if not deletable:
            tx=self._open_renewal(forced=True)
            assert tx is not None,'no negative work after completed positive packet'
            deletable=[tx]
        primary=min(deletable,key=lambda t:t.sequence)
        need=len(primary.old)-primary.removed
        want=math.ceil(self.pos/self.s.target_positive-self.count)
        limit=max(need,min(5,max(1,want)))
        for j in range(limit):
            self._room()
            choices=[t for t in self.pending if t.deletable()]
            if not choices:
                tx=self._open_renewal()
                if tx is None:break
                choices=[tx]
            must_finish=(primary.deletable() and len(primary.old)-primary.removed>=limit-j)
            tx=primary if must_finish else self.r.choice(choices)
            p=tx.old[tx.removed];self._remove(p);tx.removed+=1
        assert not primary.deletable()
        self.turn+=1

    def _check_pending_state(self):
        # Prefix bookkeeping must describe exactly the commands already emitted.
        assert self.reserved==sum(t.width for t in self.pending)
        assert len({t.group for t in self.pending})==len(self.pending)
        pending_groups={t.group for t in self.pending}
        assert all(g.busy==(g.index in pending_groups) for g in self.groups)
        represented={p.pid for g in self.groups for p in g.pipes if p.pid}
        for t in self.pending:
            assert all(p.pid==0 for p in t.old[:t.removed])
            assert all(p.pid>0 for p in t.old[t.removed:])
            assert all(p.pid>0 for p in t.new[:t.placed])
            assert all(p.pid==0 for p in t.new[t.placed:])
            if not t.growth:represented.update(p.pid for p in t.new[:t.placed])
        assert represented==set(self.live)
        assert self.arena==sum(g.width for g in self.groups)
        assert self.arena-self.F<=self.reserved

    def run(self):
        self._growth(first=True)
        try:
            while True:
                self._positive_packet()
                self._negative_packet()
        except _Done:pass
        self._check_pending_state()
        assert self.count==self.s.n and self.arena>=400
        assert self.F==sum(p.length for p in self.live.values())
        assert self.F/self.T>=.85,(self.s,self.F,self.T,self.reserved,self.arena)
        assert not any(pid in self.live for pid in self.initial),'initial population was not retired'
        assert self.max_pos_run<=11 and self.max_neg_run<=5 and self.max_pending<=self.s.concurrency
        lower=20*((self.peak+19)//20);ages=sorted(self.ages)
        def q(x):return ages[round((len(ages)-1)*x)] if ages else None
        return dict(source=Path(__file__).name,generator_version=VERSION,
            name=self.s.name,split=self.s.split,seed=self.s.seed,n=self.count,family=self.s.family,
            stratum=f'{self.s.family}_n{self.s.n}',spec=asdict(self.s),
            sha256=self.ih.hexdigest(),witness_sha256=self.wh.hexdigest(),
            F=self.F,T=self.T,bound=lower,attainable_KPI=self.F/self.T,
            bound_definition='peak-volume lower bound, witness T is a feasible upper bound',
            optimal_trench_interval=[lower,self.T],optimum_exact=lower==self.T,
            theoretical_max_KPI=self.F/self.T if lower==self.T else None,
            certificate=dict(method='parallel-microspan-transactions-with-mixed-growth',
                requested_concurrency=self.s.concurrency,max_pending_transactions=self.max_pending,
                completed_growth_spans=self.completed_growth,completed_renewals=self.completed_renewals,
                max_positive_run=self.max_pos_run,max_negative_run=self.max_neg_run,
                positive_commands=self.pos,negative_commands=self.neg,positive_fraction=self.pos/self.count,
                max_unfilled_volume=self.max_debt,max_unfilled_fraction_after_startup=self.max_debt_fraction,
                startup_volume_threshold=400,startup_finished_at_command=self.initial_fill_commands,
                initial_pipes=len(self.initial),initial_pipes_deleted=self.initial_deleted,
                initial_pipes_still_live=sum(pid in self.live for pid in self.initial),
                finite_due_dates=True,forced_early_hazard_service=self.forced_hazard,
                hazard_switches=list(self.s.switches[1:]),
                scheduled_hazard_counts={f'{a}:{b}':v for (a,b),v in self.hazards.items()},
                deleted_age_q10_q50_q90_q99=[q(x) for x in(.1,.5,.9,.99)],
                size_histogram=dict(sorted(self.hist.items())),phase_insertions=dict(self.phases),
                final_padding_commands=0,coordinates_in_input=False),
            provenance=dict(copied_public_commands=0,solver_inspected=False,results_used=False,
                limit='constructed stress; no hidden-test-distribution or exact-OPT claim'))


def verify_specs():
    """Static contract checks only: does not instantiate a builder/emit commands."""
    ss=specs();assert sum(s.split=='development' for s in ss)==12
    assert sum(s.split=='sealed_final' for s in ss)==24
    assert len({s.name for s in ss})==len(ss) and len({s.seed for s in ss})==len(ss)
    assert all(16<=s.concurrency<=64 and 0<s.n<=200000 for s in ss)
    assert all(len(s.grammar)==len(s.switches) and s.switches[0]==0 for s in ss)
    dg={x for s in ss if s.split=='development' for x in s.grammar}
    fg={x for s in ss if s.split=='sealed_final' for x in s.grammar}
    assert not dg.intersection(fg)
    # With missing volume<=10%, section rounding cannot lower final density<.85.
    assert .90*400/(400+19)>.85
    return {'cases':len(ss),'development':12,'sealed_final':24,'n200000':24}


def generate(new_dir):
    verify_specs();p=Path(new_dir);p.mkdir(parents=True,exist_ok=False)
    sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();seen=set()
    with (p/'manifest.jsonl').open('w') as mf,tempfile.TemporaryDirectory(prefix='pipes-async-witness-') as td:
        wp=Path(td)/'witness.txt'
        for s in specs():
            ip=p/(s.name+'.in')
            with ip.open('wb') as inp,wp.open('wb') as wit:r=_Build(s,inp,wit).run()
            assert r['sha256'] not in seen,'duplicate deterministic stream'
            seen.add(r['sha256']);r.update(input=ip.name,source_sha256=sha)
            mf.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n');mf.flush();wp.unlink()
    return p/'manifest.jsonl'


def replay_witness(metadata,destination):
    raw=dict(metadata['spec']);raw['grammar']=tuple(raw['grammar']);raw['switches']=tuple(raw['switches'])
    p=Path(destination)
    with p.open('xb') as wit:r=_Build(Spec(**raw),None,wit).run()
    assert r['sha256']==metadata['sha256'] and r['witness_sha256']==metadata['witness_sha256']
    return p

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('new_dir')
    print(generate(ap.parse_args().new_dir))
