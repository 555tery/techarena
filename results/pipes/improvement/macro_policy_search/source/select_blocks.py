#!/usr/bin/env python3
"""Choose macro-policy replay blocks from baseline-observable allocator state."""
import bisect
import heapq
import json
import math
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
FINAL = ROOT / "results/pipes/final/open-run-size-cohort-lanes"
OUT = ROOT / "results/pipes/improvement/macro_policy_search/analysis/block_plan.json"
BLOCK_LENGTHS = (256, 512, 1024, 2048, 4096)
CASES = (5, 9, 15)

class Geometry:
    def __init__(self):
        self.starts=[]; self.ends=[]; self.by_start={}; self.trench=0; self.free_total=0
        self.heap=[]; self.active_count=0; self.pipes=[None]
    def _remove_gap(self, i):
        a=self.starts.pop(i); b=self.ends.pop(i)
        del self.by_start[a]
        self.free_total -= b-a
        return a,b
    def add_gap(self, a, b):
        if a>=b:return
        i=bisect.bisect_left(self.starts,a)
        if i>0 and self.ends[i-1]>=a:
            pa,pb=self._remove_gap(i-1); i-=1
            a=min(a,pa);b=max(b,pb)
        while i<len(self.starts) and self.starts[i]<=b:
            pa,pb=self._remove_gap(i)
            a=min(a,pa);b=max(b,pb)
        self.starts.insert(i,a);self.ends.insert(i,b);self.by_start[a]=b
        self.free_total += b-a
        heapq.heappush(self.heap, (-(b-a), a, b))
    def split_gap_at(self, start, length):
        i=bisect.bisect_right(self.starts,start)-1
        if i<0 or self.ends[i]<start+length:
            raise ValueError(("placement outside free gap",start,length))
        a,b=self._remove_gap(i)
        self.add_gap(a,start);self.add_gap(start+length,b)
    def place(self, length, digs, start):
        if digs==0:
            self.split_gap_at(start,length)
        else:
            old=self.trench;new=old+20*digs
            tail_i=len(self.starts)-1 if self.starts and self.ends[-1]==old else None
            tail_start=old
            if tail_i is not None:
                tail_start,_=self._remove_gap(tail_i)
            self.trench=new
            if start<tail_start or start+length>new:
                raise ValueError(("bad expanded placement",old,new,start,length,tail_start))
            self.add_gap(tail_start,start);self.add_gap(start+length,new)
        self.pipes.append((start,length,True));self.active_count+=1
    def remove(self, pid):
        p=self.pipes[pid]
        if p is None or not p[2]: raise ValueError(("invalid PID",pid))
        self.pipes[pid]=(p[0],p[1],False)
        self.active_count-=1
        self.add_gap(p[0],p[0]+p[1])
    def largest_gap(self):
        while self.heap and self.by_start.get(self.heap[0][1]) != self.heap[0][2]:
            heapq.heappop(self.heap)
        return -self.heap[0][0] if self.heap else 0
    def tail_length(self):
        if self.ends and self.ends[-1]==self.trench: return self.ends[-1]-self.starts[-1]
        return 0

def load_case(case):
    vals=list(map(int,(ROOT/f"data/pipes/open/{case}.in").read_text().split()))
    n=vals[1]; cmds=vals[2:]
    if len(cmds)==n+1 and cmds[-1]==0:cmds=cmds[:-1]
    assert len(cmds)==n
    lines=(FINAL/f"runs/{case}/judge_output.txt").read_text().splitlines()
    assert len(lines)==n
    st=Geometry();snapshots=[];growth=deque(maxlen=256);line_i=0
    for op,c in enumerate(cmds,1):
        if c>0:
            largest=st.largest_gap();tail=st.tail_length()
            nofit=largest<c
            hist_growth=sum(growth)/max(1,len(growth))
            snapshots.append({
                "op":op,"length":c,"trench_m":st.trench,"free_total_m":st.free_total,
                "gap_count":len(st.starts),"largest_gap_m":largest,"tail_m":tail,
                "active_pipes":st.active_count,
                "unavoidable_growth_state":st.free_total>=c and nofit,
                "recent_growth_fraction_256":hist_growth,
                "fit_count":sum(1 for b,a in zip(st.ends,st.starts) if b-a>=c),
                "baseline_digs":int(lines[line_i].split()[0])
            })
            digs,start=map(int,lines[line_i].split());line_i+=1
            st.place(c,digs,start);growth.append(digs>0)
        elif c<0:
            st.remove(-c);line_i+=1
    assert line_i==len(lines)
    return snapshots,st.trench

def choose_unique(rows, n, metric, reverse):
    eligible=[r for r in rows if r["op"]+n-1<=r["commands"]]
    eligible.sort(key=metric,reverse=reverse)
    chosen=[]
    for r in eligible:
        # Distinct starts for a window family. We only reject exact same start;
        # cross-length overlaps are useful in duration comparisons.
        if any(x["op"]==r["op"] for x in chosen):continue
        chosen.append(r)
        if len(chosen)==1:break
    return chosen[0] if chosen else None

plan=[]
for case in CASES:
    snaps,trench=load_case(case)
    vals=list(map(int,(ROOT/f"data/pipes/open/{case}.in").read_text().split()))
    command_count=vals[1]
    min_warm_op=max(128,command_count//20)
    used={"high":[],"low":[]}
    # Select one high-pressure and one low-pressure state for each block length.
    for size in BLOCK_LENGTHS:
        eligible=[r for r in snaps if r["op"]+size-1<=command_count]
        high=[r for r in eligible if r["unavoidable_growth_state"]]
        def separated(rows, mode, metric, reverse):
            rows=sorted(rows,key=metric,reverse=reverse)
            distance=max(128,size//2)
            for r in rows:
                if all(abs(r["op"]-old)>=distance for old in used[mode]):
                    used[mode].append(r["op"])
                    return r
            r=rows[0]
            used[mode].append(r["op"])
            return r
        if high:
            # Prefer a state with many distinct unusable holes and recent trench growth.
            high_row=separated(high,"high",lambda r:(r["gap_count"],r["free_total_m"]/(r["largest_gap_m"]+1),r["recent_growth_fraction_256"],-r["op"]),True)
            high_kind="fragmented_free_volume"
        else:
            high_row=separated(eligible,"high",lambda r:(r["gap_count"],r["free_total_m"]/(r["largest_gap_m"]+1),r["recent_growth_fraction_256"],-r["op"]),True)
            high_kind="max_observed_fragmentation_fallback"
        low_eligible=[r for r in eligible if r["op"]>=min_warm_op and r["fit_count"]>0 and not r["unavoidable_growth_state"]]
        if not low_eligible:low_eligible=[r for r in eligible if r["op"]>=min_warm_op]
        low_row=separated(low_eligible,"low",lambda r:(r["gap_count"],r["recent_growth_fraction_256"],-r["tail_m"],-r["largest_gap_m"],r["op"]),False)
        for kind,row in ((high_kind,high_row),("low_fragmentation",low_row)):
            plan.append({"case":case,"block_start_op":row["op"],"block_length":size,
                "block_end_op":row["op"]+size-1,"selection_stratum":kind,
                "start_state":{k:row[k] for k in ("length","trench_m","free_total_m","gap_count","largest_gap_m","tail_m","active_pipes","unavoidable_growth_state","recent_growth_fraction_256","fit_count","baseline_digs")}})
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps({"design":"state-stratified diagnostic blocks; selection uses current baseline geometry and past growth only", "block_lengths":list(BLOCK_LENGTHS),"cases":list(CASES),"blocks":plan},indent=2)+"\n")
print("blocks",len(plan))
for b in plan:print(b["case"],b["block_start_op"],b["block_length"],b["selection_stratum"],b["start_state"]["gap_count"],b["start_state"]["unavoidable_growth_state"])
