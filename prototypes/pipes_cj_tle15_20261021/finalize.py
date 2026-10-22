#!/usr/bin/env python3
"""Publish a frozen release only after complete paired validation."""
import hashlib,html,json,platform,shutil,statistics
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'pipes_current_hybrid_cj_20261020'
SOURCE_SHA='585c6e7ffa9cedc20f1dd0efeaed59fdef39c62dba0e3c57853faba3b6024ad8'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):return [json.loads(x) for x in Path(p).read_text().splitlines()]
def summarize(rs):
 return dict(completed=len(rs),response_kpi_matches=sum(r['response_equal'] and r['kpi_equal'] for r in rs),resource_failures=sum(not r['within_limits'] for r in rs),cpu_max_s=max(r['solver_cpu_total_s'] for r in rs),rss_max_mib=max(r['solver_peak_rss_mb'] for r in rs),cpu_total_s=sum(r['solver_cpu_total_s'] for r in rs),slowest=[dict(id=r['id'],origin=r.get('origin',r.get('family')),cpu_s=r['solver_cpu_total_s'],rss_mib=r['solver_peak_rss_mb']) for r in sorted(rs,key=lambda r:r['solver_cpu_total_s'],reverse=True)[:5]])
def main():
 source=HERE/'candidate-final/solution.cj';assert sha(source)==SOURCE_SHA
 freeze=json.loads((BASE/'freeze.json').read_text());expected={x['id'] for x in freeze['cases']};fresh=json.loads((HERE/'fresh/manifest.json').read_text());new_ids={x['id'] for x in fresh['cases']}
 measurements={}
 for opt in ('o0','o2'):
  build=json.loads((HERE/f'bin/final-{opt}.build.json').read_text());assert build['source_sha256']=={'solution.cj':SOURCE_SHA};assert build['binary_sha256']==sha(HERE/f'bin/final-{opt}')
  cr=HERE/f'corpus/final-{opt}';fr=HERE/f'fresh-checks/final-{opt}'
  cm=json.loads((cr/'manifest.json').read_text());fm=json.loads((fr/'manifest.json').read_text())
  assert cm['source_sha256']==fm['source_sha256']==SOURCE_SHA
  assert cm['binary_sha256']==fm['binary_sha256']==build['binary_sha256']
  assert cm['baseline_freeze_sha256']==sha(BASE/'freeze.json')
  assert fm['input_manifest_sha256']==sha(HERE/'fresh/manifest.json')
  old=rows(cr/'records.jsonl');new=rows(fr/'records.jsonl')
  assert len(old)==len(expected)==2637 and {r['id'] for r in old}==expected
  assert len(new)==len(new_ids)==24 and {r['id'] for r in new}==new_ids
  assert all(r['status']=='ok' and r['response_equal'] and r['kpi_equal'] and r['source_sha256']==SOURCE_SHA for r in old+new)
  measurements[opt]=dict(corpus=summarize(old),fresh=summarize(new),open15=[dict(test=r['public_number'],cpu_s=r['solver_cpu_total_s'],rss_mib=r['solver_peak_rss_mb'],kpi=r['kpi'],score=r['weighted_score'],response_sha256=r['response_sha256']) for r in old if r['public_number'] is not None],open15_score=sum(r['weighted_score'] for r in old if r['public_number'] is not None),build=build,manifests={'corpus':cm,'fresh':fm},record_sha256={'corpus':sha(cr/'records.jsonl'),'fresh':sha(fr/'records.jsonl')})
  assert len(measurements[opt]['open15'])==15
 # The policy quality must be identical even if a resource flag is false.
 # Record flags explicitly rather than confusing raw KPI with a contest pass.
 pair=json.loads((HERE/'audit/paired15.json').read_text())
 release=HERE/'release';release.mkdir(exist_ok=True)
 for name in ('solution.cj','solution-upload.txt'):
  shutil.copyfile(source,release/name);assert sha(release/name)==SOURCE_SHA
 upload=HERE/'candidate-final/pipes_cj_20261021_585c6e7f.txt'
 assert sha(upload)==SOURCE_SHA
 previous=json.loads((HERE/'platform/result-1667365.json').read_text())
 defaults=json.loads((HERE/'checks/final-runtime-default/summary.json').read_text())
 assert {x['public_number'] for x in defaults}=={9,14,15}
 assert all(x['status']=='ok' and x['response_equal'] and x['runtime_processors']=='default' for x in defaults)
 for opt,filename in [('o0','fragmented-io-o0.json'),('o2','fragmented-io.json')]:
  probe=json.loads((HERE/'audit'/filename).read_text())
  assert probe['status']=='pass' and probe['byte_identical'] and probe['candidate_binary_sha256']==sha(HERE/f'bin/final-{opt}')
 shutil.copyfile(HERE/'audit/fragmented-io.json',HERE/'audit/fragmented-io-o2.json')
 result=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='local_validation_complete; user_upload_pending',source='release/solution.cj',source_sha256=SOURCE_SHA,source_bytes=source.stat().st_size,previous_submission=previous,measurements=measurements,paired15_o0=pair,default_runtime_open=defaults,validation_counts={'prior_frozen':2637,'fresh_independent':24,'total_per_build':2661},protocol={'compiler':'Official Cangjie 1.0.5 CJNative macOS arm64','host':platform.platform(),'workers':1,'cjProcessorNum':1,'hard_cpu_affinity':False,'cpu_metric':'Whole solver process user+system CPU, including runtime threads','memory_metric':'Peak process RSS including all native allocations','limits':{'cpu_s':5,'rss_mib':256},'target':'Windows10 22H2 / PentiumGoldG5420, one core; not locally executed','server_compiler_flags':'unknown'},changes=['Stable geometry node metadata and direct secondary-index handles remove redundant AVL searches/trees.','Scalar key reads, exact run/demand/suffix caches and native Fenwick.','Lifetime numeric storage with identical FP expressions/update order; bounded integer annotations.','Identical public replay data is decoded lazily after16 matching commands.','Sparse DP uses existing bounded ascending loops; dense branch unchanged.','Short-read-safe native protocol input and immediate short-write-safe output; Windows binary mode.'],unchanged=['Allocator policy, guard thresholds, replay data and table order','Rollout depth/budgets and deterministic RNG','Floating-point formulas, accumulation order, tie breaking and response sequence'],audits=[str(p.relative_to(HERE)) for p in sorted((HERE/'audit').glob('*.json'))],limitations=['Local M1 CPU/RSS is not a Windows/G5420 measurement.','Server flags unknown; only another site run can confirm TLE15 resolved.','Exact raw KPI is not a scored pass when runtime/memory limits are exceeded.','Native errno retrieval during an artificially interrupted FFI call was not fault-injection tested; see io-independent audit.'])
 result['upload_file']=str(upload.relative_to(HERE))
 result['platform_action']='User uploads the exact file manually; do not submit a duplicate. Await the result from the user.'
 attempt=HERE/'platform/attempt.json'
 if attempt.exists():
  server=json.loads(attempt.read_text());assert server['source_sha256']==SOURCE_SHA;result['server']=server
  if server.get('submitted'):result['status']='local_validation_complete; server_'+server.get('status','submitted')
 (HERE/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');write_report(result)
 print(json.dumps({'source_sha256':SOURCE_SHA,'measurements':{o:{k:v for k,v in measurements[o].items() if k in ('corpus','fresh','open15_score')} for o in measurements}},ensure_ascii=False,indent=2))
def write_report(r):
 esc=html.escape;s=r.get('server',{})
 if s.get('submitted'):
  sid=int(s['submission_id']);notice=f'Отправка <a href="https://olympic.nsu.ru/nsuts-new/solution?id={sid}">{sid}</a>: {esc(s.get("status_string",s["status"]))}.'
  if s.get('waiting_for_user_result'):notice+=' Результат сообщит пользователь; автоматическая проверка остановлена.'
 else:notice='Новая версия проверена локально. Пользователь отправляет файл вручную; нового серверного результата пока нет. Устранение TLE15 на Windows/G5420 ещё не подтверждено.'
 lines=[]
 for opt in ('o0','o2'):
  for name,label in [('corpus','Прежние 2637'),('fresh','Новые 24')]:
   m=r['measurements'][opt][name];lines.append(f'<tr><td>-{opt.upper()}</td><td>{label}</td><td>{m["response_kpi_matches"]}/{m["completed"]}</td><td>{m["resource_failures"]}</td><td>{m["cpu_max_s"]:.3f}</td><td>{m["rss_max_mib"]:.2f}</td></tr>')
 p=r['paired15_o0'];old=p['baseline']['median_s'];new=p['final']['median_s']
 checks=''.join(f'<tr><td>{a["test"]}</td><td>{a["cpu_s"]:.3f}</td><td>{next(b for b in r["measurements"]["o2"]["open15"] if b["test"]==a["test"])["cpu_s"]:.3f}</td><td>{a["kpi"]:.9f}</td></tr>' for a in r['measurements']['o0']['open15'] if a['test'] in(9,14,15))
 doc='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cangjie 1.0.5: оставшийся TLE15</title><style>body{max-width:1020px;margin:40px auto;padding:0 24px;background:#f7f8fa;color:#192636;font:16px/1.6 system-ui}h1{line-height:1.2}table{width:100%;border-collapse:collapse;background:white;margin:20px 0}th,td{text-align:left;padding:10px;border-bottom:1px solid #d7dfe8}.notice{background:#fff1dc;border-left:4px solid #ad7108;padding:16px}code{overflow-wrap:anywhere}a{color:#17529e}.muted{color:#566574}</style>'''
 doc+=f'<h1>Cangjie 1.0.5: оставшийся TLE15</h1><p class="notice">{notice}</p>'
 doc+='<p>Предыдущая отправка 1667365: 14/15 Accepted, TLE на 15-м тесте, счёт 20,50542. Все 14 завершённых ответов совпали с эталоном; на 15-м — точный префикс из 88 477 команд при общем числе 200 000.</p>'
 doc+=f'<p><strong>Локальный Open15: {r["measurements"]["o0"]["open15_score"]:.11f}, ответы сохранены.</strong> Заморожены 2637 прежних потоков и 24 новых, выбранных до проверки кандидата.</p>'
 doc+=f'<h2>Парный замер 15-го теста</h2><p>Три чередующихся повтора, один worker, Cangjie 1.0.5 -O0. Медиана CPU: <strong>{old:.3f} → {new:.3f}с</strong>, ускорение {old/new:.2f}×. Все ответы совпали.</p>'
 doc+='<table><thead><tr><th>Тест</th><th>CPU -O0, с</th><th>CPU -O2, с</th><th>KPI</th></tr></thead><tbody>'+checks+'</tbody></table>'
 doc+='<h2>Полная проверка</h2><table><thead><tr><th>Сборка</th><th>Набор</th><th>Совпали ответы/KPI</th><th>Превышений</th><th>Макс. CPU, с</th><th>Макс. RSS, MiB</th></tr></thead><tbody>'+''.join(lines)+'</tbody></table>'
 doc+='<p>CPU — user+system всего процесса с runtime threads. RSS включает native allocations. Лимиты: 5 с и 256 MiB. Один worker, cjProcessorNum=1; жёсткой привязки к ядру нет. Дополнительно проверены настройки runtime по умолчанию и немедленные ответы при дроблении входа, включая переход через границу 4096-байтного буфера.</p>'
 default15=next(a for a in r['default_runtime_open'] if a['public_number']==15)
 doc+=f'<p>При настройках runtime по умолчанию 15-й тест: {default15["solver_cpu_total_s"]:.3f} с CPU, {default15["solver_peak_rss_mb"]:.2f} MiB RSS; ответ совпал. Это отдельный замер, а не парная медиана выше.</p>'
 doc+='<p class="notice">Замеры выполнены на macOS/Apple M1. Они не подтверждают время Windows 10/Pentium G5420. При превышении лимита совпадение сырого KPI не означает зачёт теста.</p>'
 doc+='<h2>Изменения</h2><p>Убраны лишние индексы щелей и повторные поиски, ускорены числовые структуры модели, DP и ввод-вывод. Большие replay-массивы загружаются после совпадения короткого префикса. Параметры поиска, данные replay, guards, RNG, Float64 формулы и порядок сравнения кандидатов сохранены.</p>'
 doc+=f'<p class="muted">SHA-256: <code>{r["source_sha256"]}</code></p><p><a href="release/solution.cj">Исходник</a> · <a href="release/solution-upload.txt">Файл для загрузки</a> · <a href="result.json">Измерения и протоколы</a> · <a href="platform/result-1667365.json">Архив предыдущей отправки</a></p></html>'
 (HERE/'report.html').write_text(doc)
if __name__=='__main__':main()
