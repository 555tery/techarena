import hashlib, json, math
from collections import Counter, defaultdict
from pathlib import Path
root=Path.cwd(); out=root/'results/pipes/improvement/case15_survivor_rank'
trace=out/'run_exact/runs/15/solver_stderr.txt'
names=('op','gap_id','request','start','end','gap_len','birth_op','current_gap','cohort','cohort_eligible','mode','request_cohort','high_side','pool','eligibility','representative_start','target_score','target_rank','pool_size','baseline_start','baseline_score','selected_start','selected_score','selected_rank','rollout_count','mc_decisions','free_gaps','active_pipes','history_size')
rows=[]
for line in trace.read_text().splitlines():
    if not line.startswith('SVDIAG '): continue
    vals=line.split()[1:]
    if len(vals)!=len(names): raise ValueError(f'bad SVDIAG width {len(vals)}')
    row=dict(zip(names,vals))
    for k in names:
        if k not in ('pool','eligibility'): row[k]=int(row[k])
    rows.append(row)
byop=defaultdict(list); bygap=defaultdict(list)
for r in rows: byop[r['op']].append(r); bygap[r['gap_id']].append(r)
assert (len(rows),len(byop),len(bygap))==(32221,3113,97)
assert all(r['current_gap']==1 and r['cohort_eligible']==1 and r['mode']==0 for r in rows)
assert all(r['rollout_count']==0 and r['mc_decisions']>=32 and r['free_gaps']>64 and r['active_pipes']>4096 for r in rows)
assert all(r['selected_start']==r['baseline_start'] and r['selected_score']==r['baseline_score'] for r in rows)
status=Counter(r['eligibility'] for r in rows)
assert status==Counter({'same_size_shadowed':31719,'evaluated':502}),status
evaluated=[r for r in rows if r['eligibility']=='evaluated']; shadowed=[r for r in rows if r['eligibility']=='same_size_shadowed']
assert all(r['target_rank']>=2 for r in evaluated)
assert all(r['representative_start']>=0 and r['representative_start']<r['start'] for r in shadowed)
assert all(r['target_score']>=r['selected_score'] for r in rows)
# Saved COST trace: op length side cohort mode baseline start/score and selected start.
cost={}
for line in (root/'results/pipes/improvement/generator_audit/cost_runs/runs/15/solver_stderr.txt').read_text().splitlines():
    if line.startswith('COST '):
        f=line.split(); cost[int(f[1])]=tuple(map(int,(f[2],f[3],f[4],f[5],f[6],f[8],f[9])))
checks=Counter()
for op,rs in byop.items():
    c=cost[op]; r=rs[0]
    for name,ok in zip(('request','high_side','cohort','mode','baseline_start','baseline_score','selected_start'),(r['request']==c[0],r['high_side']==c[1],r['request_cohort']==c[2],r['mode']==c[3],r['baseline_start']==c[4],r['baseline_score']==c[5],r['selected_start']==c[6])): checks[name]+=ok
assert all(checks[k]==len(byop) for k in checks),dict(checks)
ranks=Counter('2-3' if r['target_rank']<=3 else '4-10' if r['target_rank']<=10 else '11-25' for r in evaluated)
rank_ops={b:len({r['op'] for r in evaluated if lo<=r['target_rank']<=hi}) for b,lo,hi in [('2-3',2,3),('4-10',4,10),('11-25',11,25)]}
delta=sorted(r['target_score']-r['selected_score'] for r in rows)
def q(p): return delta[min(len(delta)-1,math.ceil(p*len(delta))-1)]
run=json.loads((out/'run_exact/summary.json').read_text()); case=run['records'][0]
final=root/'results/pipes/final/solution.cpp'; judge=out/'run_exact/runs/15/judge_output.txt'; oldjudge=root/'results/pipes/improvement/generator_audit/geometry_runs/runs/15/judge_output.txt'
summary={'target_gap_operation_rows':len(rows),'target_ops':len(byop),'target_gap_episodes':len(bygap),'op_range':[min(byop),max(byop)],'exact_current_gap_matches':len(rows),'cohort_eligible_rows':len(rows),'cohort_mode_rows':dict(Counter(r['mode'] for r in rows)),'scorer_status_rows':dict(status),'shadowed_high_side_rows':{'low_side':sum(not r['high_side'] for r in shadowed),'high_side':sum(bool(r['high_side']) for r in shadowed)},'evaluated_rank_min_max':[min(r['target_rank'] for r in evaluated),max(r['target_rank'] for r in evaluated)],'evaluated_rank_rows':dict(ranks),'evaluated_rank_unique_ops':rank_ops,'target_minus_selected_score':{'min':delta[0],'median':q(.5),'p90':q(.9),'p99':q(.99),'max':delta[-1],'equal_rows':sum(x==0 for x in delta)},'mc_rollout_rows':sum(r['rollout_count']>0 for r in rows),'mc_budget_closed_rows':sum(r['mc_decisions']>=32 for r in rows),'mc_gap_limit_closed_rows':sum(r['free_gaps']>64 for r in rows),'mc_active_limit_closed_rows':sum(r['active_pipes']>4096 for r in rows),'free_gap_count_min_max':[min(r['free_gaps'] for r in rows),max(r['free_gaps'] for r in rows)],'active_pipe_count_min_max':[min(r['active_pipes'] for r in rows),max(r['active_pipes'] for r in rows)],'cost_reconciliation_ops':len(byop),'cost_reconciliation_fields':dict(checks),'final_sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'input_sha256':case['test_sha256'],'judge_sha256':hashlib.sha256(judge.read_bytes()).hexdigest(),'prior_judge_sha256':hashlib.sha256(oldjudge.read_bytes()).hexdigest(),'judge_outputs_identical':judge.read_bytes()==oldjudge.read_bytes(),'diagnostic_cpu_s':case['solver_cpu_total_s'],'diagnostic_peak_rss_mib':case['solver_peak_rss_mb']}
(out/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
report=f'''# Case 15: точная проверка выбора конечных свободных интервалов

## Результат

Исследованы 97 эпизодов gap-ов, которые дожили до EOF и имели физически подходящий запрос после своего `birth_op` и до последней команды: 32,221 пар «gap × операция» на 3,113 операциях (op {min(byop)}–{max(byop)}). Во всех случаях replay подтвердил точный тот же свободный `[start,end)` на момент запроса. Значит, здесь не нужно делать неоднозначные выводы о происхождении после split/merge.

Все 32,221 target были **cohort-eligible**: режим cohort был выключен. Но точный scorer не ранжирует все gap-ы каждого размера. `bestFittingGapFromSet` после одного gap размера `s` переходит через `upper_bound({{s,max}})` к следующему размеру, поэтому он оценивает только gap с самым низким адресом для каждого размера.

| Статус в текущем score loop | Строки gap×op | Уникальные операции |
|---|---:|---:|
| Тот же размер, но target скрыт за lower-address representative | {len(shadowed):,} | {len({r['op'] for r in shadowed}):,} |
| Target реально оценивался | {len(evaluated):,} | {len({r['op'] for r in evaluated}):,} |

Для shadowed-строк scorer-formula даёт ту же стоимость, что представителю того же размера, но target отдельно не попадает в candidate list. Во всех таких строках `highSide=0`, а адрес target выше адреса lower-address representative. Если сравнить эти равные по размеру интервалы тем же tie-break, выиграл бы представитель с меньшим адресом. Поэтому пропуск соседей того же размера не скрывает target, который выиграл бы текущий tie-break; это точный факт об enumeration, а не свидетельство, что альтернативная траектория размещения улучшила бы траншею.

Оставшиеся 502 строки были оценены; их rank от 2 до 22, ни один target не стал победителем. Распределение рангов среди реально оценённых targets:

| Rank | Строки | Уникальные операции с target этого диапазона |
|---|---:|---:|
| 2–3 | {ranks['2-3']:,} | {rank_ops['2-3']:,} |
| 4–10 | {ranks['4-10']:,} | {rank_ops['4-10']:,} |
| 11–25 | {ranks['11-25']:,} | {rank_ops['11-25']:,} |

Разница `target_score − выбранный score`: min {delta[0]:,}, median {q(.5):,}, P90 {q(.9):,}, P99 {q(.99):,}, max {delta[-1]:,}; равный score был у {summary['target_minus_selected_score']['equal_rows']:,} строк. Сохранённый `COST` trace согласовался по всем семи полям на всех 3,113 целевых операциях: request, highSide, cohort, parity mode, baseline start/score и post-rollout selected start. В этих событиях выбранный start совпадал с baseline winner.

## Monte Carlo и предел причинного вывода

Rollout не запускался ни в одной целевой строке. Во всех этих состояниях использованы 32 из 32 разрешённых решений; число свободных gap-ов составляло {summary['free_gap_count_min_max'][0]:,}–{summary['free_gap_count_min_max'][1]:,} при пороге 64, активных труб — {summary['active_pipe_count_min_max'][0]:,}–{summary['active_pipe_count_min_max'][1]:,} при пороге 4,096. Лимит решений достигнут, оба порога состояния превышены.

Итак, точное объяснение baseline выбора: большинство конечных gap-ов не проходят через адресный representative одного размера, а те, что проходят, уступают текущему scorer rank 1; MC уже отключён на этих поздних состояниях. Это объясняет решения baseline, но не доказывает, что выбор конечного gap снизил бы итоговую траншею. Мы не переигрывали альтернативные траектории и не запускали новую policy/penalty.

## Gap age / lineage

Сейчас allocator хранит диапазоны и cohort, но не `birth_op` gap-а и не placement/deletion lineage. Возраст можно сделать online-наблюдаемым, добавив время создания и обновляя его при split/merge. Источник lineage тоже можно вести как метаданные. Здесь они не были протестированы как placement feature: birth/lineage в replay — диагностические сведения, а отбор самих 97 gap-ов использует будущую EOF-выживаемость только для поиска мест для измерения.

## Проверки

Frozen final остался неизменным: SHA-256 `{summary['final_sha256']}`. Инструментированный harness replay прошёл все команды; judge-output SHA `{summary['judge_sha256']}` побайтно совпал с сохранённым geometry trace `{summary['judge_outputs_identical']}`. Диагностическая сборка: CPU {summary['diagnostic_cpu_s']:.3f} s, peak RSS {summary['diagnostic_peak_rss_mib']:.2f} MiB; это не submission замер. Сырые данные содержат только 32,221 target строки. Детальные счётчики и artifact hashes — в `analysis.json` и `manifest.json`.
'''
(out/'REPORT.md').write_text(report)
print(f"exact audit complete: {len(shadowed)} same-size shadowed, {len(evaluated)} evaluated")
