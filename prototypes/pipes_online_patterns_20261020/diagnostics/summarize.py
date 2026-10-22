from pathlib import Path
import json,csv,hashlib,collections
HERE=Path(__file__).resolve().parent;OLD=HERE.parents[1]/'pipes_online_core_20261020';report=json.load(open(HERE/'REPORT.json'));compact=[];counts=collections.Counter()
for c in report['cases']:
 e=c['events']['first_action'];step=e['current']['step'];s=c['state_snapshots'][str(step)]['current'][-1];cs={x[0]:x[1:]for x in s['candidates']};legacy,chosen=cs[s['legacy']],cs[s['selected']];margin=legacy[1]-chosen[1];requests=sum(s['request_freq']);tie=abs(margin)<=1e-9;sparse=requests<32
 label='sparse demand'if sparse else'DP value tie'if tie else'strict DP gap rank'
 counts[label]+=1;counts['first_MC_ran']+=c['annotations']['first_MC_ran'];counts['first_parity']+=bool(s['parity']);counts['side_changes']+=((e['baseline']['x']!=s['legacy'])!=(e['current']['x']!=s['selected']));counts['sparse_and_tie']+=sparse and tie
 counts['unsupported_current_length']+=s['request_freq'][e['current']['command']-1]==0
 row={'case':c['id'],'class':label,'extra_T':c['current_T']-c['baseline_T'],'first_difference':step,'first_extra_dig':c['events']['first_extra_dig']['current']['step'],'first_T_deficit':c['events']['first_T_deficit']['current']['step'],'persistent_T_deficit':c['events']['persistent_T_deficit']['current']['step'],'L':e['current']['command'],'gap_legacy':legacy[0],'gap_DP':chosen[0],'loss_margin':margin,'placements_window':requests,'model_age':s['model_age'],'mc_count':s['mc'],'future64_TV_hindsight':c['annotations']['future64_TV_hindsight']}
 for name in ['no_dp','mc_off_dp','fresh','legacy_tie','force_first_baseline_action_only']:row[name+'_delta_T']=c['ablations'][name]['final_T']-c['current_T']
 compact.append(row)
 c['annotations'].update(primary_origin_class=label,first_loss_margin=margin,first_tie=tie,first_sparse_below32=sparse,first_legacy_gap=legacy[0],first_DP_gap=chosen[0])
summary={'counts':dict(counts),'ablations':{},'source_hashes':{name:hashlib.sha256(path.read_bytes()).hexdigest()for name,path in [('baseline',OLD/'candidates/baseline/solution.cpp'),('current',OLD/'release/solution.cpp')]},'scope':'23 losses selected using prior outcomes; repair evidence is retrospective and does not estimate full-population gain or hidden generalization.'}
for name in ['no_dp','mc_off_dp','fresh','legacy_tie','force_first_baseline_action_only']:
 a=[c['ablations'][name]['final_T']-c['current_T']for c in report['cases']];summary['ablations'][name]={'better_T':sum(x<0 for x in a),'tie_T':sum(x==0 for x in a),'worse_T':sum(x>0 for x in a),'sum_delta_T':sum(a)}
(HERE/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n');(HERE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with(HERE/'all23.csv').open('w')as f:
 w=csv.DictWriter(f,fieldnames=list(compact[0]));w.writeheader();w.writerows(compact)
lines=['| Case | Class | extra T | first action | first extra dig | first T deficit | persistent deficit | request count | model age |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
for c in compact:lines.append('|'+ '|'.join(str(c[k])for k in ['case','class','extra_T','first_difference','first_extra_dig','first_T_deficit','persistent_T_deficit','placements_window','model_age'])+'|')
(HERE/'table.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(summary,indent=2))
