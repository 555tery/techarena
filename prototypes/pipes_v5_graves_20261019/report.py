"""Audit official results and certify the cumulative quiet-prefix counterexample."""
import csv
import hashlib
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STRATEGIES = ["release-v5", "release-v4", "bestfit", "trial22"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_commands(path):
    a = path.read_text().split()
    return list(map(int, a[2:2+int(a[1])]))


def free_gaps(active, trench):
    result, end = [], 0
    for start, length in sorted(active.values()):
        assert start >= end
        if start > end:
            result.append([end, start])
        end = start + length
    assert end <= trench
    if end < trench:
        result.append([end, trench])
    return result


def replay(cmd, record):
    lines = Path(record["judge_output_file"]).read_text().splitlines()
    assert len(lines) == len(cmd)
    active, pid, trench, peak = {}, 0, 0, 0
    states = []
    for index, (c, line) in enumerate(zip(cmd, lines), 1):
        before = {"trench_m": trench, "gaps": free_gaps(active, trench)}
        before["max_gap_m"] = max((r-l for l, r in before["gaps"]), default=0)
        if c > 0:
            digs, pos = map(int, line.split())
            trench += 20 * digs
            assert pos >= 0 and pos+c <= trench
            assert all(pos+c <= x or pos >= x+n for x, n in active.values())
            pid += 1
            active[pid] = (pos, c)
        else:
            pos, length = active.pop(-c)
            assert int(line) == pos
            digs = 0
        occupied = sum(n for _, n in active.values())
        peak = max(peak, occupied)
        states.append({"operation": index, "command": c, "reply": line, "digs": digs,
                       "before": before, "trench_m": trench, "occupied_m": occupied,
                       "peak_volume_lower_bound_m": (peak+19)//20*20,
                       "gaps": free_gaps(active, trench)})
    assert trench == record["trench_length_m"]
    assert sum(n for _, n in active.values()) == record["occupied_length_m"]
    return states, active


def final_svg(geometry):
    out = ['<svg viewBox="0 0 950 190" role="img" aria-label="40 м труб в траншеях Best-Fit 40 м и release-v5 160 м">']
    colors = ["#27798e", "#48793e", "#986140", "#87679a", "#a54e60"]
    for row, name in enumerate(["bestfit", "release-v5"]):
        y = 40 + row * 85
        a, T = geometry[name]
        title = "Best-Fit" if name == "bestfit" else "Release-v5 с fallback"
        out += [f'<text x="0" y="{y-13}" font-size="17">{title}: траншея {T} м, трубы 40 м</text>',
                f'<rect x="0" y="{y}" width="{T*5}" height="32" fill="#e0e6e8"/>']
        for pid, (pos, length) in a.items():
            out.append(f'<rect x="{pos*5}" y="{y}" width="{length*5}" height="32" fill="{colors[pid%len(colors)]}"><title>PID {pid}: [{pos}, {pos+length})</title></rect>')
    return "".join(out) + '</svg>'


def main():
    m = json.loads((HERE / "manifest.json").read_text())
    official = json.loads((HERE / "official-results.json").read_text())
    records = official["records"]
    keyed = {(r["strategy"], r["suite_case"]): r for r in records}
    assert len(keyed) == 36
    for r in records:
        assert r["status"] == "ok" and not r["solver_cpu_limit_exceeded"] and not r["solver_memory_limit_exceeded"]
    traces, final_geometry = {}, {}
    for t in m["tests"]:
        case, cut = t["name"], t["common_prefix"]
        path = REPO / t["file"]
        assert sha(path) == t["test_sha256"]
        cmd = read_commands(path)
        for s in STRATEGIES:
            r = keyed[s, case]
            assert r["test_sha256"] == t["test_sha256"]
            states, active = replay(cmd, r)
            traces[s, case] = states
            if case == "quiet-open2-beam":
                final_geometry[s] = (active, states[-1]["trench_m"])
        target = traces["release-v5", case][:cut]
        bf = traces["bestfit", case][:cut]
        max_ratio = max(x["trench_m"]/y["trench_m"] for x, y in zip(target, bf))
        max_volume_ratio = max(x["trench_m"]/x["peak_volume_lower_bound_m"] for x in target)
        assert abs(max_ratio-t["predicted_prefix_max_ratio"]) < 1e-12
        t["verified_cumulative_prefix_T_ratio"] = max_ratio
        t["verified_cumulative_prefix_T_to_volume_bound"] = max_volume_ratio
        assert abs(keyed["bestfit", case]["kpi"]-t["kpi_upper_bound_from_live_volume"]) < 1e-12
        assert keyed["bestfit", case]["kpi"] >= .9
        if t["family"] == "strict-quiet-geometry":
            assert max_ratio <= 1 and max_volume_ratio == 1
    case, cut = "quiet-open2-beam", 18
    assert keyed["release-v5", case]["kpi"] == .25
    assert keyed["bestfit", case]["kpi"] == 1
    assert keyed["trial22", case]["kpi"] == .5
    gt = traces["release-v5", case]
    bt = traces["bestfit", case]
    assert gt[cut-1]["trench_m"] == 20 and bt[cut-1]["trench_m"] == 40
    assert all(x["trench_m"] == 20 for x in gt[:cut])
    assert all(x["trench_m"] == 40 for x in bt[cut-1:])
    growth = []
    for g, b in zip(gt[cut:], bt[cut:]):
        assert g["occupied_m"] == b["occupied_m"]
        if g["digs"]:
            assert g["command"] > g["before"]["max_gap_m"]
            growth.append({"operation": g["operation"], "command": g["command"], "v5": g, "bestfit": b})
    witness = {"target_source_sha256": m["target"]["source_sha256"], "test": case,
               "test_sha256": next(t["test_sha256"] for t in m["tests"] if t["name"] == case),
               "common_open_prefix_commands": cut, "public_case": 2,
               "prefix_max_T_v5_over_T_BF": 1, "prefix_max_T_v5_over_volume_bound": 1,
               "prefix_terminal_T": {"release-v5": 20, "bestfit": 40},
               "final_volume_m": 40, "final_trench_m": {s: keyed[s, case]["trench_length_m"] for s in STRATEGIES},
               "KPI": {s: keyed[s, case]["kpi"] for s in STRATEGIES},
               "v5_runtime_counters": keyed["release-v5", case]["runtime_counters"],
               "growth_events_after_fallback": growth,
               "prefix_trace": {s: traces[s, case][:cut] for s in ["release-v5", "bestfit"]},
               "final_geometry": {s: {"T": T, "pipes": [[pid,pos,n] for pid,(pos,n) in a.items()]}
                                  for s, (a,T) in final_geometry.items()},
               "scope": "Direct certificate against the frozen v5 plus its built-in BF fallback. A simple rule that rejects excessive trench length on the shared prefix would not reject any of these prefix actions. This is not a theorem against every smarter fallback or every Open15 maximizer."}
    (HERE / "witness-main.json").write_text(json.dumps(witness, indent=2) + "\n")
    origin = REPO / m["target"]["origin"]
    for directory in [HERE / "target", origin]:
        assert sha(directory / "solution.cpp") == m["target"]["source_sha256"]
        assert sha(directory / "solver") == m["target"]["binary_sha256"]
    for suffix, name in [("open1", "quiet-open1"), ("open2_beam", "quiet-open2-beam")]:
        path = HERE / "diagnostics" / ("geometry_quiet_"+suffix+".json")
        d = json.loads(path.read_text())
        d["parent_official_validation"] = {
            "status": "4_of_4_original_official_interactor_checks_ok",
            "KPI": {s: keyed[s,name]["kpi"] for s in STRATEGIES},
            "report": "report.json", "all_within_resources": True,
            "input_sha256": keyed["release-v5",name]["test_sha256"]}
        path.write_text(json.dumps(d, indent=2) + "\n")
    shape_path = HERE / "shape_manifest.json"
    shape = json.loads(shape_path.read_text())
    shape["parent_official_validation"] = {
        "status": "12_of_12_original_official_interactor_checks_ok",
        "report": "report.json", "all_within_resources": True,
        "results": {t["name"]: {s: keyed[s,t["name"]]["kpi"] for s in STRATEGIES}
                    for t in m["tests"] if t["family"] == "moderate-quiet-geometry"}}
    shape_path.write_text(json.dumps(shape, indent=2) + "\n")
    result = {"status": official["status"], "target": m["target"], "tests": m["tests"],
              "records": records, "source_hashes": {str(p.relative_to(REPO)): sha(p) for p in [HERE / "assemble.py", HERE / "validate.py", HERE / "report.py", HERE / "reservation_tests.py"]},
              "primary_test": case, "peak_equals_final_volume_on_primary": True,
              "targets_unchanged": True, "platform_actions": 0,
              "max_solver_cpu_s": max(r["solver_cpu_total_s"] for r in records),
              "max_solver_rss_mb": max(r["solver_peak_rss_mb"] for r in records),
              "limits": "No near-zero KPI was found under the strict cumulative quiet-prefix criterion. The strongest verified strict-quiet test gives v5 .25 vs BF 1. Near-zero reservation tests expose the separately labeled early-cost weakness."}
    (HERE / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    with (HERE / "metrics.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case","family","commands","prefix","max_prefix_T_ratio",*STRATEGIES,"volume_KPI_ceiling"])
        for t in m["tests"]:
            w.writerow([t["name"],t["family"],t["operation_count"],t["common_prefix"],t["verified_cumulative_prefix_T_ratio"],
                        *[keyed[s,t["name"]]["kpi"] for s in STRATEGIES],t["kpi_upper_bound_from_live_volume"]])
    def table(family):
        out = ['<table><thead><tr><th>Вход</th><th>Команд / префикс</th><th>Макс. T v5 / BF на префиксе</th><th>v5</th><th>v4</th><th>Best-Fit</th><th>Trial22</th></tr></thead><tbody>']
        for t in m["tests"]:
            if t["family"] != family: continue
            name = t["name"]
            cells = [f'<a href="suite/{name}.in">{name}</a>',f'{t["operation_count"]} / {t["common_prefix"]}',
                     f'{t["verified_cumulative_prefix_T_ratio"]:.3f}',*[f'{keyed[s,name]["kpi"]:.9f}' for s in STRATEGIES]]
            out.append('<tr>'+''.join('<td>'+str(c)+'</td>' for c in cells)+'</tr>')
        return ''.join(out)+'</tbody></table>'
    document = '''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Гробы для Open15 release-v5</title>
<style>body{max-width:1200px;margin:44px auto;padding:0 24px;font:17px/1.6 system-ui;color:#17252c;background:#fafbf9}h1{line-height:1.2}.lead{font-size:21px}.proof{padding:18px 24px;background:#eaf2ed;border-left:4px solid #33744b}table{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}th,td{padding:10px;border:1px solid #ccd4d5;text-align:left}a{color:#00617d}pre,code{background:#e9eef0}pre{padding:16px;overflow:auto}svg{width:100%;max-width:950px}.warn{padding:16px;background:#f4eee5}</style>
<h1>Контрпримеры для нового Open15-кода: release-v5</h1>
<p class="lead">Основной результат: 89 команд, первые 18 точно совпадают с открытым тестом №2. До расхождения v5 ни разу не роет больше обычного Best-Fit и держится на объёмной нижней границе. После корректного переключения на встроенный BF его KPI падает до <b>0,25</b>, а Best-Fit с самого начала получает <b>1</b>.</p>
<p><a href="suite/quiet-open2-beam.in">Основной тест</a> · <a href="graves-v5.zip">Все 9 тестов и отчёт архивом</a> · <a href="witness-main.json">Пошаговый сертификат</a> · <a href="metrics.csv">CSV</a></p>
''' + final_svg(final_geometry) + '''
<div class="proof">Весь общий префикс v5 укладывается в 20 м — это минимально допустимая длина траншеи. Best-Fit к концу префикса имеет 40 м. Суффикс меняет времена удаления и размеры новых труб. V5 действительно включает fallback: <code>replay=14 fallback=50 table_conflict=0 T=160</code>. Оба алгоритма заканчивают с 40 м труб, но длины траншей — 160 и 40 м. Это фрагментация после смены нагрузки, без предварительного огромного резерва и без опустошения финальной загрузки.</div>
<p>У v5 рост после перехода на BF происходит на новых трубах длины 12, 16, 17, 18, 19, 20 и 21 м. Перед каждым таким размещением его свободные промежутки слишком короткие; у BF с начала все последующие трубы помещаются в существующие 40 м. Точные промежутки, PID, ответы и события роста сохранены в сертификате.</p>
<h2>Строго без раннего перерасхода</h2>
<p>Ограничение проверено на каждом шаге с начала входа, а не только в точке ветвления. У обоих тестов max(T_v5/T_BF) ≤ 1; также T_v5 совпадает с объёмной нижней границей на всём общем префиксе. Простой лимит ранней длины траншеи не отверг бы эти префиксные действия.</p>
''' + table("strict-quiet-geometry") + '''
<p>Короткий восьмикомандный пример: <code>1 4 15 -2 3 -1 | -4 5</code>. После удаления PID 4 BF получает свободный интервал [0,5), а v5 — два интервала [0,1) и [16,20). Пятиметровая труба вызывает расширение только у v5. Оба ответа корректны.</p>
<h2>Умеренные префиксы: до двукратной длины</h2>
''' + table("moderate-quiet-geometry") + '''
<p>Эти входы дают меньший разрыв и не относятся к строгому классу выше. Два из них имеют максимально возможный KPI 0,93 и 0,90 из-за округления траншеи до 20 м; Best-Fit достигает этих максимумов.</p>
<h2>Отдельно: явные ранние резервы</h2>
<p>Это дополнительные проверки старого механизма. Здесь все команды положительные: трубы вообще не удаляются. Они дают почти нулевой KPI, но предварительный ограничитель затрат способен их обнаружить.</p>
''' + table("early-reservation") + '''
<p>Новый короткий регрессионный пример <code>3 2 35</code>: у прежнего v4 KPI = 1, у достигшего потолка Open15 v5 — 40/19 520 ≈ 0,002049. Это три корректные укладки с итоговой массой 40 м. Такой результат не подменяется утверждением о стойкости против хорошей предварительной защиты.</p>
<h2>Проверка и границы результата</h2>
<p>Зафиксированы исходник v5 <code>7fe4d9430d708021f602ebb2333564ebb8c1e0b0ac5b1355855c4a18155c011f</code> и исполняемый файл; hashes исходных и скопированных файлов совпадают после проверки. Внутри этой версии остаётся exact-prefix matching и BF fallback при несовпадении или непригодном адресе. Платформу, текущий solver и остановленные кампании не меняли.</p>
<p>Все 36 официальных локальных проверок завершились корректно и в пределах ресурсов: 9 входов × v5, v4, Best-Fit и Trial22. Использована неизменённая функция project harness с исходным официальным interactor. Два первоначальных запуска короткого теста включены в эти 36 и не повторялись. Отдельно повторно воспроизведены все сохранённые ответы, проверены пересечения, удаления, рост траншеи и кумулятивные метрики префикса.</p>
<p class="warn">Под строгим ограничением благополучного префикса почти нулевой KPI пока не найден: лучший подтверждённый результат — 0,25 против 1. Trial22 на нём получает 0,50, поэтому низкий результат сам по себе не доказывает чтение будущего. Это целевые контрпримеры к конкретному коду и его BF fallback; утверждений о провале любого умного максера или о среднем качестве на скрытых тестах нет.</p>
<p><a href="manifest.json">Манифест</a> · <a href="report.json">Полные результаты</a> · <a href="official-results.json">Первичные отчёты interactor</a> · <a href="README.txt">Воспроизведение</a></p></html>'''
    (HERE / "report.html").write_text(document)
    (HERE / "README.txt").write_text('''Pipes release-v5 targeted stress suite.
Main test: suite/quiet-open2-beam.in (89 commands, exact 18-command Open2 prefix).
Actual v5 with built-in BF fallback: KPI .25; plain BF: KPI 1; Trial22: KPI .5.
For every step of the common prefix, v5 trench=20 and equals the volume bound.
Nine unique inputs; weights are normalized to 1 for local KPI comparison.
Each .in has weight, operation count, then commands. Interactor supplies final 0.
36/36 original official interactor checks passed; all answers valid and in limits.
Run any candidate through tools/pipes_harness.py with --tests pointing to suite/
and a fresh --out directory. See report.html, report.json, witness-main.json.
The suite is adversarially selected; it is not a hidden-test distribution estimate.
No claim that every smart maximizer or every fallback must fail these inputs.
''')
    with zipfile.ZipFile(HERE / "graves-v5.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted((HERE / "suite").glob("*.in")):
            z.write(p, str(p.relative_to(HERE)))
        for name in ["README.txt","report.html","report.json","manifest.json","target.json","official-results.json","metrics.csv","witness-main.json","assemble.py","validate.py","report.py","reservation_tests.py"]:
            z.write(HERE/name,name)
        for name in ["geometry_quiet_open1.json","geometry_quiet_open2_beam.json","geometry_beam_search_open2.cpp","geometry_open2_state.txt","geometry_open2_beam_result.txt"]:
            z.write(HERE/"diagnostics"/name,"diagnostics/"+name)
        z.write(HERE/"shape_manifest.json","shape_manifest.json")
    print("Verified", official["status"], "main", witness["KPI"])
    print("Prefix cumulative ratio", witness["prefix_max_T_v5_over_T_BF"], "trench at cut", witness["prefix_terminal_T"])
    print("Archive bytes", (HERE/"graves-v5.zip").stat().st_size)


if __name__ == "__main__":
    main()
