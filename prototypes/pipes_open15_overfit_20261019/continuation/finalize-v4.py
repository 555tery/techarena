"""Audit actual final solver transcripts and write an honest local-only report."""
import hashlib,json,html,shutil
from fractions import Fraction
from pathlib import Path
from datetime import datetime
from runtime import ROOT,PARENT,REPO,e
release=ROOT/'release-v4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
audit=json.loads((release/'plan-audit.json').read_text());cases={str(c['case']):c for c in audit['cases']}
open_summary=json.loads((release/'open/harness/summary.json').read_text());actual=[];bound=Fraction()
for r in open_summary['records']:
 p=Path(r['test_file']);tokens=p.read_text().split();weight=Fraction(tokens[0]);n=int(tokens[1]);commands=list(map(int,tokens[2:2+n]));answers=Path(r['judge_output_file']).read_text().splitlines();assert len(answers)==n
 cells=bytearray();live={};pid=0;T=0;F=0;peak=0
 for command,line in zip(commands,answers):
  fields=list(map(int,line.split()))
  if command>0:
   assert len(fields)==2;digs,x=fields;assert digs>=0 and x>=0;T+=20*digs;assert x+command<=T
   if len(cells)<T:cells.extend(bytes(T-len(cells)))
   assert not any(cells[x:x+command]);cells[x:x+command]=bytes([1])*command;pid+=1;live[pid]=(x,command);F+=command;peak=max(peak,F)
  else:
   assert len(fields)==1;x,l=live.pop(-command);assert fields[0]==x;assert cells[x:x+l]==bytes([1])*l;cells[x:x+l]=bytes(l);F-=l
 c=cases[r['case']];lower=20*((peak+19)//20);assert (F,T,lower)==(c['F'],c['T'],c['lower_T']);assert sha(p)==c['input_sha256'];bound+=weight*F/lower
 actual.append({'case':r['case'],'commands':n,'T':T,'F':F,'volume_lower_T':lower,'answers_sha256':sha(Path(r['judge_output_file'])),'physical_cell_replay':True})
phases={p:json.loads((release/p/'verification.json').read_text()) for p in ['open','divergence','repeat']}
score=Fraction(audit['exact_fraction']);result={'status':'verified_local_candidate','scope':'intentional_complete_Open15_overfit','platform_submissions':0,'canonical_trial22_changed':False,'public_future_used_offline':True,'hidden_generalization_claim':False,'mathematical_optimum_reached':score==bound,'score':float(score),'score_exact':str(score),'volume_ceiling':float(bound),'volume_ceiling_exact':str(bound),'remaining_gap':float(bound-score),'trial22_local_score':30.090967891345,'correctness_checks':60,'repeat_answers_identical':True,'all_shared_prefix_actions_consistent':True,'independent_actual_output_replay':actual,'cases':audit['cases'],'max_cpu_s':max(v['max_cpu'] for v in phases.values()),'max_rss_mib':max(v['max_rss'] for v in phases.values()),'source':str(release/'solution.cpp'),'source_sha256':sha(release/'solution.cpp'),'source_bytes':(release/'solution.cpp').stat().st_size,'binary_sha256':sha(release/'solver'),'processes_alive_at_finish':[],'continuation_authorization':str(ROOT/'authorization.json'),'updated_at':datetime.now().astimezone().isoformat(),'remaining_excess_m':{str(c['case']):c['T']-c['lower_T'] for c in audit['cases'] if c['T']>c['lower_T']},'research_limits':'The bounded local repairs and randomized searches did not reach the remaining two volume bounds; this is not an impossibility proof.'}
e.save(ROOT/'final.json',result);e.save(release/'actual-output-audit.json',actual)
for suffix in ['html','json']:
 old=PARENT/f'report.{suffix}';copy=PARENT/f'report-initial.{suffix}'
 if old.exists() and not copy.exists():shutil.copy2(old,copy)
e.save(PARENT/'report.json',result)
rows=''.join(f'<tr class="{"gap" if c["T"]>c["lower_T"] else "ok"}"><td>{c["case"]}</td><td>{c["T"]:,}</td><td>{c["lower_T"]:,}</td><td>{c["T"]-c["lower_T"]}</td><td>{c["weighted_score"]:.10f}</td></tr>' for c in audit['cases'])
page=f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Open15 — намеренный подгон, проверенный результат</title><style>
:root{{font-family:system-ui,sans-serif;color:#1c2a39;background:#f4f6f8}}body{{max-width:1060px;margin:36px auto;padding:0 24px 48px;line-height:1.6}}h1{{font-size:31px;line-height:1.2;margin-bottom:14px}}h2{{font-size:21px;margin-top:30px}}.badge{{font-size:13px;color:#4b627a;letter-spacing:.05em}}.notice{{padding:16px 20px;background:#fff1d5;border-left:4px solid #b77912;border-radius:5px}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:24px 0}}.metric{{padding:20px;background:white;border:1px solid #dce3e9;border-radius:10px}}.metric b{{display:block;font-size:27px}}.metric span{{font-size:14px;color:#5d6c7d}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:10px 12px;text-align:right;border-bottom:1px solid #e4e9ee}}th:first-child,td:first-child{{text-align:left}}th{{font-size:13px;color:#526174}}.gap{{background:#fff1d5}}a{{color:#175cb0}}code{{overflow-wrap:anywhere;font-size:13px}}.muted{{color:#607184;font-size:14px}}@media(max-width:760px){{.metrics{{grid-template-columns:1fr}}body{{padding:0 14px}}table{{font-size:13px}}th,td{{padding:7px 5px}}}}
</style></head><body><div class="badge">PIPES · ОТДЕЛЬНАЯ ЛОКАЛЬНАЯ ВЕТКА · 19 ОКТЯБРЯ 2026</div><h1>Open15: полный подгон с согласованными действиями</h1>
<div class="notice"><b>Намеренное запоминание открытых тестов.</b> При построении таблиц используются все будущие команды и удаления Open15. Это явно указано в начале C++-файла. Результат не является доказательством качества на закрытых тестах.</div>
<div class="metrics"><div class="metric"><b>{float(score):.11f}</b><span>официальный локальный score · 15/15 корректных</span></div><div class="metric"><b>{float(bound):.11f}</b><span>верхняя граница по пиковому живому объёму</span></div><div class="metric"><b>{float(bound-score):.11f}</b><span>остающийся разрыв · абсолютный максимум не достигнут</span></div></div>
<p>Тринадцать тестов достигли объёмных границ. В тестах 11 и 15 остаётся по 40 метров лишней траншеи. Сумма trial22 на том же наборе — 30,09096789; новый локальный прирост — {float(score)-result['trial22_local_score']:.8f}. Результат в таблице платформы не изменён: отправок в этой ветке не было.</p>
<p><a href="continuation/release-v4/solution.cpp"><b>Проверенный standalone C++ исходник</b></a> · <a href="continuation/final.json">Полный отчёт и SHA-256</a> · <a href="continuation/release-v4/actual-output-audit.json">Независимый replay фактических ответов</a></p>
<h2>Что проверено</h2><p>На одной и той же сборке выполнены 60 проверок: полный Open15, 30 входов с ранним или поздним отклонением от известного префикса, затем повтор Open15. Все корректны. Ответы повторного Open15 совпали побайтово. Фактические ответы всех 15 тестов дополнительно проверены отдельной моделью занятости каждого метра.</p><p>Максимум CPU решения в этих проверках: {result['max_cpu_s']:.6f} с; RSS: {result['max_rss_mib']:.3f} MiB. Проверены hashes входов, исходника и бинарного файла. Это локальные измерения, серверный результат ещё не получен.</p>
<h2>Единая программа, а не сумма отдельных идеальных ответов</h2><p>У тестов 5/9 совпадают первые 125 команд, у 8/13 — 388, у 11/15 — 4999. Все действия на общих префиксах согласованы. Таблицы построены обратной укладкой по известным срокам жизни, заполнением дырок через knapsack и перестановками пространственных компонентов. Общая программа читает одну команду и выдаёт один ответ с flush; будущие данные уже зашиты в таблицы.</p>
<p>При первом несовпадении с известными продолжениями программа переходит на Best Fit из фактически занятого состояния. Проверки отклонений подтверждают корректность этого перехода, но не высокое качество на новых входах: ранее выкопанная траншея сохраняется.</p>
<h2>Все 15 тестов</h2><table><thead><tr><th>Тест</th><th>Траншея, м</th><th>Граница, м</th><th>Лишние, м</th><th>Вклад в score</th></tr></thead><tbody>{rows}</tbody></table>
<p class="muted">Граница: T ≥ 20·ceil(maxₜ live_volume(t)/20), score ≤ Σ weightᵢ·Fᵢ/T_lower,ᵢ. Равенство с этой границей доказано для 13 тестов текущей программой. Неудача локального ремонта для 11/15 не доказывает невозможность улучшения.</p>
<h2>Артефакт и состояние</h2><p>SHA-256 исходника: <code>{result['source_sha256']}</code><br>Размер исходника: {result['source_bytes']:,} байт. Сборка: C++17, clang++ -O2. Ограничения платформы на размер исходника в этой локальной работе не проверялись.</p><p>Основной trial22 не менялся. Старые кампании, Shinka и validation не возобновлялись. Поисковые процессы завершены; автоматического продолжения нет. Снятие резерва лимита относится только к этой ветке и записано в <a href="continuation/authorization.json">авторизации продолжения</a>.</p><p class="muted"><a href="report-initial.html">Первоначальный частичный отчёт, сохранён без изменений</a> · <a href="continuation/release-v4/open/verification.json">Open15</a> · <a href="continuation/release-v4/divergence/verification.json">Отклонения</a> · <a href="continuation/release-v4/repeat/verification.json">Повтор</a></p></body></html>'''
(PARENT/'report.html').write_text(page)
index=REPO/'wiki/research/Index.md';text=index.read_text();lines=text.splitlines()
for i,line in enumerate(lines):
 if line.startswith('- [Намеренный полный подгон Open15, отдельная ветка]'):
  lines[i]='- [Намеренный полный подгон Open15, отдельная ветка](../../prototypes/pipes_open15_overfit_20261019/report.html) — после прямого разрешения продолжить без резерва получен проверенный standalone solver: Open15 **30.75463292044**, 15/15 корректных, 13 объёмных границ; до потолка30.75747404827 остаётся0.00284112783 (тесты11/15 по40м). На final-сборке60/60 проверок, включая30 отклонений префикса и побайтовый повтор. Код явно маркирован full overfit; обобщаемость не заявляется. Отправок нет, trial22 не менялся, поиск завершён.'
index.write_text('\n'.join(lines)+'\n')
print(json.dumps({k:result[k] for k in ['score','volume_ceiling','remaining_gap','source_sha256','source_bytes','max_cpu_s','max_rss_mib']}))
