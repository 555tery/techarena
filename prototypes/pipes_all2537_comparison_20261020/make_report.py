#!/usr/bin/env python3
"""Readable local comparison report, including explicitly labelled partials."""
import html
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
LABELS={'online_cpp':'Online · current C++','online_cj':'Online · Cangjie','primal_recent':'Online · primal_recent',
        'trial22':'Online · trial22','hybrid':'Осторожный hybrid','replay_search':'Replay + search · cache32'}

def f(x,n=6):return '—' if x is None else f'{x:.{n}f}'
def esc(x):return html.escape(str(x))

def main():
    data=json.loads((HERE/'analysis.json').read_text())
    freeze=json.loads((HERE/'freeze.json').read_text())
    methods=[m['id'] for m in freeze['methods']]
    panel=data['selected_panel_matched_summaries'];n=data['matched_completed_selected_count']
    complete=data['complete']
    state='Проверка завершена' if complete else 'Промежуточные результаты — прогон продолжается'
    desc=f'{n} / 2 537 потоков проверены всеми шестью версиями. {data["completed_runs"]:,} / {data["expected_runs"]:,} запусков, включая четыре дополнительных теста для полного Open15.'.replace(',',' ')
    body=[]
    for m in methods:
        s=panel[m];raw=s['raw_kpi_valid_scored_runs_only'];adj=s['contest_adjusted_kpi']
        counts=s.get('counts_raw_kpi_below_valid_scored_runs_only',{})
        if not counts:
            rows=[c['methods'][m] for c in data['per_case_results'] if c['selected'] and len(c['methods'])==len(methods)]
            counts={str(t):sum(r['raw_kpi'] is not None and r['raw_kpi']<t for r in rows) for t in [.85,.5,.1]}
        body.append('<tr><th>'+esc(LABELS[m])+'</th>'+''.join('<td>'+x+'</td>' for x in [f(raw['mean']),f(adj['mean']),f(raw['min']),f(raw['p05']),str(counts.get('0.85','—')),str(counts.get('0.5','—')),str(s['contest_failures_total']),f(s['cpu_process_user_plus_system_s']['max'],3),f(s['peak_rss_MiB']['max'],1)])+'</tr>')
    pairrows=[]
    for p in data['pairwise']:
        if p['first']!='online_cpp':continue
        r=p.get('raw_jointly_valid',p)
        delta=r.get('delta_mean_raw_kpi',r.get('delta_mean_adjusted_kpi'))
        if delta is None:
            # Supports schema extensions without silently substituting an adjusted comparison.
            cases=[c for c in data['per_case_results'] if c['selected'] and all(m in c['methods'] and c['methods'][m]['raw_kpi'] is not None for m in ['online_cpp',p['second']])]
            delta=math.fsum(c['methods']['online_cpp']['raw_kpi']-c['methods'][p['second']]['raw_kpi'] for c in cases)/len(cases) if cases else None
        pairrows.append('<tr><th>'+esc(LABELS[p['second']])+'</th><td>'+f(delta)+'</td><td>'+str(r['wins'])+'</td><td>'+str(r['ties'])+'</td><td>'+str(r['losses'])+'</td></tr>')
    openrows=[]
    for m in methods:
        s=data['full_open15'][m]
        openrows.append('<tr><th>'+esc(LABELS[m])+'</th><td>'+str(len(s['completed_public_numbers']))+'/15</td><td>'+f(s.get('raw_weighted_score'),8)+'</td><td>'+f(s.get('contest_adjusted_weighted_score'),8)+'</td></tr>')
    parity=data['response_parity_cpp_vs_cj']['all_frozen_including_extra_open15']
    equal=parity['identical_normalized_responses']+parity['normalized_equality_inferred_from_equal_recorded_raw_hashes']
    parity_text=f'{equal} из {parity["matched_completed_count"]} сопоставленных C++/Cangjie потоков дали одинаковые числовые ответы; обнаруженных расхождений: {len(parity["mismatches"])}.'
    portfolio=data.get('best_observed_portfolio',{})
    witness_text=(f"На {portfolio.get('KPI_at_least_085_with_observed_legal_placement',0)} из {n} полностью проверенных потоков хотя бы один метод действительно достиг KPI ≥ 0,85 при корректном размещении. "
                  f"На остальных {portfolio.get('no_observed_085_witness_count',0)} такого результата пока нет; объёмный верхний предел сам по себе его не гарантирует.")
    repeat_path=HERE/'resource-recheck/summary.json'
    repeat='Последовательная перепроверка пограничных ресурсов ещё не завершена.'
    if repeat_path.exists():
        r=json.loads(repeat_path.read_text())
        repeat=f'Последовательно повторено {r["jobs"]} запусков. Превышений/ошибок в повторе: {len(r["failures"])}. Изменившихся трасс ответов: {len(r["changed_answers"])}. Основные результаты не заменялись более удачными повторами.'
    repeat_table=''
    if repeat_path.exists() and r['complete']:
        repeat_records=[json.loads(line) for line in (HERE/'resource-recheck/records.jsonl').read_text().splitlines()]
        repeat_rows=[]
        for m in methods:
            rows=[x for x in repeat_records if x['method']==m]
            cpu=[x['solver_cpu_total_s'] for x in rows if x['solver_cpu_total_s'] is not None]
            rss=[x['solver_peak_rss_mb'] for x in rows if x['solver_peak_rss_mb'] is not None]
            repeat_rows.append('<tr><th>'+esc(LABELS[m])+'</th><td>'+str(len(rows))+'</td><td>'+f(max(cpu) if cpu else None,3)+'</td><td>'+f(max(rss) if rss else None,1)+'</td><td>'+str(sum(not x['within_limits'] for x in rows))+'</td></tr>')
        repeat_table='<div class="scroll"><table><thead><tr><th>Последовательный повтор</th><th>Запусков</th><th>CPU max, с</th><th>RSS max, MiB</th><th>Сбои / лимиты</th></tr></thead><tbody>'+''.join(repeat_rows)+'</tbody></table></div><p class="note">Здесь повторены только заранее определённые пограничные и самые тяжёлые запуски, по одному solver за раз. Эти числа не заменяют основную серию и не являются средними по всему корпусу.</p>'
    regime_section=''
    regime_path=HERE/'regime_analysis.json'
    if regime_path.exists():
        regimes=json.loads(regime_path.read_text())
        if regimes['records_snapshot_sha256']==data['hash_verification']['records_snapshot_sha256']:
            regime_rows=[]
            for key,label in [('replay_placements_eq0','Без выполненных размещений replay'),('replay_placements_gt0','Хотя бы одно размещение replay')]:
                g=regimes['regimes'][key]
                regime_rows.append('<tr><th>'+label+'</th>'+''.join('<td>'+x+'</td>' for x in [str(g['jointly_valid_count']),f(g['paired_mean_replay_search_raw_kpi']),f(g['paired_mean_online_cpp_raw_kpi']),f(g['paired_mean_delta_raw_kpi']),str(g['wins']),str(g['ties']),str(g['losses'])])+'</tr>')
            changes=regimes['regimes']['search_changes_gt0']
            regime_section='<section class="card"><h2>Когда replay + search выигрывает и проигрывает</h2><div class="scroll"><table><thead><tr><th>Наблюдавшийся режим</th><th>Потоков</th><th>Replay + search</th><th>Нынешний online</th><th>Δ KPI</th><th>Победы replay</th><th>Равенства</th><th>Проигрыши replay</th></tr></thead><tbody>'+''.join(regime_rows)+'</tbody></table></div><p>Поиск действительно изменил хотя бы одно размещение на '+str(changes['jointly_valid_count'])+' потоках; всего изменённых размещений: '+str(changes['search_changes_total'])+'.</p><p class="note">Группы выделены по фактической работе алгоритма и имеют разный состав тестов. Это описание наблюдений, а не эксперимент с отключением replay. У этого варианта собственный BF fallback; его победы нельзя приписывать только поиску или запоминанию. <a href="regime_analysis.json">Диагностика режимов и примеры</a>.</p></section>'
    source_rows=''.join('<tr><th>'+esc(LABELS[m['id']])+'</th><td><a href="'+esc(m['source'])+'">исходник</a></td><td><code>'+m['source_sha256']+'</code></td></tr>' for m in freeze['methods'])
    coverage_rows=[]
    for key,label in [('old339_selected','Из прежней проверки Cangjie'),('other_selected','Дополнительный архивный корпус')]:
        s=data.get('previous_validation_coverage_groups',{}).get(key)
        if s:
            coverage_rows.append('<tr><th>'+label+'</th><td>'+str(s['matched_completed_count'])+'/'+str(s['selected_total'])+'</td>'+''.join('<td>'+f(s['methods'][m]['raw_kpi_valid_scored_runs_only']['mean'])+'</td>' for m in methods)+'</tr>')
    cases=[c for c in data['per_case_results'] if c['selected']]
    size_rows=[]
    for low,high,label in [(1,200,'1–200'),(201,10000,'201–10 000'),(10001,100000,'10 001–100 000'),(100001,200000,'100 001–200 000')]:
        rows=[c for c in cases if low<=c['operations']<=high and len(c['methods'])==len(methods)]
        values=[]
        for m in methods:
            valid=[c['methods'][m]['raw_kpi'] for c in rows if c['methods'][m]['raw_kpi'] is not None]
            values.append(f(math.fsum(valid)/len(valid) if valid else None))
        size_rows.append('<tr><th>'+label+'</th><td>'+str(len(rows))+'</td>'+''.join('<td>'+x+'</td>' for x in values)+'</tr>')
    compact=[]
    for c in cases:
        compact.append(dict(id=c['id'],origin=c['origin'],group=c['source_group'],U=c['U'],N=c['operations'],
                            values={m:c['methods'][m]['raw_kpi'] for m in methods if m in c['methods']},
                            passes={m:c['methods'][m]['within_limits'] for m in methods if m in c['methods']}))
    encoded=json.dumps(dict(methods=methods,labels=LABELS,cases=compact),ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    page=PAGE.replace('__STATE__',esc(state)).replace('__DESC__',esc(desc)).replace('__WITNESS__',esc(witness_text)).replace('__TABLE__',''.join(body)).replace('__PAIRS__',''.join(pairrows)).replace('__OPEN__',''.join(openrows)).replace('__PARITY__',esc(parity_text)).replace('__REPEAT__',esc(repeat)).replace('__REPEAT_TABLE__',repeat_table).replace('__REGIMES__',regime_section).replace('__SOURCES__',source_rows).replace('__COVERAGE__',''.join(coverage_rows)).replace('__METHODHEAD__',''.join('<th>'+esc(LABELS[m])+'</th>' for m in methods)).replace('__DATA__',encoded)
    page=page.replace('__SIZES__',''.join(size_rows))
    if complete:
        page=page.replace('<p>'+esc(witness_text)+'</p>','<p>'+esc(witness_text)+' <a href="witnesses_085.json">Каталог достигнутых KPI ≥ 0,85</a>.</p>')
    (HERE/'report.html').write_text(page)
    lines=[state,desc,'','Средний raw KPI / adjusted KPI / min raw / CPUmax / RSSmax:']
    for m in methods:
        s=panel[m];lines.append(f"{LABELS[m]}: {f(s['raw_kpi_valid_scored_runs_only']['mean'])} / {f(s['contest_adjusted_kpi']['mean'])} / {f(s['raw_kpi_valid_scored_runs_only']['min'])} / {f(s['cpu_process_user_plus_system_s']['max'],3)} s / {f(s['peak_rss_MiB']['max'],1)} MiB")
    lines+=['',parity_text,repeat,'','Корпус наблюдавшийся; это не новый holdout и не прогноз закрытого счёта. U — объёмный верхний предел, а не доказанный достижимый оптимум. Основная серия содержит последовательные и 4-worker запуски; CPU каждого solver измерен отдельно, без деления на число workers. macOS arm64; Windows/Pentium G5420 не измерен.']
    (HERE/'REPORT.txt').write_text('\n'.join(lines)+'\n')
    print('report.html',state,n)

PAGE='''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Pipes — 2537 тестов, 6 методов</title>
<style>
:root{color-scheme:light;--ink:#182934;--muted:#5b6b73;--line:#d9e2e6;--accent:#006c67}*{box-sizing:border-box}body{margin:0;background:#f3f6f7;color:var(--ink);font:16px/1.55 system-ui,-apple-system,sans-serif}main{max-width:1440px;margin:auto;padding:36px 28px 70px}h1{font-size:38px;line-height:1.15;margin:8px 0 18px}h2{font-size:23px;margin:0 0 12px}.eyebrow{color:var(--accent);font-size:13px;font-weight:750;letter-spacing:.12em}.lead{font-size:19px;max-width:1000px}.note{color:var(--muted);max-width:1050px}.card{background:white;border:1px solid var(--line);border-radius:14px;padding:24px;margin:24px 0}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:14px}th,td{padding:11px 12px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th:first-child{text-align:left}thead{background:#eef4f4}tbody th{font-weight:600}a{color:var(--accent)}code{font-size:11px}.controls{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}input,select{padding:11px;border:1px solid #afc3c6;border-radius:8px;font:inherit}input{flex:1;min-width:250px}.path{max-width:430px;white-space:normal;word-break:break-word}.bad{color:#b52424;background:#fff0ef}.dim{color:#809099}.footer{font-size:13px;color:var(--muted)}@media(max-width:700px){main{padding:20px 12px}.card{padding:16px}h1{font-size:29px}}</style></head>
<body><main><div class="eyebrow">PIPES / ПОЛНЫЙ СОХРАНЁННЫЙ КОРПУС</div><h1>2 537 тестов · 6 версий</h1><p class="lead">__STATE__</p><p>__DESC__</p>
<p class="note">Уникальные корректные потоки с объёмным верхним пределом KPI ≥ 0,85. Каждый поток имеет одинаковый вес. Средние ниже рассчитаны на общем наборе уже полностью проверенных потоков. Это архивный корпус, содержащий знакомые генераторы и направленные ловушки; он не является независимым holdout.</p><p>__WITNESS__</p>
<section class="card"><h2>Качество размещений и ресурсы</h2><div class="scroll"><table><thead><tr><th>Метод</th><th>Средний KPI</th><th>С нулём за сбои</th><th>Минимум</th><th>5-й процентиль</th><th>KPI &lt; 0,85</th><th>KPI &lt; 0,5</th><th>Сбои / лимиты</th><th>CPU max, с</th><th>RSS max, MiB</th></tr></thead><tbody>__TABLE__</tbody></table></div><p class="note">Средний KPI — точный F/T для корректных размещений, включая завершившиеся запуски с превышением ресурсов. В соседнем столбце ошибки и CPU ≥ 5 с / RSS ≥ 256 MiB дают ноль. «Минимум» и процентили относятся к качеству размещений.</p><p class="note">CPU — user + system всего процесса solver, без деления на ядра. Основная серия включает первые последовательные и последующие 4-worker запуски; у Cangjie cjProcessorNum=1. Этот Mac не воспроизводит Windows 10 / Pentium G5420.</p><p>__REPEAT__</p>__REPEAT_TABLE__</section>
<section class="card"><h2>Нынешний online C++ против остальных</h2><div class="scroll"><table><thead><tr><th>Соперник</th><th>Δ среднего KPI</th><th>Победы online</th><th>Равенства</th><th>Проигрыши online</th></tr></thead><tbody>__PAIRS__</tbody></table></div><p class="note">Сравнение полного потока; F/T сравнивается как точная дробь. Только пары с двумя корректными геометрическими результатами. Ресурсные штрафы учитываются отдельно.</p><p>__PARITY__</p></section>
<section class="card"><h2>Что добавила расширенная проверка</h2><div class="scroll"><table><thead><tr><th>Группа</th><th>Полностью проверено</th>__METHODHEAD__</tr></thead><tbody>__COVERAGE__</tbody></table></div><p class="note">Средний KPI в каждой группе. Принадлежность к прежнему набору проверена по содержимому команд, а не по имени файла. Дополнительные 2 256 потоков взяты из архива; они не являются новым независимым holdout. <a href="coverage.json">Аудит покрытия</a>.</p></section>
<section class="card"><h2>Размер потока</h2><div class="scroll"><table><thead><tr><th>Команд в потоке</th><th>Проверено</th>__METHODHEAD__</tr></thead><tbody>__SIZES__</tbody></table></div><p class="note">Средний raw KPI в каждой группе, одинаковый вес каждого потока. Это описательный разрез того же архива; размер сам по себе не объясняет причину выигрыша, состав генераторов между группами различается.</p></section>
__REGIMES__
<section class="card"><h2>Полный Open15</h2><div class="scroll"><table><thead><tr><th>Метод</th><th>Проверено</th><th>Баллы по KPI / 32,1</th><th>С нулём за сбои</th></tr></thead><tbody>__OPEN__</tbody></table></div><p class="note">Четыре открытых теста не проходят фильтр U ≥ 0,85 и добавлены только для этой отдельной таблицы. Их нет в среднем по 2 537.</p></section>
<section class="card"><h2>Провалы и отдельные тесты</h2><p class="note">U = F / (20 × ceil(P/20)), где P — пиковый живой объём. Это верхний предел, а не доказательство достижимости такого KPI. Красный фон: данный запуск нарушил протокол или ресурсный лимит.</p><div class="controls"><input id="query" placeholder="Поиск по пути или группе тестов"><select id="sort"><option value="online">Худший нынешний online</option><option value="replay">Худший replay</option><option value="replayloss">Потеря replay относительно online</option><option value="onlineloss">Потеря online относительно primal_recent</option><option value="hybridloss">Потеря online относительно hybrid</option><option value="length">Самые длинные потоки</option></select><select id="group"><option value="">Все источники</option></select></div><p id="count" class="note"></p><div class="scroll"><table><thead><tr id="casehead"><th>Тест / вход</th><th>N</th><th>U</th></tr></thead><tbody id="cases"></tbody></table></div><p class="footer">Показаны первые 100 строк после фильтрации. Все результаты доступны в <a href="analysis.json">analysis.json</a>; исходные записи — <a href="records.jsonl">records.jsonl</a>.</p></section>
<section class="card"><h2>Зафиксированные версии</h2><div class="scroll"><table><thead><tr><th>Метод</th><th>Код</th><th>SHA256 исходника</th></tr></thead><tbody>__SOURCES__</tbody></table></div><p><a href="freeze.json">Манифест методов и всех входов</a> · <a href="REPORT.txt">Краткий текстовый отчёт</a> · <a href="resource-recheck/summary.json">Последовательная проверка ресурсов</a></p><p class="note">Исходники методов не настраивались по этому прогону. CPU-зависимый search может менять решения при повторе; такие расхождения сохраняются отдельно. Оценка на этом архиве не устанавливает победителя на неизвестных закрытых тестах.</p></section>
</main><script id="data" type="application/json">__DATA__</script><script>
const d=JSON.parse(document.getElementById('data').textContent),tb=document.getElementById('cases'),q=document.getElementById('query'),s=document.getElementById('sort'),g=document.getElementById('group');
for(const m of d.methods){const th=document.createElement('th');th.textContent=d.labels[m];document.getElementById('casehead').appendChild(th)}
for(const name of [...new Set(d.cases.map(c=>c.group))].sort()){const o=document.createElement('option');o.value=name;o.textContent=name;g.appendChild(o)}
function value(c,m){return c.values[m]===undefined||c.values[m]===null?2:c.values[m]}
function key(c){if(s.value==='replay')return value(c,'replay_search');if(s.value==='replayloss')return value(c,'replay_search')-value(c,'online_cpp');if(s.value==='onlineloss')return value(c,'online_cpp')-value(c,'primal_recent');if(s.value==='hybridloss')return value(c,'online_cpp')-value(c,'hybrid');if(s.value==='length')return -c.N;return value(c,'online_cpp')}
function draw(){const text=q.value.toLowerCase();let a=d.cases.filter(c=>(!g.value||c.group===g.value)&&(!text||(c.origin+' '+c.id).toLowerCase().includes(text)));a.sort((a,b)=>key(a)-key(b)||a.id.localeCompare(b.id));document.getElementById('count').textContent='Найдено '+a.length+' потоков; показано '+Math.min(100,a.length)+'.';tb.replaceChildren();for(const c of a.slice(0,100)){const tr=document.createElement('tr'),th=document.createElement('th'),a=document.createElement('a');th.className='path';a.href='inputs/'+c.id+'.in';a.textContent=c.origin;th.appendChild(a);tr.appendChild(th);for(const v of [c.N,c.U.toFixed(6)]){const td=document.createElement('td');td.textContent=v;tr.appendChild(td)}for(const m of d.methods){const td=document.createElement('td');td.textContent=c.values[m]===undefined||c.values[m]===null?'—':c.values[m].toFixed(6);if(c.passes[m]===false)td.className='bad';tr.appendChild(td)}tb.appendChild(tr)}}
q.addEventListener('input',draw);s.addEventListener('change',draw);g.addEventListener('change',draw);draw();
</script></body></html>'''

if __name__=='__main__':main()
