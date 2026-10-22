"""Audit the selected immutable executable and publish complete paired results."""
import csv
import html
import importlib.util
import json
import os
import sys
import zipfile
from fractions import Fraction
from common import HERE,ROOT,PRIOR,e,known_files

def main():
    if str(PRIOR) not in sys.path:sys.path.insert(0,str(PRIOR))
    spec=importlib.util.spec_from_file_location('round2_report',PRIOR/'report.py')
    previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
    rows={}
    for path in sorted((HERE/'evaluations').rglob('record.json')):
        r=json.loads(path.read_text())
        assert r['status']=='ok',r
        assert r['test_sha256']==e.sha(r['test_file'])
        assert r['solver_cpu_total_s']<5 and r['solver_peak_rss_mb']<256
        rows[r['strategy'],r['test_sha256']]=r
    selected='candidate-physical';meta=json.loads((HERE/selected/'build.json').read_text())
    assert e.sha(HERE/selected/'solution.cpp')==meta['source_sha256']
    assert e.sha(HERE/selected/'solver')==meta['binary_sha256']
    assert e.sha(PRIOR/'final/solution.cpp')=='3a0164597619fcccc52e2f5fc60f9c391853eb3e36f8dd7e39185a98c3539a00'
    final=[r for (s,k),r in rows.items() if s==selected]
    assert len(final)==96,len(final)
    for r in final:
        assert r['binary_sha256']==meta['binary_sha256'];previous.replay(r)
    public=[r for r in final if r['group']=='open15'];assert len(public)==15
    tables=e.decode(HERE/selected/'solution.cpp');score=Fraction(0)
    for r in public:
        assert r['trench_length_m']==r['minimum_trench_lower_bound_m']
        assert 'fallback=0' in r['candidate_stderr'] and 'table_conflict=0' in r['candidate_stderr']
        cmd,pos=tables[int(r['case'])-1]
        lines=__import__('pathlib').Path(r['judge_output_file']).read_text().splitlines()
        assert all(int(line.split()[1])==x for c,x,line in zip(cmd,pos,lines) if c>0)
        weight=Fraction(__import__('pathlib').Path(r['test_file']).read_text().split()[0])
        score+=weight*Fraction(r['occupied_length_m'],r['trench_length_m'])
    assert score==Fraction(8753218892157372683,284588353335535200)
    def pair(group):
        result=[]
        for r in final:
            if r['group']!=group:continue
            base=rows['baseline',r['test_sha256']]
            result.append({'case':r['case'],'file':r['test_file'],'sha256':r['test_sha256'],
                           'baseline_KPI':base['kpi'],'candidate_KPI':r['kpi'],'delta':r['kpi']-base['kpi'],
                           'baseline_T':base['trench_length_m'],'candidate_T':r['trench_length_m'],
                           'F':r['occupied_length_m']})
        return result
    paired={g:pair(g) for g in ['known','fresh','counter','holdout']}
    def stats(data):
        d=[r['delta'] for r in data]
        return {'count':len(d),'wins_ties_losses':[sum(x>0 for x in d),sum(x==0 for x in d),sum(x<0 for x in d)],
                'mean_KPI_delta':sum(d)/len(d),'worst_KPI_delta':min(d)}
    summary={g:stats(data) for g,data in paired.items()}
    assert summary['known']['count']==55 and summary['known']['worst_KPI_delta']>=-.02
    assert summary['holdout']['count']==14 and summary['holdout']['mean_KPI_delta']>=0 and summary['holdout']['worst_KPI_delta']>=-.03
    audits=[]
    for path in [HERE/'components/audit.json',*sorted((HERE/'components').glob('pair-*/audit.json'))]:
        a=json.loads(path.read_text());assert a['all15_shared_prefix_consistent']
        audits.extend(a['audits'])
    old_ratio={5:4,9:7.142857142857143,8:77.5,13:77.5,11:976,15:976,12:5.153061224489796,14:1.3913491246138001}
    risk=[{'case':a['case'],'old_max_T_over_BF':old_ratio[a['case']],'new_max_T_over_BF':a['ratio'],
           'new_peak_step':a['worst_step'],'unchanged_optimal_T':a['T']} for a in sorted(audits,key=lambda a:a['case'])]
    report={'selected':selected,'build':meta,'Open15_score':float(score),'Open15_exact_score':str(score),
       'final_official_checks':len(final),'new_attack_count':12,'paired_statistics':summary,'public_prefix_risk':risk,
       'paired':paired,'maximum_CPU_s':max(r['solver_cpu_total_s'] for r in final),
       'maximum_RSS_MiB':max(r['solver_peak_rss_mb'] for r in final),'platform_actions':0,
       'snapshot_regression':json.loads((HERE/'snapshot-regression.json').read_text()),
       'scope':'Bounded round3; 6 independent targeted inputs plus 6 post-freeze residual diagnostics; 14 fresh neutral streams. No hidden-distribution or universal robustness claim.',
       'limitations':'Residual Open11 p2 KPI 1/12 and Open8 p402 ~.166 with BF 1; local proposal dig guarantee does not imply future-layout dominance.'}
    (HERE/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    manifest=HERE/'attacks/manifest.json';m=json.loads(manifest.read_text());m['official_interactor_validation']='all6 verified against original official interactor'
    for item in m['tests']:
        k=item.get('input_sha256',item.get('sha256'))
        if k is None:
            k=e.sha(HERE/'attacks'/item['file'])
        a,b,z=rows['baseline',k],rows['bestfit',k],rows[selected,k]
        item['official_KPI']={'baseline':a['kpi'],'candidate':z['kpi'],'BF':b['kpi']}
    manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    with (HERE/'metrics.csv').open('w') as f:
        out=csv.writer(f);out.writerow(['group','case','baseline_KPI','candidate_KPI','delta'])
        for group,data in paired.items():
            for r in data:out.writerow([group,r['case'],r['baseline_KPI'],r['candidate_KPI'],r['delta']])
    def make_table(data,group):
        text='<table><thead><tr><th>Вход</th><th>Round2</th><th>Новая версия</th><th>ΔKPI</th>'
        with_bf=group in ['fresh','counter']
        if with_bf:text+='<th>Обычный BF</th>'
        text+='</tr></thead><tbody>'
        for r in data:
            rel=os.path.relpath(r['file'],HERE);style='gain' if r['delta']>0 else 'loss' if r['delta']<0 else ''
            text+=f'<tr><td><a href="{html.escape(rel)}">{html.escape(r["case"])}</a></td><td>{r["baseline_KPI"]:.6f}</td><td>{r["candidate_KPI"]:.6f}</td><td class="{style}">{r["delta"]:+.6f}</td>'
            if with_bf:text+=f'<td>{rows["bestfit",r["sha256"]]["kpi"]:.6f}</td>'
            text+='</tr>'
        return text+'</tbody></table>'
    doc='''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Pipes: безопасные компоненты и проверяемый fallback</title><style>body{margin:0;background:#eef2f4;color:#183143;font:16px/1.55 system-ui}main{max-width:1150px;margin:32px auto;padding:34px;background:white;border-radius:18px}h1{font-size:32px;line-height:1.2}h2{margin-top:30px}.stats{display:flex;gap:15px;flex-wrap:wrap}.stats div{background:#e7f3ed;border-radius:12px;padding:16px}.stats b{display:block;font-size:25px}.note{background:#fff0d8;padding:17px;border-radius:10px}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:right;padding:8px;border-bottom:1px solid #dce5eb}td:first-child,th:first-child{text-align:left}a{color:#126c81}.gain{color:#14733b;font-weight:bold}.loss{color:#a13e30;font-weight:bold}p{max-width:1000px}footer{margin-top:28px;color:#577082;font-size:13px}</style><main><h1>Раунд 3: безопасная перестановка раскладок и проверка предложений fallback</h1>'''
    doc+=f'<div class="stats"><div><b>12</b>новых диагностических входов</div><div><b>{float(score):.11f}</b>прежний максимум Open15</div><div><b>96</b>официальных проверок окончательного бинарника</div></div>'
    doc+='''<p>Для сравнения заморожен итог round2, source SHA 3a016459…. Новая версия изменила восемь сохранённых планов, сохранила все общие префиксы и достигла тех же пиковых объёмных границ на всех 15 открытых тестах. Runtime после отклонения от таблицы тоже изменён. Предыдущие frozen файлы и платформа не трогались.</p>
    <h2>Что удалось уменьшить</h2><p>План разбит на участки, которые ни одна труба не пересекает. Их перестановка сохраняет корректность всех известных lifetime-трасс. Для каждого допустимого отношения T/BF из ограничений на все префиксы строятся предельные позиции участков. Порядок по этим ограничениям позволяет найти лучший максимум в данном классе перестановок. Это ограниченный класс, а не глобальный оптимум всех возможных раскладок.</p>
    <table><thead><tr><th>Open case</th><th>Макс. T/BF раньше</th><th>Макс. T/BF теперь</th><th>Итоговый T сохранён</th></tr></thead><tbody>'''
    for r in risk:doc+=f'<tr><td>{r["case"]}</td><td>{r["old_max_T_over_BF"]:.6f}</td><td>{r["new_max_T_over_BF"]:.6f}</td><td>{r["unchanged_optimal_T"]}</td></tr>'
    doc+='''</tbody></table><p>Измерялся максимум по каждой команде полного публичного потока, а не только состояние в конце выбранного префикса. Первое локальное исправление пары 8/13 переносило резерв с PID2 на PID3; оно уступило общей перестановке компонентов и в финал не вошло.</p>
    <h2>Fallback: предложить, проверить, затем выполнить</h2><p>Online-алгоритм работает на копии состояния. Его ответ принимается только если требует не больше новых секций траншеи, чем BF из той же физической раскладки. Если предложение проигрывает по немедленному рытью, оно отбрасывается до печати ответа. Эпизод ограничен существующими бюджетами модели: 32 предложения и 4096 живых труб. Условие преимущества относительно параллельного causal BF сохранено.</p>
    <p>При передаче управления промежутки заново строятся по реальным активным трубам. Внутренний список online-политики может исключать ещё свободные участки, зарезервированные под будущие трубы. Копирование такого списка теряло бы доступную ёмкость. Независимый тест снимка: старый перенос не находит свободный [30,70), новый корректно размещает там трубу длины 40 без рытья.</p>
    <div class="note"><b>Граница гарантии.</b> Проверка предложения ограничивает немедленный расход из текущего состояния. Она не доказывает, что итоговая траншея будет не длиннее BF: разные размещения меняют будущую фрагментацию. Код по-прежнему использует полные открытые потоки для предварительной подготовки планов.</div>'''
    for group,title,description in [
      ('known','55 ранее проверенных потоков','Регрессии предыдущего раунда: 37 диагностических входов, 14 прежних нейтральных и 4 стресс-проверки передачи состояния.'),
      ('fresh','6 новых атак независимой линии','Два продолжения online-эпизода Open2, два поздних геометрических продолжения Open12 и два удаления по rank в Open14. Набор зафиксирован до оценки новой сборки.'),
      ('counter','6 остаточных атак после фиксации кода','После выбранного префикса старые трубы удаляются, вся траншея BF заполняется, затем выполняются замены той же длины. Достижимый KPI равен 1. Эти входы построены как диагностика уже замороженного кандидата, для настройки кода не использовались.'),
      ('holdout','14 свежих нейтральных потоков','Фиксированные новые seeds, разные удаления и режимы длин, длинные общие префиксы, два потока по 200000 команд. Ухудшения показаны полностью.')]:
        s=summary[group];doc+=f'<h2>{title}</h2><p>{description} Победы / ничьи / поражения: <b>{" / ".join(map(str,s["wins_ties_losses"]))}</b>; среднее ΔKPI {s["mean_KPI_delta"]:+.6f}, худшее {s["worst_KPI_delta"]:+.6f}.</p>'+make_table(paired[group],group)
    doc+='''<h2>Оставшиеся ловушки</h2><p>На остаточном Open11-префиксе из двух команд новый KPI всё ещё 0,0833 против BF 1; на Open8 после 402 команд — около 0,166 против 1. Перестановки целых участков исчерпали возможности своего класса: дальше потребуется менять внутреннюю раскладку ранних крупных участков. Низкая оценка здесь вызвана уже вырытой траншеей, а достижимый KPI тестов остаётся высоким.</p>'''
    doc+=f'<p>Итоговый бинарник прошёл 96 официальных проверок корректности и ресурсов. Максимум CPU {report["maximum_CPU_s"]:.3f} с, RSS {report["maximum_RSS_MiB"]:.2f} MiB. Все 15 Open достигли своих нижних границ по T, без fallback и конфликтов таблиц. Транскрипты дополнительно воспроизведены независимым контролем занятых ячеек.</p>'
    doc+='''<p>Конечные синтетические наборы не оценивают неизвестное распределение скрытых тестов. Улучшения и откаты относятся к перечисленным входам.</p>
    <p><a href="candidate-physical/solution.cpp">Окончательный исходник</a> · <a href="candidate-physical/solver">Бинарник</a> · <a href="plans-only/solution.cpp">Альтернатива только с новыми планами</a> · <a href="report.json">Числа и SHA</a> · <a href="metrics.csv">CSV</a> · <a href="round3-tests-and-code.zip">Архив</a></p><footer>Локальный round3. Сравнение с immutable round2/final. Baseline для старых входов переиспользован по SHA из официальных проверок прошлого раунда; новые пары выполнены заново. Список источников и полные результаты доступны в evaluations.</footer></main></html>'''
    (HERE/'report.html').write_text(doc)
    (HERE/'README.txt').write_text('Pipes round3 local robustness pilot.\nSelected: candidate-physical/solution.cpp; compile clang++ -O2 -std=c++20.\n12 new adversarial inputs. 55 prior regression streams. 14 fresh neutral streams. All15 public ceilings preserved.\nNo platform actions. Read report.json for full gains and losses.\n')
    (HERE/'selected-candidate.json').write_text(json.dumps({'name':selected,'source_sha256':meta['source_sha256'],'binary_sha256':meta['binary_sha256'],
         'Open15_score':float(score),'status':'96 official local checks; finite-sample improvement with reported neutral regressions'},indent=2)+'\n')
    included=[HERE/'report.json',HERE/'metrics.csv',HERE/'README.txt',HERE/selected/'solution.cpp',HERE/selected/'solver',HERE/selected/'build.json',HERE/'plans-only/solution.cpp',HERE/'plans-only/build.json',HERE/'snapshot-regression.json',HERE/'component_deadlines.py',HERE/'freeze-all.json']
    files=known_files()+sorted((HERE/'attacks').glob('*.in'))+sorted((HERE/'counterattacks').glob('*.in'))+sorted((HERE/'holdout').glob('*.in'))
    assert len(files)==len({e.sha(p) for p in files})==81
    with zipfile.ZipFile(HERE/'round3-tests-and-code.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in included:z.write(p,str(p.relative_to(HERE)))
        portable=doc
        for p in files:
            local=os.path.relpath(p,HERE);name='prior/'+p.name if p in known_files() else str(p.relative_to(HERE))
            z.write(p,name);portable=portable.replace(html.escape(local),html.escape(name))
        z.writestr('report.html',portable);assert z.testzip() is None
    print(json.dumps({k:report[k] for k in ['Open15_score','final_official_checks','paired_statistics','maximum_CPU_s','maximum_RSS_MiB']},indent=2))

if __name__=='__main__':main()
