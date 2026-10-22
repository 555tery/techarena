"""Summarize hash-pinned paired rollouts; never run or select a solver here."""
import csv
import hashlib
import html
import json
import random
from fractions import Fraction
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def records(mode,group,candidate,names=('baseline','candidate','bestfit')):
    rows={}
    for name in names:
        directory=candidate if name=='candidate' else name
        for f in sorted((HERE/'measurements'/mode/group/directory).glob('*/record.json')):
            r=read(f);assert r['status']=='ok',f
            if name=='candidate':assert r['binary_sha256']==sha(HERE/candidate/'solver'),f
            rows.setdefault(r['id'],{})[name]=r
    return rows
def stats(rows):
    deltas=[r['candidate']['kpi']-r['baseline']['kpi'] for r in rows.values()]
    rng=random.Random(20261019);n=len(deltas)
    boot=sorted(sum(rng.choices(deltas,k=n))/n for _ in range(20000))
    return {'count':n,'wins_ties_losses':[sum(x>1e-12 for x in deltas),sum(abs(x)<=1e-12 for x in deltas),sum(x< -1e-12 for x in deltas)],
      'mean_KPI_delta':sum(deltas)/n,'worst_KPI_delta':min(deltas),'best_KPI_delta':max(deltas),
      'paired_case_bootstrap_95':[boot[500],boot[19499]],'bootstrap_note':'descriptive case bootstrap; synthetic family sampling is not a hidden-test distribution'}
def table(rows,meta):
    body=[]
    for ident,z in sorted(rows.items()):
        a,b=z['baseline'],z['candidate'];d=b['kpi']-a['kpi'];bf=z.get('bestfit',{})
        cls='gain' if d>1e-12 else 'loss' if d< -1e-12 else ''
        body.append(f'<tr class="{cls}"><td>{ident}</td><td>{html.escape(meta.get(ident,{}).get("family",a["case"]))}</td><td>{a["kpi"]:.6f}</td><td>{b["kpi"]:.6f}</td><td>{bf.get("kpi",0):.6f}</td><td>{d:+.6f}</td><td>{b["solver_cpu_total_s"]:.3f}</td><td>{b["solver_peak_rss_mb"]:.1f}</td></tr>')
    return '<div class="scroll"><table><thead><tr><th>Тест</th><th>Семейство</th><th>Прежний код</th><th>Новый код</th><th>Best-Fit</th><th>Δ KPI</th><th>CPU, с</th><th>MiB</th></tr></thead><tbody>'+''.join(body)+'</tbody></table></div>'
def main():
    freeze=read(HERE/'freeze-causal.json');candidate='causal-final'
    assert sha(HERE/candidate/'solution.cpp')==freeze['source_sha256']
    assert sha(HERE/candidate/'solver')==freeze['binary_sha256']
    old={**records('official','sealed-final','final'),**records('official','sealed-final-extra','final')}
    fresh=records('official','confirmation',candidate);assert len(old)==len(fresh)==24
    assert all(set(z)>={'baseline','candidate','bestfit'} for z in fresh.values())
    assert sha(HERE/'evaluation/confirmation/manifest.json')==freeze['confirmation_manifest_sha256']
    open15=records('official','open15',candidate,names=('candidate',));assert len(open15)==15
    opened=[z['candidate'] for z in open15.values()]
    exact=sum((Fraction(str(z['weight']))*Fraction(z['final_occupied_length_m'],z['trench_length_m']) for z in opened),Fraction())
    assert str(exact)=='8753218892157372683/284588353335535200'
    known=records('screen','regression',candidate,names=('baseline','candidate'));assert len(known)==81
    calibration=records('screen','calibration','causal-validated');assert len(calibration)==26
    finalstats=stats(fresh)
    official=[r for z in fresh.values() for r in [z['candidate']]]+opened
    extra=[]
    for p in (HERE/'resource-stress').glob('causal-*/record.json'):
        r=read(p);assert r['binary_sha256']==freeze['binary_sha256'];extra.append(r)
    for p in (HERE/'measurements/official/calibration'/candidate).glob('*/record.json'):
        r=read(p);assert r['binary_sha256']==freeze['binary_sha256'];extra.append(r)
    official+=extra
    resource_ok=all(r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256 for r in official)
    quality_ok=finalstats['mean_KPI_delta']>0 and finalstats['wins_ties_losses'][0]>=finalstats['wins_ties_losses'][2] and finalstats['worst_KPI_delta']>=-.05
    gate=resource_ok and quality_ok
    meta={r['id']:r for r in read(HERE/'evaluation/confirmation/manifest.json')['tests']}
    flat=[]
    for ident,z in sorted(fresh.items()):
        a,b=z['baseline'],z['candidate'];flat.append({'id':ident,'family':meta[ident]['family'],'file':b['source_path'],'test_sha256':b['test_sha256'],
          'baseline_KPI':a['kpi'],'candidate_KPI':b['kpi'],'bestfit_KPI':z['bestfit']['kpi'],'delta_KPI':b['kpi']-a['kpi'],
          'baseline_T':a['trench_length_m'],'candidate_T':b['trench_length_m'],'F':b['final_occupied_length_m'],'CPU_s':b['solver_cpu_total_s'],'RSS_MiB':b['solver_peak_rss_mb']})
    report={'selected':candidate if gate else 'previous-round3-candidate-physical','gate_passed':gate,'quality_gate':quality_ok,'resource_gate':resource_ok,
       'build':freeze,'Open15_score':float(exact),'Open15_exact_score':str(exact),'confirmation':finalstats,
       'first_failed_pilot':{**stats(old),'max_CPU_s':max(z['candidate']['solver_cpu_total_s'] for z in old.values()),'status':'no-go; negative average and F05 CPU overrun'},
       'calibration_pre_cap8_resource_fix':stats(calibration),'known_regression':stats(known),
       'maximum_official_CPU_s':max(r['solver_cpu_total_s'] for r in official),'maximum_official_RSS_MiB':max(r['solver_peak_rss_mb'] for r in official),
       'official_candidate_checks':len(official),'confirmation_tests':flat,'platform_actions':0,
       'limitations':['Finite fresh seeds of known synthetic mechanisms; not the actual hidden distribution.',
         'Unchanged public prefixes still retain irreversibly excavated trench; Open11-p2 KPI1/12 remains.',
         'Delayed probes check only128actualcommands with BF continuation; windows overlap and ties are not independent confirmations.',
         '224MiB is not a fixed allocation: arena80 MiB, memo128 MiB, up to8physical snapshots; resources are released at limits.',
         'CPU envelope estimates future ordinary processing; measured local tests do not prove a universal hardware bound.']}
    (HERE/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    with (HERE/'metrics.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=flat[0]);writer.writeheader();writer.writerows(flat)
    selected={'status':'local finite-sample candidate' if gate else 'no-go; baseline retained','candidate':candidate,'source_sha256':freeze['source_sha256'],
       'binary_sha256':freeze['binary_sha256'],'gate_passed':gate,'canonical_source_changed':False,'submitted':False}
    (HERE/'selected-candidate.json').write_text(json.dumps(selected,indent=2)+'\n')
    w,t,l=finalstats['wins_ties_losses'];ci=finalstats['paired_case_bootstrap_95']
    verdict='Небольшая прибавка на новых тестах' if gate else 'Улучшение не подтверждено: прежняя версия сохранена'
    doc=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pipes: память и проверка прогнозов</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;background:#f3f5f8;color:#142238;margin:0}}main{{max-width:1200px;margin:40px auto;padding:0 24px}}h1{{font-size:34px;line-height:1.15}}h2{{margin-top:40px;font-size:24px}}p{{max-width:950px}}.card{{background:white;border-radius:16px;padding:24px;margin:20px 0;box-shadow:0 3px 18px #15223b09}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}}.metric b{{display:block;font-size:27px}}small,.muted{{color:#59667b}}table{{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}}td,th{{padding:10px;border-bottom:1px solid #e2e7ef;text-align:right}}td:nth-child(2),th:nth-child(2){{text-align:left}}.gain td:nth-child(6){{color:#087b51}}.loss td:nth-child(6){{color:#bd3542}}.scroll{{overflow:auto}}code{{font-size:12px;overflow-wrap:anywhere}}a{{color:#195cb4}}@media(max-width:750px){{.metrics{{grid-template-columns:1fr 1fr}}h1{{font-size:28px}}}}</style>
<main><p class="muted">Pipes · 19–20 октября 2026 · локальная проверка · без отправки на платформу</p><h1>{verdict}</h1>
<p>Публичные планы Open15 сохранены. После расхождения новый поиск сравнивает размещения из фактической раскладки. Доверие к рекомендациям обновляется по их последствиям на уже пришедших 128 командах.</p>
<div class="card metrics"><div class="metric"><b>{w} / {t} / {l}</b><small>лучше / равно / хуже на новых 24</small></div><div class="metric"><b>{finalstats['mean_KPI_delta']:+.6f}</b><small>средняя Δ KPI</small></div><div class="metric"><b>{report['maximum_official_CPU_s']:.2f} / 5 с</b><small>максимум CPU проверенной сборки</small></div><div class="metric"><b>{report['maximum_official_RSS_MiB']:.1f} / 256</b><small>пик памяти, MiB</small></div></div>
<div class="card"><b>Open15: {float(exact):.11f}</b><p>Все 15 тестов достигли прежней нижней границы по длине траншеи. Проверок точного бинарника через официальный interactor: {len(official)}. Новая выборка была сгенерирована до фиксации второй гипотезы и оценивалась после freeze.</p><p>Разброс среднего эффекта: [{ci[0]:+.6f}; {ci[1]:+.6f}] — описательный 95% bootstrap по 24 входам. Интервал включает ноль: статистически убедительного общего выигрыша пока нет. Он также не задаёт распределение настоящих закрытых тестов.</p></div>
<h2>Что использует память</h2><p>128 MiB — кэш повторных расчётов; до 80 MiB — ветвящиеся деревья свободных интервалов; до 8 снимков фактической раскладки — отложенная проверка рекомендаций. Объём выделяется по мере необходимости. При выходе за размер поиска и при исчерпании бюджета рабочая память освобождается.</p>
<h2>Новые24 потока</h2>{table(fresh,meta)}
<h2>Известные 81 вход</h2><p>Парный полный replay с независимой проверкой занятых интервалов: 2 улучшения, 78 равенств, 1 ухудшение. Средняя Δ KPI {report['known_regression']['mean_KPI_delta']:+.6f}; худшая потеря {report['known_regression']['worst_KPI_delta']:+.6f} на neutral-919304-walk. Это повторная проверка знакомого набора, не независимое подтверждение.</p>
<h2>Что не получилось</h2><p>Первый вариант с расширенным прогнозированием дал на своей отложенной выборке среднюю Δ KPI {report['first_failed_pilot']['mean_KPI_delta']:+.6f} и превысил CPU: {report['first_failed_pilot']['max_CPU_s']:.2f}с. Он отклонён. Параметры второй гипотезы не подбирались по новой подтверждающей выборке.</p>
<h2>Граница результата</h2><p>Результат относится к свежим seed и входам знакомых синтетических механизмов. Ловушки на полностью общем публичном префиксе сохраняются: уже выкопанную траншею нельзя уменьшить. Например, ранний префикс Open11 всё ещё допускает KPI 1/12 при KPI Best-Fit = 1. Отложенная проверка горизонта 128 также не гарантирует хорошую геометрию на всём неизвестном будущем.</p>
<div class="card"><p><a href="causal-final/solution.cpp">Полный исходник C++20</a> · <a href="report.json">Результаты JSON</a> · <a href="metrics.csv">Сравнение CSV</a> · <a href="freeze-causal.json">Freeze</a></p><small>SHA256 исходника</small><p><code>{freeze['source_sha256']}</code></p><small>SHA256 бинарника</small><p><code>{freeze['binary_sha256']}</code></p></div></main></html>'''
    (HERE/'report.html').write_text(doc)
    print(json.dumps({k:report[k] for k in ['gate_passed','confirmation','maximum_official_CPU_s','maximum_official_RSS_MiB','Open15_score']},indent=2))
if __name__=='__main__':main()
