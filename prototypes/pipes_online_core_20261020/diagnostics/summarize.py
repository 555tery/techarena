import subprocess,json,csv
from pathlib import Path
r=Path(__file__).resolve().parent;old=r.parents[1]/'pipes_closed_ready_20261020'
report={'scope':'Diagnostic counterfactual suffix replays on six already observed inputs only. No candidate/new generator/platform/fresh validation. Each simulated allocator consumes commands sequentially; comparison and reset ablations are hindsight diagnostics.','variants':['O=online original state','OI=fresh import into online physical geometry','Oshared=online metadata, shared own physical free gaps, no reservations, model dirty','H=actual hybrid import','Hkeep=online metadata plus hybrid physical geometry/shared gaps','Hcold=H with regime flags/runs/deletion-rank confidence cleared at handoff','Hmc=H with only shadow MC budget/counters retained'],'cases':[]}
for i,abort in [(54,3),(81,10),(105,155),(118,2897),(120,155),(126,17161)]:
 p=subprocess.run([str(r/'trace'),str(old/f'evaluation/final/case-{i:03d}.in'),str(abort),str(r/f'{i}-hybrid.stdout')],capture_output=True,check=True)
 (r/f'{i}-trace.csv').write_bytes(p.stdout);(r/f'{i}-state.txt').write_bytes(p.stderr)
 rows=[[int(x)for x in row]for row in csv.reader(p.stdout.decode().splitlines())];states=p.stderr.decode().splitlines()
 case={'case':i,'handoff_step':abort,'handoff':states[0],'states':states[1:],'variants':{}}
 for j,name in enumerate(['O','OI','Oshared','H','Hkeep','Hcold','Hmc']):
  finalT=rows[-1][4+j*4];first=next((q for q in rows if q[2:5]!=q[2+j*4:5+j*4]),None);extra=next((q for q in rows if q[3+j*4]>q[3]),None);deficit=next((q for q in rows if q[4+j*4]>q[4]),None)
  def event(q):return None if q is None else {'step':q[0],'command':q[1],'online':dict(zip(['start','new_excavation','trench','gapcount'],q[2:6])),'variant':dict(zip(['start','new_excavation','trench','gapcount'],q[2+j*4:6+j*4]))}
  case['variants'][name]={'final_trench':finalT,'first_suffix_action_difference':event(first),'first_extra_excavation_event':event(extra),'first_trench_deficit':event(deficit)}
  if name in ['O','H']:
   pol='online'if name=='O'else'hybrid';record=json.load(open(old/f'measurements/official/final/{pol}/final-{i:03d}/record.json'));assert finalT==record['trench_length_m'],(i,pol)
   responses=(r/f'{i}-{pol}.stdout').read_text().splitlines();T=0
   for step,line in enumerate(responses,1):
    numbers=[int(x)for x in line.split()]
    if len(numbers)==2:T+=20*numbers[0]
    if step>=abort:
     q=rows[step-abort];assert T==q[4+j*4],(i,pol,step,'T')
     if len(numbers)==2:assert numbers[1]==q[2+j*4],(i,pol,step,'x')
   case['variants'][name]['placement_and_trench_parity_verified']=True
 report['cases'].append(case)
 print(i,{name:v['final_trench']for name,v in case['variants'].items()})
(r/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
