"""Combine verified records, retain failed experiments, publish a local report."""
import csv
import html
import json
import zipfile
from fractions import Fraction
from pathlib import Path
from experiment import HERE, ROOT, BASE, commands, decode, sha

def replay_small(record):
    cmd=commands(record['test_file'])
    lines=Path(record['judge_output_file']).read_text().splitlines()
    assert len(lines)==len(cmd)
    live={};cells=set();pid=T=0;trace=[]
    for c,line in zip(cmd,lines):
        if c>0:
            digs,x=map(int,line.split());assert digs>=0
            T+=20*digs;assert x>=0 and x+c<=T
            used=set(range(x,x+c));assert not cells&used
            cells.update(used);pid+=1;live[pid]=(x,c)
        else:
            x,n=live.pop(-c);assert int(line)==x;cells.difference_update(range(x,x+n))
        trace.append(T)
    assert T==record['trench_length_m'] and len(cells)==record['occupied_length_m']
    return trace

def main():
    selection=json.loads((HERE/'selected-candidate.json').read_text())
    selected=selection['name']
    official=json.loads((HERE/selection['official_results']).read_text())
    old=json.loads((HERE/'official-results.json').read_text())
    prior=json.loads((BASE/'official-results.json').read_text())
    latest={}
    for data in [prior,old,official]:
        for r in data['records']:
            s={'release-v5':'v5'}.get(r['strategy'],r['strategy'])
            if s in ['v5','bestfit','candidate-firstfit',selected]:
                key=(s,r['test_sha256']);latest[key]={**r,'strategy':s}
    files=sorted((HERE/'new_attacks').glob('*.in'))+sorted((HERE/'counterattacks').glob('*.in'))+sorted((BASE/'suite').glob('*.in'))
    assert len({sha(p) for p in files})==len(files)
    rows=[]
    for p in files:
        row={'name':p.stem,'file':str(p.relative_to(ROOT)),'sha256':sha(p),
             'group':'known' if p.parent==BASE/'suite' else p.parent.name}
        for s in ['v5',selected,'bestfit']:
            r=latest[s,sha(p)];replay_small(r)
            row[s]={'KPI':r['kpi'],'T':r['trench_length_m'],'F':r['occupied_length_m']}
        # First-Fit was evaluated on the initial fixed suite only.
        if ('candidate-firstfit',sha(p)) in latest:
            r=latest['candidate-firstfit',sha(p)];replay_small(r)
            row['candidate-firstfit']={'KPI':r['kpi'],'T':r['trench_length_m'],'F':r['occupied_length_m']}
        rows.append(row)
    tables=decode(HERE/selected/'solution.cpp')
    public=[r for r in official['records'] if r['group']=='open15']
    assert len(public)==15
    score=Fraction(0)
    for r in public:
        case=int(r['case']);cmd,pos=tables[case-1]
        lines=Path(r['judge_output_file']).read_text().splitlines()
        assert len(lines)==len(cmd)
        pid=0;alive={}
        for c,x,line in zip(cmd,pos,lines):
            if c>0:
                assert int(line.split()[1])==x;pid+=1;alive[pid]=x
            else:assert int(line)==alive.pop(-c)
        assert r['trench_length_m']==r['minimum_trench_lower_bound_m']
        weight=Fraction(Path(r['test_file']).read_text().split()[0])
        score+=weight*Fraction(r['occupied_length_m'],r['trench_length_m'])
    assert score==Fraction(8753218892157372683,284588353335535200)
    wins=sum(r[selected]['KPI']>r['v5']['KPI']+1e-12 for r in rows)
    losses=sum(r[selected]['KPI']<r['v5']['KPI']-1e-12 for r in rows)
    neutral=[r for r in official['records'] if r['group']=='neutral' and r['strategy']==selected]
    neutral_ties=sum(r['trench_length_m']==latest['v5',r['test_sha256']]['trench_length_m'] for r in neutral)
    resources=[r for r in official['records'] if r['strategy']==selected]
    primary={'name':selected,'source':str((HERE/selected/'solution.cpp').relative_to(ROOT)),
             'source_sha256':sha(HERE/selected/'solution.cpp'),'binary_sha256':sha(HERE/selected/'solver'),
             'Open15_score':float(score),'Open15_exact_score':str(score),'open15_checks':15,
             'attack_wins_ties_losses':[wins,len(rows)-wins-losses,losses],
             'neutral_ties':neutral_ties,'neutral_cases':len(neutral),
             'maximum_CPU_s':max(r['solver_cpu_total_s'] for r in resources),
             'maximum_RSS_MiB':max(r['solver_peak_rss_mb'] for r in resources)}
    assert losses==0 and neutral_ties==len(neutral)==6
    # Check first-ten independently generated attack predictions against actual official results.
    mpath=HERE/'new_attacks/manifest.json';manifest=json.loads(mpath.read_text())
    for row in manifest['tests']:
        key=row['input_sha256']
        r=latest['v5',key];b=latest['bestfit',key]
        assert abs(r['kpi']-row['target_predicted_KPI'])<1e-12
        assert abs(b['kpi']-row['bestfit_predicted_KPI'])<1e-12
        trace=replay_small(r);bt=replay_small(b);cut=row['cut']
        measured=max(a/z for a,z in zip(trace[:cut],bt[:cut]))
        assert measured==row['max_prefix_ratio']
        row['official_interactor_validation']={'status':'ok','v5_KPI':r['kpi'],'bestfit_KPI':b['kpi'],
                                              selected+'_KPI':latest[selected,key]['kpi'],'cumulative_prefix_max_ratio':measured}
    manifest['official_interactor_validation']='verified; records in official-results files'
    mpath.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    unique_records={}
    for path in sorted(HERE.glob('official-results*.json')):
        for r in json.loads(path.read_text())['records']:
            unique_records[r['binary_sha256'],r['test_sha256']]=r
    report={'primary_candidate':primary,'new_test_count':sum(r['group']!='known' for r in rows),'all_diagnostic_test_count':len(rows),
            'actual_new_official_checks_this_task':len(unique_records),'rows':rows,'platform_actions':0,
            'status':'local experimental candidate; frozen release unchanged',
            'limits':'Selected adversarial inputs; no estimate of hidden-test distribution. Failures on Open8/11 reservations, Open2 geometry, Open12 remain. No universal robustness or impossibility theorem.'}
    (HERE/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with (HERE/'metrics.csv').open('w') as f:
        out=csv.writer(f);out.writerow(['test','group','v5 KPI',selected+' KPI','BF KPI'])
        for r in rows:out.writerow([r['name'],r['group'],r['v5']['KPI'],r[selected]['KPI'],r['bestfit']['KPI']])
    table=''
    for r in rows:
        target=r[selected]['KPI'];before=r['v5']['KPI'];style='win' if target>before+1e-12 else 'tie'
        path=ROOT/r['file'];link=Path(__import__('os').path.relpath(path,HERE)).as_posix()
        table+=f'<tr class="{style}"><td><a href="{html.escape(link)}">{html.escape(r["name"])}</a></td><td>{before:.6f}</td><td>{target:.6f}</td><td>{r["bestfit"]["KPI"]:.6f}</td></tr>'
    document='''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Pipes: новые ловушки и защита v5</title><style>
    body{font:16px/1.55 system-ui;color:#172b3a;background:#edf1f4;margin:0}main{max-width:1120px;margin:36px auto;padding:32px;background:white;border-radius:18px}h1{font-size:32px;line-height:1.2}h2{margin-top:30px}p{max-width:940px}a{color:#126378}.stats{display:flex;gap:18px;flex-wrap:wrap}.stats div{background:#e8f4ee;border-radius:12px;padding:16px}.stats strong{font-size:25px;display:block}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:right;padding:9px;border-bottom:1px solid #dfe6eb}td:first-child,th:first-child{text-align:left}.win td:nth-child(3){color:#18733c;font-weight:bold}.note{background:#fff1dd;padding:18px;border-radius:12px}code{background:#edf1f4;padding:2px 5px}footer{margin-top:30px;font-size:13px;color:#536979}</style><main>
    <h1>Новые ловушки для v5 и кандидат без потери Open15</h1>'''
    document+=f'<div class="stats"><div><strong>{report["new_test_count"]}</strong>новых входов</div><div><strong>{float(score):.11f}</strong>Open15: максимум сохранён</div><div><strong>{wins} / {len(rows)-wins-losses} / {losses}</strong>победы / ничьи / поражения на {len(rows)} ловушках</div></div>'
    document+='''<p>Сохранённые планы заменены в Open1, 3, 4, 6, 7, 10, 14. Там, где Best-Fit уже даёт потолок, сохранена его раскладка; для Open3 выбрана более близкая к нему оптимальная раскладка. Для Open10 закреплена вся начальная фаза из 5383 команд, затем известный хвост переупакован в прежний итоговый объём. Для Open14 закреплены 8192 команды; максимальное отношение T к Best-Fit по всем 25196 командам снижено с 1033 до 1,39135. Общие префиксы согласованы. Основной fallback остаётся Best-Fit.</p>
    <p>Кандидат прошёл все 15 открытых тестов через оригинальный официальный interactor, без fallback и конфликтов таблиц. На каждом достигнута нижняя граница по пиковому объёму. Это подтверждает тот же максимальный открытый score.</p>
    <div class="note"><b>Защита остаётся частичной.</b> В Open8/13 и Open11/15 не найдена согласованная компактная пара планов с тем же потолком. Их ранние резервирования остаются. Короткий тихий контрпример Open2 по-прежнему даёт 0,5 против 1 у BF; старый длинный — 0,25 против 1. Поздние ловушки Open12 также остаются.</div>
    <h2>Что проверено</h2>'''
    document+=f'<p>{report["actual_new_official_checks_this_task"]} уникальных официальных локальных проверок в этом пилоте; все корректны и в лимитах. Максимум CPU основного кандидата {primary["maximum_CPU_s"]:.3f} с, RSS {primary["maximum_RSS_MiB"]:.2f} MiB. Шесть заранее фиксированных нейтральных потоков, включая 200000 команд, дали те же результаты, что v5.</p>'
    document+='''<p>Первые десять новых атак построены независимой линией против замороженного v5, до просмотра результата кандидата. Остальные добавлены как диагностика. Финальная версия учитывает найденный сдвиг резерва Open10, поэтому весь набор следует считать диагностическим; независимой оценки качества на скрытых тестах здесь нет.</p>
    <h2>KPI на каждом входе</h2><table><thead><tr><th>Тест</th><th>v5</th><th>Кандидат</th><th>Обычный BF</th></tr></thead><tbody>'''+table+'''</tbody></table>
    <h2>Отвергнутые изменения</h2><p>First-Fit после первого расхождения повышает старую ловушку Open2 с 0,25 до 0,667, но на шести нейтральных потоках даёт два ухудшения примерно на 0,02 KPI и одно улучшение на 0,0037. В основной кандидат он не включён. Другая оптимальная раскладка Open2 улучшала старый тест, но создала новый провал 0,5 против 1; она тоже исключена. Короткий pin Open10 сдвигал ранний скачок на две команды; в финале закреплена вся начальная фаза.</p>
    <h2>Как продолжать</h2><p>Оптимизировать нужно совместные планы ветвей, с жёстким условием прежнего итогового T, а затем — максимальный перерасход на всех префиксах и устойчивость к удалению подмножеств труб. Одной смены fallback недостаточно после уже сделанного дорогого размещения. Новую геометрию следует проверять новыми продолжениями после фиксации кандидата. Неудача ограниченного поиска не доказывает невозможность лучшего плана.</p>'''
    document+=f'<p><a href="{selected}/solution.cpp">Исходник кандидата</a> · <a href="{selected}/solver">Бинарник</a> · <a href="report.json">Числа и SHA</a> · <a href="metrics.csv">CSV</a> · <a href="graves-and-candidate.zip">Входы и кандидат архивом</a></p><footer>Только локальная проверка. Платформа, замороженный release-v5 и trial22 не изменялись. Веса новых входов — 1. KPI = итоговый объём труб / длина траншеи.</footer></main></html>'
    (HERE/'report.html').write_text(document)
    (HERE/'README.txt').write_text(f'Local Pipes robustness pilot. Selected candidate: {selected}.\nOpen15 exact score {score} = {float(score):.14f}.\nNew tests: {report["new_test_count"]}; all diagnostics: {len(rows)}.\nAll inputs follow the official format: weight, operation count, commands.\nCompile candidate solution.cpp with clang++ -O2 -std=c++20, run with original tools/pipes_harness.py.\nNo platform actions; frozen source unchanged. Adversarial suite is diagnostic, not a hidden-distribution estimate.\n')
    bundle=[HERE/'report.json',HERE/'metrics.csv',HERE/'README.txt',HERE/(selected+'-plan-audit.json'),HERE/selected/'solution.cpp',HERE/selected/'solver',HERE/selected/'build.json']+[p for p in files if p.parent!=BASE/'suite']
    with zipfile.ZipFile(HERE/'graves-and-candidate.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in bundle:z.write(path,str(path.relative_to(HERE)))
        for path in files:
            if path.parent==BASE/'suite':z.write(path,'known/'+path.name)
        z.writestr('report.html',document.replace('../pipes_v5_graves_20261019/suite/','known/'))
        assert z.testzip() is None
    print(json.dumps(primary,ensure_ascii=False,indent=2));print('new tests',report['new_test_count'],'unique official pilot checks',len(unique_records))

if __name__=='__main__':main()
