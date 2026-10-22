from pathlib import Path
import json,subprocess,csv,hashlib,collections
HERE=Path(__file__).resolve().parent;losses=json.load(open(HERE/'losses.json'));names=['baseline','current','no_dp','mc_off_dp','fresh','legacy_tie']
COL=['step','command','x','dig','T','gaps','dpactive','legacy','selected','high','mc_before','mc_after','dpcount','live','deletes']
def run(name,path,focus=0,force=None):
 args=[str(HERE/name/'solver'),str(path),str(focus)]
 if force:args+=list(map(str,force))
 p=subprocess.run(args,capture_output=True,check=True,timeout=60)
 rows=[dict(zip(COL,map(int,row)))for row in csv.reader(p.stdout.decode().splitlines())]
 states=[json.loads(line)for line in p.stderr.decode().splitlines()if line.startswith('{')]
 return rows,states
report={'scope':'23 previously observed losses only, diagnostic copies and hindsight ablations, no fresh evaluation or promotion. A full-path ablation proves a counterfactual result on these inputs; it does not isolate the first differing action as final-loss cause.','cases':[]}
for case in losses:
 id=case['id'];path=Path(case['input_path']);assert hashlib.sha256(path.read_bytes()).hexdigest()==case['test_sha256']
 traces={};summary={}
 for name in names:
  rows,_=run(name,path);traces[name]=rows;(HERE/f'{id}-{name}.csv').write_text(','.join(COL)+'\n'+'\n'.join(','.join(str(row[c])for c in COL)for row in rows)+'\n');summary[name]={'final_T':rows[-1]['T']}
 assert traces['baseline'][-1]['T']==case['baseline_T']
 assert traces['current'][-1]['T']==case['current_T']
 b,c=traces['baseline'],traces['current']
 first=next(j for j,(x,y)in enumerate(zip(b,c))if(x['x'],x['dig'])!=(y['x'],y['dig']))
 deficit=next(j for j,(x,y)in enumerate(zip(b,c))if y['T']>x['T'])
 last_nonpositive=max([j for j,(x,y)in enumerate(zip(b,c))if y['T']<=x['T']],default=-1)
 persistent=last_nonpositive+1
 extra=next(j for j,(x,y)in enumerate(zip(b,c))if y['dig']>x['dig'])
 events={label:{'baseline':b[j],'current':c[j]}for label,j in [('first_action',first),('first_extra_dig',extra),('first_T_deficit',deficit),('persistent_T_deficit',persistent)]}
 states={}
 for step in sorted({first+1,deficit+1,persistent+1}):
  states[step]={}
  for name in ['baseline','current']:
   _,s=run(name,path,step);states[step][name]=s
 forced,fs=run('current',path,0,(first+1,b[first]['x']));summary['force_first_baseline_action_only']={'final_T':forced[-1]['T'],'at_step':first+1,'forced_x':b[first]['x']}
 # Actual intervention uses one previously valid action on the common state,
 # then current causal continuation. The step/action selection is hindsight.
 currentstate=states[first+1]['current'][-1]if states[first+1]['current']else{}
 freq=currentstate.get('request_freq',[])
 tokens=list(map(int,path.read_text().split()[2:]));future=[x for x in tokens[first+1:]if x>0][:64]
 futurefreq=collections.Counter(future);den=sum(freq);futureden=len(future)
 tv=sum(abs((freq[i-1]/den if den else 0)-(futurefreq[i]/futureden if futureden else 0))for i in range(1,41))/2 if freq and futureden else None
 annotations={'first_DP_active':bool(c[first]['dpactive']),'first_MC_ran':c[first]['mc_after']>c[first]['mc_before'],'model_age_at_first':currentstate.get('model_age'),'request_count_at_first':den,'future64_TV_hindsight':tv,'MCoff_DP_change_vs_current':summary['mc_off_dp']['final_T']-case['current_T'],'fresh_model_change_vs_current':summary['fresh']['final_T']-case['current_T'],'forced_first_change_vs_current':summary['force_first_baseline_action_only']['final_T']-case['current_T']}
 report['cases'].append({**case,'events':events,'state_snapshots':states,'ablations':summary,'annotations':annotations})
 (HERE/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
 print(id,'first',first+1,'persistent',persistent+1,{x:v['final_T']for x,v in summary.items()},flush=True)
