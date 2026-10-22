"""Independent exact-rational comparisons, physical transcript and prefix audit."""
from collections import Counter,defaultdict
from fractions import Fraction
import html
import json
from pathlib import Path
import re
from audit import ROOT,read_input,verify
LABELS=['candidate','bf_rollin','no_hold','bf','ss','trial22']

def load(phase,label):
    actual='train_retry' if phase=='train' and label in ['bf_rollin','bf'] else phase
    p=ROOT/'evaluations'/actual/label/'harness/summary.json'
    if not p.exists():return None
    s=json.loads(p.read_text());assert s['case_count']==s['ok_count'];return {x['case']:x for x in s['records']}
def metric(x):return Fraction(x['occupied_length_m'],x['trench_length_m'])
def means(data,names):return {l:float(sum((metric(r[n]) for n in names),Fraction())/len(names)) for l,r in data.items()}
def paired(data,names,b):
    delta=[metric(data['candidate'][n])-metric(data[b][n]) for n in names]
    return {'wins':sum(d>0 for d in delta),'losses':sum(d<0 for d in delta),'ties':sum(d==0 for d in delta),
            'mean_delta':float(sum(delta,Fraction())/len(delta)),'worst_delta':float(min(delta)),
            'mean_extra_trench_m':sum(data['candidate'][n]['trench_length_m']-data[b][n]['trench_length_m'] for n in names)/len(names)}

def main():
    result={'scope':'Fixed small-state options pilot, not a hidden-score estimate','phases':{},'learning':{},'audits':{}}
    for phase in ['train','dev','final']:
        records=json.loads((ROOT/'data'/f'{phase}.json').read_text())['records']
        data={l:load(phase,l) for l in LABELS};data={l:r for l,r in data.items() if r is not None}
        names=[r['name'] for r in records if r['branch']!='resource']
        out={'cases':len(names),'means':means(data,names),'comparisons':{b:paired(data,names,b) for b in data if b!='candidate'},'families':{},'branches':{}}
        for field in ['family','branch']:
            for val in sorted({r[field] for r in records if r['branch']!='resource'}):
                sel=[r['name'] for r in records if r[field]==val and r['branch']!='resource']
                out['families' if field=='family' else 'branches'][val]=means(data,sel)
        if phase=='final':
            out['mechanism_split']={}
            for key,fams in [('training_mechanisms',['renewal','complements','size_survival','bursts']),('heldout_mechanisms',['alternating_support','anchors','ring_queue','bursty_lengths'])]:
                sel=[r['name'] for r in records if r['family'] in fams and r['branch']!='resource']
                out['mechanism_split'][key]={'means':means(data,sel),'vs_BF':paired(data,sel,'bf')}
            checked=prefixes=0;out['resources']={};out['activity']={}
            for label,rows in data.items():
                groups=defaultdict(list);activity=Counter()
                for r in records:
                    x=rows[r['name']];cmd=read_input(ROOT/'data/final'/(r['name']+'.in'))
                    reply=Path(x['judge_output_file']).read_text().splitlines();v=verify(cmd,reply)
                    assert (v['T'],v['F'])==(x['trench_length_m'],x['occupied_length_m']);assert abs(float(metric(x))-x['kpi'])<1e-12;checked+=1
                    if r['branch']!='resource':groups[r['base']].append(reply[:24])
                    if label in LABELS[:3]:
                        for k,val in re.findall(r'(placements|decisions|non_bf_options|continuation_placements|changes|cancellations|active_crossed_deletions)=(\d+)',x['candidate_stderr']):activity[k]+=int(val)
                for g in groups.values():assert len(g)==4 and all(x==g[0] for x in g);prefixes+=3
                out['resources'][label]={'max_cpu_s':max(x['solver_cpu_total_s'] for x in rows.values()),'max_rss_MiB':max(x['solver_peak_rss_mb'] for x in rows.values())}
                if activity:out['activity'][label]=dict(activity)
            result['audits']['final_transcripts']={'replayed':checked,'matched_prefix_comparisons':prefixes,'passed':True}
        result['phases'][phase]=out
    for name in ['M1','M2','M3','BFrollin']:
        result['learning'][name]={'fit':json.loads((ROOT/'models'/name/'fit.json').read_text()),'parity':json.loads((ROOT/'models'/name/'parity.log').read_text())}
    result['audits']['waves']={str(p.parent.relative_to(ROOT)):json.loads(p.read_text()) for p in (ROOT/'labels').glob('*/*/audit.json')}
    result['audits']['repeats']=json.loads((ROOT/'repeat-audit.json').read_text())
    result['audits']['infrastructure']=json.loads((ROOT/'infrastructure-incident.json').read_text())
    result['learning']['actual_selected_rules']=json.loads((ROOT/'learned-rules.json').read_text())
    result['interpretation']={
        'own_rollin_real': 'Wave1 changed 18/32 full transcripts versus BF; wave2 changed 3/32. Teacher labels were independently replayed on those actual states.',
        'sparse_labels': '590 aggregated states, 300 full observable groups, 533 tied labels. Leaf minimum counts rows, not independent groups.',
        'learned_policy': 'M3 has only one non-BF leaf: BFright. It does not select the anchored macro; the same-input BF-rollin control does.',
        'fresh_failure': 'All four losses to BF occur in held-out bursty_lengths, from two prefix groups. They are not four independent distribution samples.',
        'commitment_ablation': 'Two improvements over hold1 occur in anchors with one shared prefix; no final wins over BF. Shared weights and changed option semantics limit causal attribution.',
        'scope': 'Only two seeds per mechanism and small-state learned control (live<=12,T<=160). Long resource cases mostly exercise BF fallback. No claim about all coordinated policies or competition hidden tests.',
        'next_hypothesis_not_tested': 'Train option values with causal policy continuation over multiple possible futures, including worst-case regret to BF and a separately qualified abstention rule; do not tune against this consumed final set.'}
    final=result['phases']['final'];result['decision']='reject_candidate' if final['comparisons']['bf']['mean_delta']<=0 else 'local_signal_only_no_promotion'
    (ROOT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    def table(data):
        cols=list(next(iter(data.values())))
        return '<table><tr><th>Срез</th>'+''.join('<th>'+html.escape(c)+'</th>' for c in cols)+'</tr>'+''.join('<tr><th>'+html.escape(k)+'</th>'+''.join(f'<td>{v[c]:.6f}</td>' for c in cols)+'</tr>' for k,v in data.items())+'</table>'
    verdict='Кандидат отклонён: финальное среднее не выше BF.' if result['decision']=='reject_candidate' else 'Получен локальный сигнал улучшения. Перенос на конкурс не установлен.'
    page='''<!doctype html><meta charset="utf-8"><title>Own trajectories + options</title><style>body{font:16px system-ui;max-width:1200px;margin:40px auto;padding:0 18px;color:#192638;background:#f5f7fa}table{border-collapse:collapse;background:white;width:100%;margin:20px 0}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:right}th:first-child{text-align:left}pre{white-space:pre-wrap;background:white;padding:16px}.card{background:#e4edf8;padding:20px;border-radius:12px}</style><h1>Обучение на собственных траекториях и согласованные действия</h1>'''
    page+=f'<p class="card">{verdict}</p><p>Три фиксированных раунда: BF → M1 → M2 → M3. Финальная версия всегда M3. Стратегия удерживается четыре укладки; удаления не расходуют этот срок. Четвёртая стратегия: первая укладка BF слева, три следующих BF справа. На точном диагностическом примере она даёт 20 м вместо 40 м. Рабочий solver не видит будущих команд.</p>'
    page+='<p>Контроль bf_rollin обучен на тех же 96 входах и с тем же рецептом, но только на состояниях BF. no_hold использует веса M3 и выбирает стратегию на каждой укладке; anchored-стратегия при этом вырождается в BF слева. Это диагностическая абляция, не отдельно обученный конкурент. За пределами 12 живых труб или 160 м все обученные политики возвращаются к BF.</p>'
    page+='<h2>Среднее F/T</h2><p>Final: 64 новых потока, 8 механизмов × 2 начала × 4 продолжения. Четыре механизма отсутствовали в обучении. Ещё четыре потока по 200 000 команд проверяют ресурсы и не входят в среднее. Seeds получены после freeze; параметры по final не менялись.</p>'
    page+=table({p:result['phases'][p]['means'] for p in ['dev','final']})+table(final['families'])+table(final['branches'])
    page+='<h2>Что удалось и где возник проигрыш</h2><p>Собственные траектории действительно менялись: 18 из 32 потоков второго раунда и 3 из 32 третьего отличались от BF. Однако M3 выучила лишь одно переключение на BF справа и не выбирает последовательность «слева, затем справа». В 533 из 590 размеченных состояний варианты имели одинаковую оценку; имеется только 300 групп наблюдаемых состояний.</p>'
    page+='<p>Все четыре финальных проигрыша BF — на новом механизме bursty_lengths: +20, +20, +40 и +20 м. Это ветви двух общих префиксов. Два выигрыша удержания над hold1 — ветви одного anchors-префикса; обе лишь возвращают результат BF. На обучающих механизмах M3 совпала с BF по итоговому F/T на всех 32 новых потоках. На четырёх новых механизмах средняя разность к BF −0.008679.</p>'
    page+='<p>Это отрицательный результат конкретного малого пилота, а не опровержение обучения на собственных траекториях или согласованных действий вообще. Всего два начала на механизм, а обученная политика работает лишь при ≤12 живых трубах и ≤160 м траншеи. Длинные ресурсные проверки преимущественно исполняют BF fallback.</p>'
    page+='<h2>Парные результаты</h2><pre>'+html.escape(json.dumps(final['comparisons'],ensure_ascii=False,indent=2))+'</pre>'
    page+='<h2>Активация и ресурсы</h2><pre>'+html.escape(json.dumps({'activity':final['activity'],'resources':final['resources'],'audit':result['audits']['final_transcripts']},indent=2))+'</pre>'
    page+='<p>Две обучающие контрольные серии первоначально получили по два пустых native report, затем по 94 пропуска. Повтор на тех же 96 входах и неизменных solver/checker binaries прошёл полностью. Исходные отчёты сохранены; причина раннего завершения checker не установлена. Всего 912 успешных проверок, отдельно 4 неуспешных старта checker и 188 пропущенных резервов; лимит 1120 не превышен. Независимо воспроизведены 408 финальных ответных траекторий, проверены 288 совпадений общих префиксов и 24 точных повтора.</p>'
    page+='<h2>Следующая гипотеза, пока без запуска</h2><p>Оценивать option при продолжении текущей causal policy по нескольким возможным будущим, отдельно контролируя потери относительно BF. Это проверило бы оставшееся расхождение: нынешний teacher после первого блока снова оптимизирует будущее, а исполнять его должен ограниченный student. Собственные состояния исправляют только часть этого расхождения. Для следующей проверки нужны новые final seeds; текущий final уже использован.</p>'
    page+='<p>Все результаты относятся к этой ограниченной синтетике. Open15, старый validation и платформа не использовались; trial22 сохранён. Никакой автоматической замены конкурсного решения.</p><p><a href="results.json">Полные результаты и аудит</a> · <a href="protocol.json">Протокол</a> · <a href="freeze.json">Hashes источников и моделей</a> · <a href="completion.json">Завершение и лимит</a></p>'
    (ROOT/'report.html').write_text(page)
    print(json.dumps({'decision':result['decision'],'means':final['means'],'comparisons':final['comparisons'],'activity':final['activity'],'audits':result['audits']['final_transcripts']}),flush=True)
if __name__=='__main__':main()
