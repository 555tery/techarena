#!/usr/bin/env python3
"""Input-only independent corpus. Never reads solver code/results or prior commands."""
from pathlib import Path
import hashlib,json,random,sys
ROOT=Path('/Users/555tery/techarena')
OUT=ROOT/'prototypes/pipes_guard_generalization_20261022'
MANIFEST=OUT/'input_manifest.jsonl'
SPLITS={'calibration':6,'final':8}
NS={
 'ordinary':{'calibration':[200000,200000,5000,16001,42003,7777],'final':[200000,200000,3499,12007,20003,48001,9001,30011]},
 'series':{'calibration':[200000,13000,6003,25001,50007,4009],'final':[200000,15001,7003,29009,51001,11003,32003,19001]},
 'interruption':{'calibration':[200000,4001,12003,26007,7001,35001],'final':[200000,5003,14009,28001,8009,37003,17011,43003]},
 'motif':{'calibration':[96,100,104,112,120,128],'final':[91,97,103,109,115,121,125,127]},
}
SEED_BASE={'calibration':202610220000,'final':202610229000}
FAMILY_INDEX={'ordinary':1,'series':2,'interruption':3,'motif':4}

def sha(b):return hashlib.sha256(b).hexdigest()
def js(x):return json.dumps(x,ensure_ascii=False,sort_keys=True)
class Stream:
 def __init__(self,seed):
  self.rng=random.Random(seed);self.cmd=[];self.active={};self.ids=[];self.pos={};self.pid=0;self.live=0;self.peak=0
 def add(self,length):
  assert 1<=length<=40
  self.pid+=1;self.active[self.pid]=length;self.pos[self.pid]=len(self.ids);self.ids.append(self.pid)
  self.live+=length;self.peak=max(self.peak,self.live);self.cmd.append(length)
 def delete(self,pid):
  length=self.active.pop(pid);i=self.pos.pop(pid);last=self.ids.pop()
  if i<len(self.ids):self.ids[i]=last;self.pos[last]=i
  self.live-=length;self.cmd.append(-pid)
 def remove(self,mode='random'):
  if mode=='old':pid=min(self.ids)
  elif mode=='new':pid=max(self.ids)
  else:pid=self.ids[self.rng.randrange(len(self.ids))]
  self.delete(pid)

def ordinary(s,n,j,final):
 # Volume-regulated changing size/lifetime process, no permanent initial background.
 targets=([800,1600,7000,25000,90000,14000,45000,2400] if final else [700,1300,6000,22000,80000,12000])
 target=targets[j];modes=['random','new','random','old'];palettes=([list(range(2,11)),[3,7,11,19,31],[17,23,29,37],list(range(21,41)),[2,3,8,13,21,34]] if final else [list(range(1,9)),list(range(12,25)),list(range(25,41)),[2,5,9,17,28,39]])
 while len(s.cmd)<n:
  p=min(len(palettes)-1,len(s.cmd)*len(palettes)//n)
  # Composition change is bounded in total live volume; final is ordinary steady operation.
  local=target-[0,11,23,7,0][p]
  length=s.rng.choice(palettes[p])
  if len(s.cmd)==n-1 or not s.ids or s.live<local or (s.live<local+35 and s.rng.random()<.24):s.add(length)
  else:s.remove(modes[(p+j)%len(modes)])
 return {'target_live_volume_m':target,'permanent_background':False,'phase_palettes':palettes,'lifetime_modes':modes,'reason':'small live volume can coexist with long command histories; deletions use active placement ordinals'}

def series(s,n,j,final):
 sizes=([3,4,7,11,16,22,29,37,39] if final else [2,5,9,14,20,28,36])
 target_count=([101,173,419,1301,6301,719,2503,311] if final else [113,211,503,1501,7103,809])[j]
 # No extra terminal fill: a normal finite stream is cut at the declared N.
 pending=[];stage=-1;rounds=0
 while len(s.cmd)<n:
  p=min(len(sizes)-1,len(s.cmd)*len(sizes)//n)
  length=sizes[p]
  if len(s.cmd)==n-1:s.add(length);break
  if len(s.ids)<target_count:
   s.add(length);continue
  if not pending:
   rounds+=1
   fraction=([.037,.061,.079,.043,.067] if final else [.04,.06,.08])[rounds%(5 if final else 3)]
   count=max(3,int(target_count*fraction)+s.rng.randrange(-2,4))
   count=min(count,len(s.ids)//8)
   # Cohort removals plus noisy/interleaved deletions. All replacements use stage length.
   chosen=(sorted(s.ids)[:count] if rounds%3 else s.rng.sample(s.ids,count))
   if rounds%4==0:
    pending=[a for pid in chosen for a in [('delete',pid),('add',length)]]
   else:pending=[('delete',pid) for pid in chosen]+[('add',length)]*count
  action,value=pending.pop(0)
  if action=='add':s.add(value)
  else:s.delete(value)
 return {'stage_sizes':sizes,'target_live_count':target_count,'cohort_rounds':rounds,'cohort_fraction_max':.08,'reason':'stable equal-size runs grow through monotone length stages; partial old cohorts are retired with noisy counts and interleaving'}

def interruption(s,n,j,final):
 target=([1100,1700,9000,27000,5000,42000,13000,73000] if final else [1000,1500,8000,24000,4500,38000])[j]
 palette=([3,7,12,18,27,38,23,11,4] if final else [2,6,13,21,33,40,17,5])
 pattern=([11,29,5,47,2,19,1,37,13] if final else [8,24,4,40,2,16,1])
 cycle=0;pending=[]
 while len(s.cmd)<n:
  if len(s.cmd)==n-1:s.add(palette[(cycle+2)%len(palette)]);break
  if not pending:
   length=palette[cycle%len(palette)];nominal=pattern[cycle%len(pattern)]
   # Shortened nominal runs, 0/1/2-command excursions, then a return to the same length.
   run=min(nominal,max(2,int(target*.035/max(length,1))))
   if cycle%3==1:run=max(1,run//2)
   excursion=cycle%3
   pending=[length]*run+[palette[(cycle+3)%len(palette)]]*excursion+[length]*max(1,run//3)
   cycle+=1
  # Burst deletions only after a bounded positive run; no permanent background.
  if s.live>target+max(40,int(target*.045)) and len(s.ids)>1:
   s.remove('random' if cycle%2 else 'new');continue
  s.add(pending.pop(0))
 return {'target_live_volume_m':target,'size_cycle':palette,'nominal_run_counts':pattern,'excursion_counts':[0,1,2],'run_cycles':cycle,'eof_truncates_schedule':bool(pending),'reason':'EOF may truncate a run; short excursions and partial cohort removals are ordinary active-PID operations'}

def motif(s,n,j,final):
 motifs=([[3,2,3,5,2],[2,3,4,3,2,5,7],[3,3,2,2,5,4],[2,5,3,2,4,3,7],[4,2,3,5,2,3],[3,2,5,3,7,2,4],[2,3,3,4,5],[3,2,4,7,2,5,3]] if final else [[3,2,3,2],[2,3,5,3,2],[3,3,2,4],[2,4,3,5,2,3],[5,2,3,2],[3,2,4,3,5]])
 motif=motifs[j];cycle=0
 while len(s.cmd)<n:
  # Sustained natural arrival surplus, not an appended fill phase.
  should_delete=len(s.ids)>8 and (len(s.cmd)+(3 if final else 0))%(7 if final else 8)==0
  if should_delete and len(s.cmd)<n-1:
   s.remove('random' if j%2 else 'new')
  else:s.add(motif[cycle%len(motif)]);cycle+=1
 return {'arrival_motif':motif,'deletion_period':7 if final else 8,'reason':'tiny independently generated local repetitions; lengths 2/3 arise from a natural small-size palette, without any public prefix input'}
GENERATORS={'ordinary':ordinary,'series':series,'interruption':interruption,'motif':motif}

def prior_hashes():
 # Whitelist metadata fields. Never read old commands, result fields, or Open15 inputs.
 manifests=[OUT.parent/'pipes_online_reservations_20261022/records.jsonl',OUT.parent/'pipes_cj_online_o0_20261022/records.jsonl',OUT.parent/'pipes_cj_tle15_20261021/corpus/final-o0/records.jsonl',OUT.parent/'pipes_cj_tle15_20261021/fresh-checks/final-o0/records.jsonl']
 tests=set();commands=set();counts={}
 for k,p in enumerate(manifests):
  seen=0
  if not p.exists():raise FileNotFoundError(p)
  for line in p.open():
   r=json.loads(line)
   if k==0 and r.get('type')!='input':continue
   if k==1 and r.get('type') not in ('fresh_input','holdout_input'):continue
   m=r.get('meta',r)
   for row in (r,m):
    if row.get('test_sha256'):tests.add(row['test_sha256'])
    if row.get('command_sha256'):commands.add(row['command_sha256'])
   seen+=1
  counts[str(p)]=seen
 return tests,commands,counts

def validate(commands,n):
 assert len(commands)==n and 1<=n<=200000
 active={};pid=live=peak=0
 for op in commands:
  assert op!=0
  if op>0:
   assert 1<=op<=40
   pid+=1;active[pid]=op;live+=op;peak=max(peak,live)
  else:
   assert -op in active,('invalid deletion',-op)
   live-=active.pop(-op)
 assert live>0 and commands[-1]>0
 rounded=20*((peak+19)//20)
 assert live/rounded>=.85,(live,peak,rounded,live/rounded)
 return {'operation_count':len(commands),'placement_count':pid,'final_occupied_length_m':live,'peak_live_pipe_length_m':peak,'minimum_trench_lower_bound_m':rounded,'kpi_upper_bound_from_live_volume':live/rounded,'final_live_pipe_count':len(active),'last_command_positive':True}

def main():
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'inputs').mkdir(exist_ok=True)
 assert not MANIFEST.exists(),'refuse to overwrite frozen metadata'
 assert not list((OUT/'inputs').iterdir()),'refuse to overwrite existing inputs'
 prior_tests,prior_commands,prior_counts=prior_hashes()
 specs=[]
 for split in SPLITS:
  for family in GENERATORS:
   for j,n in enumerate(NS[family][split]):
    specs.append({'id':f'{split}-{family}-{j+1:02d}','split':split,'stratum':family,'family':family,'seed':SEED_BASE[split]+100*FAMILY_INDEX[family]+j,'n':n,'variant':j})
 protocol={'type':'generation_freeze','generator_file':str(Path(__file__).resolve()),'generator_sha256':sha(Path(__file__).read_bytes()),'specs':specs,'declared_before_solver_evaluation':True,'solver_sources_and_outputs_read':False,'solver_runs':0,'final_evaluation_allowed':False,'prior_metadata_rows':prior_counts,'prior_test_hash_count':len(prior_tests),'prior_command_hash_count':len(prior_commands),'prior_dedup_scope':'exact test_sha256 and metadata command_sha256 if present; prior commands not read; different weight headers can hide command-equivalent prior tests','kpi_upper_bound_note':'F/rounded_peak is an upper bound only, not proof of achievable KPI; no terminal fill phases','schema_required':['id','test_file','test_sha256','command_sha256','operation_count','placement_count','final_occupied_length_m','peak_live_pipe_length_m','minimum_trench_lower_bound_m','kpi_upper_bound_from_live_volume','split','stratum','family','seed']}
 with MANIFEST.open('x') as f:
  f.write(js(protocol)+'\n');f.flush()
  new_tests=set();new_commands=set();summary=[]
  for spec in specs:
   s=Stream(spec['seed']);params=GENERATORS[spec['family']](s,spec['n'],spec['variant'],spec['split']=='final')
   measures=validate(s.cmd,spec['n'])
   command_bytes=('\n'.join(map(str,s.cmd))+'\n').encode();full=b'1\n'+str(len(s.cmd)).encode()+b'\n'+command_bytes
   th,ch=sha(full),sha(command_bytes)
   assert th not in prior_tests and th not in new_tests
   assert ch not in prior_commands and ch not in new_commands
   new_tests.add(th);new_commands.add(ch)
   p=OUT/'inputs'/(spec['id']+'.in');p.write_bytes(full)
   # Reparse generated bytes independently from the in-memory stream.
   lines=p.read_text().splitlines();assert lines[0]=='1' and int(lines[1])==spec['n']
   assert validate(list(map(int,lines[2:])),int(lines[1]))==measures
   row={k:v for k,v in spec.items() if k not in ('n','variant')};row.update(type='input',test_file=str(p),test_sha256=th,command_sha256=ch,**measures,parameters=params)
   f.write(js(row)+'\n');f.flush();summary.append(row)
  completion={'type':'generation_validation','input_count':len(summary),'calibration_count':sum(x['split']=='calibration' for x in summary),'final_count':sum(x['split']=='final' for x in summary),'long_200000_count':sum(x['operation_count']==200000 for x in summary),'minimum_upper_bound':min(x['kpi_upper_bound_from_live_volume'] for x in summary),'unique_full_test_hashes':len(new_tests),'unique_command_hashes':len(new_commands),'all_input_reparse_checks_passed':True,'no_solver_evaluation':True}
  f.write(js(completion)+'\n')
 print(js(completion));print('GENERATOR_SHA256',protocol['generator_sha256']);print('MANIFEST',MANIFEST)


def targeted_specs():
 specs=[]
 for split in ('calibration','final'):
  final=split=='final'
  for j in range(8):
   counts=([181,823,2713,6037,179,829,2741,5987] if final else [173,811,2701,6011,177,797,2683,6053])
   palettes=([[2,4,9,17,26,37],[3,6,11,19,29,39],[2,5,12,20,31,40],[4,8,13,21,30,38],[3,7,14,23,32,40],[2,6,15,22,33,39],[4,9,16,24,34,40],[3,8,17,25,35,39]] if final else [[3,8,14],[2,7,13],[4,9,15,23],[3,10,18,27],[2,6,12,20,29],[4,11,19,28,36],[3,9,17,25],[2,8,16]])
   specs.append({'id':f'{split}-targeted-reserve-{j+1:02d}','split':split,'stratum':'targeted_reserve','family':'equal_series_stride2_deletions','seed':SEED_BASE[split]+5100+j,'base_count':counts[j],'stage_lengths':palettes[j][:-1],'interrupted_length':palettes[j][-1],'partial_count':([2,3,17,65,1,53,127,419] if final else [1,2,3,17,65,89,311,701])[j],'mode':(['eof','length_change','return','inside_delete','eof','return','inside_delete','length_change'] if final else ['eof','length_change','return','inside_delete','eof','return','inside_delete','length_change'])[j],'background_placements':100000,'background_palette':[19,20,21]})
  for j,n in enumerate([43,49,57,63] if final else [46,52,58,64]):
   specs.append({'id':f'{split}-targeted-tiny-{j+1:02d}','split':split,'stratum':'targeted_tiny','family':'tiny_mixed_churn','seed':SEED_BASE[split]+6100+j,'n':n,'palette':([3,2,5,4,3,5,2] if final else [3,2,4,5,2,3]),'max_live_volume_m':60,'mode':j})
 return specs

def generate_targeted(spec):
 s=Stream(spec['seed']);r=s.rng
 if spec['stratum']=='targeted_tiny':
  palette=spec['palette'];n=spec['n'];s.add(3);s.add(2);turn=0
  while len(s.cmd)<n:
   length=palette[(turn+2)%len(palette)];turn+=1
   if len(s.cmd)==n-1:
    length=r.choice([x for x in palette if x<=60-s.live]);s.add(length)
   elif (len(s.cmd)==n-2 and s.live+length>58) or (s.live>=55 and (s.live+length>60 or r.random()<.58)):
    s.remove(['random','old','new','random'][spec['mode']])
   else:s.add(length)
  return s,{'starts':[3,2],'live_volume_ceiling_m':60,'deletions':'mixed active PID; small live-volume churn','independent_of_public_inputs':True}
 # Initial background is permanent and mixed-sized, about 2,000,000 metres.
 # It is declared upfront, not an appended KPI fill. 2 million *pipes* would
 # contradict N<=200000; the large requested background is a volume here.
 for k in range(spec['background_placements']):s.add(spec['background_palette'][k%3])
 stages=[]
 for length in spec['stage_lengths']:
  count=spec['base_count']+r.randint(-max(1,spec['base_count']//40),max(1,spec['base_count']//40))
  start=s.pid+1
  for _ in range(count):s.add(length)
  removed=list(range(start,start+count,2))
  for pid in removed:s.delete(pid)
  stages.append({'length':length,'count':count,'first_pid':start,'deletion_count':len(removed),'deletion_stride':2})
 length=spec['interrupted_length'];partial=spec['partial_count'];start=s.pid+1
 for _ in range(partial):s.add(length)
 mode=spec['mode']
 if mode=='length_change':
  for _ in range(1 if spec['split']=='calibration' else 2):s.add(max(1,length-1))
 elif mode=='return':
  for _ in range(2 if spec['split']=='calibration' else 3):s.add(max(1,length-2))
  for _ in range(3 if spec['split']=='calibration' else 5):s.add(length)
 elif mode=='inside_delete':
  for pid in range(start,start+partial,2):s.delete(pid)
  for _ in range(2 if spec['split']=='calibration' else 3):s.add(length)
 return s,{'background_permanent':True,'background_placements':spec['background_placements'],'background_volume_m':1999999,'long_stages':stages,'partial_series_count':partial,'partial_series_length':length,'interruption_mode':mode,'terminal_fill':False,'reason':'every full stage has >=64 consecutive equal placements and >=8 consecutive deletions of increasing PID with step 2; final changes stage composition and interrupted-series behaviour'}

def extend_targeted():
 assert MANIFEST.exists(),'original corpus must exist'
 existing=[json.loads(line) for line in MANIFEST.open()]
 assert not any(x.get('type')=='extension_validation' for x in existing),'extension already completed'
 all_rows=[x for x in existing if x.get('type')=='input']
 rows=[x for x in all_rows if x.get('extension')!='targeted_reserve_and_tiny'];assert len(rows)==56
 completed=[x for x in all_rows if x.get('extension')=='targeted_reserve_and_tiny']
 before_hashes={x['test_file']:sha(Path(x['test_file']).read_bytes()) for x in rows}
 assert all(before_hashes[x['test_file']]==x['test_sha256'] for x in rows)
 tests={x['test_sha256'] for x in all_rows};commands={x['command_sha256'] for x in all_rows}
 prior_tests,prior_commands,prior_counts=prior_hashes()
 specs=targeted_specs();codehash=sha(Path(__file__).read_bytes())
 freeze={'type':('extension_resume_freeze' if completed else 'extension_freeze'),'extension':'targeted_reserve_and_tiny','generator_file':str(Path(__file__).resolve()),'generator_sha256':codehash,'original_generator_sha256':existing[0]['generator_sha256'],'original_input_count':56,'original_inputs_preserved':True,'specs':specs,'declared_before_solver_evaluation':True,'solver_runs':0,'final_evaluation_allowed':False,'background_note':'100000 mixed 19/20/21m pipes form an initial permanent ~2 million metre background; 2 million pipes would exceed command budget','prior_metadata_rows':prior_counts,'prior_command_hash_count':len(prior_commands)}
 with MANIFEST.open('a') as f:
  if completed:freeze.update(repair_note='tiny penultimate operation reserves room for one ordinary final placement; prior input files remain unchanged',previous_extension_input_count=len(completed))
  f.write(js(freeze)+'\n');f.flush();added=list(completed)
  for spec in specs:
   if any(x['id']==spec['id'] for x in completed):continue
   s,params=generate_targeted(spec);measures=validate(s.cmd,len(s.cmd))
   if spec['stratum']=='targeted_tiny':assert len(s.cmd)<=64
   else:
    assert all(x['count']>=64 and x['deletion_count']>=8 for x in params['long_stages'])
    assert all(abs(x['count']/spec['base_count']-1)<=.05 for x in params['long_stages'])
   cb=('\n'.join(map(str,s.cmd))+'\n').encode();full=b'1\n'+str(len(s.cmd)).encode()+b'\n'+cb;th,ch=sha(full),sha(cb)
   assert th not in tests and th not in prior_tests
   assert ch not in commands and ch not in prior_commands
   tests.add(th);commands.add(ch);p=OUT/'inputs'/(spec['id']+'.in');assert not p.exists();p.write_bytes(full)
   lines=p.read_text().splitlines();assert lines[0]=='1';assert validate(list(map(int,lines[2:])),int(lines[1]))==measures
   row={k:spec[k] for k in ('id','split','stratum','family','seed')};row.update(type='input',extension='targeted_reserve_and_tiny',test_file=str(p),test_sha256=th,command_sha256=ch,parameters=params,**measures)
   f.write(js(row)+'\n');f.flush();added.append(row)
  assert all(sha(Path(p).read_bytes())==h for p,h in before_hashes.items())
  summary={'type':'extension_validation','extension':'targeted_reserve_and_tiny','targeted_calibration_count':8,'targeted_final_count':8,'tiny_calibration_count':4,'tiny_final_count':4,'added_input_count':24,'total_input_count':80,'all_original56_unchanged':True,'all_input_reparse_checks_passed':True,'minimum_extension_upper_bound':min(x['kpi_upper_bound_from_live_volume'] for x in added),'maximum_operation_count':max(x['operation_count'] for x in added),'unique_full_test_hashes':len(tests),'unique_command_hashes':len(commands),'no_solver_evaluation':True}
  f.write(js(summary)+'\n')
 print(js(summary));print('EXTENSION_GENERATOR_SHA256',codehash)
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='extend_targeted':extend_targeted()
 else:main()
