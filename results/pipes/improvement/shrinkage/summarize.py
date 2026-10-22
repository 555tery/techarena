from pathlib import Path
import csv, hashlib, json, math
ROOT=Path('/Users/555tery/techarena')
OUT=ROOT/'results/pipes/improvement/shrinkage'
NAMES=['policy4','recent_unfit_s50','s50_shrink_tau32','s50_shrink_tau128','s50_warmup32','s50_window64','s50_decay_hl32','s50_decay_hl64']
ADAPTIVE=NAMES[2:]

def summary(set_name,name):
    return json.loads((OUT/'reports'/set_name/name/'summary.json').read_text())
open_s={n:summary('open',n) for n in NAMES}
dev_s={n:summary('development',n) for n in NAMES}
build_data=json.loads((OUT/'builds.json').read_text())
builds={x['name']:x for x in build_data['builds']}
p4_open=28.375837599373007
p4_dev=1.870543569789272
rows=[]
for n in NAMES:
    o,d=open_s[n],dev_s[n]
    ro=o['weighted_score_sum']/p4_open
    rd=d['weighted_score_sum']/p4_dev
    b=builds[n]
    rows.append({
      'name':n,'kind':'control' if n in ('policy4','recent_unfit_s50') else 'adaptive-candidate',
      'open_score':o['weighted_score_sum'],'open_weight':o['weight_sum'],'open_valid':f"{o['ok_count']}/{o['case_count']}",
      'development_score':d['weighted_score_sum'],'development_weight':d['weight_sum'],'development_valid':f"{d['ok_count']}/{d['case_count']}",
      'R_open_vs_P4':ro,'R_development_vs_P4':rd,'R_robust_min':min(ro,rd),'geometric_mean':math.sqrt(ro*rd),
      'open_delta_vs_P4':o['weighted_score_sum']-p4_open,'development_delta_vs_P4':d['weighted_score_sum']-p4_dev,
      'open_delta_vs_S50':o['weighted_score_sum']-open_s['recent_unfit_s50']['weighted_score_sum'],
      'development_delta_vs_S50':d['weighted_score_sum']-dev_s['recent_unfit_s50']['weighted_score_sum'],
      'max_solver_cpu_s':max(float(x['solver_cpu_total_s'] or 0) for x in o['records']+d['records']),
      'max_solver_rss_mb':max(float(x['solver_peak_rss_mb'] or 0) for x in o['records']+d['records']),
      'source_sha256':b['source_sha256'],'binary_sha256':b['binary_sha256'],
      'open_report':str((OUT/'reports/open'/n/'summary.json')),
      'development_report':str((OUT/'reports/development'/n/'summary.json')),
    })
rows.sort(key=lambda x:(-x['R_robust_min'],-x['geometric_mean'],-x['open_score']))
with (OUT/'comparison.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]))
    w.writeheader();w.writerows(rows)
(OUT/'comparison.json').write_text(json.dumps({'selection_rule':json.loads((OUT/'manifest.json').read_text())['selection_rule'],'comparisons':rows},indent=2)+'\n')
for set_name,summaries in [('open',open_s),('development',dev_s)]:
    baseline=summaries['policy4']['records']
    by_name={name:{r['case']:r for r in s['records']} for name,s in summaries.items()}
    out_rows=[]
    for b in baseline:
        case=b['case']
        for n in NAMES:
            r=by_name[n][case]
            p4=by_name['policy4'][case]
            s50=by_name['recent_unfit_s50'][case]
            out_rows.append({
             'case':case,'strategy':n,'weight':r['official_weight'],'status':r['status'],
             'kpi':r['kpi'],'weighted_score':r['weighted_score'],'trench_length_m':r['trench_length_m'],
             'lower_bound_m':r['minimum_trench_lower_bound_m'],
             'weighted_delta_vs_P4':r['weighted_score']-p4['weighted_score'],
             'weighted_delta_vs_S50':r['weighted_score']-s50['weighted_score'],
             'cpu_s':r['solver_cpu_total_s'],'rss_mb':r['solver_peak_rss_mb'],
            })
    with (OUT/f'per_case_{set_name}.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out_rows[0]));w.writeheader();w.writerows(out_rows)
# Freeze the candidate selected by the preregistered robust criterion, while recording that P4 remains better on both metrics.
winner=max((r for r in rows if r['name'] in ADAPTIVE),key=lambda r:(r['R_robust_min'],r['geometric_mean'],r['open_score']))
manifest=json.loads((OUT/'manifest.json').read_text())
win_spec=next(c for c in manifest['candidates'] if c['name']==winner['name'])
freeze={
 'selected_at': '2026-10-16',
 'rule': manifest['selection_rule'],
 'winner_among_adaptive_candidates': winner['name'],
 'frozen_source': win_spec['source'],
 'source_sha256': winner['source_sha256'],
 'binary_sha256': winner['binary_sha256'],
 'compile_command': builds[winner['name']]['command'],
 'open_score':winner['open_score'],'open_weight':winner['open_weight'],'R_open_vs_P4':winner['R_open_vs_P4'],
 'development_score':winner['development_score'],'development_weight':winner['development_weight'],'R_development_vs_P4':winner['R_development_vs_P4'],
 'R_robust_min':winner['R_robust_min'],'geometric_mean':winner['geometric_mean'],
 'P4_open_score':p4_open,'P4_development_score':p4_dev,
 'adaptive_beats_P4_on_both_sets':winner['R_robust_min']>1.0,
 'frozen_set_used_for_selection':False,
}
(OUT/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
# Human-readable report with compact leaderboard and case contributions.
lines=['# Сравнение адаптивных эвристик Pipes','',
'Все варианты собраны отдельно в `results/pipes/improvement/shrinkage/`; канонический исходник не менялся. Каждый бинарник проверен официальным интерактором на 15 открытых тестах и четырёх development synthetic-потоках. Ни один frozen-набор не использовался.','',
'## Результат по заранее заданному критерию','',
'Критерий: максимизировать худшее из относительных оценок к P4 на открытом наборе и development-наборе: `min(open/P4_open, dev/P4_dev)`. При равенстве применяются геометрическое среднее и открытая оценка. Все кандидаты valid на всех 19 случаях.','',
'| Вариант | Open / 32.1 | Dev / 4 | Отн. open | Отн. dev | Min |',
'|---|---:|---:|---:|---:|---:|']
for r in rows:
    lines.append(f"| {r['name']} | {r['open_score']:.9f} | {r['development_score']:.9f} | {r['R_open_vs_P4']:.6f} | {r['R_development_vs_P4']:.6f} | {r['R_robust_min']:.6f} |")
lines += ['',f"Лучший адаптивный по этому правилу — **{winner['name']}**. У него `R_robust={winner['R_robust_min']:.9f}`: это ближе всех адаптивных вариантов к P4 одновременно на обоих наборах, но меньше 1. Следовательно, ни один исследованный adaptive-вариант не улучшил P4 на обоих наборах; P4 остаётся лучшим robust-контролем.",'',
'## Точные разницы','',
'| Сравнение | Open | Development |',
'|---|---:|---:|',
]
for n in ['recent_unfit_s50','s50_shrink_tau32','s50_shrink_tau128','s50_warmup32','s50_window64','s50_decay_hl32','s50_decay_hl64']:
    r=next(x for x in rows if x['name']==n)
    lines.append(f"| {n} − P4 | {r['open_delta_vs_P4']:+.9f} | {r['development_delta_vs_P4']:+.9f} |")
lines += ['',
'## Покейсовая картина выбранного варианта','',
'`per_case_open.csv` и `per_case_development.csv` содержат KPI, фактическую длину траншеи, вес и взвешенную дельту каждого варианта к P4 и S50. У выбранного `s50_shrink_tau128` основные открытые эффекты: тест 15 (вес 10) даёт −0.01158575 к P4, тест 12 (вес 4) +0.00765405, тест 13 (вес 4) −0.02330778; остальные изменения малы или нулевые. На development он совпадает с P4 на high-churn, long-heavy и short-heavy; проигрывает −0.00430273 на uniform. В сумме это −0.00430273 к P4 на dev. S50 выигрывает на тесте 15 +0.06532043, но проигрывает P4 на dev суммарно −0.01751817; shrinkage снимает большую часть synthetic-просадки ценой отказа от части выгоды на тесте 15.','',
'Это ограниченное свидетельство только для 15 опубликованных и 4 development случаев. Оно не даёт оснований считать shrinkage лучше на закрытом распределении.','',
'## Воспроизводимость','',
'- Полные официальные отчёты и логи: `reports/open/<variant>/` и `reports/development/<variant>/`.','- Хеши исходников, тестов, параметры и веса: `manifest.json`.','- Команды компиляции, версия компилятора и бинарные SHA-256: `builds.json`.','- Выбранные исходник, бинарник и числовые метрики: `freeze.json`.','- Сводная таблица: `comparison.csv`; все случаи: `per_case_open.csv`, `per_case_development.csv`.','']
(OUT/'COMPARISON.md').write_text('\n'.join(lines))
print('winner',winner['name'],'R_robust',winner['R_robust_min'])
print('P4 source sha',builds['policy4']['source_sha256'],'S50 source sha',builds['recent_unfit_s50']['source_sha256'])
print('wrote comparison, per-case CSVs, freeze and report')
