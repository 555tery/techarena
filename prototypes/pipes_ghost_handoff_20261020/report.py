"""Frozen outcome report, without selecting on fresh scores."""
import csv,hashlib,html,json,re,zipfile
from fractions import Fraction
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def read(path):return json.loads((HERE/path).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def summary(pairs):
    ds=[r['delta'] for r in pairs]
    return {'count':len(ds),'wins':sum(d>1e-12 for d in ds),'ties':sum(abs(d)<=1e-12 for d in ds),'losses':sum(d<-1e-12 for d in ds),
            'mean_delta':sum(ds)/len(ds) if ds else 0,'worst_delta':min(ds,default=0),'best_delta':max(ds,default=0)}
def main():
    freeze=read('freeze.json');name=freeze['candidate'];b=read(name+'/build.json')
    assert sha(HERE/name/'solution.cpp')==freeze['source_sha256']==b['source_sha256']
    assert sha(HERE/name/'solver')==freeze['binary_sha256']==b['binary_sha256']
    known=read(f'screen-known-{name}.json');fresh=read(f'official-fresh-{name}.json')
    early=read(f'screen-early-diagnostics-{name}.json');early_official=read(f'official-early-diagnostics-{name}.json')
    controls={'d11-cap-pid1','d11-cap-pid2'}
    newpairs=[r for r in fresh['pairs'] if r['id'] not in controls];controlpairs=[r for r in fresh['pairs'] if r['id'] in controls]
    assert len(newpairs)==46 and len(controlpairs)==2
    public=read(f'official-open15-{name}.json');stress=read(f'official-stress-{name}.json');directed=read(f'official-known-{name}.json')
    official=[r for group in [public,stress,fresh,directed,early_official] for r in group['records'] if r['strategy']=='candidate']
    assert all(r['binary_sha256']==b['binary_sha256'] for r in official)
    score=Fraction(0);weights=[.1,1,1,1,1,1,1,1,1,1,1,4,4,4,10]
    for row,w in zip(public['records'],weights):
        assert row['trench_length_m']==row['minimum_trench_lower_bound_m']
        score+=Fraction(str(w))*row['final_occupied_length_m']/row['trench_length_m']
    physical=[p for p in known['pairs'] if p['id']!='prior24-B23']
    gate=not summary(known['pairs'])['losses'] and not summary(fresh['pairs'])['losses'] and not summary(early['pairs'])['losses']
    report={'frozen_candidate':name,'selected':name if gate else None,
      'status':'finite directed gate passed' if gate else 'not promoted; independent no-loss gate failed',
      'source_sha256':b['source_sha256'],'binary_sha256':b['binary_sha256'],'Open15_score':float(score),'Open15_exact':str(score),
      'known155':summary(known['pairs']),'known_excluding_timing_sensitive_B23':summary(physical),
      'fresh46':summary(newpairs),'deterministic_controls2':summary(controlpairs),'all_confirmation48':summary(fresh['pairs']),
      'postfreeze_early24':summary(early['pairs']),
      'early_diagnostic_losses':[r for r in early['pairs'] if r['delta']<-1e-12],
      'fresh_losses':[r for r in fresh['pairs'] if r['delta']<-1e-12],
      'official_candidate_checks':len(official),'maximum_local_CPU_s':max(r['solver_cpu_total_s'] for r in official),
      'maximum_local_RSS_MiB':max(r['solver_peak_rss_mb'] for r in official),'host':'macOS arm64','target_hardware_run':False,
      'certificate':'After live PID geometry equals internal parent and actualT<=parentT, following all parent addresses preserves this inequality for every suffix.',
      'limits':['No terminal dominance before coupling.',
                'The guarantee compares to the internally executed parent. Extra processing can change CPU-budgeted planner choices relative to a standalone run.',
                'Fresh46 are new seeded inputs from known mechanisms; two deterministic controls were specified before selection.',
                'B23 varied with CPU termination, repeated parent and candidate both reached0.0787033547; do not count it as a layout gain.',
                'The independent46 mostly diverge after modified PID2 was removed;24 postfreeze retained-marker probes were added to audit this coverage gap without tuning the source.',
                'Early probes exposed10 losses, including exact-capacity cases1.0→0.9230769. Coupling does not hold there; these are real geometry regressions.',
                'Open11-p8 and Open8-prefix traps remain unresolved.',
                'All timing/RSS measurements are from this macOS host, not Windows/G5420.'],
      'platform_actions':0,'canonical_and_parent_unchanged':sha(ROOT/'prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp')=='a843822451c2a7c5e07330daa33268fc77bccfbc08fd196bfaf98a673ae24cfe'}
    (HERE/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    rows=[{'suite':label,**r} for label,group in [('known155',known),('confirmation48',fresh),('postfreeze-early24',early)] for r in group['pairs']]
    with (HERE/'metrics.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['suite','id','baseline','candidate','delta']);w.writeheader();w.writerows(rows)
    def row(label,r):return f'<tr><td>{label}</td><td>{r["count"]}</td><td>{r["wins"]} / {r["ties"]} / {r["losses"]}</td><td>{r["mean_delta"]:+.9f}</td><td>{r["worst_delta"]:+.9f}</td></tr>'
    table=''.join(row(label,r) for label,r in [('Знакомые155',report['known155']),('Новые seeded46',report['fresh46']),('Заданные заранее controls2',report['deterministic_controls2']),('Дополнительные early24 послеfreeze',report['postfreeze_early24'])])
    losshtml=''.join(f'<li>{html.escape(r["id"])}: {r["baseline"]:.9f} → {r["candidate"]:.9f} (Δ{r["delta"]:+.9f})</li>' for r in report['fresh_losses']) or '<li>Наблюдаемых потерь на48 входах нет.</li>'
    text=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Pipes — coupling после префикса</title>
<style>body{{font:17px/1.55 system-ui;max-width:1050px;margin:48px auto;padding:0 24px;color:#172637;background:#fafbf9}}table{{width:100%;border-collapse:collapse;margin:24px 0}}td,th{{padding:10px;border-bottom:1px solid #ccd6dd;text-align:left}}.note{{background:#eef3f5;padding:18px}}code{{word-break:break-all}}a{{color:#175b9e}}</style>
<h1>Направленные ловушки: виртуальный parent и coupling</h1>
<p class="note"><b>{'Кандидат прошёл конечную проверку без наблюдаемых потерь.' if gate else 'Независимая проверка выявила потери; кандидат не заменяет прежний код.'}</b> Open15 сохранён: <b>{float(score):.14f}</b>. Это конечные локальные измерения, не гарантия на скрытом распределении.</p>
<p>Изменён один общий блок: в Open11/Open15 труба длиной2 на второй команде размещается в38 вместо229. Траншея на этом шаге40м вместо240м. Граница40 выбрана до новых результатов, чтобы избежать заранее заданного плотного заполнения40+29+9.</p>
<p>Внутренняя копия полностью исполняет прежний parent: публичные таблицы, advanced episode и сценарный Planner. После расхождения физический allocator использует Best-Fit, пока живые координаты различаются. Когда живые PID совпали и реальная траншея не длиннее виртуальной, он точно повторяет дальнейшие адреса parent.</p>
<h2>Что доказано</h2><p>После coupling одинаковые живые трубы означают одинаковую занятость. Адрес parent свободен и в реальной геометрии; обе траншеи обновляются одной монотонной функцией max(T,ceil20(x+L)). Поэтому реальная итоговая траншея не больше внутренней виртуальной при любом дальнейшем потоке. <b>До coupling гарантии нет.</b> Время CPU может изменить виртуальные решения относительно отдельно запущенного parent.</p>
<table><tr><th>Набор</th><th>N</th><th>Лучше / равно / хуже</th><th>Средняя ΔKPI</th><th>Худшая ΔKPI</th></tr>{table}</table><ul>{losshtml}</ul>
<p>155 знакомых входов включают прежние holdout и оба прошлых fresh-набора. Они использованы только для отбора. Новый набор46 сформирован отдельно до freeze;2 фиксированных controls известны заранее. После48 результатов код не менялся и другой кандидат не выбирался.</p>
<p><b>Проверка покрытия выявила отдельный провал до coupling.</b> Большинство новых46 входов расходятся с публичным потоком после удаления изменённой трубы. Поэтому послеfreeze добавлены24 seeded проверки с живойPID2, без смены исходника. Результат6 улучшений /8 равенств /10 потерь; три коротких exact-capacity теста дают KPI1→0.9230769. Они проверены ещё и официальным interactor. Это реальные потери от геометрии, не шум CPU.</p>
<h2>Выигрыши и границы</h2><p>Известная Open11-p2: KPI0.08333→0.5; reserve-p2:0.16667→1. Более агрессивное x3 давало1 в первой ловушке, но оставляло другую точную ловушку заполнения. Новая версия сохраняет запас40м. Open8-p402 остаётся0.165644; Open11-p8 остаётся0.090909 при обычном BF1.</p>
<p>B23 дал малую разницу из-за исчерпания CPU: повторы обоих бинарников совпали0.0787033547. Это не выигрыш от новой геометрии.</p>
<p>В46-наборе малые различия на других публичных ветвях также проверены отдельно: например n05-l7000 вообще не достигает исправленного префикса. Эти различия не приписываются сдвигу трубы и не скрывают реальные ранние регрессии.</p>
<h2>Проверка и ресурсы</h2><p>{len(official)} официальных проверок точного бинарника; максимум CPU{report['maximum_local_CPU_s']:.6f}s / RSS{report['maximum_local_RSS_MiB']:.3f}MiB. Хост macOS arm64. Windows10/G5420 на одном ядре не запускался; процессный таймер Windows GetProcessTimes сохранён, solver однопоточный.</p>
<p>Отдельный контроль повторил stdout прежнего parent на12 полных потоках, включая advanced episode. Проверены все280156 публичных префиксов: выкопка не выросла. Общие префиксы согласованы, все15 объёмных нижних границ достигнуты.</p>
<p><a href="{name}/solution.cpp">Standalone C++20</a> · <a href="report.json">JSON</a> · <a href="metrics.csv">Парные метрики</a> · <a href="freeze.json">Freeze</a> · <a href="audit_coupled.json">Аудит</a> · <a href="code-and-tests.zip">Код и тесты</a></p>
<p>Source SHA256: <code>{b['source_sha256']}</code></p><p>Canonical, frozen parents и платформа не изменялись.</p></html>'''
    (HERE/'report.html').write_text(text)
    (HERE/'README.txt').write_text(f'''Pipes ghost handoff local pilot,2026-10-20.
Frozen candidate:{name}. Status:{report['status']}.
Compile:clang++ -std=c++20 -O2 {name}/solution.cpp -o solver
Full source SHA256:{b['source_sha256']}
Source Windows support inherited: processCPU user+kernel, one worker. No native G5420 benchmark.
Parent source unchanged. No platform actions. Read report.json and all per-case metrics before promotion.
Coupling proves dominance against internal parent only after physical live geometry agrees; before coupling no such claim.
Fresh48 consists46 newseeded known-mechanism inputs and2 deterministic controls fixed before candidate selection.
''')
    with zipfile.ZipFile(HERE/'code-and-tests.zip','w',zipfile.ZIP_DEFLATED) as z:
        for file in ['README.txt','report.json','metrics.csv','freeze.json','experiment.json','audit_coupled.json','coupled-control.json','timing-sensitive-B23.json','timing-sensitive-n05.json',name+'/solution.cpp',name+'/build.json','build_coupled.py','evaluate.py','early_diagnostics.py']:
            z.write(HERE/file,file)
        for f in (HERE/'evaluation').rglob('*'):
            if f.is_file() and f.suffix in ['.py','.json','.in']:z.write(f,f.relative_to(HERE))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
