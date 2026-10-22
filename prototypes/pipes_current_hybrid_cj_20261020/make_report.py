#!/usr/bin/env python3
"""Self-contained report from the completed frozen comparison."""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = {"online_cj": "Online · Cangjie", "hybrid_cpp": "Гибрид · C++", "hybrid_cj": "Гибрид · Cangjie"}
SCENARIOS = {
    "archive_uniform": "Архив без Open15, равномерно",
    "additional_archive": "Дополнительная часть архива",
    "without_short": "Архив без коротких ≤200 команд",
    "long_only": "Только длинные >100 000 команд",
    "expensive_are_long": "Дорогие — длинные; остальные — короче",
    "short_only": "Только короткие ≤200 команд",
    "fresh_uniform": "Все 96 новых ловушек",
    "fresh_prefix": "60 новых ловушек с открытым префиксом",
    "fresh_nonpublic": "36 новых потоков без открытого префикса",
}

def table(headers, rows):
    return "<div class='scroll'><table><thead><tr>" + "".join(f"<th>{html.escape(x)}</th>" for x in headers) + \
        "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{x}</td>" for x in row) + "</tr>" for row in rows) + \
        "</tbody></table></div>"

def main():
    d = json.loads((HERE / "analysis.json").read_text())
    assert d["complete"]
    summary_rows = []
    text_lines = ["Осторожный гибрид на нынешнем online-ядре, Cangjie 1.2.0 -O2",
                  "Полный прогон: 2637 потоков × 3 варианта = 7911 запусков.",
                  "2537 архивных, ещё 4 для полного Open15, 96 независимых новых входов.", ""]
    platform_notice = ""
    platform_file = HERE / "platform/result.json"
    if platform_file.exists():
        platform = json.loads(platform_file.read_text())
        failed = ", ".join(map(str, platform["time_limit_tests"]))
        notice = (f"Сервер NSUts, отправка {platform['submission_id']}, {platform['compiler']}: "
                  f"{platform['accepted_tests']}/15 Accepted, Time Limit на тестах {failed}; "
                  f"счёт {platform['visible_score']:.5f}. "
                  "Все завершённые ответы совпали с локальными; незавершённые совпадают до обрыва. "
                  "Причина TLE (вычисления, I/O или runtime) ещё не установлена. "
                  "Эта версия пока не проходит серверные лимиты. "
                  "Приведённые ниже сценарии счёта рассчитаны по успешным локальным прогонам "
                  "и не описывают текущий результат на сервере.")
        text_lines[0:0] = [notice, ""]
        platform_notice = (f"<div class='note'><strong>Проверка на сервере · 20 октября 2026</strong>"
                           f"<p>{html.escape(notice)}</p>"
                           "<a href='platform/result.json'>Результат и сверка ответов</a> · "
                           "<a href='platform/result-1667192.png'>Снимок сайта</a></div>")
    for group, title in [("archive2537", "Архив · 2 537"), ("fresh96", "Новые · 96")]:
        group_data = d["summaries"][group]
        pair = group_data["hybrid_minus_online"]
        for m in ("online_cj", "hybrid_cj"):
            s = group_data["methods"][m]
            k = s["contest_adjusted_kpi"]
            summary_rows.append([title, LABELS[m], f"{k['mean']:.9f}", f"{k['min']:.6f}",
                                 str(s["counts_adjusted_kpi_below"]["0.5"]),
                                 str(s["counts_adjusted_kpi_below"]["0.85"])])
            text_lines.append(f"{title}, {LABELS[m]}: mean={k['mean']:.12f}, min={k['min']:.9f}, below .5={s['counts_adjusted_kpi_below']['0.5']}.")
        text_lines.append(f"Парно гибрид к online: {pair['wins']} выигрышей / {pair['ties']} совпадений / {pair['losses']} проигрышей; Δmean={pair['delta_mean_adjusted_kpi']:+.12f}.")
    score_rows = []
    for s in d["score_scenarios"]:
        a, b = (s["exact_expected"][m] for m in ("online_cj", "hybrid_cj"))
        delta = s["exact_delta"]
        score_rows.append([SCENARIOS[s["name"]], f"{a['total']:.6f}", f"{b['total']:.6f}",
                           f"<strong class='{'up' if delta >= 0 else 'down'}'>{delta:+.6f}</strong>",
                           f"{a['cangjie_top2_bonus']:.6f} / {b['cangjie_top2_bonus']:.6f}"])
        text_lines.append(f"Счёт, {SCENARIOS[s['name']]}: online {a['total']:.9f}, hybrid {b['total']:.9f}, Δ={delta:+.9f}.")
    resources = []
    for m in LABELS:
        s = d["summaries"]["all2637"]["methods"][m]
        cpu, rss = s["cpu_process_user_plus_system_s"], s["peak_rss_MiB"]
        resources.append([LABELS[m], f"{cpu['p95']:.4f}", f"{cpu['max']:.6f}",
                          f"{rss['max']:.3f}", str(s["contest_failures_total"])])
        text_lines.append(f"Ресурсы {LABELS[m]}: max CPU={cpu['max']:.6f}s, peak RSS={rss['max']:.3f}MiB, failures={s['contest_failures_total']}.")
    family_rows = []
    for name, item in d["fresh_families"].items():
        a, b = [item["methods"][m]["contest_adjusted_kpi"] for m in ("online_cj", "hybrid_cj")]
        p = item["pair"]
        family_rows.append([html.escape(name), str(item["count"]), f"{a['mean']:.6f}", f"{b['mean']:.6f}",
                            f"{p['wins']} / {p['ties']} / {p['losses']}", f"{p['delta_mean_adjusted_kpi']:+.6f}"])
    open_rows = []
    for c in sorted((x for x in d["per_case"] if x["public_number"] is not None), key=lambda c: c["public_number"]):
        a, b = [c["methods"][m] for m in ("online_cj", "hybrid_cj")]
        open_rows.append([str(c["public_number"]), f"{a['contest_adjusted_kpi']:.9f}",
                          f"{b['contest_adjusted_kpi']:.9f}", f"{c['delta']:+.9f}",
                          html.escape(c["hybrid_diagnostic"])])
    per_case = []
    for c in d["per_case"]:
        a, b = [c["methods"][m] for m in ("online_cj", "hybrid_cj")]
        per_case.append(dict(id=c["id"], name=c["name"], cohort=c["cohort"], family=c["family"],
                             open=c["public_number"], n=c["operations"], input=c["input"],
                             online=a["contest_adjusted_kpi"], hybrid=b["contest_adjusted_kpi"], delta=c["delta"],
                             cpu_o=a["cpu_process_s"], cpu_h=b["cpu_process_s"],
                             mem_o=a["peak_rss_MiB"], mem_h=b["peak_rss_MiB"],
                             diagnostic=c["hybrid_diagnostic"]))
    data = json.dumps(per_case, ensure_ascii=False).replace("<", "\\u003c")
    main_score = d["score_scenarios"][0]
    bars = []
    colors = ["#9aabc1", "#7db7f1", "#3b7ada", "#b694df"]
    parts = [("open15", "Open15"), ("closed11_weight4", "11 × 4"),
             ("closed4_weight10", "4 × 10"), ("cangjie_top2_bonus", "Бонус Cangjie")]
    for m in ("online_cj", "hybrid_cj"):
        e = main_score["exact_expected"][m]
        cells = "".join(f"<div title='{title}: {e[key]:.6f}' style='width:{e[key]/136.1*100:.6f}%;background:{color}'></div>"
                        for (key, title), color in zip(parts, colors))
        bars.append(f"<div class='barlabel'>{LABELS[m]} <b>{e['total']:.6f}</b></div><div class='bar'>{cells}</div>")
    parity = d["hybrid_cpp_cj_parity"]
    archive_pair = d["summaries"]["archive2537"]["hybrid_minus_online"]
    fresh_pair = d["summaries"]["fresh96"]["hybrid_minus_online"]
    invalid = sum(s["contest_failures_total"] for s in d["summaries"]["all2637"]["methods"].values())
    overall_cpu_ratio = d["summaries"]["all2637"]["paired_cpu_totals"]["hybrid_cj_over_online_cj"]
    long_cpu_ratio = d["summaries"]["long_gt100000"]["paired_cpu_totals"]["hybrid_cj_over_online_cj"]
    cj_cpp_ratio = d["summaries"]["all2637"]["paired_cpu_totals"]["hybrid_cj_over_cpp"]
    body = f"""<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Гибрид на нынешнем online · Cangjie · 2637 тестов</title>
<style>
:root{{color-scheme:light;font-family:system-ui,-apple-system,sans-serif;color:#182b45;background:#f3f6fa}}
body{{margin:0}}main{{max-width:1180px;margin:auto;padding:38px 22px 80px}}h1{{font-size:35px;line-height:1.15;max-width:900px}}
h2{{font-size:23px;margin-top:38px}}p,li{{line-height:1.6}}.lead{{font-size:19px;max-width:980px}}.muted{{color:#586c83}}
.card{{background:white;border:1px solid #d9e3ef;border-radius:14px;padding:20px 24px;margin:18px 0}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.cards .card{{margin:0}}.metric{{font-size:27px;font-weight:700}}
table{{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}}th,td{{padding:10px;border-bottom:1px solid #e1e8f1;text-align:right;vertical-align:top}}
th:first-child,td:first-child{{text-align:left}}th{{color:#485f79;background:#f5f8fc;white-space:nowrap}}.scroll{{overflow:auto}}td{{max-width:620px}}a{{color:#225db4}}
.up{{color:#146e50}}.down{{color:#b1363b}}.bar{{display:flex;height:25px;background:#e9eef5;border-radius:5px;overflow:hidden;margin-bottom:18px}}.barlabel{{display:flex;justify-content:space-between;margin:8px 0}}.bar div{{height:100%}}
.controls{{display:flex;gap:10px;flex-wrap:wrap;margin:15px 0}}input,select{{font:inherit;border:1px solid #c4d1e0;border-radius:7px;padding:10px;background:white}}input{{flex:1;min-width:180px}}.tiny{{font-size:12px}}.wide{{min-width:1150px}}
@media(max-width:700px){{.cards{{grid-template-columns:1fr}}h1{{font-size:28px}}main{{padding:20px 12px}}.card{{padding:16px}}}}
</style><main>
<p class="muted">Pipes · завершённый локальный эксперимент · 20 октября 2026</p>
<h1>Осторожный гибрид на нынешнем online-ядре: реальный перенос на Cangjie</h1>
{platform_notice}
<p class="lead">Проверены все 2 537 выбранных архивных тестов и 96 новых входов. Ещё четыре открытых теста добавлены для полного Open15.
Итого <b>2 637 потоков × 3 варианта = 7 911 запусков</b> с официальным интерактором.</p>
<div class="cards"><div class="card"><div class="metric">{parity['identical']} / 2637</div><p>Полностью совпавших трасс гибрида C++ и Cangjie.</p></div>
<div class="card"><div class="metric">{archive_pair['wins']} / {archive_pair['losses']}</div><p>Выигрышей / проигрышей гибрида против online на архиве; {archive_pair['ties']} совпадений.</p></div>
<div class="card"><div class="metric">{fresh_pair['wins']} / {fresh_pair['losses']}</div><p>Выигрышей / проигрышей на новых 96; {fresh_pair['ties']} совпадений.</p></div></div>
<div class="card"><b>Что именно сравнивалось.</b> Нынешнее online-ядро перенесено без изменений. Гибрид использует прежние открытые таблицы только при совпадающем префиксе,
согласованном ответе, допустимой позиции у края свободного участка и траншее не больше, чем у параллельного online.
Первый отказ навсегда переключает на online с импортом фактической раскладки и наблюдавшейся истории.
Порогов и таблиц по результатам новых тестов не подбирали. Guard ограничивает траншею во время replay, но не гарантирует итоговый KPI чистого online.</div>
<p class="lead"><b>Вывод: гибрид — немного более выгодный кандидат по проверенным сценариям счёта, но строгого превосходства нет.</b>
Главная прибавка сосредоточена в коротких архивных ловушках. Без потоков до 200 команд преимущество общего счёта с бонусом уменьшается до +0,005684 балла,
причём закрытая часть этого сценария слегка хуже у гибрида: разницу перекрывает Open15. На новых 96 средняя ΔKPI составляет лишь +0,000011319.
Исходный online сохранён; решение о финальной отправке требует проверки лимитов на Windows/G5420.</p>
<h2>KPI и нижний хвост</h2>
{table(["Набор", "Вариант", "Средний KPI", "Минимум", "KPI < 0,5", "KPI < 0,85"], summary_rows)}
<p class="muted">Это парное описательное сравнение. Архив уже использовался в исследованиях. Условие U≥0,85 в фильтре — объёмная верхняя оценка, а не сертификат достижимого оптимума.</p>
<h2>Общий конкурсный счёт с бонусом</h2>
<p><b>S = Open15 + 4·Σ₁₁ KPI + 10·Σ₄ KPI + 10·(два лучших KPI из этих четырёх).</b>
Бонус применяется к обоим Cangjie-вариантам; каждый выбирает собственные два лучших дорогих результата.
Ошибки и измеренные превышения ресурсов обнуляют KPI. Максимальная сумма весов с бонусом — 136,1.</p>
<div class="card">{''.join(bars)}<p class="tiny muted">Равномерный архивный сценарий. Слева направо: Open15, 11 тестов по 4, четыре по 10, бонус. Шкала 0–136,1.</p></div>
{table(["Модель закрытого набора", "Online + бонус", "Гибрид + бонус", "Δ гибрид − online", "Бонус online / гибрид"], score_rows)}
<p class="muted">В таблице точные математические ожидания при указанной модели выборки, а не прогноз настоящего закрытого счёта.
Без Open15 выбираются 15 разных тестов; для обоих методов используются одни и те же входы. В длинном/коротком смешанном сценарии группы раздельны.
Нелинейный бонус рассчитан точно по порядковым статистикам; в analysis.json также сохранены сводки по 100 000 парным выборкам каждого сценария.</p>
<h2>CPU time и память</h2>
{table(["Вариант", "CPU p95, с", "CPU максимум, с", "RSS максимум, MiB", "Ошибки / лимиты"], resources)}
<p><b>Всего {invalid} ошибок или превышений локальных лимитов.</b> Во всём прогоне работал один solver за раз;
Cangjie: <code>cjProcessorNum=1</code>. CPU — user+system всего процесса, включая GC и завершение, без деления на число ядер.
Лимиты: строго меньше 5 секунд CPU и 256 MiB.</p>
<p>Суммарный CPU гибрида на Cangjie выше чистого online на {(overall_cpu_ratio-1)*100:.2f}%.
На потоках длиннее 100 000 команд отношение равно {long_cpu_ratio:.4f} — практически одинаково в этом прогоне.
Относительно своего C++ эталона Cangjie-гибрид потребовал в {cj_cpp_ratio:.3f} раза больше суммарного CPU.</p>
<p class="muted">Локальная машина — macOS/Apple M1, без жёсткой привязки к одному логическому CPU. Это не замер Windows 10 / Pentium Gold G5420.
Готовый Windows-пакет закрепляет процесс на одном CPU до запуска и измеряет GetProcessTimes, peak working set и private commit.
Нативный Windows-прогон здесь не выполнялся; версию компилятора организаторов ещё требуется подтвердить.</p>
<h2>Новые независимые входы</h2>
<p>60 общих открытых префиксов с новыми продолжениями, 32 композиции без открытого префикса и четыре потока по 200 000 команд.
Генератор и seeds зафиксированы до оценки; совпадений со всеми 3 934 архивными потоками нет.
Отбора по результатам solver не было. Восемь механизмов комбинируют размеры, сроки жизни и порядок удалений.</p>
{table(["Механизм", "Тестов", "Online", "Гибрид", "Выигрыш / равно / проигрыш", "Δ среднего"], family_rows)}
<p class="muted">Ограничение этого holdout: для высокой финальной загрузки добавлены хвосты из вставок, составляющие 31–38% новой части.
Они могут сглаживать ущерб ранней фрагментации. Поэтому совпадение среднего здесь не доказывает устойчивости ко всем ловушкам.</p>
<h2>Полный Open15</h2>
<p>Online: <b>{d['open15']['online_cj']['adjusted']:.9f}</b>; гибрид: <b>{d['open15']['hybrid_cj']['adjusted']:.9f}</b>.</p>
{table(["№", "Online KPI", "Гибрид KPI", "Δ", "Переход replay → online"], open_rows)}
<h2>Все тесты и оставшиеся проигрыши</h2>
<p>По умолчанию первыми показаны потери гибрида. Отрицательная Δ означает более низкий итоговый KPI, даже при корректном fallback.</p>
<div class="card"><b>Конкретный контрпример: 16 команд, online 0,95 → гибрид 0,6333.</b>
На второй команде replay кладёт трубу длины 2 в позицию 2, а online — в позицию 18.
Replay прекращается уже на третьей команде. Позднее удаление PID 2 и PID 3 освобождает у online единый участок [14,20),
а у гибрида — отдельные [2,4) и [16,20). Последняя труба длины 6 вынуждает гибрид увеличить траншею с 40 до 60 м.
Online достигает объёмного потолка 38/40=0,95. Это существовавший архивный тест, не новый holdout.
<a href="counterexample.json">Все команды, ответы и проверяемые координаты</a>.</div>
<div class="controls"><input id="query" placeholder="Название, механизм или hash"><select id="cohort"><option value="">Все потоки</option><option value="archive">Архив</option><option value="fresh">Новые 96</option><option value="open">Open15</option></select>
<select id="order"><option value="loss">Сначала проигрыши</option><option value="gain">Сначала выигрыши</option><option value="cpu">Самые дорогие по CPU</option><option value="memory">Самые большие по памяти</option></select></div>
<p id="count" class="muted"></p><div class="scroll"><table class="wide"><thead><tr><th>Поток</th><th>N</th><th>Online</th><th>Гибрид</th><th>Δ</th><th>CPU online / гибрид</th><th>RSS online / гибрид</th><th>Переход</th></tr></thead><tbody id="cases"></tbody></table></div>
<h2>Исходники и воспроизводимость</h2>
<ul><li><a href="release/solution.cj">Гибрид на Cangjie — один файл для сборки</a>; <a href="methods/online_cj/solution.cj">чистый online на Cangjie</a>; <a href="cpp/solution.cpp">C++ эталон гибрида</a>.</li>
<li><a href="current-hybrid-cangjie-windows.zip">Windows-пакет: три исходника, runner и все 2 637 тестов</a>.</li>
<li><a href="analysis.json">Полные результаты и сценарии</a>, <a href="freeze.json">фиксация исходников / бинарников / входов</a>, <a href="protocol.json">протокол до оценки</a>.</li>
<li><a href="fresh/manifest.json">Новые тесты и seeds</a>, <a href="cpp/review.json">независимая проверка переноса</a>, <a href="final_audit.json">финальная проверка чисел и артефактов</a>.</li></ul>
<p class="muted tiny">Замороженные прежние решения сохранены. Платформа и отправки не затрагивались. Отчёт отражает локальные измерения и явно указанные сценарии.</p>
<script type="application/json" id="data">{data}</script>
<script>
const data=JSON.parse(document.getElementById('data').textContent);
const byId=id=>document.getElementById(id);
const fmt=(v,n)=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(n):'—';
function show(){{
 const q=byId('query').value.toLowerCase(),group=byId('cohort').value,order=byId('order').value;
 let rows=data.filter(r=>(!group||(group==='open'?r.open!==null:r.cohort===group))&&[r.name,r.family,r.id].join(' ').toLowerCase().includes(q));
 rows.sort((a,b)=>order==='gain'?b.delta-a.delta:order==='cpu'?b.cpu_h-a.cpu_h:order==='memory'?b.mem_h-a.mem_h:a.delta-b.delta);
 byId('count').textContent=`Найдено ${{rows.length}}; показано до 300. Полный набор — в analysis.json.`;
 const body=byId('cases');body.replaceChildren();
 for(const r of rows.slice(0,300)){{
  const tr=document.createElement('tr'),title=document.createElement('td'),a=document.createElement('a');
  a.href=r.input;a.textContent=r.open!==null?`Open ${{r.open}}`:r.cohort==='fresh'?r.name:r.id.slice(0,16);
  title.append(a);const family=document.createElement('div');family.className='tiny muted';family.textContent=r.family;title.append(family);tr.append(title);
  const vals=[r.n,r.online.toFixed(6),r.hybrid.toFixed(6),(r.delta>=0?'+':'')+r.delta.toFixed(6),`${{fmt(r.cpu_o,4)}} / ${{fmt(r.cpu_h,4)}}`,`${{fmt(r.mem_o,2)}} / ${{fmt(r.mem_h,2)}}`,r.diagnostic];
  vals.forEach((v,i)=>{{const td=document.createElement('td');td.textContent=v;if(i===3)td.className=r.delta<0?'down':'up';if(i===6)td.className='tiny';tr.append(td)}});body.append(tr);
 }}
}}
for(const id of ['query','cohort','order'])byId(id).addEventListener('input',show);show();
</script></main></html>"""
    (HERE / "report.html").write_text(body)
    text_lines += ["", "Ограничения:"] + d["limitations"]
    (HERE / "REPORT.txt").write_text("\n".join(text_lines) + "\n")
    print("Wrote report.html and REPORT.txt")

if __name__ == "__main__":
    main()
