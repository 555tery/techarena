"""Render measured outcomes without promoting a failed candidate."""
import csv,datetime,hashlib,html,json,re
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(name):return json.loads((HERE/name).read_text())
def stats(rows):
    d=[r['delta'] for r in rows]
    return dict(n=len(d),wins=sum(x>1e-12 for x in d),ties=sum(abs(x)<=1e-12 for x in d),losses=sum(x<-1e-12 for x in d),mean_delta=sum(d)/len(d),worst_delta=min(d),best_delta=max(d))
def main():
    f=read('freeze.json');b=read('tail-transport/build.json');known=read('screen-known-tail-transport.json')
    fresh=read('official-fresh-tail-transport.json');public=read('official-open15-tail-transport.json');diagnostic=read('official-diagnostic-tail-transport.json')
    differences=read('official-known-tail-transport-differences.json');stress=read('official-stress-tail-transport.json')
    assert sha(HERE/'tail-transport/solution.cpp')==f['source_sha256']==b['source_sha256']
    assert sha(HERE/'tail-transport/solver')==f['binary_sha256']==b['binary_sha256']
    parent=ROOT/'prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp';assert sha(parent)==f['parent_source_sha256']
    for s in f['fresh_sets']:
        assert sha(HERE/s['manifest'])==s['manifest_sha256'];assert sha(HERE/s['generator'])==s['generator_sha256']
        folder=(HERE/s['manifest']).parent
        for r in json.loads((folder/'manifest.json').read_text())['cases']:assert sha(folder/r['filename'])==r['sha256']
    assert len(public['records'])==15
    for r in public['records']:assert r['trench_length_m']==r['minimum_trench_lower_bound_m'] and r['status']=='ok'
    joint=json.loads((ROOT/'prototypes/pipes_open15_overfit_20261019/joint.json').read_text())
    score=sum((Fraction(str(c['weight']))*c['F']/c['lower_T'] for c in joint['cases']),Fraction())
    assert str(score)==b['Open15_exact']
    affected=set()
    for r in fresh['records']:
        if r['strategy']!='candidate':continue
        m=re.search(r'local_accepted=(\d+) bf_steps=(\d+) identity_steps=(\d+)',r['candidate_stderr'])
        if m and any(map(int,m.groups())):affected.add(r['id'])
    selected_fresh=[r for r in fresh['pairs'] if r['id'] in affected]
    all_runs=[]
    for batch in [public,stress,differences,fresh,diagnostic]:all_runs.extend(r for r in batch['records'] if r['strategy']=='candidate')
    assert len(all_runs)==len({r['test_sha256'] for r in all_runs})==126
    assert all(r['status']=='ok' and r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256 for r in all_runs)
    previous_hashes={r['sha256'] for r in read('known.json')['tests']}
    assert not previous_hashes.intersection(r['test_sha256'] for r in fresh['records'])
    meta={
        'status':'completed_local_round_candidate_rejected','promoted':False,'candidate':'tail-transport','source_sha256':f['source_sha256'],'binary_sha256':f['binary_sha256'],
        'parent_source_sha256':f['parent_source_sha256'],'Open15_score':float(score),'Open15_exact':str(score),'known':stats(known['pairs']),
        'affected_known32_screen':stats(read('screen-known-tail-transport-affected.json')['pairs']),
        'official_recheck7':stats(differences['pairs']),'fresh96':stats(fresh['pairs']),
        'fresh_base64':stats([r for r in fresh['pairs'] if r['id'].startswith('base64-')]),
        'fresh_late32':stats([r for r in fresh['pairs'] if r['id'].startswith('late32-')]),
        'fresh_actually_uncoupled14':stats(selected_fresh),
        'new_partition_certificates':diagnostic['pairs'][:4],
        'official_runs':len(all_runs),'official_distinct_inputs':126,
        'max_cpu_s':max(r['solver_cpu_total_s'] for r in all_runs),'max_rss_mib':max(r['solver_peak_rss_mb'] for r in all_runs),
        'platform_actions':0,'target_hardware_run':False,'canonical_and_original_parent_changed':False,
        'scope':'Single solver worker on macOS arm64; no Windows 10 / Pentium Gold G5420 measurements.',
        'next_round':'These96 independent inputs and5 targeted diagnostics are now observed regression data. A newly tuned candidate requires a new independent set.',
        'limitations':[
            'No-loss gate failed. Full existing screen contains CPU-sensitive differences; none are filtered out.',
            'All3 fresh losses had zero Planner decisions, so they are physical pre-sync regressions, not timer noise.',
            'Local transport certificate is only a current-state/current-allocation invariant. Subsequent requests may make continuation impossible within parentT.',
            'The4 subset-sum certificates exclude any fallback for these4 already selected coordinates on their respective suffixes. They do not prove impossibility of every solver improvement.',
            'Fresh streams are new seeds/inputs of known mechanisms. Base64 covers public11/15 and neutral streams; extra32 covers public8/13. Only14 actually execute uncoupled fallback.'
        ]}
    (HERE/'report.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    with (HERE/'metrics.csv').open('w') as out:
        writer=csv.DictWriter(out,fieldnames=['group','id','baselineT','candidateT','baseline','candidate','delta']);writer.writeheader()
        for group,batch in [('known293_screen',known),('official_recheck7',differences),('fresh96',fresh),('diagnostics5',diagnostic)]:
            for r in batch['pairs']:writer.writerow({'group':group,**r})
    def h(x):return html.escape(str(x))
    def table(rows):
        return '<table><thead><tr><th>Тест</th><th>Траншея parent → candidate, м</th><th>KPI parent → candidate</th><th>ΔKPI</th></tr></thead><tbody>'+''.join(
            f'<tr><td>{h(r["id"])}</td><td>{r["baselineT"]} → {r["candidateT"]}</td><td>{r["baseline"]:.8f} → {r["candidate"]:.8f}</td><td class="{("bad" if r["delta"]<0 else "good")}">{r["delta"]:+.8f}</td></tr>' for r in rows)+'</tbody></table>'
    aggregates=[('Старые 293, screening',meta['known']),('Затронутые старые 32',meta['affected_known32_screen']),('Свежие 96, официальный interactor',meta['fresh96']),('Из них поздние 32',meta['fresh_late32']),('Из них реально до синхронизации 14',meta['fresh_actually_uncoupled14'])]
    agg=''.join(f'<tr><td>{h(name)}</td><td>{s["wins"]}</td><td>{s["ties"]}</td><td>{s["losses"]}</td><td>{s["worst_delta"]:+.8f}</td></tr>' for name,s in aggregates)
    changed=table([r for r in fresh['pairs'] if abs(r['delta'])>1e-12])
    diagnostic_table=table(diagnostic['pairs'])
    body=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Переносы до синхронизации — проверка на новых ловушках</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:1120px;margin:40px auto;padding:0 20px;color:#202530;background:#f5f6f8}}main{{background:white;padding:32px;border-radius:16px}}h1{{font-size:30px;line-height:1.2}}h2{{margin-top:30px;font-size:21px}}table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{padding:10px 9px;text-align:left;border-bottom:1px solid #e4e6eb;vertical-align:top}}.bad{{color:#ad2440}}.good{{color:#146c51}}.verdict{{background:#fff0f2;padding:16px;border-left:4px solid #ad2440}}a{{color:#245db0}}code{{overflow-wrap:anywhere}}small{{color:#606979}}details{{margin:18px 0}}.scroll{{overflow-x:auto}}</style><main>
<small>Локальный раунд · 20 октября 2026 · source {f['source_sha256'][:12]}</small>
<h1>Переносы до синхронизации: новый кандидат и новые контрпримеры</h1>
<p class="verdict"><b>Условие отсутствия регрессий не выполнено.</b> Новый вариант сохранён для исследования. Основной код и исходный parent не заменены.</p>
<p>Все 15 открытых тестов достигли объёмной нижней границы. Сохранён максимум <b>{float(score):.14f}</b>. На 96 независимо подготовленных тестах: <b>1 улучшение, 92 совпадения, 3 ухудшения</b>. Худшее изменение KPI: <b>−0.02708134</b>.</p>
<h2>Что изменено</h2>
<p>Четыре публичные трубы сдвинуты влево внутри того же свободного хвостового участка:562→557 м,799→633 м,799→792 м и879→868 м. Все общие публичные префиксы согласованы. Раннее положение PID2 Open11/15 осталось 229 м.</p>
<p>Исходный алгоритм продолжает работать как виртуальный parent. Физическое состояние создаётся только после изменённого размещения и освобождается после совпадения адресов всех живых PID. До этого проверяется локальное отражение с общей константой C и неизменными внешними трубами; при отказе используются допустимый адрес parent или Best-Fit. Подтверждение текущего шага не гарантирует успешного продолжения.</p>
<p>Проверены 30 ограниченных профилей на знакомых потоках. Выбранный вариант собран отдельно; проведён независимый разбор runtime и 11 проверок геометрического helper. После freeze исходник не менялся.</p>
<h2>Полные парные прогоны</h2><div class="scroll"><table><thead><tr><th>Набор</th><th>Лучше</th><th>Равно</th><th>Хуже</th><th>Худшая Δ</th></tr></thead><tbody>{agg}</tbody></table></div>
<p>Старый screening сравнивает с сохранёнными baseline-измерениями. У 7 ненулевых различий проведён новый официальный парный прогон: 1/5/1. Стабильная направленная прибавка на prev64-public_10: 0.55087719→0.57090909. Неизменённая геометрическая ветка prev64-public_07 дала 0.62016129→0.59153846 из-за иной CPU-зависимой траектории поиска; исходная потеря не исключена из gate.</p>
<h2>Все изменения на новых 96</h2><div class="scroll">{changed}</div>
<p>Во всех трёх новых проигрышах Planner имеет decisions=0. Это реальные последствия геометрии до синхронизации. Базовые 64 дали0/64/0; новые 32 вокруг поздних исправлений —1/28/3. Из 96 только 14 дошли до несовпадающих размещений при fallback: 1/10/3. Нельзя трактовать большой общий набор совпадений как широкую гарантию.</p>
<h2>Семейство ловушек, которые fallback уже не исправит</h2>
<p>После публичного префикса оставляем только перенесённую трубу, удаляем остальные и заполняем исходные левую и правую щели трубами длиной ≤40. Итоговый объём равен прежней траншее T. Для новой позиции её левую щель нельзя получить суммой никакого подмножества добавляемых длин. Значит, даже идеальный fallback со знанием будущего не уложится в T.</p>
<div class="scroll">{diagnostic_table}</div>
<p>Например, после префикса 17 остаётся труба длины 5. Parent оставил её на 562 м и укладывается в 580 м; кандидат оставил на 557 м и получает 620 м. Геометрическая нижняя граница для любого его продолжения — минимум 600 м. Это доказательство для конкретного нового адреса и suffix, а не запрет любых улучшений online-алгоритма.</p>
<p>Четыре контрпримера построены после freeze из публичной геометрии и проверены официальным interactor. Они отмечены отдельно от независимых96. Дополнительный 200000-командный стресс удерживает изменённый PID до конца; оба решения получили одинаковую траншею 4130720 м.</p>
<h2>Ресурсы и границы проверки</h2>
<p>126 официальных запусков кандидата на126 разных входах: максимум <b>{meta['max_cpu_s']:.6f}с CPU</b> и <b>{meta['max_rss_mib']:.3f}MiB RSS</b>. Лимиты 5 с / 256 MiB соблюдены локально, один solver worker, CPU=user+system. Хост macOS arm64; Windows 10 / Pentium Gold G5420 не измерялся. Платформа не использовалась.</p>
<p>Новые 96 имеют уникальные hashes и не совпадают с 293 прежними входами. Генераторы не читали кандидат и не отбирали по score. Базовые 64 используют Open11/15 и нейтральные потоки; дополнительные 32 — Open8/13. Это новые входы известных механизмов, не выборка закрытых тестов. Все 101 новых входа теперь являются знакомыми данными для следующих раундов.</p>
<h2>Воспроизведение и артефакты</h2>
<ul><li><a href="tail-transport/solution.cpp">Экспериментальный standalone source</a> · <a href="tail-transport/build.json">сборка и public audit</a></li>
<li><a href="freeze.json">Freeze</a> · <a href="experiment.json">границы поиска</a> · <a href="report.json">числаJSON</a> · <a href="metrics.csv">все парные метрики</a></li>
<li><a href="evaluation/fresh/manifest.json">Новые 64</a> · <a href="evaluation/fresh-late/manifest.json">новые 32</a> · <a href="diagnostics/manifest.json">4 сертификата и стресс</a></li>
<li><a href="make_certificates.py">Генератор проверяемых контрпримеров</a> · <a href="theory/local_transport.hpp">геометрический helper</a> · <a href="theory/local_transport_notes.txt">границы его гарантий</a></li>
<li><a href="../pipes_g5420_cpu_20261020/cache32/solution.cpp">Сохранённый исходный parent</a></li></ul>
</main></html>'''
    (HERE/'report.html').write_text(body)
    outcome={'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),**meta,'report_sha256':sha(HERE/'report.html'),'freeze_sha256':sha(HERE/'freeze.json')}
    (HERE/'outcome.json').write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:meta[k] for k in ['status','Open15_score','fresh96','fresh_actually_uncoupled14','official_runs','max_cpu_s','max_rss_mib']},indent=2))
if __name__=='__main__':main()
