"""Package the frozen recommendation and measured comparison, without submission."""
import csv
import datetime
import hashlib
import html
import json
import shutil
import zipfile
from pathlib import Path

from analyze import read_records
from evaluate import HERE, ROOT, NAMES, sha, verify_freeze

LABELS = {'online': 'Online', 'full': 'Полный replay + online', 'hybrid': 'Осторожный гибрид'}


def main():
    verify_freeze('final')
    result = json.loads((HERE/'analysis-final.json').read_text())
    calibration = json.loads((HERE/'analysis-calibration.json').read_text())
    production = json.loads((HERE/'production-validation.json').read_text())
    parity = json.loads((HERE/'production-parity.json').read_text())
    selected = result['recommended']
    groups = {g: read_records('official', g) for g in ['calibration', 'final', 'open15', 'stress']}
    expected = {'calibration': 192, 'final': 384, 'open15': 45, 'stress': 9}
    assert all(len(groups[g]) == expected[g] for g in expected)
    all_rows = [r for rows in groups.values() for r in rows]
    chosen_rows = production['records']
    assert len(chosen_rows) == 210 and production['policy'] == selected
    assert parity['exact_stdout_parity'] and parity['n'] == 210
    assert all(r['status'] == 'ok' and r['resources_ok'] for r in chosen_rows)
    release = HERE/'release'
    release.mkdir(exist_ok=True)
    source = HERE/'candidates-fast'/selected/'solution.cpp'
    shutil.copy2(source, release/'solution.cpp')
    shutil.copy2(ROOT/'prototypes/pipes_g5420_cpu_20261020/windows_bench.py', release/'windows_bench.py')
    (release/'build_windows.bat').write_text('@echo off\ncl /nologo /O2 /std:c++17 /EHsc solution.cpp /Fe:solution.exe\nif errorlevel 1 exit /b 1\n', encoding='ascii')
    for g in ['stress', 'final']:
        dest = release/'tests'/g
        dest.mkdir(parents=True, exist_ok=True)
        manifest = json.loads((HERE/'evaluation'/g/'manifest.json').read_text())
        shutil.copy2(HERE/'evaluation'/g/'manifest.json', dest/'manifest.json')
        for row in manifest['cases']:
            shutil.copy2(HERE/'evaluation'/g/row['file'], dest/row['file'])
    dest = release/'tests/open15'
    dest.mkdir(parents=True, exist_ok=True)
    for i in range(1, 16):
        shutil.copy2(ROOT/f'data/pipes/open/{i}.in', dest/f'{i:02}.in')
    outcome = dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   status='locally_validated_release_native_windows_pending', recommended=selected,
                   frozen_calibration_choice=result['frozen_selection'],
                   confirmation_passed=result['confirmation_passed'],
                   source_sha256=sha(source), binary_sha256=sha(source.with_name('solver')),
                   original_policy_source_sha256=sha(HERE/'candidates'/selected/'solution.cpp'),
                   production_freeze_sha256=sha(HERE/'production-freeze.json'),
                   exact_output_parity_inputs=parity['n'], exact_output_parity_commands=parity['commands'],
                   candidates_freeze_sha256=sha(HERE/'candidates-freeze.json'),
                   selection_freeze_sha256=sha(HERE/'selection-freeze.json'),
                   open15_scores=result['open15_score'],
                   official_runs=len(all_rows)+len(chosen_rows), comparison_official_runs=len(all_rows),
                   production_official_runs=len(chosen_rows), selected_official_runs=len(chosen_rows),
                   selected_maximum_cpu_s=max(r['solver_cpu_total_s'] for r in chosen_rows),
                   selected_maximum_rss_mib=max(r['solver_peak_rss_mb'] for r in chosen_rows),
                   all_candidates_valid=all(r['status']=='ok' for r in all_rows),
                   original_candidates_within_local_limits=all(r['resources_ok'] for r in all_rows),
                   production_within_local_limits=all(r['resources_ok'] for r in chosen_rows),
                   native_windows_tested=False, target_g5420_tested=False,
                   platform_actions=0, canonical_changed=False,
                   scope='Best recommended of three preregistered policies on synthetic tests; not a hidden-test guarantee.')
    (HERE/'outcome.json').write_text(json.dumps(outcome, indent=2)+'\n')
    (release/'manifest.json').write_text(json.dumps(outcome, indent=2)+'\n')
    for name, rows in groups.items():
        with (HERE/f'metrics-{name}.csv').open('w') as f:
            fields = ['id','strategy','stratum','family','kpi','trench_length_m','final_occupied_length_m',
                      'solver_cpu_total_s','solver_peak_rss_mb','status','resources_ok','test_sha256','source_sha256']
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
    readme = f'''# Вариант для закрытой части — {LABELS[selected]}

Подготовлен по локальному сравнению трёх вариантов с одним ядром trial22.
Выбран после calibration64, проверен на final128 без дальнейшей настройки политики.
В финальной сборке ускорен только ввод/вывод. На 210 входах ({parity['commands']} команд)
stdout побайтно совпал с выбранной замороженной политикой; затем повторены 210 официальных интерактивных проверок.
Исходник: solution.cpp, SHA256 `{sha(source)}`.
Open15: **{result['open15_score'][selected]:.14f}**.

## Сборка и проверка на целевой машине

Откройте x64 Native Tools Command Prompt for VS 2022 в этой папке:

```
build_windows.bat
py windows_bench.py --solver solution.exe --tests tests --out windows-results.json --repeat 1
```

Runner использует только Python standard library, закрепляет solver на одном разрешённом логическом CPU,
считает user+kernel CPU процесса и измеряет пиковую память. Каждый запрос отправляется отдельно;
размещения и удаления проверяются независимо. Это не официальный C++ interactor.

В комплекте Open15, final128 и три теста по 200000 команд. Все эти тесты уже использованы,
поэтому после дальнейшей настройки они будут регрессионными, а не независимым holdout.

На локальном macOS arm64 выполнено {len(chosen_rows)} официальных интерактивных запусков выбранного кода:
максимум {outcome['selected_maximum_cpu_s']:.6f} с CPU и {outcome['selected_maximum_rss_mib']:.3f} MiB RSS.
Нативная сборка MSVC и замеры Windows10/Pentium Gold G5420 пока не выполнены.
Лимиты конкурса: менее 5 с CPU и 256 MiB; 16 GB RAM машины не меняют лимит процесса.

Платформа не использовалась. Этот пакет не заменяет последнюю отправку автоматически.
Синтетический набор проверяет перенос и известные классы рисков, но не является распределением закрытых тестов.
Полное сравнение, выбор и hashes: ../report.html, ../analysis-final.json, ../selection-freeze.json.
'''
    (release/'README.md').write_text(readme)
    with zipfile.ZipFile(HERE/'closed-ready.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(release.rglob('*')):
            if path.is_file():
                z.write(path, Path('closed-ready')/path.relative_to(release))
    stats = result['statistics']
    cells = []
    for name in NAMES:
        s = stats[name]
        p = s['paired_by_stratum']['prefix']
        cells.append(f'<tr><td>{LABELS[name]}</td><td>{result["open15_score"][name]:.8f}</td>'
                     f'<td>{s["stratum_macro"]["ordinary"]:.6f}</td><td>{s["stratum_macro"]["prefix"]:.6f}</td>'
                     f'<td>{p["wins"]} / {p["ties"]} / {p["losses"]}</td><td>{p["worst_delta"]:+.6f}</td></tr>')
    losses = []
    for name in ['full', 'hybrid']:
        for pair in sorted(stats[name]['pairs'], key=lambda p: p['delta'])[:8]:
            losses.append(f'<tr><td>{LABELS[name]}</td><td>{html.escape(pair["id"])}</td>'
                          f'<td>{html.escape(pair["family"])}</td><td>{pair["online"]:.6f}</td>'
                          f'<td>{pair["candidate"]:.6f}</td><td>{pair["delta"]:+.6f}</td></tr>')
    resource_rows = []
    for name in NAMES:
        rr = [r for r in all_rows if r['strategy']==name]
        resource_rows.append(f'<tr><td>{LABELS[name]}</td><td>{len(rr)}</td>'
                             f'<td>{max(r["solver_cpu_total_s"] for r in rr):.6f}</td>'
                             f'<td>{max(r["solver_peak_rss_mb"] for r in rr):.3f}</td></tr>')
    scenarios = {n: {'open': result['open15_score'][n], 'ordinary': stats[n]['stratum_macro']['ordinary'],
                     'prefix': stats[n]['stratum_macro']['prefix']} for n in NAMES}
    report = f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pipes: online, replay и осторожный гибрид</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;background:#f4f6f8;color:#172433;margin:0}}main{{max-width:1120px;margin:auto;padding:30px 24px 80px}}h1{{line-height:1.15;font-size:34px}}h2{{font-size:23px;margin-top:32px}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{padding:10px 12px;border-bottom:1px solid #dae0e6;text-align:left}}.scroll{{overflow:auto}}.verdict{{padding:18px;border-left:4px solid #21766a;background:#e7f4ef}}.note{{color:#536477}}code{{overflow-wrap:anywhere}}a{{color:#225fa8}}.metric{{font-size:20px}}input{{width:300px;max-width:100%}}small{{color:#536477}}</style><main>
<small>Локальная проверка · 20 октября 2026 · три заранее заданные стратегии</small>
<h1>Подготовка к закрытым тестам</h1>
<p class="verdict"><b>Рекомендован: {LABELS[selected]}.</b> Выбор на 64 тестах: {LABELS[result['frozen_selection']]};
независимая проверка условий принятия: {'пройдена' if result['confirmation_passed'] else 'не пройдена, возврат к online по заранее заданному правилу'}.
Готовы <a href="release/solution.cpp">исходник</a>, <a href="closed-ready.zip">пакет для Windows</a> и <a href="release/README.md">инструкция</a>.</p>
<p>Общий online-core — trial22. Полный replay использует публичные координаты до первого расхождения,
затем продолжает тем же ядром из фактической геометрии. Осторожный гибрид дополнительно требует:
траншея не длиннее online-shadow и размещение на краю свободного промежутка. При отказе replay прекращается навсегда.</p>
<p>При импорте восстанавливаются история команд, lifetime/cohort/run/Fenwick-модели и физические промежутки.
Чужие резервации снимаются, ownership свободных промежутков становится shared, их age задаётся последней эпохой удаления.
Это одинаковая политика продолжения у full и hybrid; состояние закономерно отличается от online с начала.</p>
<h2>Независимые 128 тестов</h2><p>64 обычных потока с сочетаниями режимов и 64 потока с общим публичным префиксом.
Средний KPI ниже — сначала среднее внутри семейства, затем по семействам. Изменения считаются относительно online.</p>
<div class="scroll"><table><tr><th>Вариант</th><th>Open15, баллы</th><th>Обычные, KPI</th><th>Префиксы, KPI</th><th>Префиксы: лучше / равно / хуже</th><th>Худшая ΔKPI</th></tr>{''.join(cells)}</table></div>
<p class="note">Это не настоящие закрытые тесты и не оценка их вероятностного распределения. Префиксы намеренно повторяют открытые данные.
Новые композиции и seeds дают независимую проверку кандидата, но не доказывают универсальное обобщение.</p>
<h2>Что меняет разбалловка</h2><p>Открытая часть имеет сумму весов 32,1, закрытая — 84.
Ниже только анализ чувствительности: условно считаем, что доля <i>p</i> закрытого веса ведёт себя как наши prefix-тесты,
а остальное — как ordinary. Это сценарий, не прогноз финального счёта.</p>
<label>Условная доля prefix: <b id="pvalue">50%</b><br><input id="mix" type="range" min="0" max="100" value="50"></label>
<div id="scenario" class="metric"></div>
<h2>Самые заметные потери относительно online</h2><div class="scroll"><table><tr><th>Вариант</th><th>Тест</th><th>Семейство</th><th>Online KPI</th><th>Вариант KPI</th><th>ΔKPI</th></tr>{''.join(losses)}</table></div>
<h2>Корректность и ресурсы</h2><p>{len(all_rows)} официальных интерактивных запусков исходных трёх вариантов: 192 calibration, 384 final, 45 Open15 и 9 stress.
Все входы проверены, в каждом запуске работает один solver. Бинарники сравниваемых политик после выбора не изменялись.
Таблица ниже относится к исходному вводу/выводу.</p>
<div class="scroll"><table><tr><th>Вариант</th><th>Запуски</th><th>Максимум CPU, с</th><th>Максимум RSS, MiB</th></tr>{''.join(resource_rows)}</table></div>
<p><b>В выпуске ускорен только ввод/вывод.</b> Побайтное совпадение ответов подтверждено на {parity['n']} входах / {parity['commands']} командах.
Дополнительно выполнено {len(chosen_rows)} официальных интерактивных запусков итогового исходника:
максимум <b>{outcome['selected_maximum_cpu_s']:.6f} с CPU / {outcome['selected_maximum_rss_mib']:.3f} MiB RSS</b>.
Это изменение не использовалось для настройки решений по финальным данным.</p>
<p><b>Замеры сделаны на macOS arm64.</b> Windows10/G5420 не измерялся. В комплекте runner для одного CPU с user+kernel time;
нативная проверка остаётся обязательным этапом перед финальной отправкой. Платформа не использовалась.</p>
<h2>Выбор и воспроизводимость</h2><p>До результатов заданы три политики и наборы 64/128. Допуск:
family-macro каждой группы не ниже online более чем на 0,002, ordinary retention каждого теста не ниже 80%,
корректность и лимиты. Среди допущенных выбран минимальный максимальный regret условных сценариев p=0 и p=1 с учётом Open15.
При провале независимого подтверждения предусмотрен возврат к online; никакой последующей подстройки.</p>
<p>SHA256 выбранного исходника: <code>{sha(source)}</code>.</p>
<p><a href="experiment.json">Предварительный план</a> · <a href="selection-freeze.json">Фиксация выбора</a> ·
<a href="analysis-calibration.json">Calibration</a> · <a href="analysis-final.json">Final</a> ·
<a href="metrics-final.csv">Покейсовые результаты</a> · <a href="evaluation/generation-summary.json">Происхождение тестов</a> ·
<a href="candidates/AUDIT.md">Аудит общего ядра</a></p>
<script>const data={json.dumps(scenarios)},names={json.dumps(LABELS, ensure_ascii=False)};
const slider=document.getElementById('mix');function update(){{let p=slider.value/100;document.getElementById('pvalue').textContent=slider.value+'%';document.getElementById('scenario').textContent=Object.entries(data).map(([n,v])=>names[n]+': '+(v.open+84*((1-p)*v.ordinary+p*v.prefix)).toFixed(3)).join(' · ');}}slider.addEventListener('input',update);update();</script></main></html>'''
    (HERE/'report.html').write_text(report)
    print(json.dumps(outcome, indent=2))


if __name__ == '__main__':
    main()
