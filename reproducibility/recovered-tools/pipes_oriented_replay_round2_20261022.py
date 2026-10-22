"""Pure oriented-guarded transformer; no writes/builds/solver runs.

Order is explicit: pinned guarded-envelope(source, compact=True) exactly once,
then decode those compact tables and reflect selected components in-place.
There is no second permutation/compaction. Cangjie input must be uncached policy
source; DeferredReplayTable prefix arrays are regenerated with the tables.

A group contains tables sharing their first two commands. Its components are
unions of non-transient spatial intervals, as in the pinned compact compiler.
For each component and EVERY complete public path in that group, reflect only
if the cumulative reflected local right endpoint never exceeds the original.
A strict benefit on at least one path is required. Transient placements (removed
by the immediately following command) keep the parent's best-fit treatment.
All resulting complete paths are geometrically checked, every prefix trench is
required <= compact parent, final T must be equal, and all common command-prefix
positions across all 15 tables must agree. This proves public table geometry,
not fallback quality or a guarantee on unknown continuations.
"""
import bisect
import hashlib
import importlib.util
import re
from pathlib import Path

GUARD=Path('/tmp/pipes_replay_guarded_envelope_round2_20261022.py')
GUARD_SHA='0ec7f2f6694191db3a3ff10d7e553b83500a7e33f5355a869af189f0842736f0'
REPLAY=Path('/tmp/pipes_replay_round2_20261022.py')
REPLAY_SHA='44b22b8cc4a6567fd4ec6aee88fd7baa1532561ad24fa702a03a3b451696bff2'
ORDER='parent_guard_first_compact_true_then_orientation'


def _module(path,digest,name):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,(str(path),'parent changed')
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def _parents():
    return (_module(GUARD,GUARD_SHA,'oriented_guard_parent'),
            _module(REPLAY,REPLAY_SHA,'oriented_geometry_parent'))


def _temporary(table,step):
    n,x,p=table[step]
    return n>0 and step+1<len(table) and table[step+1][0]==-p


def orient_tables(tables):
    """Return oriented tables and concise proof metadata; no global mutations."""
    _,parent=_parents()
    groups={}
    for i,table in enumerate(tables):groups.setdefault(tuple(r[0] for r in table[:2]),[]).append(i)
    out=[[r[:] for r in table] for table in tables];group_proofs=[]
    for group in groups.values():
        intervals=[]
        for i in group:
            for step,(n,x,p) in enumerate(tables[i]):
                if n>0 and not _temporary(tables[i],step):intervals.append((x,x+n,step))
        components=[]
        for left,right,step in sorted(intervals):
            if components and left<components[-1][1]:
                components[-1][1]=max(components[-1][1],right)
                components[-1][2]=min(components[-1][2],step)
            else:components.append([left,right,step])
        starts=[c[0] for c in components]
        flips=set(range(len(components)));strict=set()
        for i in group:
            heights={}
            for step,(n,x,p) in enumerate(tables[i]):
                if n<=0 or _temporary(tables[i],step):continue
                j=bisect.bisect_right(starts,x)-1
                left,right,_=components[j];assert left<=x and x+n<=right
                ordinary,reflected=heights.get(j,(0,0))
                ordinary=max(ordinary,x+n-left);reflected=max(reflected,right-x)
                heights[j]=(ordinary,reflected)
                if reflected>ordinary:flips.discard(j)
                if reflected<ordinary:strict.add(j)
        flips.intersection_update(strict)
        for i in group:
            for step,(n,x,p) in enumerate(tables[i]):
                if n<=0:continue
                if _temporary(tables[i],step):out[i][step][1]=-2;continue
                j=bisect.bisect_right(starts,x)-1
                if j in flips:
                    left,right,_=components[j];out[i][step][1]=left+right-x-n
        group_proofs.append(dict(public_tables=[i+1 for i in group],
            components=len(components),reflected_components=len(flips),
            first_reflections=[dict(start=components[j][0],end=components[j][1],
                first_command=components[j][2]+1) for j in sorted(flips,key=lambda j:components[j][2])[:3]]))
    paths=[]
    for i,(old,new) in enumerate(zip(tables,out)):
        original=parent._Geometry();oriented=parent._Geometry();prefix={};changed=0
        for step,(a,b) in enumerate(zip(old,new)):
            n,x,p=a;assert n==b[0] and p==b[2]
            if n<0:
                assert original.pipes[p][1]>0 and oriented.pipes[p][1]>0
                original.remove(p);oriented.remove(p)
            else:
                original.place(n,x);b[1]=oriented.place(n,b[1]);changed+=x!=b[1]
            assert oriented.T<=original.T,('prefix trench increased',i+1,step+1,original.T,oriented.T)
            if step+1 in (11,18,31,63,97,127,509):prefix[step+1]=[original.T,oriented.T]
        assert oriented.T==original.T,('final trench changed',i+1,original.T,oriented.T)
        paths.append(dict(public_table=i+1,commands=len(new),changed_placements=changed,
            prefix_trenches=prefix,final_T=[original.T,oriented.T]))
    common=[]
    for i,a in enumerate(out):
        for j in range(i+1,len(out)):
            length=0
            for left,right in zip(a,out[j]):
                if left[0]!=right[0]:break
                assert left[0]<0 or left[1]==right[1],('common prefix conflict',i+1,j+1,length+1)
                length+=1
            if length:common.append(dict(public_tables=[i+1,j+1],equal_prefix_commands=length))
    proof=dict(order=ORDER,groups=group_proofs,paths=paths,common_prefix_checks=common,
        complete_geometry_valid=True,every_prefix_T_nonincreasing=True,all_final_T_equal=True,
        transient_policy='parent best-fit, immediately deleted',
        quality_scope='public replay table geometry only; fallback needs independent evaluation')
    return out,proof


def _rewrite_cpp(source,tables,parent):
    for i,table in enumerate(tables):
        pattern=r'(static const char\* const encoded'+str(i)+r'\[\]=\{).*?\n\};'
        blob=parent._encode(table);body='\n'.join('"'+blob[j:j+120]+'",' for j in range(0,len(blob),120))
        source,count=re.subn(pattern,lambda m:m[1]+'\n'+body+'\n};',source,flags=re.S)
        assert count==1,('CPP table anchor',i,count)
    return source


def _rewrite_cj(source,tables,parent):
    for i,table in enumerate(tables):
        blob=parent._encode(table)
        body='\n'.join('    decoder.feed("'+blob[j:j+4096]+'")' for j in range(0,len(blob),4096))
        replacement=f'func replayTable{i}(): ReplayTable {{\n    let decoder = ReplayDecoder()\n'+body+'\n    return decoder.finish()\n}'
        source,count=re.subn(r'func replayTable'+str(i)+r'\(\): ReplayTable \{.*?\n\}',lambda _:replacement,source,flags=re.S)
        assert count==1,('CJ table anchor',i,count)
        prefix=table[:16];commands=', '.join(str(r[0])for r in prefix);positions=', '.join(str(r[1])for r in prefix)
        replacement=f'tables.add(DeferredReplayTable({i}, {len(table)}, [{commands}], [{positions}]))'
        source,count=re.subn(r'tables.add\(DeferredReplayTable\('+str(i)+r', .*?\)\)',lambda _:replacement,source)
        assert count==1,('CJ prefix anchor',i,count)
    return source


def transform_cpp(source):
    guard,parent=_parents();compact=guard.apply_cpp(source,compact=True)
    tables,proof=orient_tables(parent._cpp_tables(compact))
    return _rewrite_cpp(compact,tables,parent),proof


def transform_cj(source):
    guard,parent=_parents();compact=guard.apply_cj(source,compact=True)
    tables,proof=orient_tables(parent._cj_tables(compact))
    return _rewrite_cj(compact,tables,parent),proof


def apply_cpp(source):return transform_cpp(source)[0]
def apply_cj(source):return transform_cj(source)[0]
