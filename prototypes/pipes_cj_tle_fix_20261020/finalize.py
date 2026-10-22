#!/usr/bin/env python3
"""Package only a completely checked source, with explicit local/server limits."""
import hashlib
import html
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "pipes_current_hybrid_cj_20261020"
CANDIDATE = "candidate-final"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def main():
    source = HERE / CANDIDATE / "solution.cj"
    digest = sha(source)
    freeze = json.loads((BASE / "freeze.json").read_text())
    expected = {c["id"] for c in freeze["cases"]}
    measurements = {}
    for opt in ("o0", "o2"):
        directory = HERE / "corpus" / f"{CANDIDATE}-{opt}"
        manifest = json.loads((directory / "manifest.json").read_text())
        assert manifest["source_sha256"] == digest
        assert manifest["baseline_freeze_sha256"] == sha(BASE / "freeze.json")
        rows = read_rows(directory / "records.jsonl")
        assert len(rows) == len(expected) and {r["id"] for r in rows} == expected
        assert all(r["status"] == "ok" and r["response_equal"] and r["kpi_equal"] for r in rows)
        assert all(r["source_sha256"] == digest for r in rows)
        build = json.loads((HERE / "bin" / f"{CANDIDATE}-{opt}.build.json").read_text())
        assert build["source_sha256"]["solution.cj"] == digest
        assert build["binary_sha256"] == manifest["binary_sha256"]
        metrics = {
            "completed": len(rows),
            "response_and_kpi_matches": len(rows),
            "resource_failures": sum(not r["within_limits"] for r in rows),
            "cpu_total_s": sum(r["solver_cpu_total_s"] for r in rows),
            "cpu_max_s": max(r["solver_cpu_total_s"] for r in rows),
            "rss_max_mib": max(r["solver_peak_rss_mb"] for r in rows),
            "open15_score": sum(r["weighted_score"] for r in rows if r["public_number"] is not None),
            "open15": [{
                "test": r["public_number"], "cpu_s": r["solver_cpu_total_s"],
                "rss_mib": r["solver_peak_rss_mb"], "kpi": r["kpi"],
                "score": r["weighted_score"], "response_sha256": r["response_sha256"],
                "within_limits": r["within_limits"],
            } for r in rows if r["public_number"] is not None],
            "slowest": [{
                "id": r["id"], "origin": r["origin"],
                "cpu_s": r["solver_cpu_total_s"], "rss_mib": r["solver_peak_rss_mb"],
            } for r in sorted(rows, key=lambda r: r["solver_cpu_total_s"], reverse=True)[:10]],
            "build": build, "manifest": manifest,
            "records_sha256": sha(directory / "records.jsonl"),
        }
        measurements[opt] = metrics

    baseline = json.loads((HERE / "checks/baseline105-o0/summary.json").read_text())
    comparison = []
    for old in baseline:
        new = next(r for r in measurements["o0"]["open15"] if r["test"] == old["public_number"])
        comparison.append({
            "test": old["public_number"], "baseline_cpu_s": old["solver_cpu_total_s"],
            "candidate_cpu_s": new["cpu_s"],
            "speedup": old["solver_cpu_total_s"] / new["cpu_s"],
            "baseline_rss_mib": old["solver_peak_rss_mb"], "candidate_rss_mib": new["rss_mib"],
        })

    release = HERE / "release"
    release.mkdir(exist_ok=True)
    shutil.copyfile(source, release / "solution.cj")
    assert sha(release / "solution.cj") == digest
    # Safari's file chooser accepts .txt for this contest form.
    shutil.copyfile(source, release / "solution-upload.txt")
    assert sha(release / "solution-upload.txt") == digest

    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "local_validation_complete; server_resubmission_pending",
        "source": "release/solution.cj", "source_sha256": digest,
        "source_bytes": source.stat().st_size,
        "previous_submission": {
            "id": 1667192, "score": 15.85787, "accepted": 12, "tle": [9, 14, 15],
            "source_sha256": sha(BASE / "release/solution.cj"),
        },
        "protocol": {
            "compiler": "Official Cangjie 1.0.5, cjnative aarch64-apple-darwin",
            "host": platform.platform(), "workers": 1, "cjProcessorNum": 1,
            "cpu": "Whole solver process user+system CPU, including all runtime threads",
            "memory": "Peak process RSS, including native allocations",
            "limits": {"cpu_s": 5, "rss_mib": 256},
            "hard_cpu_affinity": False,
            "limitations": [
                "Local macOS/M1 timings are not Windows10/Pentium G5420 timings.",
                "The server's Cangjie optimization flags and exact CPU/RSS were not available.",
                "Only a new server submission can confirm that the competition TLE is resolved.",
            ],
        },
        "corpus": {"total": len(expected), "archive": 2537, "fresh": 96, "open15_extra": 4},
        "measurements": measurements,
        "open_failures_before_after_o0": comparison,
        "changes": [
            "Exact concrete Int64 collections remove generic overhead in integer hot paths.",
            "Incremental counters replace repeated scans of unchanged recent history.",
            "The exact last three run lengths/counts replace repeated scans of the 2048-entry window; counts are clipped to the current suffix.",
            "AVL repair stops only when the subtree height is unchanged.",
            "Fixed native numeric buffers remove large VArray copies at -O0.",
            "DP keeps all FP updates in the same order, excluding only exactly-zero rate sizes.",
            "The minimum active reward skips only elimination passes that would perform no FP update.",
            "Integer overflow traps are removed only from the two explicitly bounded DP methods.",
            "Bounded DP borrows stable numeric buffers to avoid per-cell wrapper overhead.",
            "Native numeric tree storage, contiguous Key triples and direct comparisons retain the same indexed AVL sequence.",
            "Transient AVL pointer borrows keep their strong owner alive with public std.runtime.blackBox; no borrow crosses a reallocation.",
            "Small AVL height/parent helpers are expanded with the same integer reads and writes.",
            "Eight ordered lifetime age bins use an exactly equivalent comparison tree.",
            "Large-gap DP request loops are expanded in ascending size order; small-gap loops and every FP accumulation remain unchanged.",
            "Lifetime fit expands exposure formulas, avoids duplicate cell reads and reuses identical borrowed-exposure quotients; accumulation order is unchanged.",
            "Both DP methods explicitly keep their fixed-buffer owners strongly reachable after the last raw access with blackBox(this).",
        ],
        "unchanged": [
            "Replay tables and guards, policy thresholds, rollout depth and budgets",
            "Deterministic random sequence, floating-point recurrence and tie breaking",
            "Interactive response protocol with immediate flush",
        ],
        "audit_files": [str(p.relative_to(HERE)) for p in sorted((HERE / "audit").glob("*.json"))],
        "rejected_experiments": [
            "Native wrappers for lifetime structs regressed -O0 CPU and are not included.",
            "DP scalar rate/reward storage regressed the focused timings and is not included.",
            "Diagnostic DP memoization opportunity was too small on the measured heavy streams; no memoization was added.",
            "The if(true)-scoped unroll triggered Cangjie 1.0.5 unreachable warnings; the selected source uses independently checked unique local names.",
        ],
    }
    platform_attempt = HERE / "platform/attempt.json"
    if platform_attempt.exists():
        attempt = json.loads(platform_attempt.read_text())
        assert attempt["source_sha256"] == digest
        result["server"] = attempt
        if attempt.get("submission_id"):
            result["status"] = "local_validation_complete; server_" + attempt["status"]
    old_remaining = HERE / "corpus/baseline105-remaining-limits-o0/records.jsonl"
    if old_remaining.exists():
        old_rows = read_rows(old_remaining)
        new_rows = read_rows(HERE / "corpus/candidate-final-o0/records.jsonl")
        failed = {r["id"]: r for r in new_rows if not r["within_limits"]}
        if {r["id"] for r in old_rows} == set(failed):
            assert all(r["response_equal"] and r["kpi_equal"] and r["status"] == "ok" for r in old_rows)
            assert all(r["source_sha256"] == sha(BASE / "release/solution.cj") for r in old_rows)
            result["archive_limit_comparison_o0"] = [{
                "id": old["id"], "origin": old["origin"],
                "baseline_cpu_s": old["solver_cpu_total_s"],
                "candidate_cpu_s": failed[old["id"]]["solver_cpu_total_s"],
                "baseline_within_limits": old["within_limits"],
                "candidate_within_limits": failed[old["id"]]["within_limits"],
                "response_and_kpi_equal": True,
            } for old in old_rows]
    (HERE / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    write_report(result)
    print(json.dumps({
        "source_sha256": digest,
        "o0": {k: measurements["o0"][k] for k in ("completed", "resource_failures", "cpu_max_s", "rss_max_mib", "open15_score")},
        "o2": {k: measurements["o2"][k] for k in ("completed", "resource_failures", "cpu_max_s", "rss_max_mib", "open15_score")},
    }, ensure_ascii=False, indent=2))


def write_report(result):
    measurements = result["measurements"]
    rows = []
    for row in result["open_failures_before_after_o0"]:
        optimized = next(r for r in measurements["o2"]["open15"] if r["test"] == row["test"])
        rows.append(
            f'<tr><td>{row["test"]}</td><td>{row["baseline_cpu_s"]:.3f}</td>'
            f'<td>{row["candidate_cpu_s"]:.3f}</td><td>{row["speedup"]:.2f}×</td>'
            f'<td>{optimized["cpu_s"]:.3f}</td></tr>'
        )
    summaries = []
    for opt in ("o0", "o2"):
        m = measurements[opt]
        summaries.append(
            f'<tr><td>-{opt.upper()}</td><td>{m["completed"]}</td>'
            f'<td>{m["response_and_kpi_matches"]}</td><td>{m["resource_failures"]}</td>'
            f'<td>{m["cpu_max_s"]:.3f}</td><td>{m["rss_max_mib"]:.2f}</td></tr>'
        )
    server = result.get("server", {})
    if server.get("submission_id"):
        sid = int(server["submission_id"])
        verdict = html.escape(server.get("status_string", server["status"]))
        status = (
            f'Отправка <a href="https://olympic.nsu.ru/nsuts-new/solution?id={sid}">{sid}</a>, '
            f'Cangjie 1.0.5: {verdict}. '
        )
        if server.get("waiting_for_user_result"):
            status += (
                'Пользователь сообщит результат; автоматическая проверка сайта остановлена. '
                'Устранение серверного TLE пока не подтверждено.'
            )
    else:
        status = "Повторная отправка ещё не подтверждена. Устранение серверного TLE пока не подтверждено."
    document = """<!doctype html><html lang="ru"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cangjie 1.0.5 — ускорение без изменения ответов</title>
<style>
body{max-width:1000px;margin:40px auto;padding:0 24px;font:16px/1.6 system-ui;color:#182332;background:#f7f8fa}
h1{line-height:1.2}table{border-collapse:collapse;width:100%;background:white;margin:20px 0}
th,td{text-align:left;padding:10px;border-bottom:1px solid #d5dce5}th{font-size:14px}
.notice{padding:18px;background:#fff0d9;border-left:4px solid #ac6b00}code{overflow-wrap:anywhere}
a{color:#17519c}.muted{color:#546274}
</style><h1>Cangjie 1.0.5: ускорение без изменения ответов</h1>
"""
    document += f'<p class="notice">{status}</p>'
    document += (
        '<p>Замороженный корпус: 2537 архивных тестов, 96 новых независимых ловушек и 4 дополнительных Open15. '
        'Каждый запуск проверен официальным checker; полные ответы и KPI сравнены с прежним гибридом.</p>'
        f'<p><strong>Локальный счёт Open15: {measurements["o2"]["open15_score"]:.11f}.</strong> '
        'Политика выбора, replay, пороги и случайная последовательность сохранены.</p>'
        '<h2>Три теста, на которых была остановка по времени</h2>'
        '<p>CPU в секундах. Старый и новый код собраны одним Cangjie 1.0.5.</p>'
        '<table><thead><tr><th>Тест</th><th>Прежний -O0</th><th>Новый -O0</th><th>Ускорение -O0</th><th>Новый -O2</th></tr></thead><tbody>'
        + "".join(rows) + '</tbody></table>'
        '<h2>Полный корпус</h2><table><thead><tr><th>Сборка</th><th>Тестов</th><th>Совпали ответы/KPI</th>'
        '<th>Превышений лимитов</th><th>Макс. CPU, с</th><th>Макс. RSS, MiB</th></tr></thead><tbody>'
        + "".join(summaries) + '</tbody></table>'
        '<p>Лимиты проверки: 5 с CPU и 256 MiB RSS. CPU — user+system всего процесса, включая runtime; '
        'RSS включает native allocations. Один worker, cjProcessorNum=1. Жёсткая привязка к одному ядру не применялась.</p>'
        '<p class="notice">Это macOS на Apple M1. Эти числа нельзя выдавать за время Windows 10 на Pentium G5420. '
        'Флаги компиляции сервера неизвестны. При превышении времени точное совпадение KPI само по себе не означает зачёт теста.</p>'
    )
    if result.get("archive_limit_comparison_o0"):
        document += '<h2>Оставшиеся превышения при -O0</h2><table><thead><tr><th>Тест</th><th>Прежний CPU, с</th><th>Новый CPU, с</th></tr></thead><tbody>'
        for row in result["archive_limit_comparison_o0"]:
            document += (
                f'<tr><td>{html.escape(Path(row["origin"]).name)}</td>'
                f'<td>{row["baseline_cpu_s"]:.3f}</td><td>{row["candidate_cpu_s"]:.3f}</td></tr>'
            )
        document += '</tbody></table><p>Те же входы, Cangjie 1.0.5 -O0, один worker. Ответы и KPI в обоих вариантах совпали с замороженным эталоном.</p>'
    document += (
        '<h2>Что изменилось</h2><p>Убраны лишние копирования больших VArray и повторные обходы истории; '
        'ускорены целочисленные коллекции, AVL и внутренние циклы DP. Расчёт модели времени жизни '
        'сохраняет формулы и порядок суммирования. Параметры алгоритма ради скорости не урезались.</p>'
        '<p>В прежней отправке 1667192 было 12/15 Accepted и TLE на 9, 14, 15; счёт 15.85787. '
        'Архив сервера подтвердил совпадение завершённых ответов и префиксов незавершённых. '
        'Точная причина серверной остановки и серверный CPU/RSS недоступны.</p>'
        f'<p class="muted">SHA-256 исходника: <code>{result["source_sha256"]}</code></p>'
        '<p><a href="release/solution.cj">Исходник Cangjie</a> · '
        '<a href="release/solution-upload.txt">Тот же исходник для загрузки</a> · '
        '<a href="result.json">Измерения и манифесты</a></p></html>'
    )
    (HERE / "report.html").write_text(document)


if __name__ == "__main__":
    main()
