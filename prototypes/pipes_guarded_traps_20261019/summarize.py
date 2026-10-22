"""Audit paired official runs and publish the exact scope of each trap."""
import hashlib
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STRATEGIES = ["bestfit", "guarded-joint", "guarded-reverse", "trial22"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def commands(path):
    tokens = path.read_text().split()
    return list(map(int, tokens[2:2 + int(tokens[1])]))


def gaps(active, trench):
    result, end = [], 0
    for pos, length in sorted(active.values()):
        if pos > end:
            result.append([end, pos])
        assert pos >= end
        end = pos + length
    if end < trench:
        result.append([end, trench])
    return result


def geometry(record, cmd):
    replies = Path(record["judge_output_file"]).read_text().splitlines()
    assert len(replies) == len(cmd)
    trench, pid, active, states = 0, 0, {}, []
    for index, (c, reply) in enumerate(zip(cmd, replies), 1):
        free = gaps(active, trench)
        before = trench
        if c > 0:
            digs, pos = map(int, reply.split())
            trench += 20 * digs
            assert pos + c <= trench
            assert all(pos + c <= x or pos >= x + length for x, length in active.values())
            pid += 1
            active[pid] = (pos, c)
        else:
            pos, length = active.pop(-c)
            assert int(reply) == pos
        after = gaps(active, trench)
        states.append({"operation": index, "command": c,
                       "trench_before_m": before, "trench_after_m": trench,
                       "max_gap_before_m": max((y-x for x, y in free), default=0),
                       "gaps_after": after, "reply": reply,
                       "occupied_m": sum(length for _, length in active.values())})
    return states, active, trench


def svg_geometry(active_by_strategy):
    colors = ["#2c7c91", "#8a603c", "#7f5f9c", "#367b4a", "#ad4c58"]
    parts = ['<svg viewBox="0 0 940 180" role="img" aria-label="Равная финальная загрузка 120 м в траншеях 120 и 320 м">']
    for row, strategy in enumerate(["bestfit", "guarded-joint"]):
        active, trench = active_by_strategy[strategy]
        y = 32 + row * 80
        label = "Best-Fit" if strategy == "bestfit" else "Guarded joint replay"
        parts.append(f'<text x="0" y="{y-10}" font-size="16">{label}: {trench} м траншеи, 120 м труб</text>')
        parts.append(f'<rect x="0" y="{y}" width="{trench*2.8}" height="30" fill="#e0e5e9"/>')
        for pid, (pos, length) in active.items():
            parts.append(f'<rect x="{pos*2.8}" y="{y}" width="{length*2.8}" height="30" fill="{colors[pid%len(colors)]}"><title>PID {pid}: [{pos}, {pos+length})</title></rect>')
    return "".join(parts) + "</svg>"


def main():
    manifest = json.loads((HERE / "manifest.json").read_text())
    meta = {row["name"]: row for row in manifest["tests"]}
    records = []
    for strategy in STRATEGIES:
        for suffix in ["summary.json", "beam/summary.json"]:
            path = HERE / "evaluations" / strategy / suffix
            records.extend(json.loads(path.read_text())["records"])
    keyed = {(r["strategy"], r["case"]): r for r in records}
    assert len(keyed) == len(records) == 20
    for r in records:
        assert r["case"] in meta
        assert r["test_sha256"] == meta[r["case"]]["test_sha256"]
        assert r["status"] == "ok" and not r["solver_cpu_limit_exceeded"] and not r["solver_memory_limit_exceeded"]
        assert r["judge_commands_seen_including_final_zero"] == meta[r["case"]]["operation_count"] + 1
    for case in meta:
        if case != "public-case15-control":
            assert meta[case]["kpi_upper_bound_from_live_volume"] == 1
            assert keyed["bestfit", case]["kpi"] == 1
    assert keyed["guarded-joint", "joint-multiphase"]["kpi"] == .375
    assert keyed["trial22", "joint-multiphase"]["kpi"] == .5
    assert keyed["guarded-reverse", "reverse-reservation-128"]["trench_length_m"] == 418760
    assert keyed["guarded-joint", "reverse-reservation-128"]["kpi"] == 1

    case = "joint-multiphase"
    cmd = commands(HERE / "inputs" / (case + ".in"))
    geo = {}
    active_by_strategy = {}
    for strategy in ["bestfit", "guarded-joint", "trial22"]:
        states, active, trench = geometry(keyed[strategy, case], cmd)
        geo[strategy] = states
        active_by_strategy[strategy] = (active, trench)
    growth = []
    for good, bad in zip(geo["bestfit"], geo["guarded-joint"]):
        assert good["occupied_m"] == bad["occupied_m"]
        if good["operation"] >= 32:
            assert good["trench_after_m"] == 120
        if bad["operation"] > 32 and bad["trench_after_m"] > bad["trench_before_m"]:
            assert bad["command"] > bad["max_gap_before_m"]
            growth.append({"operation": bad["operation"], "command": bad["command"],
                           "bestfit": good, "guarded_joint": bad})
    witness = {"case": case, "shared_prefix": 32,
               "same_final_occupied_m": 120, "bestfit_trench_is_constant_m": 120,
               "growth_events_after_fallback": growth,
               "final_geometry": {s: {"trench_m": t, "pipes": [[pid, pos, length] for pid, (pos, length) in sorted(a.items())]}
                                  for s, (a, t) in active_by_strategy.items()}}
    (HERE / "witness.json").write_text(json.dumps(witness, indent=2) + "\n")
    protocol = json.loads((HERE / "beam-protocol.json").read_text())
    protocol["parent_final_validation"] = {
        "status": "official_interactor_4_of_4_ok", "report": "report.json",
        "joint_multiphase_kpi": {s: keyed[s, case]["kpi"] for s in STRATEGIES},
        "persistent_suffix": "beam-suffix.json",
        "all_within_cpu_and_rss_limits": True}
    (HERE / "beam-protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    source_paths = [HERE / name for name in ["build_tests.py", "summarize.py", "beam-suffix.json", "beam_search.cpp", "beam-protocol.json", "manifest.json", "prepare_search.py", "window_search.cpp", "joint-tape.txt", "reverse-tape.txt"]]
    source_paths += [REPO / name for name in [
        "prototypes/pipes_prefix_shock_20261019/allocator_probe.cpp",
        "prototypes/pipes_prefix_shock_20261019/allocator-probe",
        "prototypes/pipes_prefix_shock_20261019/trial22",
        "tools/pipes_harness.py", "tools/interactor", "vendor/pipes_official/interactor.cpp"]]
    result = {
        "status": "20_of_20_official_local_checks_ok", "platform_actions": 0,
        "invalid_answers": 0, "intrinsic_kpi_ceiling_of_every_trap": 1,
        "frozen_profiles": manifest["profiles"],
        "claims": ["The exact previous joint guarded replay remains valid but reaches KPI .375 versus generic BF 1 on a fixed 186-command input sharing 32 commands with Open15 case15.",
                   "A different existing case15-specific reverse future plan is hit much harder: KPI .00085968096 after 128 shared commands, while BF, trial22 and joint replay all reach 1.",
                   "This is a targeted adversarial construction, not an estimate of hidden-test generalization or proof of rule violations. Trial22 itself reaches .5 on the joint multi-phase trap, so poor performance does not identify a future-reading implementation."],
        "hashes": {str(p.relative_to(REPO)): sha(p) for p in source_paths},
        "max_solver_cpu_s": max(r["solver_cpu_total_s"] for r in records),
        "max_solver_rss_mb": max(r["solver_peak_rss_mb"] for r in records),
        "tests": manifest["tests"], "records": records,
    }
    (HERE / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    order = ["joint-multiphase", "joint-fragmentation", "reverse-reservation-128", "reverse-reservation-4096", "public-case15-control"]
    rows = []
    for name in order:
        cells = [f'<a href="inputs/{name}.in">{name}</a>', str(meta[name]["common_command_prefix"])]
        cells += [f'{keyed[strategy, name]["kpi"]:.9f}' for strategy in STRATEGIES]
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    document = '''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Корректные тесты против подгонки Pipes</title>
<style>body{max-width:1150px;margin:48px auto;padding:0 24px;font:17px/1.6 system-ui;color:#17202a;background:#fafbf9}h1{line-height:1.2}table{border-collapse:collapse;width:100%;font-size:15px;font-variant-numeric:tabular-nums}td,th{padding:11px;border:1px solid #cbd4d6;text-align:left}a{color:#00627b}code{background:#e9efee;padding:2px 5px}.lead{font-size:21px}.proof{padding:16px 24px;background:#edf3ee;border-left:4px solid #367b4a}svg{width:100%;max-width:940px}</style>
<h1>Общий префикс, корректный replay, резкий провал KPI</h1>
<p class="lead">Главный тест: 186 команд, общий префикс 32 команды с открытым №15. Обычный Best-Fit получает KPI 1,000; тот же защищённый joint replay, что в предыдущей проверке, — 0,375. Все ответы корректны, финальная загрузка обоих — 120 м.</p>
<p><a href="inputs/joint-multiphase.in">Скачать главный тест joint-multiphase.in</a> · <a href="report.json">Полные измерения</a> · <a href="witness.json">Проверяемые состояния и события роста траншеи</a></p>
''' + svg_geometry(active_by_strategy) + '''
<p>После общего префикса меняются удаления и размеры. Guarded replay сразу обнаруживает расхождение и переключается на обычный Best-Fit, сохраняя реальные координаты. Суффикс многократно использует свободное место Best-Fit; прежние размещения replay оставляют разрозненные промежутки и вынуждают рыть дальше. Best-Fit остаётся в 120 м, replay доходит до 320 м. Финальные метровые трубы заполняют 120 м, поэтому низкий KPI не вызван опустошением входа.</p>
<div class="proof">Все четыре стресс-входа имеют достижимый потолок KPI = 1, и Best-Fit его достигает. Все 20 локальных запусков с официальным interactor завершились корректно и уложились в лимиты. Ошибок протокола и искусственного обнуления итоговой массы нет.</div>
<h2>Результаты: фактический KPI</h2>
<table><thead><tr><th>Вход</th><th>Общий префикс</th><th>Best-Fit</th><th>Guarded joint</th><th>Guarded reverse</th><th>Trial22 online</th></tr></thead><tbody>''' + "".join(rows) + '''</tbody></table>
<h2>Два разных сохранённых плана</h2>
<p><b>Guarded joint</b> использует неизменённый <code>best-positions.txt</code> из прежнего опыта — общий префикс согласован со всеми Open15. Для него основной тест даёт падение KPI на 62,5% относительно Best-Fit.</p>
<p><b>Guarded reverse</b> использует другой существовавший до этой проверки файл <code>future/2/15.txt</code>: офлайн-план для одного публичного теста №15, с обратным порядком выживших труб. Он не является прежним joint-планом и не согласован со всеми общими префиксами Open15. На полном исходном тесте его KPI = 0,999945079, что подтверждено официальным interactor.</p>
<p>Reverse-план размещает ранние трубы далеко от начала под ожидаемое будущее и уже успевает вырыть более 418 тысяч метров. В <a href="inputs/reverse-reservation-128.in">reverse-reservation-128</a> после 128 общих команд удаляются текущие трубы и укладываются девять труб по 40 м. Финальная загрузка 360 м достигает максимума объёма этого нового теста; Best-Fit и Trial22 имеют траншею 360 м и KPI = 1, тогда как reverse replay сохраняет 418 760 м и KPI ≈ 0,000859681 — примерно в 1163 раза хуже. Все удаления и ответы остаются корректными.</p>
<p><a href="inputs/reverse-reservation-4096.in">Вариант с префиксом 4096 команд</a> сохраняет 10 160 м финальной загрузки: KPI reverse replay ≈ 0,024262107 против 1 у Best-Fit, Trial22 и joint replay.</p>
<h2>Что эти тесты устанавливают</h2>
<p>Это целевые воспроизводимые контрпримеры к конкретным сохранённым планам и стратегиям. Trial22 на основном тесте получает 0,500, хотя читает поток причинно: плохой результат сам по себе не доказывает использование будущего или нарушение правил. Проверенный перенос на распределение закрытых тестов здесь не оценивается. Нельзя обещать, что один вход обрушит любую подгонку: joint replay, например, выдерживает оба теста против reverse-плана с KPI = 1.</p>
<p>Генератор: <a href="build_tests.py">build_tests.py</a>. Сохранённый суффикс: <a href="beam-suffix.json">beam-suffix.json</a>. Поиск: <a href="beam_search.cpp">beam_search.cpp</a> и <a href="beam-protocol.json">протокол</a>. Hashes, происхождение планов, параметры и контроль: <a href="manifest.json">manifest.json</a>. Оптимизационные кампании, платформа и прежние проверки не возобновлялись.</p></html>'''
    (HERE / "report.html").write_text(document)
    for name in order:
        print(name, {s: keyed[s, name]["kpi"] for s in STRATEGIES})
    print("checks", len(records), "max CPU", result["max_solver_cpu_s"], "max RSS", result["max_solver_rss_mb"])


if __name__ == "__main__":
    main()
