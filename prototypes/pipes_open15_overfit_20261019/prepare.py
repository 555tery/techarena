"""Build a joint public-test lifetime problem, merging identical command prefixes."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'prototypes/pipes_options_v4_20261019'))
import evaluate as guard
guard.ROOT=ROOT
guard.quota()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary_path=REPO/'research-campaigns/20261018T141843+0700-autonomous/proposals/trial_0022/evaluation_0/open15/harness/summary.json'
summary=json.loads(summary_path.read_text());assert summary['ok_count']==summary['case_count']==15
records={int(r['case']):r for r in summary['records']}
trie={};positive_nodes={};blocks=[];cases=[];offset=0
for number in range(1,16):
 p=REPO/'data/pipes/open'/f'{number}.in';x=p.read_text().split();weight=float(x[0]);n=int(x[1]);cmd=list(map(int,x[2:2+n]))
 assert sha(p)==records[number]['test_sha256']
 replies=Path(records[number]['judge_output_file']).read_text().splitlines();assert len(replies)==n
 ids=[None];birth={};node=0;events=[];occupied=peak=0
 for t,(c,line) in enumerate(zip(cmd,replies)):
  key=(node,c)
  if key not in trie:trie[key]=len(trie)+1
  node=trie[key]
  if c>0:
   coord=int(line.split()[1])
   if node not in positive_nodes:
    positive_nodes[node]=len(blocks);blocks.append({'length':c,'seed':coord,'first':t,'intervals':[]})
   bid=positive_nodes[node];assert blocks[bid]['seed']==coord and blocks[bid]['length']==c
   ids.append(bid);birth[len(ids)-1]=t;events.append(bid);occupied+=c;peak=max(peak,occupied)
  else:
   bid=ids[-c];start=birth.pop(-c);blocks[bid]['intervals'].append([offset+start,offset+t,number-1]);events.append(-1);occupied-=blocks[bid]['length']
 for pid,start in birth.items():blocks[ids[pid]]['intervals'].append([offset+start,offset+n,number-1])
 cases.append({'case':number,'weight':weight,'F':occupied,'peak_volume':peak,'lower_T':20*((peak+19)//20),'commands':cmd,'block_ids':events,'input_sha256':sha(p)})
 offset+=n
joint={'cases':cases,'blocks':blocks,'time_count':offset,'baseline_summary':str(summary_path),'baseline_summary_sha256':sha(summary_path)}
guard.save(ROOT/'joint.json',joint)
with (ROOT/'problem.txt').open('w') as f:
 print(len(blocks),offset,15,file=f)
 for c in cases:print(c['weight'],c['F'],file=f)
 for b in blocks:
  print(b['length'],b['seed'],b['first'],len(b['intervals']),file=f)
  for span in b['intervals']:print(*span,file=f)
guard.save(ROOT/'protocol.json',{
 'purpose':'Deliberate complete Open15 overfit, explicitly authorized by user. No generalization claim.',
 'uses_public_future_at_build_time':True,'uses_stored_placement_tables':True,
 'runtime':'one observed command then one flushed reply; exact prefix matching; BF fallback after mismatch',
 'prefix_consistency':'identical public input prefixes share the same placement variables',
 'search':'128 bounded offline ordering/compaction trials, select solely by weighted Open15 F/T',
 'offline_seconds_cap':900,'native_workers':2,'native_case_cap':60,
 'min_remaining_quota':65,'conservative_work_gate':67,
 'platform_submission':False,'incumbent_overwritten':False,'old_campaign_restarted':False,
 'rules_scope':'Local statement.pdf inspected: interactive contract; no explicit hardcode clause found in that PDF. Broader contest policy not established.',
 'statement_sha256':sha(REPO/'data/pipes/statement.pdf'),
 'baseline_score':summary['weighted_score_sum'],
 'optimistic_volume_ceiling':sum(c['weight']*c['F']/c['lower_T'] for c in cases),
 'blocks':len(blocks),'observations':offset})
print(json.dumps({'blocks':len(blocks),'observations':offset,'baseline_score':summary['weighted_score_sum']}))
