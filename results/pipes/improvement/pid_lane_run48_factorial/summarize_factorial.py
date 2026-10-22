#!/usr/bin/env python3
"""Summarize the fixed four-cell Pipes factorial from official-harness outputs."""
import csv, hashlib, json, platform, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LABELS=['c4_run46','cohort_run48','pid_run46','pid_run48']
DATASETS={
 'open15':ROOT/'runs/open15',
 'holdout-v2':ROOT/'runs/holdout-v2',
 'prior-fresh8':ROOT/'runs/fresh8',
 'new-seed-six':ROOT/'runs/new_seed_streams',
}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
per_case=[]; ds_meta={}
for dataset,folder in DATASETS.items():
 comp_path=folder/'comparison.json'; comp=json.loads(comp_path.read_text())
 runs={}; all_recs=[]
 for label in LABELS:
  path=folder/label/'summary.json'; d=json.loads(path.read_text()); runs[label]=d
  recs=[]
  for r in d['records']:
   out=Path(r['judge_output_file'])
   rec={
    'dataset':dataset,'case':r['case'],'variant':label,'status':r['status'],
    'weighted_score':r['weighted_score'],'kpi':r['kpi'],'trench_m':r['trench_length_m'],
    'solver_cpu_s':r['solver_cpu_total_s'],'solver_rss_mib':r['solver_peak_rss_mb'],
    'input_sha256':r['test_sha256'],'judge_output_sha256':sha(out),
   }
   per_case.append(rec); recs.append(rec); all_recs.append(rec)
  row=next(x for x in comp['solvers'] if x['label']==label)
  ds_meta.setdefault(dataset,{})[label]={
   'ok_count':d['ok_count'],'case_count':d['case_count'],'weight_sum':d['weight_sum'],
   'weighted_score_sum':d['weighted_score_sum'],
   'delta_vs_c4':d['weighted_score_sum']-runs['c4_run46']['weighted_score_sum'] if label!='c4_run46' else 0.0,
   'max_solver_cpu_s':row['max_solver_cpu_s'],'max_solver_rss_mib':row['max_solver_peak_rss_mb'],
   'matching_output_count_vs_c4':None,'summary_sha256':sha(path),'binary_sha256':row['binary_sha256'],
  }
 base={r['case']:r for r in all_recs if r['variant']=='c4_run46'}
 for label in LABELS:
  drec=ds_meta[dataset][label]
  candidate={r['case']:r for r in all_recs if r['variant']==label}
  drec['matching_output_count_vs_c4']=sum(candidate[k]['judge_output_sha256']==base[k]['judge_output_sha256'] for k in base)

with (ROOT/'per_case.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=list(per_case[0]));w.writeheader();w.writerows(per_case)
manifest=json.loads((ROOT/'manifest.json').read_text())
manifest['environment']={
 'platform':platform.platform(),
 'python':platform.python_version(),
 'compiler_version':subprocess.run(['clang++','--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0],
 'harness_sha256':sha(Path('tools/pipes_harness.py')),
 'comparison_runner_sha256':sha(Path('tools/compare_pipes_binaries.py')),
 'interactor_sha256':sha(Path('tools/interactor')),
}
manifest['datasets']=ds_meta
# Pairwise exact transcript agreement, not only score agreement.
manifest['pairwise_output_match_counts']={}
for dataset in DATASETS:
 rows=[r for r in per_case if r['dataset']==dataset]
 by={label:{r['case']:r for r in rows if r['variant']==label} for label in LABELS}
 pairs={}
 for i,a in enumerate(LABELS):
  for b in LABELS[i+1:]:
   common=sorted(set(by[a]) & set(by[b]))
   pairs[f'{a}__{b}']={
    'identical_judge_outputs':sum(by[a][c]['judge_output_sha256']==by[b][c]['judge_output_sha256'] for c in common),
    'case_count':len(common),
    'identical_trench_lengths':sum(by[a][c]['trench_m']==by[b][c]['trench_m'] for c in common),
    'identical_weighted_scores':sum(by[a][c]['weighted_score']==by[b][c]['weighted_score'] for c in common),
   }
 manifest['pairwise_output_match_counts'][dataset]=pairs
manifest['test_input_hashes']={}
for dataset,folder in DATASETS.items():
 comp=json.loads((folder/'comparison.json').read_text())
 manifest['test_input_hashes'][dataset]=comp['tests_sha256']
 manifest.setdefault('comparison_files_sha256',{})[dataset]={
  'comparison_json':sha(folder/'comparison.json'),
  'comparison_csv':sha(folder/'comparison.csv'),
  'per_case_comparison_csv':sha(folder/'per-case-comparison.csv'),
 }
manifest['per_case_csv_sha256']=sha(ROOT/'per_case.csv')
manifest['variant_artifacts']={
 label:{
  'source_path':f'sources/{label}.cpp',
  'source_sha256':sha(ROOT/'sources'/f'{label}.cpp'),
  'binary_path':f'binaries/{label}',
  'binary_sha256':sha(ROOT/'binaries'/label),
 } for label in LABELS
}
manifest['generation_artifacts']={
 'previous_fresh8_manifest_sha256':sha(Path('results/pipes/improvement/run48_synthetic_independent/input_manifest.json')),
 'new_seed_synthetic_manifest_sha256':sha(ROOT/'new_synthetic_manifest.json'),
 'new_seed_generator_sha256':sha(ROOT/'generate_new_streams.py'),
}
manifest['factorial_effects_open15']={
 'size_cohort_threshold_46_to_48':ds_meta['open15']['cohort_run48']['weighted_score_sum']-ds_meta['open15']['c4_run46']['weighted_score_sum'],
 'pid_lane_threshold_46_to_48':ds_meta['open15']['pid_run48']['weighted_score_sum']-ds_meta['open15']['pid_run46']['weighted_score_sum'],
 'pid_lane_vs_size_cohort_at_46':ds_meta['open15']['pid_run46']['weighted_score_sum']-ds_meta['open15']['c4_run46']['weighted_score_sum'],
 'pid_lane_vs_size_cohort_at_48':ds_meta['open15']['pid_run48']['weighted_score_sum']-ds_meta['open15']['cohort_run48']['weighted_score_sum'],
 'difference_in_differences':(ds_meta['open15']['pid_run48']['weighted_score_sum']-ds_meta['open15']['pid_run46']['weighted_score_sum'])-(ds_meta['open15']['cohort_run48']['weighted_score_sum']-ds_meta['open15']['c4_run46']['weighted_score_sum']),
 'interpretation':'The factors interact; PID lane does not add to threshold 48 on Open15.'
}
# Archive-source preprobe exact reproduction at the case/output level.
oldroot=Path('results/pipes/improvement/case9_next/preliminary_pid_lane_excluded')
old=json.loads((oldroot/'open15/pid-lane-preprobe/summary.json').read_text())
new=runs=json.loads((ROOT/'runs/open15/pid_run46/summary.json').read_text())
old_equal=True
for a,b in zip(old['records'],new['records']):
 pa=oldroot/'open15/pid-lane-preprobe/runs'/a['case']/'judge_output.txt'
 pb=Path(b['judge_output_file'])
 old_equal &= sha(pa)==sha(pb)
manifest['archived_preprobe_reproduction']={
 'source_sha256':sha(oldroot/'source/proactive_pid_lanes_preprobe.cpp'),
 'archived_binary_sha256':sha(oldroot/'bin/proactive_pid_lanes_preprobe'),
 'isolated_rebuild_binary_sha256':sha(ROOT/'binaries/pid_run46'),
 'open15_score_archived':old['weighted_score_sum'],
 'open15_score_reproduced':new['weighted_score_sum'],
 'all_15_judge_outputs_byte_identical':old_equal,
 'note':'The archived binary hash differs from this fresh build; source SHA and every case output match exactly.'
}
manifest['protected_after_run']={
 'frozen_final_sha256':sha(Path('results/pipes/final/solution.cpp')),
 'canonical_sha256':sha(Path('src/pipes.cpp')),
 'frozen_final_unchanged':sha(Path('results/pipes/final/solution.cpp'))=='c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991',
 'canonical_unchanged':sha(Path('src/pipes.cpp'))=='526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8',
}
manifest['scope_notes']={
 'open15':'Official open inputs were used in prior development and threshold selection; not independent evidence.',
 'holdout_v2':'Previously reused during development/tuning; neutral result here is a regression check, not independent holdout evidence.',
 'prior_fresh8':'These eight streams were generated earlier and used for frozen-final vs run-48 comparison; this run extends the comparison to the PID variants, not a new unseen set.',
 'new_seed_six':'Six streams generated with new seed/configuration and verified hash-unique against 108 distinct saved .in hashes under data/pipes and results/pipes. This is exploratory synthetic evidence, not contest generalization.',
 'platform':'No website access or submissions were made.',
}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
for dataset in DATASETS:
 print('\n'+dataset)
 base=ds_meta[dataset]['c4_run46']['weighted_score_sum']
 for label in LABELS:
  x=ds_meta[dataset][label]
  print(label, f"{x['weighted_score_sum']:.12f}",f"delta={x['delta_vs_c4']:+.12f}",f"ok={x['ok_count']}/{x['case_count']}",f"outmatch={x['matching_output_count_vs_c4']}/{x['case_count']}",f"cpu_max={x['max_solver_cpu_s']:.3f}s",f"rss_max={x['max_solver_rss_mib']:.3f}MiB")
print('\narchived preprobe outputs identical:',old_equal)
print('per_case rows:',len(per_case))
