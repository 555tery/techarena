"""Report and package only the unchanged, independently confirmed candidate."""
import csv, datetime, html, json, shutil, zipfile
from evaluate import HERE, ROOT, cases, sha
from summarize import load, stats

LABELS={'baseline':'Прежний online','old_hybrid':'Прежний гибрид','handoff_exact':'Только точный handoff','primal_recent':'Новый online','hybrid_recent':'Новое ядро + гибрид'}

def main():
    frozen=json.loads((HERE/'selection-freeze.json').read_text());selected=frozen['selected']
    assert selected=='primal_recent'
    for n in frozen['final_names']:
        assert sha(HERE/'candidates'/n/'solution.cpp')==frozen['sources'][n]
        assert sha(HERE/'candidates'/n/'solver')==frozen['binaries'][n]
    for g in ['calibration','final','stress']:
        assert sha(HERE/'evaluation'/g/'manifest.json')==frozen['manifests'][g]
    baseline=load('screen','final','baseline')
    scores={n:stats(load('screen','final',n),baseline) for n in frozen['final_names']}
    official_names=['baseline','old_hybrid','primal_recent','hybrid_recent']
    official=[]
    public={}
    for g,num in [('final',128),('open15',15),('stress',3)]:
        for n in official_names:
            rows=load('official',g,n);bulk=load('screen',g,n)
            assert len(rows)==num and set(rows)==set(bulk)
            for k,r in rows.items():
                assert r['status']=='ok' and r['resources_ok']
                assert r['source_sha256']==frozen['sources'][n]
                assert r['test_sha256']==bulk[k]['test_sha256'] and r['trench_length_m']==bulk[k]['trench_length_m']
            official.extend(rows.values())
            if g=='open15':public[n]=sum(r['weight']*r['kpi'] for r in rows.values())
    cal=load('official','calibration',selected)
    assert len(cal)==64 and all(r['status']=='ok' and r['resources_ok'] for r in cal.values())
    official.extend(cal.values())
    edge=json.loads((HERE/'resource-edges-results.json').read_text())['records']
    assert len(edge)==4 and all(r['status']=='ok' and r['resources_ok'] for r in edge)
    official.extend(edge)
    chosen=[r for r in official if r['strategy']==selected]
    assert len(chosen)==212
    s=scores[selected]
    endpoint_delta={n:{str(p):(public[selected]-public[n])+84*((1-p)*(s['macro']['ordinary']-scores[n]['macro']['ordinary'])+p*(s['macro']['prefix']-scores[n]['macro']['prefix'])) for p in [0,.25,.5,.75,1]} for n in ['baseline','old_hybrid']}
    gates=dict(ordinary_positive=s['by_stratum']['ordinary']['family_macro_delta']>0,
        prefix_not_below_minus002=s['by_stratum']['prefix']['family_macro_delta']>=-.002,
        retention=s['min_retention']>=.85,
        positive_equal_stratum_mean=sum(s['by_stratum'][t]['family_macro_delta'] for t in ['ordinary','prefix'])>0,
        total_score_endpoints=min(endpoint_delta['baseline'].values())>0,
        official_valid_and_within_local_limits=all(r['status']=='ok' and r['resources_ok'] for r in chosen))
    outcome=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),selected=selected,
        confirmation_passed=all(gates.values()),gates=gates,source_sha256=frozen['sources'][selected],binary_sha256=frozen['binaries'][selected],
        previous_online_source_sha256=frozen['sources']['baseline'],previous_hybrid_source_sha256=frozen['sources']['old_hybrid'],
        selection_freeze_sha256=sha(HERE/'selection-freeze.json'),official_runs=len(official),selected_official_runs=len(chosen),
        maximum_cpu_s=max(r['solver_cpu_total_s'] for r in chosen),maximum_rss_mib=max(r['solver_peak_rss_mb'] for r in chosen),
        final_statistics=scores,open15_scores=public,scenario_gain_vs_controls=endpoint_delta,
        relative_to_previous_hybrid=stats(load('screen','final',selected),load('screen','final','old_hybrid')),
        native_windows_tested=False,target_g5420_tested=False,host='macOS arm64; one solver worker; process CPU user+system',
        platform_actions=0,canonical_changed=False,source_changed_after_final=False,
        independent_quality_inputs=128,calibration_inputs=64,predeclared_stress_inputs=3,post_freeze_resource_inputs=2,
        caveat='Independent synthetic transfer, not a guarantee on official hidden tests. Resource-edge tests are post-freeze validation, not quality evidence.')
    (HERE/'outcome.json').write_text(json.dumps(outcome,indent=2)+'\n')
    assert outcome['confirmation_passed'],'Do not release a failed candidate'
    release=HERE/'release';release.mkdir(exist_ok=True)
    shutil.copy2(HERE/'candidates'/selected/'solution.cpp',release/'solution.cpp')
    shutil.copy2(ROOT/'prototypes/pipes_closed_ready_20261020/release/windows_bench.py',release/'windows_bench.py')
    shutil.copy2(ROOT/'prototypes/pipes_closed_ready_20261020/release/build_windows.bat',release/'build_windows.bat')
    for g in ['calibration','final','stress','open15']:
        target=release/'tests'/g;target.mkdir(parents=True,exist_ok=True)
        rows=[]
        for c in cases(g):
            filename=c['id']+'.in';shutil.copy2(c['path'],target/filename)
            rows.append(dict(id=c['id'],file=filename,sha256=sha(target/filename)))
        (target/'manifest.json').write_text(json.dumps(dict(cases=rows),indent=2)+'\n')
    target=release/'tests/resource_edges';target.mkdir(parents=True,exist_ok=True)
    for p in (HERE/'resource_edges').glob('*.in'):shutil.copy2(p,target/p.name)
    (release/'manifest.json').write_text(json.dumps({k:v for k,v in outcome.items() if k not in ['final_statistics','relative_to_previous_hybrid']},indent=2)+'\n')
    for g in ['final','open15','stress']:
        with (HERE/f'metrics-{g}.csv').open('w') as f:
            fields=['id','strategy','stratum','family','kpi','trench_length_m','final_occupied_length_m','solver_cpu_total_s','solver_peak_rss_mb','source_sha256','test_sha256']
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
            for n in official_names:w.writerows(load('official',g,n).values())
    readme=f'''# Online-ядро для закрытой части

Локально подтверждённый вариант `primal_recent`, без таблиц Open15 и replay.
SHA256: `{outcome['source_sha256']}`.

После выбора на новых 64 calibration исходник зафиксирован; 128 final не использовались для настройки.
Final: средний KPI 0.910067→0.918646; 68 выигрышей, 37 равенств, 23 проигрыша против прежнего online.
Худшая ΔKPI −0.011798. Open15: 30.01926429 против 30.09096789 online и 30.10271159 прежнего hybrid.
Это положительный перенос на независимой синтетике, не гарантия официальных закрытых тестов.

Изменения: существующая оценка будущей полезности gaps включается при >=128 live,
 >=256 прошлых событий и>=32 удаления в текущем окне; прежняя ветка>4096 сохранена.
Окно спроса для этой оценки сокращено 2048→256; остальные истории и side/cohort heuristics сохранены.
Никакие test IDs, будущие команды или публичные ответы не используются.

Проверено{len(chosen)} полных интерактивных входов выбранного кода официальным interactor,
включая Open15, 64+128 новых, 3 stress и 2 дополнительные проверки нагрузки по 200000 команд.
CPU максимум {outcome['maximum_cpu_s']:.6f} с, RSS {outcome['maximum_rss_mib']:.3f} MiB на macOS arm64.
Windows 10/Pentium Gold G5420 не измерялся. Лимиты конкурса 5 с CPU/256 MiB.

## Windows: сборка и один CPU

В x64 Native Tools Command Prompt for Visual Studio:

```
build_windows.bat
py windows_bench.py --solver solution.exe --tests tests --out windows-results.json --repeat 1
```

Runner закрепляет solver на одном разрешённом CPU, измеряет user+kernel time и пиковую память,
подаёт запросы отдельно и независимо проверяет размещения. Это отдельный runner, не официальный interactor.
Все вложенные тесты уже наблюдались: для следующей настройки это regression corpus.

MC rollout всё ещё моделирует прежний gap policy; новый DP может расходиться с ним в будущем.
Это известное ограничение модели. Источник после final не менялся. Полный отчёт:../report.html.
Платформа и прежние frozen/canonical исходники не изменены.
'''
    (release/'README.md').write_text(readme)
    rows=''.join(f'<tr><td>{LABELS[n]}</td><td>{public[n]:.8f}</td><td>{scores[n]["macro"]["ordinary"]:.6f}</td><td>{scores[n]["macro"]["prefix"]:.6f}</td><td>{scores[n]["wins"]}/{scores[n]["ties"]}/{scores[n]["losses"]}</td></tr>' for n in official_names)
    tests={c['id']:c for c in cases('final')};candidate=load('screen','final',selected)
    case_rows=''
    for k in sorted(candidate,key=lambda k:candidate[k]['kpi']-baseline[k]['kpi']):
        d=candidate[k]['kpi']-baseline[k]['kpi'];typ='loss' if d<-1e-12 else 'win' if d>1e-12 else 'tie'
        case_rows+=f'<tr data-result="{typ}"><td><a href="evaluation/final/{tests[k]["file"]}">{k}</a></td><td>{html.escape(candidate[k]["family"])}</td><td>{baseline[k]["kpi"]:.6f}</td><td>{candidate[k]["kpi"]:.6f}</td><td class="{typ}">{d:+.6f}</td></tr>'
    ci=s['by_stratum'];old_delta=outcome['relative_to_previous_hybrid']['mean_delta']
    doc=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Pipes — новое online-ядро</title>
<style>body{{margin:0;background:#f3f5f7;color:#182634;font:16px/1.55 system-ui,sans-serif}}main{{max-width:1140px;margin:auto;padding:38px 24px}}h1{{font-size:38px;line-height:1.15}}h2{{margin-top:36px;font-size:24px}}p{{max-width:950px}}a{{color:#165ca8}}.eyebrow{{letter-spacing:.13em;font-size:12px;font-weight:750;color:#50677f}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.card,section{{background:white;border:1px solid #dbe2e9;border-radius:13px;padding:21px}}.card strong{{display:block;font-size:26px}}.muted{{color:#546474}}.good,.win{{color:#087544}}.loss{{color:#a13a15}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{padding:10px;border-bottom:1px solid #e3e7eb;text-align:left}}th{{background:#eaf0f5}}.scroll{{overflow:auto}}.notice{{background:#e7f4ed;border-left:4px solid #15855b;padding:17px 21px;border-radius:6px}}code{{overflow-wrap:anywhere;font-size:12px}}select{{font:inherit;padding:7px;margin:10px 0}}details{{margin-top:15px}}.tag{{font-size:12px;color:#5d6e80}}@media(max-width:760px){{.cards{{grid-template-columns:1fr 1fr}}h1{{font-size:29px}}main{{padding:22px 12px}}td,th{{padding:7px}}}}</style>
<main><div class="eyebrow">PIPES · ЛОКАЛЬНЫЙ РАУНД · 20 ОКТЯБРЯ 2026</div><h1>Прибавка в online-ядре<br>с проверкой на новых потоках</h1>
<p class="notice"><b>Выбран чистый online без replay.</b> Кандидат зафиксирован до 128 финальных тестов. Положительный перенос подтвердился в обеих группах. Это свидетельство на независимой синтетике, а не обещание счёта официальных закрытых.</p>
<div class="cards"><div class="card"><span class="muted">Средняя ΔKPI / final128</span><strong class="good">{s['mean_delta']:+.6f}</strong>68 побед · 37 равенств · 23 потери</div><div class="card"><span class="muted">Open15 /32.1</span><strong>{public[selected]:.5f}</strong>−0.08345 к прежнему hybrid</div><div class="card"><span class="muted">Худшая ΔKPI / final</span><strong class="loss">{s['worst'][0]['delta']:.6f}</strong>Универсального доминирования нет</div><div class="card"><span class="muted">Максимум CPU / выбранный код</span><strong>{outcome['maximum_cpu_s']:.3f}с</strong>{outcome['maximum_rss_mib']:.2f}MiB ·macOS arm64</div></div>
<p><a href="release/solution.cpp">Исходник</a> · <a href="online-core-ready.zip">Пакет для Windows и 212 тестов</a> · <a href="release/README.md">Инструкция</a> · <a href="outcome.json">Полные результаты и hashes</a></p>
<h2>Независимое сравнение</h2><section><div class="scroll"><table><thead><tr><th>Политика</th><th>Open15</th><th>Обычные: macro KPI</th><th>Ловушки: macro KPI</th><th>Final W/T/L vs old online</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Средний KPI всех 128: <b>{scores['baseline']['mean']:.6f}→{s['mean']:.6f}</b>. Против прежнего гибрида средняя прибавка <b>{old_delta:+.6f}</b>. 64 ordinary используют новые композиции механизмов; 64 prefix намеренно повторяют начало публичных входов, но имеют новые продолжения.</p>
<p>Парный family-bootstrap 95% для ΔKPI: ordinary [{ci['ordinary']['family_bootstrap95'][0]:+.6f};{ci['ordinary']['family_bootstrap95'][1]:+.6f}], prefix [{ci['prefix']['family_bootstrap95'][0]:+.6f};{ci['prefix']['family_bootstrap95'][1]:+.6f}]. Интервалы описывают этот генератор и его группировку, не неизвестное распределение конкурса.</p></section>
<h2>Что изменено в ядре</h2><section><p>Прежний код оценивал будущую полезность свободных участков только при более 4096 активных трубах. В меньших состояниях оставался грубый штраф за неиспользуемый остаток. Теперь существующая DP-оценка доступна уже при 128 live, 256 наблюдавшихся событиях и 32 удалениях в окне. Она сравнивает, сколько полезной вместимости теряется после укладки текущей трубы.</p><p>Спрос и частота удалений для этой модели считаются по последним 256 событиям вместо 2048, чтобы старый режим быстрее переставал влиять на выбор. Остальные side/cohort/LIFO истории сохранены. Все признаки причинные; в выбранном исходнике нет таблиц публичных ответов.</p><p class="muted">Проверены три отдельных гипотезы и одна композиция. Ослабление parity-confidence отклонено: наDEV дало крупную потерю−0.108949. Короткое окно без расширения области DP почти ничего не меняло. Измеренная ранняя версия gate исправлена с array capacity на реальное число событий до независимой calibration; исходная ревизия сохранена.</p></section>
<h2>Что ломалось в гибриде</h2><section><p>На прежних шести проигрышах разделены физическая геометрия и внутреннее состояние. В old-final105/120 геометрия совпадала, но import обнулял уже потраченный MC budget. Лишний rollout менял размещение, затем требовал дополнительного рытья. Точный перенос shadow при совпадении live PID-позиций иT исправляет эти два случая.</p><p>В old-final054/081/118/126 размещения отличались до переключения. Для118 накопилось 520 лишних метров: 452 промежутка длины 5 вместо 146. Перенос metadata это не исправляет. Handoff repair тоже не гарантирует рост KPI: на old-final090 он потерял 60 м, потому что прежний сброс бюджета случайно помогал.</p><p><a href="diagnostics/REPORT.md">Диагностика шести проигрышей</a> · <a href="diagnostics/handoff_exact/README.md">Проверка точного handoff</a></p><p>В новой calibration чистый online оказался предпочтительнее гибрида по заранее заданному критерию. Final даёт их почти равенство; выбор после final не пересматривался.</p></section>
<h2>Общий счёт, а не только Open15</h2><section><p>Известные веса: 32.1 открытых + 84 закрытых. Используем чувствительность <code>Open15 +84×((1−p)×ordinary_macro +p×prefix_macro)</code>, где доля ловушекp неизвестна. Это не прогноз официального счёта.</p>
<p>На final новая политика даёт <b>от{min(endpoint_delta['old_hybrid'].values()):+.3f} до{max(endpoint_delta['old_hybrid'].values()):+.3f} условного балла</b> к прежнему гибриду приp от 0 до 1. К прежнему online: от{min(endpoint_delta['baseline'].values()):+.3f} до{max(endpoint_delta['baseline'].values()):+.3f}. Потерю 0.08345 Open15 к hybrid окупает средний взвешенный прирост закрытого KPI около 0.000993.</p><p class="muted">Относительно исторического максимума Open15=30.75747405 потеря 0.73821; порог окупаемости около 0.008788 закрытого KPI. Полный replay в этом раунде повторно не сравнивался. Нельзя из этой таблицы заключить превосходство над любой стратегией на любом закрытом распределении.</p></section>
<h2>Ресурсы и границы проверки</h2><section><p>Выполнено <b>{len(official)} официальных интерактивных прогонов</b>, из них <b>{len(chosen)} для выпуска</b>. Финальные trench совпадают с независимой полной проверкой занятости. Пять нагрузочных входов имеют по 200000 команд: три заранее сгенерированных и два дополнительных после freeze для умеренной популяции и пересечения 4096 live. Последние два не использованы как свидетельство качества или для настройки.</p><p>Сборка C++17, один solver worker; CPU считается user+system процесса. <b>Windows 10/G5420 и MSVC нативно не проверены.</b> Пакет содержит runner с закреплением на одном CPU. Локальные замеры нельзя пересчитать по частоте процессора.</p><p>Оставшиеся ограничения: MC rollout продолжает моделировать прежний gap policy; DP и прогноз иногда расходятся. Lifetime confidence может кратко сохраняться ниже 4097 live до обновления модели. DP ограничен 512 состояниями, но обновляется и по смене спроса — строгой гарантии 5 с на целевой машине нет. <a href="core_audit/primary_review.json">Независимая проверка исходника</a>.</p></section>
<h2>Все 128 пар результатов</h2><section><label>Показать <select id="filter"><option value="all">Все</option><option value="loss">Только проигрыши</option><option value="win">Только выигрыши</option><option value="tie">Равенства</option></select></label><div class="scroll"><table id="cases"><thead><tr><th>Тест</th><th>Механизм</th><th>Прежний online</th><th>Новый online</th><th>ΔKPI</th></tr></thead><tbody>{case_rows}</tbody></table></div></section>
<h2>Воспроизводимость</h2><p><a href="experiment.json">План и критерии</a> · <a href="selection-freeze.json">Выбор до final</a> · <a href="evaluation/generation-summary.json">Происхождение 195 новых входов</a> · <a href="evaluation/disk-validation.json">Проверка входов</a> · <a href="metrics-final.csv">CSV финальных измерений</a></p><p class="tag">SHA256 выпуска: <code>{outcome['source_sha256']}</code><br>Платформа не использовалась; прежние frozen/canonical источники сохранены. Final теперь наблюдался: следующая настройка требует нового holdout.</p></main>
<script>document.getElementById('filter').addEventListener('change',function(){{document.querySelectorAll('#cases tbody tr').forEach(r=>r.hidden=this.value!=='all'&&r.dataset.result!==this.value);}});</script></html>'''
    (HERE/'report.html').write_text(doc)
    with zipfile.ZipFile(HERE/'online-core-ready.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(release.rglob('*')):
            if p.is_file():z.write(p,PathLike(p,release))
    print(json.dumps({k:outcome[k] for k in ['selected','confirmation_passed','source_sha256','official_runs','selected_official_runs','maximum_cpu_s','maximum_rss_mib','scenario_gain_vs_controls']},indent=2))

def PathLike(p,root):
    return 'online-core-ready/'+str(p.relative_to(root))

if __name__=='__main__':main()
