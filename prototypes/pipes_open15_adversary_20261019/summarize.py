"""Verify actual frozen binaries, checker evidence and irreversible-prefix trap."""
import csv
import hashlib
import html
import json
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STRATEGIES = ["release-v1", "release-v2", "release-v3", "release-v4", "bestfit", "trial22"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((HERE / "manifest.json").read_text())
    tests = {t["name"]: t for t in manifest["tests"]}
    assert len(tests) == 6
    records = []
    for strategy in STRATEGIES:
        records += json.loads((HERE / "evaluations" / strategy / "summary.json").read_text())["records"]
    keyed = {(r["strategy"], r["case"]): r for r in records}
    assert len(keyed) == len(records) == 36
    for r in records:
        meta = tests[r["case"]]
        assert r["status"] == "ok"
        assert not r["solver_cpu_limit_exceeded"] and not r["solver_memory_limit_exceeded"]
        assert r["test_sha256"] == meta["test_sha256"] == sha(REPO / meta["file"])
        assert r["judge_commands_seen_including_final_zero"] == meta["operation_count"] + 1
        assert meta["kpi_upper_bound_from_live_volume"] == 1
        if r["strategy"].startswith("release"):
            counters = {k: int(v) for k, v in re.findall(r"(replay|fallback|table_conflict|T)=(\d+)", r["candidate_stderr"])}
            assert counters["fallback"] > 0 and counters["table_conflict"] == 0
            assert counters["T"] == r["trench_length_m"]
            r["runtime_counters"] = counters
    for case in tests:
        assert keyed["bestfit", case]["kpi"] == 1
        assert keyed["trial22", case]["kpi"] > .998
        assert keyed["release-v3", case]["kpi"] < .03
    primary = "grave-01-open14-p8"
    for version in STRATEGIES[:4]:
        assert keyed[version, primary]["trench_length_m"] == 20660
        assert keyed[version, primary]["occupied_length_m"] == 40
    evidence = {}
    for version, profile in manifest["profiles"].items():
        snap = REPO / profile["snapshot"]
        origin = REPO / profile["origin"]
        for directory in [snap, origin]:
            assert sha(directory / "solution.cpp") == profile["source_sha256"]
            assert sha(directory / "solver") == profile["binary_sha256"]
        verification = origin / "open/verification.json"
        if verification.exists():
            d = json.loads(verification.read_text())
            assert d["correct"] and d["cases"] == 15
            assert d["source_sha256"] == profile["source_sha256"]
            assert d["binary_sha256"] == profile["binary_sha256"]
            evidence[version] = {"kind": "pre_existing_official_local_Open15_verification",
                                 "score": d["score"], "file": str(verification.relative_to(REPO)),
                                 "sha256": sha(verification)}
        else:
            evidence[version] = {"kind": "offline_plan_audit_only", "score": profile["audited_open15_score"],
                                 "file": str((snap / "plan-audit.json").relative_to(REPO)),
                                 "sha256": sha(snap / "plan-audit.json")}
    raw = (REPO / tests[primary]["file"]).read_text().split()
    cmd = list(map(int, raw[2:]))
    witness = {"case": primary, "commands": cmd, "common_public_prefix": 8,
               "source_public_case": 14, "peak_volume_m": 40, "final_volume_m": 40,
               "attainable_optimal_trench_m": 40, "strategies": {},
               "conditional_certificate": "Every allocator that has already excavated at least 20660 m after this 8-command prefix has KPI <= 40/20660 on this fixed continuation, whatever its mismatch fallback does. Excavation is irreversible."}
    for strategy in STRATEGIES:
        r = keyed[strategy, primary]
        lines = Path(r["judge_output_file"]).read_text().splitlines()
        assert len(lines) == len(cmd)
        trench = 0
        trajectory = []
        for index, (c, line) in enumerate(zip(cmd, lines), 1):
            if c > 0:
                trench += int(line.split()[0]) * 20
            trajectory.append({"operation": index, "command": c, "reply": line, "trench_m": trench})
        witness["strategies"][strategy] = trajectory
    assert witness["strategies"]["release-v3"][7]["reply"] == "1032 20650"
    assert witness["strategies"]["bestfit"][7]["reply"] == "0 12"
    (HERE / "witness.json").write_text(json.dumps(witness, indent=2) + "\n")
    result = {"status": "36_of_36_official_local_checks_ok", "platform_actions": 0,
              "actual_target_releases": manifest["profiles"], "original_Open15_evidence": evidence,
              "old_or_proxy_replay_used_as_target": False,
              "targets_modified": False, "snapshots_and_original_hashes_rechecked": True,
              "all_traps_have_attained_optimal_kpi_1": True,
              "scope": "All four frozen versions v1-v4 of this actual method are hit by the primary trap. V4 was checked after this suite was fixed. This is not a theorem about all algorithms optimized on Open15; a method that avoids early reservations may pass.",
              "max_solver_cpu_s": max(r["solver_cpu_total_s"] for r in records),
              "max_solver_rss_mb": max(r["solver_peak_rss_mb"] for r in records),
              "tests": manifest["tests"], "records": records,
              "source_hashes": {str(p.relative_to(REPO)): sha(p) for p in [HERE / "construct.py", HERE / "summarize.py", REPO / "tools/pipes_harness.py", REPO / "tools/interactor", REPO / "vendor/pipes_official/interactor.cpp"]}}
    (HERE / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    fields = ["test", "common_prefix", "commands", "F", *STRATEGIES]
    with (HERE / "metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for name, meta in tests.items():
            writer.writerow({"test": name, "common_prefix": meta["prefix"], "commands": meta["operation_count"], "F": meta["F"], **{s: keyed[s, name]["kpi"] for s in STRATEGIES}})
    rows = []
    for name, meta in tests.items():
        cells = [f'<a href="suite/{name}.in">{name}</a>', str(meta["prefix"]), str(meta["operation_count"])]
        cells += [f'{keyed[s, name]["kpi"]:.9f}' for s in STRATEGIES]
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    text = '''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Ловушки для актуального Open15-метода</title>
<style>body{max-width:1250px;margin:45px auto;padding:0 24px;font:17px/1.6 system-ui;color:#18252b;background:#fafbf9}h1{line-height:1.2}.lead{font-size:21px}.proof{background:#eaf2ed;border-left:4px solid #367b4a;padding:18px 24px}table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}td,th{padding:10px;border:1px solid #ccd5d5;text-align:left}a{color:#005c79}pre{overflow:auto;padding:18px;background:#e9eef0}code{background:#e9eef0;padding:2px 5px}</style>
<h1>Ловушки для нынешнего метода максимизации Open15</h1>
<p class="lead">Проверены настоящие, неизменённые программы release-v1, release-v2, release-v3 и release-v4 из текущей разработки. Один тест из 17 команд обрушает KPI всех четырёх до 0,001936108, тогда как обычные Best-Fit и Trial22 получают 1. Все ответы остаются корректными. Версия v4 появилась после фиксации набора и была проверена на тех же входах.</p>
<p><a href="suite/grave-01-open14-p8.in">Главный вход, 17 команд</a> · <a href="graves.zip">Архив всех 6 входов с отчётом</a> · <a href="witness.json">Пошаговый сертификат</a> · <a href="metrics.csv">Таблица CSV</a></p>
<h2>Почему работает</h2>
<p>Первые восемь запросов в точности совпадают с открытым тестом №14:</p>
<pre>2 2 3 1 1 2 1 6</pre>
<p>На восьмом запросе обычный Best-Fit размещает трубу по адресу 12 и остаётся в траншее длиной 20 м. Все четыре Open15-версии отвечают <code>1032 20650</code>: заранее выкапывают ещё 20 640 м и ставят шестиметровую трубу по адресу 20 650 под ожидаемое публичное будущее. Длина траншеи уже равна 20 660 м.</p>
<p>Настоящее продолжение меняется: <code>-1 -2 -3 -4 -5 -6 -7 -8 40</code>. Все восемь труб корректно удаляются, затем укладывается одна труба 40 м. Replay замечает расхождение и правильно переключается на BF, но траншея не сокращается.</p>
<div class="proof">Финальная масса и пиковая масса обе равны 40 м. Оптимальная траншея 40 м реально достигнута двумя обычными online-контролями: KPI = 1. Подогнанные версии сохраняют 20 660 м: KPI = 40 / 20 660 ≈ 0,001936108, в 516,5 раза хуже. Любое продолжение, даже идеальное и знающее суффикс, уже не исправит такую затрату на общем префиксе.</div>
<h2>Проверенная матрица: фактический KPI</h2>
<table><thead><tr><th>Вход</th><th>Общий префикс</th><th>Команд</th><th>Release v1</th><th>Release v2</th><th>Release v3</th><th>Release v4</th><th>Best-Fit</th><th>Trial22</th></tr></thead><tbody>''' + "".join(rows) + '''</tbody></table>
<p>Во всех 36 новых запусках официальный interactor принял все ответы. Каждый стресс-вход имеет потолок KPI = 1, достигнутый Best-Fit. У release-v3 все шесть KPI ниже 0,03; у Trial22 минимум 0,998374. Это целевой набор контрпримеров, а не случайная оценка скрытого распределения.</p>
<h2>Регрессия при максимизации открытого результата</h2>
<p>Пятикомандный вход <code>3 2 -1 -2 40</code> начинается как открытые №11 и №15. Release v1 и v2 проходят его с KPI = 1, а release v3 — с KPI ≈ 0,003696858. Этот пример показывает новую уязвимость именно текущей версии; нельзя переносить результат старого плана на новую программу без запуска. Более длинный тест сохраняет первые 5002 команды открытого №15, после чего release v3 получает 0,029322, Best-Fit — 1, Trial22 — 0,998374.</p>
<h2>Что именно зафиксировано</h2>
<p>Скопированы неизменённые source и binary четырёх готовых release. До и после проверки сверены hashes snapshots и исходных release; оптимизируемый метод не менялся. Для release-v3 имеется ранее выполненная официальная локальная проверка Open15: 30,753692580164. Её исходник SHA256 <code>0cf8bc500497ab08283c2384075254ccf6c6d34f504154829c39608e2c99f4cd</code>. Источники прежних проверок и точный статус каждой версии записаны в report.json; Open15 заново здесь не запускался.</p>
<p>Тест даёт общую гарантию против механизма: любой алгоритм, который на этом восьмикомандном префиксе вырыл не менее 20 660 м, получит KPI не выше 40/20 660. Но из факта оптимизации на Open15 не следует, что любой возможный алгоритм делает такую затрату. Поэтому проверено «все четыре готовые версии нынешнего метода», а не заявлено «все возможные методы максимизации Open15». Новую версию нужно снова проверять.</p>
<p><a href="manifest.json">Происхождение, snapshots, hashes и входы</a> · <a href="report.json">Все результаты официального checker</a> · <a href="construct.py">Конструктор тестов</a>. Платформа, остановленные кампании и исходники другого чата не изменялись.</p></html>'''
    (HERE / "report.html").write_text(text)
    readme = """Pipes: targeted graves for actual Open15 releases v1/v2/v3/v4.
All six .in files have format: local weight 1, command count, commands.
The terminator 0 is issued by the interactor and is not part of the command count.
36/36 official local checks passed. Best-Fit achieves KPI=1 on every input.
The primary 17-command input hits all four frozen releases at KPI=40/20660.
This is a targeted adversarial suite; it does not prove that every algorithm
optimized for Open15 must fail or estimate performance on random hidden tests.
In the original repository, run a new candidate with tools/pipes_harness.py
and --tests prototypes/pipes_open15_adversary_20261019/suite,
using a new --out directory. See report.html and metrics.csv.
"""
    (HERE / "README.txt").write_text(readme)
    with zipfile.ZipFile(HERE / "graves.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for p in sorted((HERE / "suite").glob("*.in")):
            archive.write(p, str(p.relative_to(HERE)))
        for name in ["report.html", "report.json", "manifest.json", "metrics.csv", "witness.json", "README.txt", "construct.py", "summarize.py"]:
            archive.write(HERE / name, name)
    print("36/36 correct; primary KPI", {s: keyed[s, primary]["kpi"] for s in STRATEGIES})
    print("max CPU", result["max_solver_cpu_s"], "max RSS", result["max_solver_rss_mb"])
    print("package bytes", (HERE / "graves.zip").stat().st_size)


if __name__ == "__main__":
    main()
