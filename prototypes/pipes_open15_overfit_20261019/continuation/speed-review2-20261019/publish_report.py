"""Assemble the measured CPU tradeoffs without running or submitting solvers."""
from pathlib import Path
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote
import hashlib
import json
import re
import psutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
PARENT=ROOT.parent
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
checks=load(HERE/'final-checks.json')
assert checks['status']=='verified'
comparisons={name:load(HERE/path/'result.json') for name,path in
             [('speed-v5','direct-io'),('speed-v6','ready-replies'),('speed-v7','compact-replies')]}
direct=load(HERE/'size-tradeoff/result.json')
artifacts={}
for name,result in comparisons.items():
    build=load(ROOT/name/'build.json')
    assert sha(ROOT/name/'solution.cpp')==result['candidate_source_sha256']==build['source_sha256']
    assert sha(ROOT/name/'solver')==build['binary_sha256']
    assert result['status']=='verified' and result['exact_open_answer_parity'] and result['exact_divergence_answer_parity']
    artifacts[name]={'source':str(ROOT/name/'solution.cpp'),'source_sha256':build['source_sha256'],
                     'binary_sha256':build['binary_sha256'],'source_bytes':(ROOT/name/'solution.cpp').stat().st_size}
assert sha(ROOT/'release-v5/solution.cpp')=='7fe4d9430d708021f602ebb2333564ebb8c1e0b0ac5b1355855c4a18155c011f'
assert sha(ROOT/'speed-v4/solution.cpp')=='01e1c58621276de7b04b3dd1138c3549fc85934b3eb422f8f8cedc887d319368'
processes=[]
for p in (ROOT/'processes').glob('*.json'):
    r=load(p)
    if not any(str(HERE) in str(a) for a in r.get('command',[])):continue
    live=False
    try:live=abs(psutil.Process(r['pid']).create_time()-r['created_at'])<.01
    except psutil.NoSuchProcess:pass
    assert not live and r['status']=='finished' and r['returncode']==0,r
    processes.append({'pid':r['pid'],'created_at':r['created_at'],'live':False,'returncode':r['returncode']})
assert processes
leftovers=[]
for p in psutil.process_iter(['pid','cmdline','create_time']):
    try:
        cmd=p.info['cmdline'] or []
        if cmd and (cmd[0].endswith('/solver') or any(a.endswith('/native_harness.py') for a in cmd)):
            if any(str(HERE) in a or any(str(ROOT/n) in a for n in artifacts) for a in cmd):leftovers.append(p.info)
    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
assert not leftovers
save(HERE/'process-audit.json',{'owned_finished':processes,'matching_live_processes':leftovers})
resources={}
for name in ['speed-v5','speed-v6']:
    paths=list((HERE/('direct-io' if name=='speed-v5' else 'ready-replies')).glob('*/fast/verification.json'))
    paths+=[HERE/'boundaries'/name/'fast/verification.json']
    paths+=list((HERE/(name+'-stdio')).glob('*/fast/verification.json'))
    rows=[load(p) for p in paths]
    resources[name]={'max_cpu_s':max(x['max_cpu_s'] for x in rows),'max_rss_mib':max(x['max_rss_mib'] for x in rows)}
first=load(HERE/'direct-io/paired-0/fast/harness/summary.json')['records']
system_fraction=sum(x['solver_cpu_system_s'] for x in first)/sum(x['solver_cpu_total_s'] for x in first)
report={'status':'verified','completed_at':datetime.now(timezone.utc).isoformat(),
        'fastest_measured_variant':'speed-v6','compact_variant':'speed-v5','platform_submissions':0,
        'score':30.75747404826914,'intentional_full_Open15_overfit':True,'hidden_generalization_claim':False,
        'artifacts':artifacts,'comparisons':comparisons,'direct_v5_v6_comparison':direct,
        'final_checks':checks,'resources':resources,'system_cpu_fraction_in_direct_io_sample':system_fraction,
        'total_checks_each_final_variant':274,'owned_finished_jobs':len(processes),
        'limitations':['Local macOS timings; no server CPU measurement or submissions.',
                       'speed-v6 source is about 12 MB; platform source-size acceptance is unverified.',
                       'speed-v6 restores state by replaying the matched prefix at divergence, adding transition work.',
                       'Small differences have visible run-to-run noise. Windows uses tested stdio path, not POSIX direct I/O.',
                       'The 29 boundary cases measure correctness, not a repeated speed comparison.']}
save(HERE/'report.json',report)
for name in ['speed-v5','speed-v6']:
    save(ROOT/name/'verification-summary.json',{'status':'verified','source_sha256':artifacts[name]['source_sha256'],
         'score':report['score'],'checks':274,'report':str(HERE/'report.json'),'platform_submissions':0})
rows=''
for name,r in comparisons.items():
    rows+=f'<tr><td>{name}</td><td>{r["baseline_median_cpu_sum_s"]:.6f}</td><td>{r["candidate_median_cpu_sum_s"]:.6f}</td><td>{r["cpu_reduction_percent"]:.2f}%</td><td>{r["faster_pairs"]}/5</td><td>{artifacts[name]["source_bytes"]/1e6:.2f} МБ</td></tr>'
html=f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pipes: дальнейшее ускорение</title>
<style>body{{font:17px/1.6 system-ui,sans-serif;max-width:1080px;margin:36px auto;padding:0 24px;background:#f5f7f9;color:#203040}}h1{{line-height:1.2}}a{{color:#165db0}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{padding:10px;text-align:right;border-bottom:1px solid #dae1e8}}th:first-child,td:first-child{{text-align:left}}.notice{{background:#fff1d5;border-left:4px solid #b77912;padding:16px}}code{{overflow-wrap:anywhere;font-size:13px}}</style></head><body>
<h1>Ещё около 6% относительно speed-v4</h1>
<p>Самый быстрый по измеренной медиане вариант — <a href="../speed-v6/solution.cpp"><b>speed-v6</b></a>: сумма CPU Open15 <b>0.719228 → 0.676221 с</b>. Пять пар, все пять быстрее. Счёт и ответы сохранены: <b>30.75747404826914</b>.</p>
<div class="notice">Это прежний намеренный full overfit Open15, с явной маркировкой в коде. Текущая работа меняет скорость исполнения, не качество решений. Новых отправок нет; серверное ускорение не измерено.</div>
<h2>Два готовых варианта</h2><p><a href="../speed-v6/solution.cpp">speed-v6, максимум измеренной скорости</a> хранит готовые ответы и создаёт состояние аллокатора только при несовпадении входа. Размер исходника — 11.95 МБ, принятие такого размера платформой не проверено. Переход после длинного совпавшего префикса требует его повторного прохода.</p>
<p><a href="../speed-v5/solution.cpp">speed-v5, компактный вариант</a> сохраняет прежние таблицы и устройство аллокатора, использует прямые read/write и быстрый lookup декодера. Размер {artifacts['speed-v5']['source_bytes']/1e6:.2f} МБ; локально −4.08% CPU, пять из пяти пар быстрее. Это удобный вариант при ограничении размера исходника.</p>
<h2>Парные замеры</h2><table><thead><tr><th>Версия</th><th>Медиана speed-v4, с</th><th>Медиана кандидата, с</th><th>Снижение CPU</th><th>Быстрее в парах</th><th>Размер исходника</th></tr></thead><tbody>{rows}</tbody></table>
<p>Для каждой строки — собственные пять пар с чередованием порядка. Время — сумма user+system CPU самого решения на всех 15 тестах; два evaluator workers. Старые абсолютные времена из другого сеанса не используются как контроль.</p>
<p>Отдельное прямое сравнение v5/v6: медианы {direct['baseline_median_cpu_sum_s']:.6f} → {direct['candidate_median_cpu_sum_s']:.6f} с, но v6 быстрее только в 3 из 5 пар. Небольшой выигрыш шумный; это не обещание точного процента на сервере. Компактное хранение готовых ответов (v7) уменьшило файл до 4.36 МБ, но убедительного преимущества над маленьким v5 не показало.</p>
<h2>Почему следующий выигрыш небольшой</h2><p>В одном полном образце v5 {system_fraction*100:.1f}% CPU приходится на системную часть. Прямой ввод-вывод убирает промежуточные операции stdio, однако сохраняет интерактивный обмен: сначала прочитать текущую команду, затем сразу отправить её ответ. Выдачи ответов на ещё не прочитанные команды нет. Поэтому дальнейшее облегчение арифметики затрагивает лишь небольшую долю CPU.</p>
<h2>Проверка поведения</h2><p>Для каждой из двух готовых версий: 115 основных запусков, ещё 75 в прямом сравнении, 29 новых граничных входов и 55 проверок пути stdio — всего 274. Все корректны, ответы совпадают с speed-v4. Новые границы: продолжение после полного конца известных потоков, добавление или удаление как первое расхождение, несовпадение уже первой команды. Путь stdio собран как C++14 на macOS; полноценная Windows-сборка не проверялась.</p>
<p>Максимумы по основным, граничным и stdio-проверкам: v5 CPU {resources['speed-v5']['max_cpu_s']:.6f} с / RSS {resources['speed-v5']['max_rss_mib']:.3f} MiB; v6 CPU {resources['speed-v6']['max_cpu_s']:.6f} с / RSS {resources['speed-v6']['max_rss_mib']:.3f} MiB. Frozen release-v5 и speed-v4 не изменены. Все принадлежащие работе процессы завершены.</p>
<p><a href="report.json">Полный отчёт, hashes и все результаты</a> · <a href="ready-replies/result.json">Замеры v6</a> · <a href="direct-io/result.json">Замеры v5</a> · <a href="final-checks.json">Граничные и stdio-проверки</a> · <a href="../speed-review-20261019/report.html">Предыдущая оптимизация и правила тайбрейка</a></p>
<p>SHA-256 v6: <code>{artifacts['speed-v6']['source_sha256']}</code><br>SHA-256 v5: <code>{artifacts['speed-v5']['source_sha256']}</code></p></body></html>'''
(HERE/'report.html').write_text(html)
for suffix in ['html','json']:
    archived=PARENT/f'report-speed-v4.{suffix}'
    assert not archived.exists()
    archived.write_bytes((PARENT/f'report.{suffix}').read_bytes())
current=(PARENT/'report.html').read_text()
banner='<div class="notice"><b>Дальнейшее ускорение, 19 октября:</b> <a href="continuation/speed-review2-20261019/report.html">сравнение трёх вариантов</a>. <a href="continuation/speed-v6/solution.cpp">speed-v6</a> — около −6% CPU против v4, исходник 11.95 МБ; <a href="continuation/speed-v5/solution.cpp">компактный v5</a> — около −4%. Счёт и ответы сохранены. Новых отправок нет; серверное время не измерено. Ниже — исторический отчёт о потолке.</div>'
current=re.sub(r'(?<=<body>)<div class="notice">.*?</div>',lambda m:banner,current,count=1,flags=re.S)
(PARENT/'report.html').write_text(current)
parent=load(PARENT/'report.json')
parent['speed_update']={'report':'continuation/speed-review2-20261019/report.json',
                      'fastest_measured':'continuation/speed-v6/solution.cpp','compact':'continuation/speed-v5/solution.cpp',
                      'scope':'Original fields describe frozen release-v5; speed artifacts have separate verification.'}
save(PARENT/'report.json',parent)
class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        self.urls += [v for k,v in attrs if k in ('href','src')]
for path in [HERE/'report.html',PARENT/'report.html']:
    parser=Links();parser.feed(path.read_text())
    for url in parser.urls:
        x=urlparse(url)
        if not x.scheme and x.path:assert (path.parent/unquote(x.path)).resolve().exists(),url
print(json.dumps({'report':str(HERE/'report.html'),'source_hashes':artifacts,'owned_jobs_finished':len(processes),
                  'resources':resources},indent=2))
