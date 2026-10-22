"""Independent exact-rational score audit and a compact human report."""
from collections import defaultdict
from fractions import Fraction
import html
import json
from pathlib import Path
import re
from audit import ROOT, read_input, verify

def mean(v):return float(sum(v,Fraction())/len(v)) if v else None
def load(phase,label):
    p=ROOT/'evaluations'/phase/label/'harness/summary.json'
    if not p.exists():return None
    s=json.loads(p.read_text());assert s['case_count']==s['ok_count']
    return {r['case']:r for r in s['records']}

def quality(rows,names):
    return {label:mean([Fraction(data[n]['occupied_length_m'],data[n]['trench_length_m']) for n in names]) for label,data in rows.items()}

def compare(rows,names,a,b):
    deltas=[];wins=losses=ties=0;trench=[]
    for n in names:
        x,y=rows[a][n],rows[b][n]
        d=Fraction(x['occupied_length_m'],x['trench_length_m'])-Fraction(y['occupied_length_m'],y['trench_length_m'])
        deltas.append(d);wins+=d>0;losses+=d<0;ties+=d==0
        trench.append(x['trench_length_m']-y['trench_length_m'])
    return {'wins':wins,'losses':losses,'ties':ties,'mean_delta':mean(deltas),'worst_delta':float(min(deltas)),
            'best_delta':float(max(deltas)),'mean_extra_trench_m':sum(trench)/len(trench)}

def main():
    result={'scope':'One fixed small-state student; fresh mechanisms are not an estimate of hidden leaderboard performance.',
            'source_sha256':{},'phases':{}}
    labels=['candidate','kernel_bf','bf','ss','trial22']
    for phase in ['train','dev','final']:
        records=json.loads((ROOT/'data'/f'{phase}.json').read_text())['records']
        rows={l:load(phase,l) for l in labels};rows={k:v for k,v in rows.items() if v is not None}
        names=[r['name'] for r in records if r['branch']!='resource']
        fam=sorted({r['family'] for r in records if r['branch']!='resource'})
        out={'cases':len(names),'means':quality(rows,names),'families':{},'branches':{},'comparisons':{}}
        for f in fam:out['families'][f]=quality(rows,[r['name'] for r in records if r['family']==f and r['branch']!='resource'])
        for b in ['growth','drain','size_shift','early_stop']:out['branches'][b]=quality(rows,[r['name'] for r in records if r['branch']==b])
        for b in ['bf','ss','trial22']:
            if b in rows:out['comparisons']['candidate_vs_'+b]=compare(rows,names,'candidate',b)
        if phase=='final':
            out['mechanism_split']={}
            for k,families in [('same_mechanisms_new_seeds',fam[:0]+['renewal','complements','size_survival','bursts']),
                               ('new_mechanisms',['alternating_support','anchors','cohorts','sawtooth'])]:
                selected=[r['name'] for r in records if r['family'] in families and r['branch']!='resource']
                out['mechanism_split'][k]={'means':quality(rows,selected),'candidate_vs_bf':compare(rows,selected,'candidate','bf')}
            checked=prefix_checks=0;active=changed=0;resources={}
            for label,data in rows.items():
                cpu=rss=0;groups=defaultdict(list)
                for r in records:
                    item=data[r['name']]
                    commands=read_input(ROOT/'data'/phase/(r['name']+'.in'))
                    replies=Path(item['judge_output_file']).read_text().splitlines()
                    checked_values=verify(commands,replies)
                    assert checked_values['T']==item['trench_length_m'] and checked_values['F']==item['occupied_length_m']
                    assert abs(float(Fraction(checked_values['F'],checked_values['T']))-item['kpi'])<1e-12
                    checked+=1;cpu=max(cpu,item['solver_cpu_total_s']);rss=max(rss,item['solver_peak_rss_mb'])
                    if r['branch']!='resource':groups[r['base']].append(replies[:24])
                    if label=='candidate':
                        m=re.search(r'decisions=(\d+) changed=(\d+)',item['candidate_stderr'])
                        if m:active+=int(m[1]);changed+=int(m[2])
                    if label=='kernel_bf':assert replies==Path(rows['bf'][r['name']]['judge_output_file']).read_text().splitlines()
                for g in groups.values():
                    assert len(g)==4 and all(x==g[0] for x in g);prefix_checks+=3
                resources[label]={'max_cpu_s':cpu,'max_rss_mib':rss}
            out['independent_audit']={'full_transcripts_replayed':checked,'paired_prefix_comparisons':prefix_checks,'kernel_bf_equals_independent_bf_all_cases':True,'passed':True}
            out['candidate_activity']={'decisions':active,'changed_vs_BF_in_own_state':changed}
            out['resources']=resources
        result['phases'][phase]=out
    result['teacher']=json.loads((ROOT/'teacher-independent-audit.json').read_text())
    result['teacher'].pop('examples',None)
    result['coordination_fixture']=json.loads((ROOT/'coordination-fixture.json').read_text())
    fit=json.loads((ROOT/'model/fit.json').read_text())
    result['fit']={k:v for k,v in fit.items() if k!='weights'}
    for l in labels:
        m=json.loads((ROOT/'builds'/l/'manifest.json').read_text());result['source_sha256'][l]=m['source_files_sha256'];
    final=result['phases']['final']
    result['decision']='reject_candidate' if final['comparisons']['candidate_vs_bf']['mean_delta']<=0 else 'local_pilot_improvement_only_no_promotion'
    (ROOT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    def table(data):
        cols=list(next(iter(data.values())).keys())
        return '<table><tr><th>Срез</th>'+''.join('<th>'+html.escape(c)+'</th>' for c in cols)+'</tr>'+''.join('<tr><th>'+html.escape(k)+'</th>'+''.join(f'<td>{v[c]:.6f}</td>' for c in cols)+'</tr>' for k,v in data.items())+'</table>'
    tables=table({k:v['means'] for k,v in result['phases'].items() if k!='train'})+table(final['families'])+table(final['branches'])
    title='Проверка совместного планирования и причинной политики'
    verdict='Кандидат отклонён: на свежей полной проверке не превзошёл BF.' if result['decision']=='reject_candidate' else 'Локальный пилот улучшил BF; перенос на конкурс пока не установлен.'
    page=f'''<!doctype html><meta charset="utf-8"><title>{title}</title><style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px;color:#182334;background:#f7f8fa}}table{{border-collapse:collapse;background:white;width:100%;margin:22px 0}}td,th{{padding:9px;border-bottom:1px solid #ddd;text-align:right}}th:first-child{{text-align:left}}pre{{white-space:pre-wrap;background:white;padding:18px}}.card{{padding:20px;background:#e6edf5;border-radius:12px}}</style>
    <h1>{title}</h1><p class="card">{verdict} Источники и модель заморожены до генерации final; platform, Open15 и старый validation не использовались.</p>
    <p>Teacher оптимизирует все последующие размещения до конца короткого потока, beam width 12. Student — причинная линейная модель на взаимодействиях истории и геометрии, до 12 живых труб и 160 м, затем обычный BF. Учитель видит будущее только офлайн; рабочая программа читает по одной команде.</p>
    <h2>Конкретная причина попробовать совместное планирование</h2><p>На [7,7,6,−2,5,−1,−3,15], при первой трубе в позиции 0, BF и все 81 одиночных вмешательства с дальнейшим BF требуют 40 м. Точный совместный план требует 20 м. Это диагностический пример, а не результат онлайн-алгоритма.</p>
    <h2>Среднее F/T</h2><p>Dev: 32 потока. Final: 96 потоков, 8 механизмов × 3 независимых начала × 4 продолжения одного префикса; ещё 4 потока по 200 000 команд проверяют ресурсы и корректность и не входят в среднее. Семейства и ветки равновесны. Нулевое F сохранено.</p>{tables}
    <h2>Парные результаты и проверка</h2><pre>{html.escape(json.dumps({'comparisons':final['comparisons'],'resources':final['resources'],'audit':final['independent_audit'],'activity':final['candidate_activity']},ensure_ascii=False,indent=2))}</pre>
    <h2>Границы вывода</h2><p>Контроль trial22 сохранён без изменений. Малые обучающие состояния, ограниченный beam и одна линейная модель не исчерпывают подход. Улучшение учителя не доказывает, что студент может его повторить. Синтетика не даёт оценки неизвестного распределения закрытых тестов; настройки по final не менялись. Никакой отправки на платформу не было.</p><p><a href="results.json">Полные числа и hashes</a> · <a href="teacher-independent-audit.json">Независимый аудит учителя</a> · <a href="protocol.json">Зафиксированный протокол</a></p>'''
    (ROOT/'report.html').write_text(page)
    print(json.dumps({'decision':result['decision'],'means':final['means'],'comparisons':final['comparisons'],'audit':final['independent_audit'],'resources':final['resources']}))
if __name__=='__main__':main()
