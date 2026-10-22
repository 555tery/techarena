"""Independently replay final transcripts and publish the round-2 evidence."""
import csv
import html
import json
import os
import zipfile
from fractions import Fraction
from pathlib import Path
from build_online_fallback import HERE,ROOT,PREV,e
from validate import old_files

def read_registry():
    good={};failed=[]
    for p in sorted((HERE/'evaluations').rglob('record.json')):
        r=json.loads(p.read_text())
        if 'strategy' not in r:continue
        if r['status']!='ok':failed.append({'record':str(p.relative_to(HERE)),'status':r['status'],'detail':r['detail']});continue
        assert r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256
        assert r['test_sha256']==e.sha(r['test_file'])
        good[r['strategy'],r['test_sha256']]=r
    return good,failed

def replay(r):
    cmd=e.commands(r['test_file']);lines=Path(r['judge_output_file']).read_text().splitlines()
    assert len(cmd)==len(lines)==r['operation_count']
    assert r['judge_commands_seen_including_final_zero']==len(cmd)+1
    active={};cells=set();pid=T=0;trace=[]
    for c,line in zip(cmd,lines):
        if c>0:
            digs,x=map(int,line.split());assert digs>=0 and x>=0
            T+=20*digs;assert x+c<=T
            used=set(range(x,x+c));assert not cells&used
            cells.update(used);pid+=1;active[pid]=(x,c)
        else:
            x,n=active.pop(-c);assert x==int(line);cells.difference_update(range(x,x+n))
        trace.append(T)
    assert T==r['trench_length_m'] and len(cells)==r['occupied_length_m']
    return trace

def main():
    registry,failed=read_registry()
    final=[r for (s,k),r in registry.items() if s=='final']
    assert len(final)==70,len(final)
    assert e.sha(PREV/'candidate-v3/solution.cpp')=='a3d414a4872796fb570753c0e61db5c80dc59c1b8cbd7ec57e95dec345aff53a'
    assert e.sha(ROOT/'prototypes/pipes_open15_overfit_20261019/continuation/release-v5/solution.cpp')=='7fe4d9430d708021f602ebb2333564ebb8c1e0b0ac5b1355855c4a18155c011f'
    build=json.loads((HERE/'final/build.json').read_text())
    assert e.sha(HERE/'final/solution.cpp')==build['source_sha256'] and e.sha(HERE/'final/solver')==build['binary_sha256']
    for r in final:
        assert r['binary_sha256']==build['binary_sha256'];replay(r)
    score=Fraction(0);public=sorted((r for r in final if r['group']=='open15'),key=lambda r:int(r['case']))
    tables=e.decode(HERE/'final/solution.cpp')
    for r in public:
        assert r['trench_length_m']==r['minimum_trench_lower_bound_m']
        assert 'fallback=0' in r['candidate_stderr'] and 'table_conflict=0' in r['candidate_stderr']
        c,p=tables[int(r['case'])-1]
        lines=Path(r['judge_output_file']).read_text().splitlines()
        assert all(int(s.split()[1])==x for op,x,s in zip(c,p,lines) if op>0)
        weight=Fraction(Path(r['test_file']).read_text().split()[0])
        score+=weight*Fraction(r['occupied_length_m'],r['trench_length_m'])
    assert len(public)==15 and score==Fraction(8753218892157372683,284588353335535200)
    files=old_files()+sorted((HERE/'attacks').glob('*.in'))+sorted((HERE/'counterattacks').glob('*.in'))
    assert len(files)==len({e.sha(p) for p in files})==37
    rows=[]
    for p in files:
        key=e.sha(p)
        row={'name':p.stem,'file':str(p.relative_to(ROOT)),'sha256':key,'group':'known24' if p in old_files() else 'control' if p.name.startswith('control-') else 'new'}
        for s in ['baseline','final','bestfit']:
            r=registry[s,key];replay(r)
            row[s]={'KPI':r['kpi'],'T':r['trench_length_m'],'F':r['occupied_length_m']}
        rows.append(row)
    differences=[r['final']['KPI']-r['baseline']['KPI'] for r in rows]
    assert min(differences)>=0
    holdout=[];safety=[]
    for r in final:
        if r['group'] in ['holdout','safety']:
            b=registry['baseline',r['test_sha256']]
            entry={'case':r['case'],'baseline_KPI':b['kpi'],'final_KPI':r['kpi'],'delta':r['kpi']-b['kpi'],
                   'baseline_T':b['trench_length_m'],'final_T':r['trench_length_m'],'file':r['test_file']}
            (holdout if r['group']=='holdout' else safety).append(entry)
    assert len(holdout)==14 and all(r['delta']==0 for r in holdout)
    assert len(safety)==4
    # The first ungated candidate failed on data that were fresh at its freeze.
    ungated=[]
    for (s,k),r in registry.items():
        if s=='online-fallback' and r['group']=='neutral':
            b=registry['baseline',k];ungated.append(r['kpi']-b['kpi'])
    assert len(ungated)==12
    failure_audit={'interrupted_attempts':failed,'interpretation':'Four long attempts ended before protocol completion in both unchanged baseline and candidate; cause not established. Serial retries of the same binaries passed. Interrupted attempts excluded from KPI comparison.',
                   'serial_retry_status':'all four interrupted strategy/input pairs have successful retry records'}
    for f in failed:
        p=HERE/f['record'];r=json.loads(p.read_text());assert (r['strategy'],r['test_sha256']) in registry
    (HERE/'failure-audit.json').write_text(json.dumps(failure_audit,ensure_ascii=False,indent=2)+'\n')
    report={'baseline':'candidate-v3','final':build,'Open15_exact_score':str(score),'Open15_score':float(score),
       'new_attack_inputs':12,'known_control_inputs':1,'old_attacks':24,'diagnostic_inputs':37,
       'attack_wins_ties_losses':[sum(x>0 for x in differences),sum(x==0 for x in differences),sum(x<0 for x in differences)],
       'final_official_checks':len(final),'unique_successful_strategy_input_checks_round2':len(registry),
       'interrupted_attempts':len(failed),'maximum_final_CPU_s':max(r['solver_cpu_total_s'] for r in final),
       'maximum_final_RSS_MiB':max(r['solver_peak_rss_mb'] for r in final),
       'maximum_open15_CPU_s':max(r['solver_cpu_total_s'] for r in public),
       'ungated_online_neutral_mean_delta':sum(ungated)/len(ungated),
       'ungated_online_neutral_wins_ties_losses':[sum(x>0 for x in ungated),sum(x==0 for x in ungated),sum(x<0 for x in ungated)],
       'holdout':holdout,'safety':safety,'rows':rows,'platform_actions':0,
       'Open12_public_prefix_max_ratio_before':7.841269841269841,'Open12_public_prefix_max_ratio_after':5.153061224489796,
       'scope':'One bounded local round; no universal guarantee or hidden-test distribution estimate. New Open2 variants share one mechanism. First neutral set became development after ungated rejection; fresh holdout fixed after runtime freeze. Final Open12 plan selected by public-only feasibility/risk objective.'}
    (HERE/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    manifest_path=HERE/'attacks/manifest.json';m=json.loads(manifest_path.read_text());m['official_interactor_validation']='verified by root; final and frozen candidate-v3 compared'
    for r in m['tests']:
        k=r['input_sha256'];a=registry['baseline',k];b=registry['bestfit',k];z=registry['final',k]
        at=replay(a);bt=replay(b);cut=r['cut'];measured=max(x/y for x,y in zip(at[:cut],bt[:cut]));assert measured==r['max_prefix_ratio_candidate_v3_vs_causal_BF']
        r['official_KPI']={'baseline':a['kpi'],'final':z['kpi'],'BF':b['kpi']}
    manifest_path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    with (HERE/'metrics.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['case','group','candidate-v3_KPI','final_KPI','causal_BF_KPI'])
        for r in rows:writer.writerow([r['name'],r['group'],r['baseline']['KPI'],r['final']['KPI'],r['bestfit']['KPI']])
    table=''
    for r in rows:
        link=os.path.relpath(ROOT/r['file'],HERE)
        table+=f'<tr><td><a href="{html.escape(link)}">{html.escape(r["name"])}</a></td><td>{r["baseline"]["KPI"]:.6f}</td><td class="'+('gain' if r['final']['KPI']>r['baseline']['KPI'] else '')+f'">{r["final"]["KPI"]:.6f}</td><td>{r["bestfit"]["KPI"]:.6f}</td></tr>'
    doc='''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Pipes · второй раунд устойчивости</title><style>
    body{margin:0;background:#edf2f5;color:#193143;font:16px/1.55 system-ui}main{max-width:1120px;margin:32px auto;padding:34px;background:white;border-radius:18px}h1{line-height:1.2;font-size:32px}h2{margin-top:30px}.stats{display:flex;gap:16px;flex-wrap:wrap}.stats div{padding:16px;background:#e7f3ee;border-radius:12px}.stats b{display:block;font-size:25px}.note{padding:18px;background:#fff1d9;border-radius:10px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:right;padding:8px;border-bottom:1px solid #dbe5ec}td:first-child,th:first-child{text-align:left}.gain{font-weight:bold;color:#177345}a{color:#126e82}p{max-width:950px}footer{font-size:13px;color:#577082;margin-top:28px}</style><main><h1>Ловушки и устойчивость: второй локальный раунд</h1>'''
    w,t,l=report['attack_wins_ties_losses'];doc+=f'<div class="stats"><div><b>12</b>новых атак + 1 известный контроль</div><div><b>{w} / {t} / {l}</b>победы / ничьи / поражения на 37 входах</div><div><b>{float(score):.11f}</b>максимум Open15 сохранён</div></div>'
    doc+='''<p>Исходная версия для сравнения — candidate-v3 из предыдущего раунда. У окончательного кандидата изменены план Open12 и fallback. Все 15 публичных входов по-прежнему достигают своих границ по пиковому объёму, через оригинальный официальный interactor; replay не прерывается и конфликтов таблиц нет.</p>
    <h2>Изменения кода</h2><p>План Open12 следует обычному BF первые 151 команду и допаковывает известный хвост в прежние 10260 м. Максимум T/BF по всему открытому потоку снизился с 7,841 до 5,153. Это уменьшение риска на публичной траектории; более поздняя атака всё ещё возможна.</p>
    <p>Новый fallback использует causal online-алгоритм с импортом фактических координат, PID и наблюдавшейся истории. Он включается только при уже существующем преимуществе replay по длине траншеи относительно параллельного causal BF. Когда online теряет это преимущество и становится длиннее BF, эпизод завершается и работа продолжается обычным BF из фактического состояния. Это условие остановки, а не строгая гарантия конечного T≤T_BF: уже сделанный рост необратим.</p>
    <p>Безусловный online-fallback был отвергнут: на первом свежем нейтральном наборе он систематически проигрывал. Этот набор после диагностики считался development. Ограниченный вариант проверен на новых 14 потоках с фиксированными seeds, включая новые режимы размеров и два потока по 200000 команд: все результаты совпали с candidate-v3. Это конечная проверка, не доказательство качества на скрытом распределении.</p>
    <div class="note"><b>Ограничения.</b> Open8/11 всё ещё уязвимы к раннему резервированию. На Open2 после короткого префикса остаются тихие ловушки 0,5 против BF 1. Поздний plateau Open12 после команды 224 даёт около 0,194 против BF 1; Open9 — 0,14 против 1. Устойчивость не универсальна.</div>
    <h2>Проверки</h2>'''
    doc+=f'<p>Окончательный бинарник прошёл {len(final)} официальных проверок: 15 Open, 37 диагностических входов, 14 новых нейтральных потоков и 4 проверки передачи состояния. Все ответы корректны и в лимитах. Максимум CPU {report["maximum_final_CPU_s"]:.3f} с, RSS {report["maximum_final_RSS_MiB"]:.2f} MiB. На максимальном Open-тесте дополнительный shadow BF увеличивает вычислительную работу; CPU также является вторичным критерием конкурса.</p>'
    doc+='''<p>В четырёх проверках передачи состояния три результата совпали с baseline. После общего префикса Open15 длиной 199950 команд появился небольшой проигрыш: дополнительные 20 м траншеи и ΔKPI ≈ −0,000048. Корректность и ограничения ресурсов соблюдены. Четыре первоначальных длинных прогона были прерваны без установленной причины; повторные серийные прогоны тех же бинарников прошли, первые попытки сохранены отдельно и не засчитаны как KPI.</p>
    <h2>Новые входы и старые регрессии</h2><p>Семь из восьми новых коротких атак — варианты одного delete/refill механизма Open2; восьмой относится к Open12. Четыре дополнительные plateau-атаки после общих префиксов завершаются полным заполнением траншеи BF, затем несколькими заменами труб. Их достижимый KPI равен 1; низкий KPI целевого решения вызван расходом траншеи, а не малым максимально возможным числителем. Ещё один вход — известный контроль для ранее отвергнутой раскладки Open2.</p>
    <table><thead><tr><th>Вход</th><th>candidate-v3</th><th>Новый код</th><th>causal BF</th></tr></thead><tbody>'''+table+'''</tbody></table>
    <h2>Оставшаяся работа</h2><p>Совместный ремонт Open11/15 остаётся задачей с жёстким ограничением потолков обоих тестов. Проверенные альтернативы уменьшили ранний риск, но теряли открытые баллы, поэтому в финал не вошли. Нужны совместное размещение общего префикса и проверка новых продолжений после фиксации плана; частные исправления одного trigger недостаточны.</p>
    <p><a href="final/solution.cpp">Окончательный исходник</a> · <a href="final/solver">Бинарник</a> · <a href="final-plan/solution.cpp">Вариант только с новым планом, без online fallback</a> · <a href="report.json">Результаты и SHA</a> · <a href="metrics.csv">CSV</a> · <a href="round2-tests-and-code.zip">Архив входов и кода</a></p><footer>Локальный эксперимент. Платформа и предыдущие frozen версии не изменялись. Новые тесты — диагностические контрпримеры; веса нормализованы к 1.</footer></main></html>'''
    (HERE/'report.html').write_text(doc)
    (HERE/'README.txt').write_text('Round2 Pipes robustness pilot.\nFinal solver: final/solution.cpp (compile clang++ -O2 -std=c++20).\n12 new attack inputs, 1 known control, 24 prior attacks; 14 fresh holdout streams; 4 handoff stress cases.\nAll 15 public volume ceilings retained. No platform actions.\nSee report.html/report.json and raw evaluations.\n')
    (HERE/'selected-candidate.json').write_text(json.dumps({'name':'final','source_sha256':build['source_sha256'],'binary_sha256':build['binary_sha256'],'status':'validated finite local pilot','known_limit':'20m regression on longest handoff stress; remaining reserve traps'},indent=2)+'\n')
    bundle=[HERE/'report.json',HERE/'metrics.csv',HERE/'README.txt',HERE/'final/solution.cpp',HERE/'final/solver',HERE/'final/build.json',HERE/'final-plan/solution.cpp',HERE/'final-plan/build.json',HERE/'freeze.json']
    with zipfile.ZipFile(HERE/'round2-tests-and-code.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in bundle:z.write(p,str(p.relative_to(HERE)))
        portable=doc
        for p in files:
            rel=os.path.relpath(p,HERE)
            name='prior/'+p.name if p in old_files() else str(p.relative_to(HERE))
            z.write(p,name);portable=portable.replace(html.escape(rel),html.escape(name))
        z.writestr('report.html',portable)
        assert z.testzip() is None
    print(json.dumps({k:report[k] for k in ['Open15_score','attack_wins_ties_losses','final_official_checks','unique_successful_strategy_input_checks_round2','maximum_final_CPU_s','maximum_final_RSS_MiB','ungated_online_neutral_mean_delta','ungated_online_neutral_wins_ties_losses']},indent=2))

if __name__=='__main__':main()
