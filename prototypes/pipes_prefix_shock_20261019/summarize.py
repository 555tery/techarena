#!/usr/bin/env python3
"""Collect official local checker results without assigning a KPI to invalid runs."""
import hashlib
import html
import json
import platform
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((HERE / "manifest.json").read_text())
    rows = []
    for strategy in ["trial22", "bestfit", "guarded", "blind"]:
        summary = json.loads((HERE / "evaluations" / strategy / "summary.json").read_text())
        for record in summary["records"]:
            case = Path(record["case"]).stem
            message_file = Path(record["interactor_report_file"])
            message = message_file.read_text().strip() if message_file.exists() else record["interactor_stderr"].strip()
            rows.append({
                "strategy": strategy, "case": case,
                "status": record["status"], "detail": record["detail"],
                "raw_kpi": record["kpi"] if record["status"] == "ok" else None,
                "harness_kpi_field": record["kpi"],
                "score_for_local_weight_1": record["weighted_score"] if record["status"] == "ok" else 0,
                "final_occupied_m": record["final_occupied_length_m"],
                "trench_m": record["trench_length_m"],
                "volume_efficiency": record["fraction_of_bound"] if record["status"] == "ok" else None,
                "commands_seen": record["judge_commands_seen_including_final_zero"],
                "interactor_message": message,
                "solver_cpu_s": record["solver_cpu_total_s"],
                "solver_rss_mb": record["solver_peak_rss_mb"],
                "within_resources": not record["solver_cpu_limit_exceeded"] and not record["solver_memory_limit_exceeded"],
                "test_sha256": record["test_sha256"],
            })
    by_key = {(r["strategy"], r["case"]): r for r in rows}
    for strategy in ["trial22", "bestfit", "guarded"]:
        for case in ["prefix-control", "prefix-drain", "prefix-shock"]:
            r = by_key[strategy, case]
            assert r["status"] == "ok" and r["within_resources"]
        assert by_key[strategy, "prefix-drain"]["raw_kpi"] <= 1 / 241380 + 1e-14
        assert by_key[strategy, "prefix-shock"]["raw_kpi"] > 0.99
    assert by_key["blind", "prefix-control"]["status"] == "ok"
    for case in ["prefix-shock", "prefix-drain"]:
        assert by_key["blind", case]["status"] != "ok"
        assert by_key["blind", case]["raw_kpi"] is None
        meta = next(c for c in manifest["cases"] if c["name"] == case)
        assert by_key["blind", case]["commands_seen"] == meta["first_divergent_operation_1based"]
        assert "position of pipe 1 is wrong" in by_key["blind", case]["interactor_message"]
    baseline = REPO / "research-campaigns/20261018T141843+0700-autonomous/releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp"
    report = {
        "status": "constructed_and_checked_locally", "platform_actions": 0,
        "search_or_tuning_trials": 0, "case_count": 3,
        "checker_run_count": len(rows),
        "expected_replay_failures": 2,
        "claim": "Drain guarantees raw KPI <= 1/241380 for every legal solution; shock separates blind replay from the checked causal and guarded controls.",
        "limit": "The raw KPI collapse is not selective for overfitting. Shock produces invalid output and a zero local score for blind replay, not a valid near-zero KPI. Guarded replay and trial22 survive; no claim about all tuned algorithms.",
        "controls": {
            "trial22": "Unchanged actual released online source, rebuilt for this diagnostic.",
            "bestfit": "Plain generic Best-Fit with tail reuse.",
            "guarded": "Diagnostic execution of the frozen public-future placement plan; exact command matching, permanent BF fallback preserving all prior placements on mismatch.",
            "blind": "Explicitly defective diagnostic control: uses the same frozen tape even after the observed command diverges.",
        },
        "baseline_source_sha256": sha(baseline),
        "hashes": {str(p.relative_to(REPO)): sha(p) for p in [
            HERE / "generate.py", HERE / "allocator_probe.cpp", HERE / "tape.txt",
            HERE / "allocator-probe", HERE / "trial22", REPO / "vendor/pipes_official/interactor.cpp",
            REPO / "tools/interactor", REPO / "tools/pipes_harness.py",
        ]},
        "compiler": subprocess.check_output(["clang++", "--version"], text=True).splitlines()[0],
        "compiler_flags": {"probe": "-O2 -std=c++17 -Wall -Wextra", "trial22": "-O2 -std=c++20"},
        "host": platform.platform(), "cases": manifest["cases"], "results": rows,
    }
    (HERE / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    table = []
    for strategy in ["trial22", "bestfit", "guarded", "blind"]:
        columns = []
        for case in ["prefix-control", "prefix-drain", "prefix-shock"]:
            r = by_key[strategy, case]
            columns.append(f"{r['raw_kpi']:.12g}" if r["status"] == "ok" else "ошибка ответа; балл 0")
        table.append("<tr><th>" + strategy + "</th>" + "".join(f"<td>{html.escape(x)}</td>" for x in columns) + "</tr>")
    document = '''<!doctype html><html lang="ru"><meta charset="utf-8">
<title>Тесты с общим префиксом Open15</title>
<style>body{max-width:1000px;margin:48px auto;padding:0 24px;font:17px/1.55 system-ui;color:#17202a;background:#fafbf9}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}td,th{padding:12px;border:1px solid #ccd3d6;text-align:left}code{background:#eaf0eb;padding:2px 5px}a{color:#075e85}h1{line-height:1.2}</style>
<h1>Общий префикс, другое продолжение</h1>
<p>Построены три фиксированных входа. Все 12 проверок выполнены локально официальным interactor; два ошибочных ответа слепого replay — ожидаемый результат. Платформа и остановленные поиски не использовались.</p>
<p><a href="inputs/prefix-drain.in">prefix-drain.in</a>: первые 100 000 команд точно совпадают с открытым тестом №15. Затем удаляются все 60 380 активных труб и добавляется одна труба длины 1. Всего 160 381 команда, длины 1–40, все удаления допустимы. Пиковая сумма длин 241 363, поэтому траншея любого корректного решения не короче 241 380 м. Итоговый KPI ≤ 1 / 241 380 ≈ 0,0000041428453, то есть 0,0004143%. Это обрушает KPI любого решения и само по себе ничего не доказывает о подгонке.</p>
<p><a href="inputs/prefix-shock.in">prefix-shock.in</a>: первые 8192 команды совпадают с тестом №15. На шаге 8193 вместо ожидаемого удаления PID 6567 приходит удаление активного PID 1. Затем удаляются остальные активные трубы и укладываются 4000 труб по 40 м. Всего 17 174 команды, финальная загрузка и объёмная нижняя граница — 160 000 м; потолок KPI равен 1. Слепое воспроизведение ломается сразу, а solver с проверкой входа может корректно продолжить.</p>
<p><a href="inputs/prefix-control.in">prefix-control.in</a>: неизменённые первые 8193 команды теста №15. Подтверждает, что сохранённые ответы законны до смены входа.</p>
<table><thead><tr><th>Контроль</th><th>Общий префикс</th><th>Удаление почти всего</th><th>Смена нагрузки</th></tr></thead><tbody>''' + "".join(table) + '''</tbody></table>
<p><code>trial22</code> — неизменённый исходник последней подтверждённой отправки. <code>bestfit</code> — обычный Best-Fit. <code>guarded</code> выполняет сохранённые размещения офлайн-плана, проверяет каждую команду и при расхождении навсегда переключается на Best-Fit, сохраняя реальные координаты. <code>blind</code> намеренно продолжает отвечать по таблице после расхождения. Последние два — диагностические контроли, а не опубликованные решения участников.</p>
<p>Ошибка ответа не является вычисленным KPI = 0: interactor отклоняет ответ до расчёта KPI. В таблице отдельно указан нулевой локальный балл за некорректное выполнение. Утверждения о гарантированном провале всех алгоритмов, настроенных по открытым тестам, нет; защищённый replay этот тест проходит.</p>
<p><a href="manifest.json">Манифест входов</a> · <a href="report.json">Все метрики, hashes и границы вывода</a> · <a href="generate.py">Генератор</a> · <a href="allocator_probe.cpp">Диагностические контроли</a></p>
</html>'''
    (HERE / "report.html").write_text(document)
    for row in rows:
        print(row["strategy"], row["case"], row["status"], row["raw_kpi"], row["trench_m"])


if __name__ == "__main__":
    main()
