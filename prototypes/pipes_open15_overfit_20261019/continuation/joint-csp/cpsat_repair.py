"""OPEN15_FULL_OVERFIT: exact finite-domain rectangle feasibility, known future lifetimes."""
import sys,json,hashlib,argparse,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'local-deps'))
from ortools.sat.python import cp_model
ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('partial',type=Path);ap.add_argument('output',type=Path);ap.add_argument('H',type=int);ap.add_argument('--seconds',type=float,default=90);ap.add_argument('--hint',type=Path);ap.add_argument('--workers',type=int,default=1);a=ap.parse_args()
v=a.input.read_text().split();n=int(v[1]);cmd=list(map(int,v[2:2+n]));L=[0];B=[0];D=[n]
for t,c in enumerate(cmd):
 if c>0:L.append(c);B.append(t);D.append(n)
 else:D[-c]=t
P=[-1]+list(map(int,a.partial.read_text().split()));assert len(P)==len(L)
mov=[i for i in range(1,len(L)) if P[i]<0];fixed=[i for i in range(1,len(L)) if P[i]>=0];assert all(P[i]+L[i]<=a.H for i in fixed)
model=cp_model.CpModel();xs={};rect_x=[];rect_t=[];domains={}
hints=([-1]+list(map(int,a.hint.read_text().split()))) if a.hint else None
for i in mov:
 cap=a.H-L[i];diff=[0]*(cap+2)
 for j in fixed:
  if max(B[i],B[j])>=min(D[i],D[j]):continue
  lo=max(0,P[j]-L[i]+1);hi=min(cap,P[j]+L[j]-1)
  if lo<=hi:diff[lo]+=1;diff[hi+1]-=1
 runs=[];active=0;start=-1
 for z in range(cap+2):
  active+=diff[z]
  if z<=cap and active==0:
   if start<0:start=z
  elif start>=0:runs.append((start,z-1));start=-1
 if not runs:print('EMPTY_DOMAIN',i,flush=True);raise SystemExit(4)
 domains[i]=runs;x=model.new_int_var_from_domain(cp_model.Domain.from_intervals(runs),f'x{i}');xs[i]=x
 rect_x.append(model.new_fixed_size_interval_var(x,L[i],f'X{i}'));rect_t.append(model.new_fixed_size_interval_var(B[i],D[i]-B[i],f'T{i}'))
 if hints and any(lo<=hints[i]<=hi for lo,hi in runs):model.add_hint(x,hints[i])
model.add_no_overlap_2d(rect_x,rect_t)
solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=a.seconds;solver.parameters.num_search_workers=a.workers;solver.parameters.random_seed=20261019;solver.parameters.log_search_progress=True
print(json.dumps({'movables':len(mov),'fixed':len(fixed),'target':a.H,'domain_intervals':sum(map(len,domains.values()))}),flush=True)
status=solver.solve(model);print('CP_STATUS',solver.status_name(status),flush=True)
if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
 for i in mov:P[i]=solver.value(xs[i])
 # Independent physical occupancy replay, including the previously fixed background.
 cells=bytearray(a.H);live={};pid=0;extent=0
 for t,c in enumerate(cmd):
  if c>0:
   pid+=1;x=P[pid];assert not any(cells[x:x+c]),(t,pid,x,c);cells[x:x+c]=b'\1'*c;live[pid]=(x,c);extent=max(extent,x+c)
  else:
   x,l=live.pop(-c);assert all(cells[x:x+l]);cells[x:x+l]=b'\0'*l
 a.output.write_text('\n'.join(map(str,P[1:]))+'\n');print('VERIFIED_EXTENT',extent,'T',20*((extent+19)//20),flush=True)
result={'status':solver.status_name(status),'H':a.H,'movables':len(mov),'solver_stats':solver.response_stats(),'source_sha256':hashlib.sha256(a.partial.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'success':status in (cp_model.OPTIMAL,cp_model.FEASIBLE),'time':time.time()};a.output.with_suffix('.report.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(0 if result['success'] else 2)
