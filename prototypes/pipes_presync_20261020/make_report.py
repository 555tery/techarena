"""Produce the final local evidence report without changing frozen sources."""
import csv,hashlib,html,json
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stats(pairs):
    ds=[p['delta'] for p in pairs]
    return {'n':len(ds),'wins':sum(d>1e-12 for d in ds),'ties':sum(abs(d)<=1e-12 for d in ds),'losses':sum(d<-1e-12 for d in ds),
      'mean_delta':sum(ds)/len(ds) if ds else 0,'worst_delta':min(ds,default=0)}
def main():
    freeze=json.loads((HERE/'freeze.json').read_text());name=freeze['candidate'];build=json.loads((HERE/name/'build.json').read_text())
    assert sha(HERE/name/'solution.cpp')==freeze['source_sha256'] and sha(HERE/name/'solver')==freeze['binary_sha256']
    known=json.loads((HERE/f'screen-known-{name}.json').read_text());fresh=json.loads((HERE/f'official-fresh-{name}.json').read_text())
    opened=json.loads((HERE/f'official-open15-{name}.json').read_text());stress=json.loads((HERE/f'official-stress-{name}.json').read_text());diagnostic=json.loads((HERE/f'official-diagnostic-{name}.json').read_text())
    affected=set(json.loads((HERE/'known.json').read_text())['affected_ids']);manifest=json.loads((HERE/'evaluation/fresh/manifest.json').read_text())
    directed={x['name'] for x in manifest['cases'] if x['family']=='prefix_3_2_live_pid2'};assert len(directed)==32
    groups={'known227':stats(known['pairs']),'known_affected72':stats([r for r in known['pairs'] if r['id'] in affected]),
      'fresh64':stats(fresh['pairs']),'fresh_directed32':stats([r for r in fresh['pairs'] if r['id'] in directed]),
      'fresh_other32':stats([r for r in fresh['pairs'] if r['id'] not in directed])}
    score=sum((Fraction(str(r['weight']))*r['final_occupied_length_m']/r['trench_length_m'] for r in opened['records']),Fraction())
    assert score==Fraction(8753218892157372683,284588353335535200)
    confirmed=json.loads((HERE/f'official-known-{name}-selected-losses.json').read_text())
    timing=json.loads((HERE/'timing-public07.json').read_text())
    official=opened['records']+fresh['records']+stress['records']+diagnostic['records']+confirmed['records']+timing['records'];candidate=[r for r in official if r['strategy']=='candidate']
    assert all(r['status']=='ok' and r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256 for r in candidate)
    resources={'official_selected_run_count':len(candidate),'official_selected_unique_inputs':len({r['test_sha256'] for r in candidate}),'maximum_cpu_s':max(r['solver_cpu_total_s'] for r in candidate),
      'maximum_rss_mib':max(r['solver_peak_rss_mb'] for r in candidate),'host':'macOS arm64; one solver worker; process CPU=user+system',
      'target':'Windows10 64bit/PentiumGoldG5420/one core','target_measurement':False}
    result={'candidate':name,'source_sha256':build['source_sha256'],'binary_sha256':build['binary_sha256'],'parent_source_sha256':build['parent_source_sha256'],
      'open15_score':float(score),'open15_score_exact':str(score),'all15_volume_ceiling':True,'groups':groups,'resources':resources,
      'promoted':False,'reason':'Known and independent fresh no-regression gates failed. Original parent and canonical sources remain unchanged.',
      'frozen_before_fresh':True,'fresh_manifest_sha256':sha(HERE/'evaluation/fresh/manifest.json'),'generator_sha256':sha(HERE/'evaluation/generate_fresh.py'),
      'fresh_exposure':'New seeded inputs, same known mechanisms; independently constructed without candidate code/results. Generator read historical wiki terminology, recorded in manifest.',
      'search':'2043 simple marker/rule profiles;1816 projection/mirror variants plus2 joint component-reorder profiles. Three actual standalone finalists, all failed known no-loss gate.',
      'limitations':['Only full PID identity coupling gives a sticky terminal-T guarantee versus the internal timed parent.','Equal occupied unions permit the current allocation; future deletion can break equality.','Accepted mirror/projection actions fit and do not exceed current internal parent T. Fallback has no universal guarantee.','Virtual parent timing can differ from a separate frozen baseline executable.','Extra physical Planner committed zero decisions on known227; not selected. Its headroom time-frame issue was identified in a separate audit; that experimental variant is not promoted.'],
      'diagnostic_certificate':json.loads((HERE/'diagnostics/certificate.json').read_text()),'diagnostic_pairs':diagnostic['pairs'],
      'timing_public07_repeats':timing['pairs'],'timing_public07_scope':'Unchanged geometry, zero pre-sync choices; 3 repeated pairs show a loss, tie, and win. Preserve the original fresh64 result; do not silently discard or average away its loss.',
      'harness_sha256':sha(ROOT/'tools/pipes_harness.py'),'interactor_binary_sha256':sha(ROOT/'tools/interactor'),'platform_actions':0}
    (HERE/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    with (HERE/'metrics.csv').open('w') as f:
        fields=['group','id','baseline','candidate','baselineT','candidateT','delta'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for group,data in [('known227',known),('fresh64',fresh),('diagnostic',diagnostic)]:
            for row in data['pairs']:w.writerow({'group':group,**{k:row[k] for k in fields if k!='group'}})
    esc=html.escape
    summary=''.join(f'<tr><td>{esc(label)}</td><td>{s["n"]}</td><td>{s["wins"]}</td><td>{s["ties"]}</td><td>{s["losses"]}</td><td>{s["worst_delta"]:+.8f}</td></tr>' for label,s in groups.items())
    rows=''
    for group,data in [('Новые64',fresh),('Знакомые72 с изменённым префиксом',{'pairs':[r for r in known['pairs'] if r['id'] in affected]}),('Дополнительная диагностика',diagnostic)]:
        for r in data['pairs']:
            cls='loss' if r['delta']<-1e-12 else 'win' if r['delta']>1e-12 else ''
            rows+=f'<tr class="{cls}"><td>{esc(group)}</td><td>{esc(r["id"])}</td><td>{r["baseline"]:.9f}</td><td>{r["candidate"]:.9f}</td><td>{r["baselineT"]} → {r["candidateT"]}</td><td>{r["delta"]:+.9f}</td></tr>'
    body=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pipes: до синхронизации</title>
<style>body{{font:16px/1.55 system-ui;margin:0;background:#f2f4f8;color:#172038}}main{{max-width:1140px;margin:auto;padding:38px 25px}}h1{{font-size:38px;line-height:1.15}}h2{{margin-top:36px}}.card{{background:white;padding:24px;border-radius:16px;margin:20px 0}}.decision{{border-left:5px solid #b65b25}}.metrics{{display:flex;gap:18px;flex-wrap:wrap}}.metrics div{{flex:1;background:#fff;border-radius:14px;padding:22px;min-width:180px}}.metrics strong{{display:block;font-size:28px}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:9px;text-align:left;border-bottom:1px solid #e2e6ed}}th{{position:sticky;top:0;background:#e9edf5}}.loss{{background:#fff0e9}}.win{{background:#eaf7f0}}code{{overflow-wrap:anywhere;font-size:13px}}a{{color:#204dad}}.scroll{{overflow:auto;max-height:650px}}.muted{{color:#536077}}</style>
<main><p class="muted">Локальный эксперимент · 20 октября2026 · платформа не использовалась</p><h1>Ловушки до синхронизации</h1>
<div class="card decision"><strong>Максимум Open15 сохранён. Улучшение без регрессий не подтверждено.</strong><p>Версия {esc(name)} оставлена экспериментальной. Основной исходник и прежний замороженный parent не заменены. Новые тесты открывались только после фиксации исходника и бинарника; после результатов кандидат не настраивался.</p></div>
<div class="metrics"><div>Open15<strong>{float(score):.14f}</strong>Все15 достигли объёмной границы</div><div>Новые64: победы / равенства / потери<strong>{groups['fresh64']['wins']} / {groups['fresh64']['ties']} / {groups['fresh64']['losses']}</strong>Официальный локальный интерактор</div><div>Ресурсы, максимум<strong>{resources['maximum_cpu_s']:.3f}s · {resources['maximum_rss_mib']:.1f}MiB</strong>macOS arm64; Windows/G5420 не измерен</div></div>
<section class="card"><h2>Что добавлено в код</h2><p>До полного совпадения PID алгоритм ищет отражение живых труб: <code>actual_x + parent_x + length = C</code>. Новый адрес получается как <code>C − parent_x − request</code>. Код проверяет свободное место и то, что текущая траншея не станет длиннее внутреннего parent. Отдельно ведётся точная разность занятых объединений; равенство позволяет выполнить текущую команду parent.</p><p>После совпадения адресов всех живых PID и условия <code>actualT ≤ parentT</code> solver продолжает полный виртуальный parent. До этого момента отказ отражения может приводить к потерям. Дополнительный физический поиск не дал ни одного committed-изменения на знакомых227 и не вошёл в выбранный кандидат.</p></section>
<section class="card"><h2>Парная проверка</h2><p>Знакомые227 использовались для выбора. Отдельные64 содержат32 ранних расхождения при живойPID2,16 других публичных префиксов и16 нейтральных потоков. Это новые входы и seed уже известных механизмов, а не неизвестное распределение. Генератор не читал кандидат и результаты, но читал историческую wiki; это отражено в provenance.</p><table><thead><tr><th>Набор</th><th>N</th><th>Лучше</th><th>Равно</th><th>Хуже</th><th>Худшая ΔKPI</th></tr></thead><tbody>{summary}</tbody></table><p>Из9 улучшений на знакомых227 два малых отличия относятся к неизменённым веткам и не приписываются новой геометрии: CPU-бюджет внутреннего parent может отличаться от отдельного процесса.</p></section>
<section class="card"><h2>Чувствительность CPU-поиска</h2><p>Потеря public_07 возникла на ветке без единого зеркального размещения и без шагов до coupling. Первоначальный результат: parent1220м, кандидат1260м. Три дополнительные пары дали1260→1280,1260→1260 и1260→1220м. Это чувствительность решений внутреннего поиска к CPU-бюджету. Первоначальный результат независимых64 сохранён; эта потеря не исключена из gate.</p></section>
<section class="card"><h2>Новый короткий контрпример</h2><p><code>3, 2, 9, 40, 40, 40, 40, 40, 26</code></p><p>У кандидата первые трубы занимают [0,3) и[9,11). Оставшиеся6м между ними нельзя заполнить: каждая следующая труба длиннее6. Итоговый объём240м требует как минимум260м траншеи при этих двух первых ответах. Никакой fallback после них не исправит это размещение. Исходный parent и обычный Best-Fit достигают240м и KPI1. Это отдельная диагностика после freeze, не часть независимых64.</p></section>
<section class="card"><h2>Точные результаты</h2><div class="scroll"><table><thead><tr><th>Набор</th><th>Тест</th><th>Parent KPI</th><th>Кандидат KPI</th><th>T,м</th><th>ΔKPI</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section class="card"><h2>Артефакты и границы</h2><p><a href="{name}/solution.cpp">Экспериментальный исходник</a> · <a href="freeze.json">Freeze</a> · <a href="report.json">JSON</a> · <a href="metrics.csv">Парные метрики</a> · <a href="evaluation/fresh/manifest.json">Новые64</a> · <a href="diagnostics/certificate.json">Короткий контрпример</a></p><p>SHA256 source: <code>{build['source_sha256']}</code><br>SHA256 binary: <code>{build['binary_sha256']}</code></p><p>Проверено с лимитами5CPU-seconds и256MiB, один solver worker. CPU=user+system процесса. Замеры macOS не переносятся на PentiumGoldG5420 по частоте; нативная Windows-проверка остаётся отдельным этапом.</p><p>Перебраны2043 простых варианта и1816 вариантов переносов/отражений, а также совместные перестановки компонентов; ни один нетривиальный вариант не прошёл все знакомые тесты без потерь. Это конечный отрицательный поиск, не доказательство невозможности любых улучшений.</p></section></main></html>'''
    (HERE/'report.html').write_text(body);print(json.dumps({k:result[k] for k in ['candidate','open15_score','groups','resources','promoted']},indent=2))
if __name__=='__main__':main()
