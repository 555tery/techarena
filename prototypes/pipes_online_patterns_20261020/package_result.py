"""Package the exact frozen source only after all independent checks pass."""
import csv,datetime,html,json,shutil,zipfile
from evaluate import HERE,ROOT,cases,source,sha
from summarize import load,stats

LABELS={'stable_patterns':'Устойчивые паттерны','changing_patterns':'Смена паттернов','neutral':'Контрольные потоки','public_prefix':'Публичный префикс'}

def main():
    q=json.loads((HERE/'quality-outcome.json').read_text())
    frozen=json.loads((HERE/'selection-freeze.json').read_text());selected=frozen['selected']
    assert q['quality_passed'] and selected=='strict_improvement'
    review=json.loads((HERE/'strict_source_audit.json').read_text())
    assert not review['fatal_correctness_flaw_found'] and review['candidate_sha256']==q['source_sha256']
    for n in frozen['sources']:
        assert sha(source(n))==frozen['sources'][n]
        assert sha(source(n).with_name('solver'))==frozen['binaries'][n]
    for g in ['calibration','final','stress']:
        assert sha(HERE/'evaluation'/g/'manifest.json')==frozen['manifests'][g]
    official=[]
    for g,num,names in [('final',192,['baseline',selected]),('calibration',96,[selected]),('open15',15,['baseline',selected]),('stress',4,['baseline',selected])]:
        inputs={c['id']:c for c in cases(g)}
        for n in names:
            a=load('official',g,n);b=load('screen',g,n)
            assert len(a)==num and set(a)==set(b)==set(inputs)
            for k,r in a.items():
                assert r['status']=='ok' and r['resources_ok']
                assert r['source_sha256']==frozen['sources'][n] and r['binary_sha256']==frozen['binaries'][n]
                assert r['test_sha256']==sha(inputs[k]['path'])==b[k]['test_sha256']
                assert r['trench_length_m']==b[k]['trench_length_m']
            official.extend(a.values())
    chosen=[r for r in official if r['strategy']==selected]
    assert len(official)==518 and len(chosen)==307
    original=(ROOT/'prototypes/pipes_online_core_20261020/release/solution.cpp')
    assert sha(original)==q['baseline_sha256']
    q.update(official_confirmation_pending=False,confirmation_passed=True,
        official_runs=len(official),selected_official_runs=len(chosen),
        maximum_cpu_s=max(r['solver_cpu_total_s'] for r in chosen),
        maximum_rss_mib=max(r['solver_peak_rss_mb'] for r in chosen),
        native_windows_tested=False,target_G5420_tested=False,host='macOS arm64, one solver worker, CPU user+system',
        source_review_sha256=sha(HERE/'strict_source_audit.json'),
        recommendation='Small incremental local candidate; passed the fixed point-estimate gates, but the incremental effect is not statistically resolved by the descriptive mechanism bootstrap.',
        generated_new_inputs=292,selection_calibration_inputs=96,independent_final_inputs=192,
        packaged_tests=307,final_now_observed=True)
    (HERE/'outcome.json').write_text(json.dumps(q,indent=2)+'\n')
    release=HERE/'release';release.mkdir(exist_ok=True)
    shutil.copy2(source(selected),release/'solution.cpp')
    old_release=ROOT/'prototypes/pipes_online_core_20261020/release'
    for name in ['build_windows.bat','windows_bench.py']:shutil.copy2(old_release/name,release/name)
    for g in ['calibration','final','stress','open15']:
        folder=release/'tests'/g;folder.mkdir(parents=True,exist_ok=True);entries=[]
        for c in cases(g):
            filename=c['id']+'.in';shutil.copy2(c['path'],folder/filename)
            entries.append(dict(id=c['id'],file=filename,sha256=sha(folder/filename)))
        (folder/'manifest.json').write_text(json.dumps(dict(cases=entries),indent=2)+'\n')
    (release/'manifest.json').write_text(json.dumps({k:v for k,v in q.items() if k not in ['target23','final_statistics','relative_to_legacy']},indent=2)+'\n')
    s=q['final_statistics'];pub=q['public_scores'];ci=q['uncertainty']['intervals95'];ep=q['total_score_endpoints_delta']
    note=f'''Pipes — небольшой шаг в online-ядре, 20 октября 2026

Исходник: strict_improvement, SHA256 {q['source_sha256']}
Основа: прежний primal_recent, SHA256 {q['baseline_sha256']}

В первичном DP-сравнении legacyBest становится исходным выбором.
Менять его можно только при score+1e-9<currentScore. Равенство модели
само по себе больше не меняет предпочтение адреса. Последующие lifetime
correction и MC сохранены: фактического доминирования по KPI это не даёт.
Нет таблиц Open15/replay, новых контейнеров памяти или чтения будущего.

После 96 новых calibration исходник зафиксирован. На отдельных 192 final:
средний KPI 0.907398581 -> {s['mean']:.9f}; 37 побед,122 равенства,33 потери.
Устойчивые паттерны: macro delta -0.000313; меняющиеся +0.000500;
контрольные +0.000277; публичные префиксы +0.000453.
Open15 {pub['baseline']:.8f} -> {pub[selected]:.8f}.
Общий счёт при равной смеси четырёх strata: условная прибавка
{q['total_score_equal_mix_delta']:+.6f}; при разных смесях от {min(ep.values()):+.6f}
до {max(ep.values()):+.6f}. Это чувствительность, не прогноз закрытого конкурса.
Bootstrap95% equal-stratum delta [{ci['equal_four_strata'][0]:+.6f};{ci['equal_four_strata'][1]:+.6f}]
пересекает ноль: небольшая прибавка пока статистически неубедительна.

Из прежних 23 потерь улучшены6, полностью устранены2, ухудшена1,16 ties.
На полном прежнем final128 осталось22 потери против legacy вместо23:
две старые ушли, одна новая появилась. Сохранено99.85% прежней средней прибавки.
Ни один кандидат не прошёл исходное DEV mean>=0. До свежих результатов
допуск был расширен на неотрицательные сценарии общего счёта с Open15.
Финальные критерии остались прежними; после final код не менялся.

Все307 тестов этого исходника прошли официальный интерактор и отдельную
проверку занятости. Четыре stress имеют200000 команд. Максимумы на macOS arm64:
CPU user+system {q['maximum_cpu_s']:.6f}s, RSS {q['maximum_rss_mib']:.3f}MiB.
Лимиты5s CPU и256MiB. Windows10/Pentium Gold G5420 не измерены.

В x64 Native Tools Command Prompt for Visual Studio:
  build_windows.bat
  py windows_bench.py --solver solution.exe --tests tests --out windows-results.json --repeat 1

Runner использует один разрешённый CPU и user+kernel time. Это отдельная
независимая проверка протокола/размещения, не официальный интерактор.
Все вложенные тесты теперь наблюдались и пригодны для regression, не holdout.
Прежний release и canonical сохранены. Платформа не использовалась.
Полный отчёт, генератор и диагностика находятся на уровень выше release.
'''
    (release/'README.txt').write_text(note)
    for g in ['final','open15','stress']:
        with (HERE/f'metrics-{g}.csv').open('w') as f:
            fields=['id','strategy','stratum','family','kpi','trench_length_m','final_occupied_length_m','solver_cpu_total_s','solver_peak_rss_mb','source_sha256','test_sha256']
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
            for n in ['baseline',selected]:w.writerows(load('official',g,n).values())
    with zipfile.ZipFile(HERE/'online-patterns-ready.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(release.rglob('*')):
            if p.is_file():z.write(p,'online-patterns-ready/'+str(p.relative_to(release)))

    final_base=load('screen','final','baseline');final=load('screen','final',selected)
    comparison=''.join(f'<tr><td>{LABELS[t]}</td><td>{s["macro"][t]-s["by_stratum"][t]["family_macro_delta"]:.6f}</td><td>{s["macro"][t]:.6f}</td><td>{s["by_stratum"][t]["family_macro_delta"]:+.6f}</td><td>{ci[t][0]:+.6f}…{ci[t][1]:+.6f}</td><td>{ep[t]:+.5f}</td></tr>' for t in LABELS)
    target_rows=''.join(f'<tr><td>{x["id"]}</td><td>{x["legacy_T"]}</td><td>{x["current_T"]}</td><td>{x["candidate_T"]}</td><td class="{x["result"]}">{x["delta_KPI"]:+.6f}</td><td>{"Да" if x["repaired"] else "Нет"}</td></tr>' for x in q['target23'])
    case_rows=''
    input_map={c['id']:c for c in cases('final')}
    for k in sorted(final,key=lambda k:final[k]['kpi']-final_base[k]['kpi']):
        d=final[k]['kpi']-final_base[k]['kpi'];typ='loss' if d<-1e-12 else 'win' if d>1e-12 else 'tie'
        case_rows+=f'<tr data-result="{typ}"><td><a href="evaluation/final/{input_map[k]["file"]}">{k}</a></td><td>{LABELS[final[k]["stratum"]]}</td><td>{html.escape(final[k]["family"])}</td><td>{final_base[k]["kpi"]:.6f}</td><td>{final[k]["kpi"]:.6f}</td><td class="{typ}">{d:+.6f}</td></tr>'
    sliders=''.join(f'<label>{label}<input class="mix" type="range" min="0" max="100" value="25" data-stratum="{t}" aria-label="{label}"><span class="share">25%</span></label>' for t,label in LABELS.items())
    doc=f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Pipes — online и паттерны</title>
<style>body{{margin:0;background:#f3f5f7;color:#192c3b;font:16px/1.55 system-ui,sans-serif}}main{{max-width:1160px;margin:auto;padding:34px 22px}}h1{{font-size:38px;line-height:1.15}}h2{{margin-top:34px;font-size:24px}}a{{color:#12639c}}section,.card{{background:white;border:1px solid #dbe3e9;border-radius:12px;padding:20px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.card strong{{display:block;font-size:25px}}.muted{{color:#556c7c}}.notice{{background:#fff3d5;border-left:4px solid #b78321;padding:17px 20px}}.win{{color:#14714d}}.loss{{color:#a33e28}}.scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{padding:9px;border-bottom:1px solid #e1e7eb;text-align:left}}th{{background:#edf2f5}}.eyebrow{{font-size:12px;letter-spacing:.1em;color:#596d7f}}code{{overflow-wrap:anywhere;font-size:12px}}.mixes{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}label input{{display:block;width:90%}}select{{padding:7px;font:inherit}}summary{{cursor:pointer;font-weight:600;margin:15px 0}}@media(max-width:760px){{main{{padding:20px 12px}}h1{{font-size:29px}}.cards,.mixes{{grid-template-columns:1fr 1fr}}td,th{{padding:6px}}}}</style></head><body><main>
<div class="eyebrow">PIPES · ЛОКАЛЬНЫЙ РАУНД · 20 ОКТЯБРЯ 2026</div><h1>Стабильнее выбирать участок.<br>Проверять перенос на другие паттерны.</h1>
<p class="notice"><b>Небольшой шаг, с оставшимися регрессиями.</b> Зафиксированный кандидат прошёл заранее заданные final-критерии. Средняя прибавка положительна на calibration96 и final192, но описательный интервал неопределённости пересекает ноль. Универсальное улучшение и официальный закрытый счёт не установлены.</p>
<div class="cards"><div class="card">Средняя ΔKPI / final192<strong class="win">{s['mean_delta']:+.6f}</strong>37 побед · 122 равенства · 33 потери</div><div class="card">Open15 / 32.1<strong>{pub[selected]:.5f}</strong>{q['delta_public']:+.5f} к текущему online</div><div class="card">Прежние 23 потери<strong>6 улучшены</strong>2 устранены · 1 ухудшена · 16 равны</div><div class="card">CPU максимум<strong>{q['maximum_cpu_s']:.3f} с</strong>{q['maximum_rss_mib']:.2f}MiB · macOS arm64</div></div>
<p><a href="release/solution.cpp">Исходник</a> · <a href="online-patterns-ready.zip">Пакет Windows + 307 тестов</a> · <a href="release/README.txt">Инструкция</a> · <a href="outcome.json">Результаты и hashes</a> · <a href="../pipes_online_core_20261020/release/solution.cpp">Предыдущий выпуск</a></p>
<h2>Что исправлено и что осталось</h2><section><p>Все 23 первые расхождения начинались в DP-выборе свободного участка: 18 строгих перестановок по оценке, 4 равенства и 1 решение при почти пустой истории спроса. В последнем случае окно до решения содержит 255 удалений и всего один запрос. Однако исправление только первого действия помогает лишь 7 случаям и ухудшает 4: нельзя приписывать весь итог одной ранней разнице.</p><p>Новый первичный DP-проход начинает с прежнего выбора <code>legacyBest</code> и меняет его только при <code>score + 1e-9 &lt; currentScore</code>. Равные оценки модели больше не задают новое предпочтение адреса. Позднейшие lifetime correction и MC сохранены; гарантий меньшего рытья это не даёт. Новых структур памяти и чтения будущих команд нет.</p><p>На прежнем final128 относительно старого online осталось <b>22 проигрыша вместо 23</b>: две старые потери исчезли, одна новая появилась. Сохранено <b>{100*q['original_DEV_gain_retained']:.2f}%</b> прежней средней прибавки. Это DEV, а не новое независимое подтверждение.</p><p><a href="diagnostics/REPORT.txt">Подробная причинная диагностика</a> · <a href="diagnostics/all23.csv">Состояния и абляции</a> · <a href="target23-results.csv">Все 23 результата кандидата</a> · <a href="strict_source_audit.json">Независимая проверка исходника</a></p>
<details><summary>Все 23 прежние потери, T в метрах</summary><div class="scroll"><table><thead><tr><th>Вход</th><th>Старый online</th><th>Текущий</th><th>Кандидат</th><th>ΔKPI к текущему</th><th>Потеря устранена</th></tr></thead><tbody>{target_rows}</tbody></table></div></details></section>
<h2>192 финальных входа, после фиксации кода</h2><section><p>Средний KPI: <b>0.907398581 → {s['mean']:.9f}</b>. Худшая ΔKPI <b>{s['worst'][0]['delta']:.6f}</b>; каждый вход сохранил не менее <b>{100*s['min_retention']:.2f}%</b> текущего KPI. На этих же новых входах преимущество над старым online до предыдущего улучшения составляет <b>{q['relative_to_legacy']['mean_delta']:+.6f}</b>.</p>
<div class="scroll"><table><thead><tr><th>Группа</th><th>Текущий macro KPI</th><th>Кандидат</th><th>ΔKPI</th><th>Описательный 95% интервал</th><th>Δ общего счёта, чистая группа</th></tr></thead><tbody>{comparison}</tbody></table></div>
<p>При равном весе групп ΔKPI <b>{q['equal_stratum_KPI_delta']:+.6f}</b>, интервал по механизмам <b>[{ci['equal_four_strata'][0]:+.6f}; {ci['equal_four_strata'][1]:+.6f}]</b>. Знак прибавки пока статистически неубедителен. Bootstrap группирует 12 механизмов совместно с их matched controls, отдельно 6 IID profiles и 8 prefix suffix families; это описание генератора, а не интервал официальных закрытых.</p><p class="muted">В исходном evaluator поле family у обычных входов содержало также variant: его первоначальные интервалы были по вариантам. Здесь приведена дополнительная группировка по механизму. Точечные оценки и правило выбора не изменены; этот пересчёт не использовался для настройки.</p></section>
<h2>Общий счёт при неизвестной смеси закрытых тестов</h2><section><p>Известные веса: 32.1 открытых + 84 закрытых. Считаем <code>Open15 + 84 × Σ(доля группы × её macro KPI)</code>. При равной смеси прибавка <b>{q['total_score_equal_mix_delta']:+.5f}</b> условного балла; во всём диапазоне смесей <b>{min(ep.values()):+.5f}…{max(ep.values()):+.5f}</b>. На чисто устойчивых паттернах есть небольшая потеря. Частоты групп в закрытых неизвестны.</p>
<div class="mixes">{sliders}</div><p id="mix-output" aria-live="polite"></p><p class="muted">Доли нормируются к 100%. Это анализ чувствительности по синтетике; он не предсказывает конкурсный результат.</p></section>
<h2>Генераторы: какие паттерны и как не переобучиться на них</h2><section><p>Анализ команд Open15 обнаруживает длинные серии одинаковых размеров, разную концентрацию длин и режимы удалений. Максимальная серия в последовательности вставок достигает 5061; этот счётчик игнорирует удаления между вставками. Медиана завершённых времён жизни по тестам меняется от 2 до 4358 команд; ещё живые трубы в неё не входят. Наличие таких структур в открытых не доказывает конкретные структуры закрытых.</p><p>Созданы <b>96 calibration + 192 final + 4 stress</b>. Четыре равные группы: устойчивые мотивы/грамматики/зависимые lifetimes; их прерывание, инверсия и возврат; контрольные потоки; публичные префиксы с новыми продолжениями. В final другие длины мотивов, периоды, диапазоны lifetimes, композиции и расписания смен.</p><p>24 final-контроля сохраняют ровно histogram длин и знаки команд своих patterned пар, но меняют порядок длин и PID удалений. Это контроль совместной роли порядка и lifetimes, а не полностью IID поток. На этих 24 парах новая правка имеет ΔKPI {q['matched_controls']['mean_pattern_delta']:+.6f} на patterned стороне и {q['matched_controls']['mean_control_delta']:+.6f} на перемешанной: её нельзя выдавать за улучшение распознавания паттернов.</p><p>Генератор был отделён от кандидатов и результатов; отбора входов по KPI не было. Все 292 входа валидны, точных совпадений с проверенными прежними hashes нет. Публичные префиксы намеренно общие; 158/192 final имеют F/peak≥0.9. Низкая достижимая загрузка не является основой всего набора.</p><p><a href="evaluation/design.json">Дизайн</a> · <a href="evaluation/generate.py">Генератор</a> · <a href="evaluation/open15-structure.json">Структура Open15</a> · <a href="evaluation/disk-validation.json">Проверка входов</a></p></section>
<h2>Что отклонено и как выбирали</h2><section><p>Проверены пять причинных гипотез, шесть вариантов исходника: stability gate, смесь окон спроса, минимальная поддержка спроса, сохранение выбора при равенстве и условный спрос по переходам размеров; последняя версия уточняет семантику равенств. Пороговой сетки не было. Stability gate и смесь окон дали крупные DEV-регрессии. Условная модель с проверкой предсказаний до наблюдения ответа не улучшила общий DEV KPI; добавлять её в выпуск оснований пока нет.</p><p><b>Отклонение от первоначального плана открыто зафиксировано.</b> Ни один кандидат не прошёл исходное DEV-условие mean≥0. До любых свежих результатов допуск расширили на неотрицательные сценарии общего счёта Open15+84×macro с сохранением ≥95% прежней прибавки и неотрицательной средней Δ на 23 потерях. Критерии calibration/final не смягчались. Два варианта прошли на calibration; один из них отклонён из-за отрицательного среднего прироста. Выбор второго зафиксирован до final.</p><p>Final проверял положительную среднюю прибавку и общий счёт, положительный средний эффект на двух patterned группах, нижний предел −0.002 на группу, retention≥95% каждого входа и худший сценарий общего счёта≥−0.05. Все проверки пройдены. Исходник после final не менялся. Предыдущий выпуск сохранён.</p><p><a href="experiment.json">Исходный план</a> · <a href="calibration-freeze.json">Допуск до calibration</a> · <a href="selection-freeze.json">Фиксация до final</a> · <a href="quality-outcome.json">Критерии и неопределённость</a></p></section>
<h2>Протокол, ресурсы и границы</h2><section><p><b>518 официальных интерактивных прогонов</b>, из них <b>307 выбранного исходника</b>: 96+192 новых, Open15 и четыре stress по 200000 команд. Все ответы валидны; T совпал с отдельной полной проверкой занятости. Пиковый CPU выбранного кода {q['maximum_cpu_s']:.6f}с, RSS {q['maximum_rss_mib']:.3f}MiB на macOS arm64. Один solver worker, CPU=user+system. Лимиты конкурса5с/256MiB.</p><p><b>Windows10 / Pentium Gold G5420 не измерены.</b> В пакете сборка MSVC и runner с affinity на один CPU, измерением user+kernel time и проверкой размещений. Заполнять память без доказанной пользы не стали: эта правка не добавляет хранилищ. CPU всё ещё может зависеть от изменившейся траектории.</p><p>Следующее обоснованное направление — совместно предсказывать последовательность размеров и удаления по возрасту/контексту, оценивать прогноз до наблюдения ответа, быстро снижать доверие после смены режима. Нужны отдельные новые композиции и целые траектории: хорошее предсказание следующей длины само по себе не гарантирует хороший layout. Это направление работы, не уже реализованный выигрыш.</p><p class="muted">MC продолжает моделировать прежний gap policy; lower predicted DP loss не гарантирует lower actual trench. Final теперь наблюдался и далее является regression corpus. Платформа и старые frozen/canonical источники не изменены. Отчёт проверен статически; визуальная проверка браузером недоступна в этой среде.</p><p><code>SHA256 {q['source_sha256']}</code></p></section>
<h2>Все финальные результаты</h2><p><label>Показать <select id="filter"><option value="all">Все192</option><option value="loss">33 проигрыша</option><option value="win">37 выигрышей</option><option value="tie">122 равенства</option></select></label> · <span id="count"></span> · <a href="metrics-final.csv">Точные измерения</a></p>
<section class="scroll"><table><thead><tr><th>Вход</th><th>Группа</th><th>Механизм</th><th>Текущий KPI</th><th>Кандидат KPI</th><th>ΔKPI</th></tr></thead><tbody>{case_rows}</tbody></table></section>
<script>const endpoints={json.dumps(ep)};const sliders=[...document.querySelectorAll('.mix')];function mix(){{const sum=sliders.reduce((s,e)=>s+Number(e.value),0);let d=0;for(const e of sliders){{const w=sum?Number(e.value)/sum:.25;d+=w*endpoints[e.dataset.stratum];e.parentElement.querySelector('.share').textContent=(100*w).toFixed(1)+'%';}}document.getElementById('mix-output').textContent='Условная Δ общего счёта: '+(d>=0?'+':'')+d.toFixed(5);}}sliders.forEach(e=>e.addEventListener('input',mix));mix();const filter=document.getElementById('filter');function apply(){{let count=0;document.querySelectorAll('[data-result]').forEach(r=>{{r.hidden=filter.value!=='all'&&filter.value!==r.dataset.result;if(!r.hidden)count++;}});document.getElementById('count').textContent='Строк: '+count;}}filter.addEventListener('change',apply);apply();</script></main></body></html>'''
    (HERE/'report.html').write_text(doc)
    print(json.dumps({k:q[k] for k in ['confirmation_passed','official_runs','selected_official_runs','maximum_cpu_s','maximum_rss_mib','source_sha256']},indent=2))

if __name__=='__main__':main()
