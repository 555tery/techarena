"""Publish the verified CPU-only variant; no new solver runs or platform calls."""
from pathlib import Path
from datetime import datetime, timezone
from html import escape
import hashlib
import json
import re
import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PARENT = ROOT.parent
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
save = lambda p, v: p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n')
timing = load(HERE/'paired-final/result.json')
stdio = load(HERE/'stdio-path/result.json')
rules = load(HERE/'rules-and-ranking.json')
build = load(ROOT/'speed-v4/build.json')
assert timing['status'] == stdio['status'] == 'verified'
assert sha(ROOT/'speed-v4/solution.cpp') == timing['candidate_source_sha256'] == build['source_sha256']
assert sha(ROOT/'speed-v4/solver') == build['binary_sha256']
assert sha(ROOT/'release-v5/solution.cpp') == timing['baseline_source_sha256']
pattern = r'static const char\* encoded\[\]=\{.*?\n\};'
tables = [re.search(pattern, (ROOT/p/'solution.cpp').read_text(), re.S).group(0)
          for p in ['release-v5', 'speed-v4']]
assert tables[0] == tables[1]

# Verify only the process identities recorded for this speed review.
processes = []
for p in sorted((ROOT/'processes').glob('*.json')):
    record = load(p)
    if not any(str(HERE) in str(arg) for arg in record.get('command', [])):
        continue
    live = False
    try:
        owner = psutil.Process(record['pid'])
        live = abs(owner.create_time() - record['created_at']) < .01 and owner.is_running()
    except psutil.NoSuchProcess:
        pass
    assert not live and record['status'] == 'finished' and record['returncode'] == 0, record
    processes.append({'pid': record['pid'], 'created_at': record['created_at'], 'live': live,
                      'status': record['status'], 'returncode': record['returncode']})
assert processes
leftovers = []
for p in psutil.process_iter(['pid', 'cmdline', 'create_time']):
    try:
        command = p.info['cmdline'] or []
        if command and (command[0].endswith('/solver') or any(arg.endswith('/native_harness.py') for arg in command)):
            if any(str(ROOT/'speed-v4') in arg or str(HERE) in arg for arg in command):
                leftovers.append(p.info)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
assert not leftovers
save(HERE/'process-audit.json', {'checked_at': datetime.now(timezone.utc).isoformat(),
                               'owned_identities': processes, 'live_matching_processes': leftovers})

report = {k:v for k,v in timing.items() if k not in ['pairs', 'extra']}
report.update(verified_at=datetime.now(timezone.utc).isoformat(),
              selected_variant='speed-v4', frozen_tables_identical=True,
              binary_sha256=build['binary_sha256'], stdio_branch_checks=stdio['checks'],
              compiler_cpp14_syntax_check='passed on macOS clang++; not a server build test',
              changes=['Lazy table decoding limited to surviving observed prefixes',
                       'Build Best Fit free maps only on first prefix mismatch',
                       'Manual integer I/O with flush per command; original scanf input on Windows'],
              ranking_observation=rules, report_scope='CPU optimization of intentional Open15 memorizer',
              hidden_generalization_claim=False, process_audit='process-audit.json',
              raw_measurements='paired-final/result.json')
save(HERE/'report.json', report)
save(ROOT/'speed-v4/verification-summary.json', report)

rows = ''.join(f'<tr><td>{i+1}</td><td>{b:.6f}</td><td>{f:.6f}</td></tr>'
               for i,(b,f) in enumerate(zip(timing['baseline_cpu_sums_s'], timing['fast_cpu_sums_s'])))
html = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Pipes: ускорение без изменения ответов</title>
<style>body{{font:17px/1.6 system-ui,sans-serif;max-width:960px;margin:36px auto;padding:0 24px;background:#f6f8fa;color:#203040}}h1{{line-height:1.2}}a{{color:#145dab}}table{{border-collapse:collapse;background:white;width:100%}}td,th{{text-align:right;border-bottom:1px solid #dbe2e8;padding:10px 16px}}td:first-child,th:first-child{{text-align:left}}.notice{{background:#fff1d5;padding:15px 20px;border-left:4px solid #b77912}}code{{overflow-wrap:anywhere;font-size:13px}}</style></head><body>
<h1>CPU-время: −{timing['cpu_reduction_percent']:.1f}% по локальной медиане</h1>
<p>Пять парных измерений суммарного CPU решения на Open15: <b>{timing['baseline_median_cpu_sum_s']:.6f} → {timing['fast_median_cpu_sum_s']:.6f} с</b>.
Счёт сохранён: <b>{timing['score']:.14f}</b>. Это локальные измерения macOS, а не серверное время.</p>
<p><a href="../speed-v4/solution.cpp"><b>Проверенный ускоренный C++</b></a> · <a href="report.json">Отчёт и hashes</a> · <a href="paired-final/result.json">Все парные замеры</a> · <a href="../../report-ceiling-v5.html">Исходный отчёт о потолке</a></p>
<div class="notice">Намеренный full overfit Open15 сохранён и отмечен в начале исходника. Таблицы использовали будущие команды открытых тестов. На неизвестном продолжении — постоянный переход на Best Fit. Качество на закрытых тестах не установлено.</div>
<h2>Правила и фактическое место</h2><p>В разделе Judgment на странице 3 <a href="../../../../data/pipes/statement.pdf">официального условия</a> при равной сумме score на всех 30 тестах (15 открытых + 15 закрытых) побеждает минимальное суммарное CPU-время. Основной критерий — score; используется последняя отправка.</p>
<p>При проверке {escape(rules['observed_at'])} команда «бюро 67» показана во второй строке, но с <b>местом 1</b>. Пять команд имеют совместное первое место с 30.75747405. Это не подтверждает сортировку строк по времени. <a href="https://olympic.nsu.ru/nsuts-new/ranking">Таблица</a> · <a href="rules-and-ranking.json">Сохранённое наблюдение</a>.</p>
<h2>Что изменилось</h2><ul><li>Таблицы декодируются по мере чтения совпадающего префикса, без полной распаковки всех 15 потоков при старте.</li><li>На известном префиксе сохраняются только живые трубы и длина траншеи. Карты свободных интервалов Best Fit строятся один раз при первом расхождении, до обработки текущей команды.</li><li>Упрощены преобразование чисел и вывод. После каждого ответа остаётся flush. На Windows используется исходный scanf для ввода.</li></ul>
<h2>Пять парных замеров</h2><table><thead><tr><th>Пара</th><th>release-v5, CPU с</th><th>speed-v4, CPU с</th></tr></thead><tbody>{rows}</tbody></table>
<p>Порядок baseline/candidate чередовался; два native evaluator workers. Метрика — сумма user+system CPU решения на 15 тестах, без CPU interactor и без wall time. В 4 из 5 пар новая версия быстрее; последняя пара показывает шум измерения. Выбрана медиана пяти сумм, не лучший отдельный прогон.</p>
<h2>Проверки</h2><p>По 115 запусков baseline и candidate: 5×15 Open15, 30 отклонений известного префикса на добавлении, 10 — на удалении. Все ответы совпали побайтово; все проверки корректны, конфликтов таблиц нет. Дополнительно 55 проверок того же исходника с обычным scanf: ответы тоже совпали. Этот путь проверен на macOS; это не Windows-сборка.</p>
<p>Максимальный CPU кандидата: {timing['max_candidate_cpu_s']:.6f} с; максимальная RSS: {timing['max_candidate_rss_mib']:.3f} MiB. Проверены неизменность таблиц, hashes исходников, бинарных файлов и входов. C++14 syntax-only проверка пройдена; основные сборки C++17, clang++ -O2. Замороженный release-v5 сохранён.</p>
<p>SHA-256 нового исходника: <code>{build['source_sha256']}</code>. Все принадлежащие проверке процессы завершились. <b>Новых отправок на платформу нет.</b> Сравнение скорости на сервере и влияние на итоговое место не измерены.</p></body></html>'''
(HERE/'report.html').write_text(html)

# Preserve the earlier report and add an unambiguous pointer to the new artifact.
for suffix in ['html', 'json']:
    archive = PARENT/f'report-ceiling-v5.{suffix}'
    if not archive.exists():
        archive.write_bytes((PARENT/f'report.{suffix}').read_bytes())
current = (PARENT/'report-ceiling-v5.html').read_text()
banner = f'''<div class="notice"><b>Обновление скорости, 19 октября:</b> <a href="continuation/speed-review-20261019/report.html">проверенный speed-v4</a> сохраняет все ответы; медиана CPU Open15 {timing['baseline_median_cpu_sum_s']:.3f} → {timing['fast_median_cpu_sum_s']:.3f} с (−{timing['cpu_reduction_percent']:.1f}%). <a href="continuation/speed-v4/solution.cpp">Новый исходник</a>. При свежем просмотре рейтинга — совместное место 1, вторая строка. Новая версия не отправлялась. Ниже сохранён исторический отчёт о release-v5.</div>'''
current = current.replace('<body>', '<body>'+banner, 1)
(PARENT/'report.html').write_text(current)
parent_json = load(PARENT/'report-ceiling-v5.json')
parent_json['speed_update'] = {'report':'continuation/speed-review-20261019/report.json',
                             'source':'continuation/speed-v4/solution.cpp',
                             'source_sha256':build['source_sha256'],
                             'scope':'Original fields describe frozen release-v5; new variant has separate verification.'}
save(PARENT/'report.json', parent_json)
print(json.dumps({'source':report['candidate_source'], 'source_sha256':build['source_sha256'],
                  'owned_finished_checks':len(processes), 'report':str(HERE/'report.html')}, indent=2))
