"""Render the completed fixed comparison; no experiments or model calls."""
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
R=json.loads((ROOT/'results.json').read_text())
A=json.loads((ROOT/'independent-result-audit.json').read_text())
D=json.loads((ROOT/'dataset/design.json').read_text())
F=json.loads((ROOT/'freeze.json').read_text())
labels=('trial22','bf','ss')
names={'trial22':'trial22','bf':'BF','ss':'SS'}
family_names={
 'size_lifetime_inversion':'Инверсия связи размера и времени жизни',
 'fifo_lifo_reversal':'FIFO ↔ LIFO при прежнем законе размеров',
 'renewal_deadlines':'Серии вставок и тяжёлый хвост сроков',
 'moving_support_aba':'Смена размеров A → B → A → C',
 'asynchronous_cohorts':'Асинхронные группы и выжившие объекты',
 'anchor_replacement':'Замена старых долгоживущих объектов',
 'avalanche_regrowth':'Массовое освобождение и повторный рост',
 'reservoir_growth_drain':'Ограниченный пул → рост → освобождение',
 'jittered_motifs':'Повторяемые мотивы с шумом и сменой удалений',
 'prefix_branch':'Разные правила продолжения после префикса',
 'micro_rank_bursts':'Микропотоки со сменой ранга удалений',
 'micro_complements':'Микропотоки с дополняющими размерами',
}


def table(headers,rows,caption=None):
    body='<table>'
    if caption: body+='<caption>'+html.escape(caption)+'</caption>'
    body+='<thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'
    for row in rows:
        body+='<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>'
    return body+'</tbody></table>'


def f(x): return f'{x:.6f}'
def pp(x): return f'{100*x:+.4f}'


body='''<h1>trial22, BF и SS: независимое сравнение</h1>
<p>Завершено 19 октября 2026. Реализации BF/SS и независимый генератор подготовлены
двумя GPT-6.1 Sol; координатор проверил код, определения, ввод, результаты и ресурсы.
Платформа, Open15, старый validation и завершённые кампании не использовались.</p>
<p><strong>На этом заранее зафиксированном наборе среднее F/T: SS &gt; BF &gt; trial22.</strong>
Trial22 уступил SS в среднем по 11 из 12 семейств. Это свидетельство ограниченной
переносимости текущего решения, но не доказательство причины переобучения и не
прогноз распределения закрытых тестов. Код алгоритмов после результатов не менялся.</p>
<p>48 независимо сгенерированных базовых потоков: 12 механизмов × 4 длины/seed.
Каждый оценён на точных префиксах 20%, 40%, 60%, 80%, 100%: всего 240 входов.
Десять длинных семейств имеют длины 12 000 / 32 000 / 80 000 / 200 000 команд;
два микросемейства — 80 / 160 / 240 / 400. В micro пиковый живой объём ≤60 м;
это ограничивает объёмную нижнюю границу тремя секциями, но не длину траншеи решателя.</p>
<p>Основная метрика — F/T. Семейства, четыре базы внутри семейства и пять остановок
внутри базы имеют равный вес. H0 = 20·ceil(пиковый живой объём / 20) — оптимистичная
объёмная граница; достижимость её каузальным алгоритмом не предполагается.
34 входа завершаются при F=0; они сохранены. Среднее F/peak=0,6562, диапазон 0…1;
49 концовок ниже 20% пика, 90 выше 95%. Поэтому абсолютное среднее F/T здесь
сильно зависит от остановок и напрямую не сопоставляется с конкурсной суммой.</p>'''
rows=[]
for label in labels:
    v=R['overall']['algorithms'][label]
    batches=[json.loads((ROOT/'evaluations'/phase/label/'manifest.json').read_text()) for phase in ('preflight','final','repeat')]
    rows.append([names[label],f(v['mean_F_over_T']),f'{100*(v["mean_T_over_H0"]-1):.3f}%',
                 f'{max(b["max_cpu"] for b in batches):.3f}',f'{max(b["max_rss"] for b in batches):.3f}'])
body+=table(['Алгоритм','Среднее F/T','Средний (T/H0 − 1)','Макс. CPU, с','Макс. RSS, MiB'],rows,'Общий результат и ресурсы')
rows=[]
for pair in ('trial22_minus_bf','ss_minus_bf','trial22_minus_ss'):
    v=R['overall']['pairs'][pair]
    rows.append([pair.replace('_minus_',' − '),pp(v['mean_delta_F_over_T']),
                 '/'.join(map(str,v['wins_losses_ties_F_over_T'])),
                 '/'.join(map(str,v['wins_losses_ties_trench']))])
body+=table(['Пара','ΔF/T, процентные пункты','Победы/поражения/ничьи по F/T','По длине траншеи'],rows,'Парные сравнения; меньшая траншея считается победой')
body+='<p>240 входов не являются 240 независимыми наблюдениями: пять префиксов принадлежат одной базе. При F=0 равные F/T не означают равные траншеи.</p>'
rows=[]
for spec in D['families']:
    family=spec['id'];v=R['families'][family]
    rows.append([family_names[family],*[f(v['algorithms'][label]['mean_F_over_T']) for label in labels],
                 pp(v['pairs']['trial22_minus_ss']['mean_delta_F_over_T'])])
body+=table(['Семейство (20 входов)','trial22','BF','SS','trial22 − SS, п.п.'],rows,'Результаты по семействам')
rows=[]
for stop,v in R['stops'].items():
    rows.append([str(round(float(stop)*100))+'%',*[f(v['algorithms'][label]['mean_F_over_T']) for label in labels],
                 pp(v['pairs']['trial22_minus_ss']['mean_delta_F_over_T'])])
body+=table(['Момент остановки','trial22','BF','SS','trial22 − SS, п.п.'],rows,'Раннее завершение — каждый столбец остановки содержит 48 баз')
body+='''<p><strong>Главное наблюдение:</strong> на 20% длины trial22 уступает SS примерно
на 1,206 п.п., на полных потоках — лишь на 0,007 п.п. Первая смена режима задана
на 25%, поэтому самые большие ранние провалы нельзя автоматически приписать
именно плохой адаптации после смены режима. Тестирование только полных концовок
скрывало бы значительную часть этих различий.</p>
<p>На длинных потоках средние trial22/BF/SS равны 0,686986 / 0,689162 / 0,690206;
на micro — 0,304375 / 0,310762 / 0,310762. На семействах замены долгоживущих
объектов trial22 немного обошёл SS: 0,669561 против 0,669391.
SS обошёл BF в 5 семействах, уступил в 4 и совпал по среднему в 3: его небольшое
общее преимущество не означает универсального превосходства.</p>
<p>Конкретный micro-пример: F=46 м, trial22 выкопал 80 м, BF и SS — 60 м;
F/T составил 0,575 против 0,766667. Первая разница возникла уже на третьей
команде: после вставок 5,5 запрос длины 1 trial22 разместил по адресу 19,
BF/SS — по адресу 10. Это фиксирует разницу политик, но не доказывает, что
одна эта развилка вызвала весь итоговый проигрыш.</p>
<p>В раннем префиксе инверсии времени жизни (база r2, 20%) trial22 получил
20 200 м против BF 17 600 и SS 17 640 м. На полной той же базе длины составили
267 600 / 267 780 / 267 580 м. В двух приведённых ранних провалах primal-DP
trial22 вообще не активировался по сохранённым счётчикам. Поэтому обвинять
последнюю DP-правку в этих потерях по данному эксперименту нельзя.</p>'''
rows=[]
for pair,v in A['leave_one_family_out'].items():
    rows.append([pair.replace('_minus_',' − '),pp(v['min']),pp(v['max'])])
body+=table(['Пара','Мин. Δ, п.п.','Макс. Δ, п.п.'],rows,'Чувствительность среднего: исключение по одному семейству')
body+='''<p>Порядок общих средних сохраняется при исключении любого одного семейства.
Предусмотренный bootstrap ресэмплирует целые базы внутри семейства; его числа
сохранены в results.json. В каждой ячейке «семейство × длина» всего один seed,
поэтому ресэмплирование одновременно меняет состав длин. Эти интервалы описывают
чувствительность к наблюдавшимся базам и не являются калиброванными доверительными
интервалами для фиксированной длины или для неизвестных закрытых тестов.</p>
<p><strong>Проверки:</strong> 720 основных оценок + 48 коротких preflight + 12 повторов
= 780 официальных проверок, все корректны; CPU &lt;5 с, RSS &lt;256 MiB.
Независимый координаторский full-Phi/bitmap oracle проверил по 29 871 команде
на BF и SS, включая interactive flush. Все 576 сравнений короткого и длинного
answer-prefix совпали; все 12 повторов дали побайтно те же ответы.
Итоговые средние дополнительно пересчитаны координатором через точные дроби
по иерархии «остановка → база → семейство». Одновременно работали не более двух
native workers. Источники, генератор и параметры фиксированы до свежей entropy.</p>
<p><strong>Границы вывода:</strong> механизмы намеренно созданы для проверки режимных
переходов и ранних остановок; неизвестно, как часто они встречаются на hidden.
Новые seed не означают, что все абстрактные механизмы никогда ранее не рассматривались.
Семейство prefix_branch содержит разные правила продолжения, но не парные ветви
одного реализованного префикса; branch смешан с длиной. Нет оснований объявлять
trial22 универсальным алгоритмом или заменять конкурсную версию только по этой синтетике.
Его следует сохранять как специалиста и проверять новые идеи относительно BF и SS.</p>'''
body+='<details><summary>Фиксированные определения и воспроизводимость</summary><p>BF выбирает самую короткую подходящую физическую щель; tie — меньший адрес. SS минимизирует точное ΔΣcount(h)² по всем подходящим coalesced gaps, включая свободный хвост; tie — меньшая щель, затем адрес. Оба размещают слева и расширяют траншею минимально только при отсутствии подходящей щели. Это конкретная версия SS, не утверждение обо всех его вариантах.</p><pre>'+html.escape(json.dumps({'solver_sha256':F['solver_sha256'],'binary_sha256':F['binary_sha256'],'generator_sha256':F['generator_sha256'],'design_sha256':F['design_sha256']},indent=2))+'</pre></details>'
body+='<p>Артефакты: <a href="paired-cases.csv">240 парных строк CSV</a> · <a href="results.json">полные результаты JSON</a> · <a href="PROTOCOL.md">исходный протокол</a> · <a href="data/generated/manifest.json">seeds и манифест входов</a> · <a href="first-divergences.json">первые расхождения</a> · <a href="completion.json">статус завершения</a>.</p>'
document='<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>trial22 / BF / SS — независимое сравнение</title><style>body{font:16px/1.55 system-ui,sans-serif;max-width:1250px;margin:40px auto;padding:0 24px;color:#18202b;background:#fff}h1{font-size:29px}p{max-width:1050px}table{border-collapse:collapse;width:100%;margin:24px 0;font-size:14px}caption{text-align:left;font-weight:650;margin:0 0 8px}th,td{border-bottom:1px solid #d9e0e8;padding:9px;text-align:right;font-variant-numeric:tabular-nums}th:first-child,td:first-child{text-align:left}thead{background:#edf1f6}pre{overflow:auto;background:#f3f5f7;padding:16px;font-size:12px}a{color:#1555a0}details{margin:24px 0}strong{font-weight:650}</style><main>'+body+'</main></html>'
(ROOT/'report.html').write_text(document)
print(ROOT/'report.html')
