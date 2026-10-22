"""Report every frozen round, including the failed confirmation."""
import csv,hashlib,html,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(name):return json.loads((HERE/name).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def small(r):return {k:r[k] for k in ['wins','ties','losses','mean_delta','worst_delta','best_delta'] if k in r}
def main():
    selected='conservative'
    build=read(selected+'/build.json');freeze=read('freeze-conservative.json')
    assert sha(HERE/selected/'solution.cpp')==freeze['source_sha256']==build['source_sha256']
    old=read('official-fresh-final.json')
    groups={name:read(f'screen-{name}-{selected}.json') for name in ['regression','prior-confirmation','round1-regression']}
    fresh=read('official-fresh-conservative-conservative.json')
    files=['official-open15-conservative.json','official-stress-conservative.json','official-fresh-conservative-conservative.json','official-regression-conservative.json']
    official=[r for f in files for r in read(f)['records'] if r['strategy']=='candidate']
    assert all(r['binary_sha256']==build['binary_sha256'] for r in official)
    gate=all(r['losses']==0 for r in groups.values()) and fresh['losses']==0
    report={'selected':selected if gate else None,'evaluated_candidate':selected,
            'recommended_source':'prototypes/pipes_g5420_cpu_20261020/cache32/solution.cpp' if not gate else str((HERE/selected/'solution.cpp').relative_to(HERE.parents[1])),
            'source_sha256':build['source_sha256'],'binary_sha256':build['binary_sha256'],
            'status':'bounded local no-observed-loss candidate' if gate else 'experimental; no-loss gate failed',
            'gate_passed':gate,'Open15_score':build['Open15_score'],'Open15_exact':build['Open15_exact'],
            'runtime_unchanged':True,'individual_block_changes':len(build['changes']),
            'public_prefix_excavation_never_increased':all(r['public_prefix_excavation_never_increased'] for r in build['audits']),
            'regressions':{k:small(v) for k,v in groups.items()},'fresh_confirmation':small(fresh),
            'first_round_confirmation':small(old),'first_round_status':'not promoted; one fresh loss',
            'fresh_loss_first_round':[p for p in old['pairs'] if p['delta']<0],
            'maximum_official_CPU_s':max(r['solver_cpu_total_s'] for r in official),
            'maximum_official_RSS_MiB':max(r['solver_peak_rss_mb'] for r in official),
            'official_candidate_checks':len(official),'host':'macOS arm64','target_hardware_run':False,'platform_actions':0,
            'limits':['Fresh streams are new seeds/inputs of known directed mechanisms, not a hidden-distribution sample.',
                      'The first24 fresh inputs became reused diagnostic data in the second round, never fresh again.',
                      'No-observed-loss is finite empirical evidence; table changes do not prove final-KPI dominance on arbitrary continuations.',
                      'Open8-p402 coordinated exchange remains experimental: first-round fresh loss. Conservative retains its old KPI.',
                      'Public prefix failures remain: the post-freeze Open11-p8 and Open8-p410 counterexamples still break replay.',
                      'CPU/RSS checks are local macOS measurements, not native Windows/G5420 certification.',
                      'CPU-budget-dependent planner trajectories can vary between runs and hardware; tiny score differences are not stable proof.']}
    (HERE/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    rows=[]
    for suite,r in [*groups.items(),('fresh-conservative',fresh)]:
        for p in r['pairs']:rows.append({'suite':suite,**p})
    with (HERE/'metrics.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['suite','id','baseline','candidate','delta']);w.writeheader();w.writerows(rows)
    def tr(label,r):
        return f'<tr><td>{html.escape(label)}</td><td>{r["wins"]} / {r["ties"]} / {r["losses"]}</td><td>{r["mean_delta"]:+.9f}</td><td>{r["worst_delta"]:+.9f}</td></tr>'
    comparisons=''.join(tr(label,r) for label,r in [('Знакомые81',groups['regression']),('Повторные24',groups['prior-confirmation']),('Первые24, теперь регрессия',groups['round1-regression']),('Новые24, после второго freeze',fresh)])
    txt=f'''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Pipes: ловушки и перепланирование</title>
<style>body{{font:17px/1.5 system-ui;max-width:1050px;margin:50px auto;padding:0 24px;color:#18212b;background:#fafbf9}}h1{{font-size:32px}}table{{border-collapse:collapse;width:100%;margin:24px 0}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #cbd5dd}}a{{color:#175b9e}}.note{{padding:18px;background:#eef3f6}}code{{word-break:break-all}}</style>
<h1>Ловушки: два отдельных замороженных раунда</h1>
<p><b>{'Кандидат прошёл конечную проверку без наблюдавшихся потерь.' if gate else 'Обе новые версии не прошли независимую проверку на отсутствие потерь. Прежний G5420 parent остаётся основным.'}</b></p>
<p>Проверенный осторожный кандидат <a href="conservative/solution.cpp">conservative/solution.cpp</a>: только {len(build['changes'])} сдвигов труб со временем жизни в публичном продолжении ровно одну команду. Online runtime и аппаратные бюджеты совпадают с G5420 parent. Все сравнения в таблице — с прежним G5420 cache32.</p>
<p><b>Open15: {build['Open15_score']:.14f}, максимум сохранён.</b> Полный аудит каждого публичного префикса подтвердил отсутствие роста траншеи; ответы проверены официальным interactor.</p>
<table><tr><th>Набор</th><th>Лучше / равно / хуже</th><th>Средняя ΔKPI</th><th>Худшая ΔKPI</th></tr>{comparisons}</table>
<p class="note">Новый второй набор: {fresh['wins']} улучшений / {fresh['ties']} равенств / {fresh['losses']} ухудшений. Худшая ΔKPI {fresh['worst_delta']:+.9f}. Кандидат не принят как улучшение без потерь. Это конечная проверка направленных механизмов, не выборка настоящих скрытых тестов.</p>
<h2>Неудачная более широкая версия сохранена</h2>
<p>Версия <a href="final/solution.cpp">final/solution.cpp</a> дополнительно обменивала постоянные трубы: Open8-p402 улучшился с0.165644 до0.375, но первая независимая проверка дала0 улучшений /23 равенства /1 ухудшение. P0204:0.896436526→0.892461197. Поэтому она не объявлена улучшением без потерь. Кандидат после первого freeze не изменялся.</p>
<p>Широкие индивидуальные сдвиги и перестановка целых компонентов также не выбраны: выявлены регрессии. Повторное использование первых24 входов явно отмечено в таблице.</p>
<h2>Оставшиеся контрпримеры</h2><p><a href="evaluation/remaining/manifest.json">Два новых теста после первого freeze</a> сохраняют KPI0.0909 и0.1818 при Best-Fit1. Простого универсального исправления replay пока нет; будущие действия fallback не уменьшают уже выкопанную траншею.</p>
<h2>Ресурсы и воспроизводимость</h2><p>{len(official)} официальных проверок точного проверяемого бинарника. Максимум CPU {report['maximum_official_CPU_s']:.6f}s, RSS {report['maximum_official_RSS_MiB']:.3f}MiB. Это macOS arm64; Windows/G5420 не запускался. Solver однопоточный, Windows CPU=user+kernel процесса.</p>
<p>Source SHA256: <code>{build['source_sha256']}</code></p><p><a href="freeze.json">Первый freeze</a> · <a href="freeze-conservative.json">Второй freeze</a> · <a href="report.json">JSON</a> · <a href="metrics.csv">Парные метрики</a> · <a href="code-and-tests.zip">Код и тесты</a></p>
<p>Canonical source, прежние frozen-версии и платформа не изменялись.</p></html>'''
    (HERE/'report.html').write_text(txt)
    (HERE/'README.md').write_text(f'''# Directed prefix repairs, 2026-10-20

Evaluated local candidate: `conservative/solution.cpp`; exact source SHA256 `{build['source_sha256']}`.
No-loss gate passed: `{gate}`. Neither new version is promoted when false; retain the unchanged G5420 parent.
Build: `clang++ -std=c++20 -O2 conservative/solution.cpp -o solver`.
Windows CPU accounting and32MiB memo profile are inherited unchanged. Actual Windows/G5420 testing is pending.

Open15 exact maximum preserved. See `report.html`, `report.json`, `metrics.csv`, both freeze manifests and raw `measurements/`.
First-round `final/` is experimental: one fresh regression; do not silently replace the selected source with it.
The second round used a new seed set and a separate freeze. The first24 tests are now regression data.
No universal no-loss or hidden-distribution claim. Canonical and frozen parents untouched; no platform actions.
''')
    archive=HERE/'code-and-tests.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in [HERE/'README.md',HERE/'report.json',HERE/'metrics.csv',HERE/'freeze.json',HERE/'freeze-conservative.json',HERE/'experiment.json',HERE/'conservative/solution.cpp',HERE/'conservative/build.json',HERE/'final/solution.cpp']:
            z.write(path,path.relative_to(HERE))
        for path in (HERE/'evaluation').rglob('*'):
            if path.is_file() and path.suffix in ['.py','.json','.in']:z.write(path,path.relative_to(HERE))
    print(json.dumps({k:v for k,v in report.items() if k not in ['limits','fresh_loss_first_round']},indent=2))

if __name__=='__main__':main()
