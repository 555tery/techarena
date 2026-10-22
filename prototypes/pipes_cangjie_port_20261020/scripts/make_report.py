#!/usr/bin/env python3
"""Summarize frozen paired runs; package sources, inputs, and Windows checker."""
import hashlib
import html
import json
from pathlib import Path
import shutil
import statistics
import zipfile

BASE = Path(__file__).resolve().parents[1]
RELEASE = BASE / 'release'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    data = json.loads((BASE/'official/results.json').read_text())
    cases = data['cases']
    assert len(cases) == 339 and len({x['id'] for x in cases}) == 339
    assert all(x['answers_equal'] and x['kpi_equal'] for x in cases)
    assert all(x[k]['status'] == 'ok' for x in cases for k in ['cpp','cj'])
    assert data['source_manifest']['single_file_sha256'] == sha(RELEASE/'solution.cj')
    for name in ['cpp','cj']:
        assert data['binary_sha256'][name] == sha(BASE/'bin'/('solution-'+name))
    groups = {'all339':cases,
              'previous307':[x for x in cases if x['group'] != 'fresh'],
              'fresh32':[x for x in cases if x['group'] == 'fresh']}
    for group in sorted({x['group'] for x in cases}):
        groups[group] = [x for x in cases if x['group'] == group]
    summary = {'paired_cases':len(cases),
        'operations':sum(x['cpp']['operation_count'] for x in cases),
        'equal_response_streams':sum(x['answers_equal'] for x in cases),
        'equal_kpi':sum(x['kpi_equal'] for x in cases),
        'all_within_local_limits':all(x['passed'] for x in cases),
        'limits':{'CPU_seconds':5,'RSS_MiB':256},
        'host':data['host'],'architecture':data['machine'],
        'native_Windows_G5420_validated':False,'hard_CPU_affinity':False,
        'measurement':'sequential official interactive pairs; whole-process user+system CPU, including runtime; os.wait4 peak RSS',
        'runtime_environment':data['runtime_environment'],
        'source_sha256':{'cpp':sha(RELEASE/'solution.cpp'),'cj':sha(RELEASE/'solution.cj')},
        'binary_sha256':data['binary_sha256'],
        'weighted_score_scope':'sum of local test weights, not a measured official closed-test score',
        'fresh_manifest_sha256':sha(BASE/'fresh_tests/manifest.json'),
        'gc_policy':'internal threshold 64 MiB; explicit heavy GC after a command when allocated heap exceeds 96 MiB; no GC environment overrides',
        'groups':{}}
    for name, rows in groups.items():
        g={'cases':len(rows),'operations':sum(x['cpp']['operation_count'] for x in rows)}
        for language in ['cpp','cj']:
            cpu=[x[language]['solver_cpu_total_s'] for x in rows]
            rss=[x[language]['solver_peak_rss_mb'] for x in rows]
            worst_cpu=max(rows,key=lambda x:x[language]['solver_cpu_total_s'])
            worst_rss=max(rows,key=lambda x:x[language]['solver_peak_rss_mb'])
            g[language]={'CPU_total_s':sum(cpu),'CPU_median_s':statistics.median(cpu),
                'CPU_max_s':max(cpu),'CPU_max_case':worst_cpu['id'],
                'peak_RSS_max_MiB':max(rss),'peak_RSS_max_case':worst_rss['id'],
                'mean_KPI':statistics.mean(x[language]['kpi'] for x in rows),
                'weighted_score_unrounded':sum(x[language]['weight']*x[language]['kpi'] for x in rows),
                'limit_violations':[x['id'] for x in rows if not x[language]['within_limits']]}
        g['CPU_sum_ratio_CJ_over_CPP']=g['cj']['CPU_total_s']/g['cpp']['CPU_total_s']
        summary['groups'][name]=g
    repeat_paths=sorted(BASE.glob('timing_repeat_*/results.json'))
    if repeat_paths:
        slowest=max(cases,key=lambda row:row['cj']['solver_cpu_total_s'])
        samples=[{'source':'official', 'record':slowest}]
        for path in repeat_paths:
            repeat_data=json.loads(path.read_text())
            assert repeat_data['binary_sha256']==data['binary_sha256']
            assert len(repeat_data['cases'])==1
            row=repeat_data['cases'][0]
            assert row['id']==slowest['id'] and row['input_sha256']==slowest['input_sha256']
            samples.append({'source':str(path.relative_to(BASE)),'record':row})
        summary['slowest_case_repeats']={'case':slowest['id'],'samples':len(samples),
            'selection':'slowest Cangjie case from the complete339; two additional paired runs',
            'all_equal_and_within_local_limits':all(x['record']['passed'] for x in samples),
            'observations':[{'source':x['source'],
                'cpp_CPU_s':x['record']['cpp']['solver_cpu_total_s'],
                'cj_CPU_s':x['record']['cj']['solver_cpu_total_s'],
                'cpp_RSS_MiB':x['record']['cpp']['solver_peak_rss_mb'],
                'cj_RSS_MiB':x['record']['cj']['solver_peak_rss_mb']} for x in samples]}
    (BASE/'REPORT.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    labels={'all339':'Все 339','previous307':'Прежние 307','fresh32':'Новые 32'}
    lines=['Перенос online-решения Pipes на Cangjie — 20 октября 2026','',
        'Чистый Cangjie 1.2.0, -O2; C++ FFI не используется.',
        f"На 339 тестах совпали все {summary['operations']:,} числовых ответов и KPI.",
        'Проверка: официальный интерактор, полный поток команд и ответов.',
        'Прежний C++ исходник и алгоритмические бюджеты сохранены.',
        'Новые 32 входа заморожены до первого запуска Cangjie solver. Это новые',
        'экземпляры известных механизмов; новый класс генераторов не заявляется.',
        'Паритет порта не означает улучшение обобщаемости исходного алгоритма.','',
        f"Измерения: {data['host']}, {data['machine']}; один solver за раз.",
        'CPU=user+system всего процесса; время ожидания ввода и CPU интерактора',
        'не включены. cjProcessorNum=1; жёсткой affinity на Mac нет.',
        'Windows 10 / Pentium Gold G5420 в этом запуске не измерены.',
        'Пересчёт по частоте CPU не делался; целевой лимит ещё не подтверждён.','']
    for key,label in labels.items():
        g=summary['groups'][key]
        lines.append(label)
        for language in ['cpp','cj']:
            m=g[language]
            lines.append(f"  {language}: max CPU {m['CPU_max_s']:.6f} s; max RSS {m['peak_RSS_max_MiB']:.3f} MiB; sum CPU {m['CPU_total_s']:.6f} s")
        lines.append(f"  CJ/C++ по сумме CPU: {g['CPU_sum_ratio_CJ_over_CPP']:.3f}x")
    if 'slowest_case_repeats' in summary:
        repeat=summary['slowest_case_repeats']
        lines += ['', 'Повторы самого медленного теста: '+repeat['case']]
        for row in repeat['observations']:
            lines.append(f"  {row['source']}: C++ {row['cpp_CPU_s']:.6f} s, Cangjie {row['cj_CPU_s']:.6f} s")
        lines.append('  Ответы и локальные лимиты во всех повторах: '+str(repeat['all_equal_and_within_local_limits']))
    lines += ['',f"Все локальные ограничения 5 s / 256 MiB выполнены: {summary['all_within_local_limits']}.",
        'Open15: '+str(summary['groups']['open15']['cj']['weighted_score_unrounded'])+' / 32.1 у обоих.',
        '', 'Что пришлось изменить при переносе',
        '- Ordered indexes реализованы собственным AVL на массивах с переработкой слотов.',
        '- Rollout копируется независимо, включая вложенные массивы и историю.',
        '- UInt32 PRNG воспроизведён явными масками; tie-break и Float64 порядок сохранены.',
        '- Интерактивный I/O выдаёт и flush-ит один ответ на каждую команду.',
        '- Первый диагностический порт превысил память: 262.844 MiB на final-153.',
        '  Итоговая версия задаёт GC threshold 64 MiB внутри программы и вызывает',
        '  heavy GC после команды, если allocated heap превысил 96 MiB.',
        '  Настройки heap/GC из окружения для итогового прогона не использовались.',
        '', 'Дополнительные проверки',
        '- AVL: 20000 случайных операций с независимым sorted-array oracle, стабильные',
        '  ID узлов, bounds, обход в обе стороны, successor deletion, clone, reuse.',
        '- Модели: независимость deepCopy и вложенных данных, обе стороны gap merge,',
        '  порядок при равных оценках, swap-pop, границы истории 2048 и паттерна 46.',
        '- Fresh32: fragmentation, adjacency, смена deletion policy, пороги MC64/4096,',
        '  geometric46/history2048, DP512, UInt32 wrap; восемь потоков по 200000 команд.',
        '  Названия обозначают цель теста, а не измеренное покрытие ветвей.',
        '', 'Артефакты', 'release/solution.cj — единый исходник для Cangjie1.2.0.',
        'release/solution.cpp — неизменённый C++ эталон.',
        'release/tests — все 339 входов; manifests содержат SHA256.',
        'release/windows_bench.py — нативный парный WinAPI runner, один логический CPU.',
        'release/build_windows.bat — сборка без установки SDK и глобальных изменений.',
        'Windows runner прошёл проверку синтаксиса на Mac; нативное исполнение не проверено.',
        'Проверка на Windows использует независимую occupancy модель, не официальный интерактор.',
        'Официальная версия SDK и параметры сборки на конкурсе остаются неизвестны.',
        'Архив, hashes и локальные ссылки HTML проверены. Визуальный просмотр',
        'HTML недоступен: Local browser use is disabled in Work settings.',
        '', 'C++ SHA256: '+summary['source_sha256']['cpp'],
        'Cangjie SHA256: '+summary['source_sha256']['cj']]
    report='\n'.join(lines)+'\n'
    (BASE/'REPORT.txt').write_text(report)
    rows=''.join('<tr><td>'+labels[k]+'</td>'+''.join(
        f"<td>{summary['groups'][k][lang]['CPU_max_s']:.3f} s</td><td>{summary['groups'][k][lang]['peak_RSS_max_MiB']:.1f} MiB</td>"
        for lang in ['cpp','cj'])+'</tr>' for k in labels)
    open_score=summary['groups']['open15']['cj']['weighted_score_unrounded']
    page=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pipes: Cangjie — проверка переноса</title><style>body{{max-width:1060px;margin:45px auto;padding:0 24px;font:17px/1.55 system-ui;color:#1b2838;background:#f6f8fb}}h1{{font-size:34px;line-height:1.2}}.card{{background:white;border:1px solid #dce3ec;border-radius:14px;padding:24px;margin:24px 0}}.warning{{background:#fff3dc}}table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}td,th{{padding:11px 8px;border-bottom:1px solid #dce3ec;text-align:left}}pre{{white-space:pre-wrap;font:14px/1.55 ui-monospace,monospace}}a{{color:#185abc}}.small{{font-size:14px;color:#53627a}}</style>
<h1>Online-ядро перенесено на Cangjie</h1><p>339 тестов · {summary['operations']:,} ответов · KPI совпадает с C++</p>
<div class="card"><b>Проверка логики</b><p>307 прежних тестов и 32 новые ловушки прошли официальный интерактор. Решения, итоговая траншея и KPI совпадают. Open15 у обеих версий: <b>{open_score:.12f} / 32.1</b>.</p><p>Алгоритмические бюджеты сохранены. Новый поиск или replay не добавлялись.</p></div>
<div class="card"><b>Максимумы на macOS arm64</b><table><tr><th>Набор</th><th>C++ CPU</th><th>C++ RSS</th><th>Cangjie CPU</th><th>Cangjie RSS</th></tr>{rows}</table><p class="small">User+system CPU всего процесса, включая runtime; один solver за раз, cjProcessorNum=1. Максимумы CPU и RSS могут относиться к разным тестам.</p></div>
<div class="card warning"><b>Windows / Pentium G5420 ещё не измерены</b><p>Лимиты конкурса — 5 CPU-секунд и 256 MiB на тест. Замеры Mac не подтверждают прохождение на целевой машине. В комплект включён Windows runner с привязкой процесса к одному логическому CPU.</p></div>
<p><a href="release/solution.cj">Исходник Cangjie</a> · <a href="pipes-cangjie-release.zip">Комплект с 339 тестами</a> · <a href="REPORT.json">Сводные данные</a> · <a href="official/results.json">Все парные измерения</a></p>
<details><summary>Подробности и границы проверки</summary><pre>{html.escape(report)}</pre></details></html>'''
    (BASE/'report.html').write_text(page)
    for file in ['REPORT.txt','REPORT.json']:
        shutil.copyfile(BASE/file,RELEASE/file)
    expected={x['id']:{'input_sha256':x['input_sha256'],
        'normalized_response_sha256':x['cpp']['response_sha256'],
        'KPI':x['cpp']['kpi'],'T':x['cpp']['trench_length_m'],
        'F':x['cpp']['occupied_length_m']} for x in cases}
    (RELEASE/'expected_results.json').write_text(json.dumps(expected,indent=2)+'\n')
    for file in ['windows_bench.py','build_windows.bat','README.txt']:
        assert (RELEASE/file).exists(), file
    # SDK, native Mac binaries and raw traces are deliberately outside this portable package.
    files=[p for p in RELEASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    manifest={p.relative_to(RELEASE).as_posix():sha(p) for p in sorted(files) if p.name != 'package_manifest.json'}
    (RELEASE/'package_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    target=BASE/'pipes-cangjie-release.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(RELEASE.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                z.write(p,'pipes-cangjie/'+p.relative_to(RELEASE).as_posix())
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
    print(json.dumps({'summary':summary,'zip_bytes':target.stat().st_size,'zip_sha256':sha(target)},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
