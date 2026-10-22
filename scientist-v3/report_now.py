#!/usr/bin/env python3
"""Один отчёт о прогрессе исследования (генерируется report_watch.sh каждые 30 мин).

Печатает отчёт в stdout (идёт в scientist-v3/reports.log), обновляет состояние
.report_state.json (счётчики для дельт) и шлёт короткое macOS-уведомление.
"""
import datetime as dt
import glob
import json
import os
import re
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = HERE / ".report_state.json"
REPORTS = sorted(glob.glob(str(HERE / "runs" / "pipes" / "opencode" / "*")), key=os.path.getmtime)


def last_jsonl(path):
    try:
        lines = [ln for ln in open(path, encoding="utf-8", errors="replace") if ln.strip()]
    except OSError:
        return None
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except ValueError:
        return None


def count_lines(path):
    try:
        return sum(1 for ln in open(path, encoding="utf-8", errors="replace") if ln.strip())
    except OSError:
        return 0


def pid_alive(pidfile):
    try:
        pid = int((HERE / pidfile).read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        return pid
    except Exception:
        return None


def pipe_pids():
    try:
        out = subprocess.run(["pgrep", "-f", "agsci run"], capture_output=True, text=True).stdout
        return out.split()
    except Exception:
        return []


def notify(msg, title="Pipes research"):
    msg = str(msg).replace("\\", "\\\\").replace('"', '\\"')[:220]
    title = title.replace('"', '\\"')
    subprocess.run(
        ["osascript", "-e", f'display notification "{msg}" with title "{title}"'],
        capture_output=True,
    )


def age_str(p):
    try:
        a = int(time.time() - os.path.getmtime(p))
    except OSError:
        return None
    return a


def human_age(a):
    if a is None:
        return "—"
    if a < 180:
        return f"{a} с"
    return f"{a // 60}м{a % 60:02d}с"


def main():
    now = dt.datetime.now()
    state = {}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except ValueError:
            state = {}

    run = Path(REPORTS[-1]) if REPORTS else None
    inv = (run / "investigation") if run else None

    lines = []
    lines.append("")
    lines.append("=" * 66)
    lines.append(f"ОТЧЁТ {now.strftime('%Y-%m-%d %H:%M')}  (каждые 30 мин; история: scientist-v3/reports.log)")
    lines.append("=" * 66)

    pids = pipe_pids()
    loop_pid = pid_alive(".research_loop.pid")
    lines.append(
        "процессы: пайплайн " + (f"ЖИВ (pid {pids[0]})" if pids else "НЕ РАБОТАЕТ")
        + " | контур " + (f"ЖИВ (pid {loop_pid})" if loop_pid else "не запущен")
    )

    if run is None:
        lines.append("прогонов пока нет")
        print("\n".join(lines))
        return

    new_run = str(run) != state.get("run")
    lines.append(f"прогон: {run.name}")

    # --- фаза и шаг ---
    pe = last_jsonl(run / "pipeline_events.jsonl")
    if pe:
        f = pe.get("fields", {})
        lines.append(f"фаза  : {f.get('phase_name','?')} — {f.get('label','')} (идёт {f.get('elapsed','?')})")
    ev = last_jsonl(inv / "events.jsonl")
    if ev:
        f = ev.get("fields", {})
        parts = [f"{k}={f[k]}" for k in ("step", "cycle", "generation_attempt") if k in f]
        lines.append("шаг   : " + (" | ".join(parts) if parts else ev.get("event", "?")))

    # --- счётчики и дельты ---
    n_ideas = count_lines(inv / "ideas_history.jsonl")
    n_att = count_lines(inv / "attempts_history.jsonl")
    n_fail = count_lines(inv / "idea_generation_failures.jsonl")
    n_prom = count_lines(HERE / ".promotions.log")
    d_ideas = n_ideas - int(state.get("ideas", 0))
    d_att = n_att - int(state.get("attempts", 0))
    d_prom = n_prom - int(state.get("promotions", 0))
    if new_run:
        d_ideas = d_att = d_prom = 0
        lines.append("(новый прогон — дельты сброшены)")

    ost = None
    try:
        ost = json.loads((inv / "outer_state.json").read_text(encoding="utf-8"))
    except Exception:
        pass

    lines.append(
        f"итоги : идей {n_ideas} (+{d_ideas} за период) | оценок {n_att} (+{d_att}) | "
        f"продвижений {n_prom} (+{d_prom}) | сбоев генерации {n_fail}"
    )
    if ost:
        max_cycles = "?"
        try:
            m = re.search(r"max_idea_cycles=(\d+)", (HERE / "run_pipes.sh").read_text(encoding="utf-8", errors="replace"))
            if m:
                max_cycles = m.group(1)
        except Exception:
            pass
        lines.append(
            f"цикл  : {ost.get('current_cycle','?')}/{max_cycles} | лучшее {ost.get('best_combined_score','?')} "
            f"(correct={ost.get('best_correct','?')}) | неудач подряд {ost.get('failure_streak','?')}"
        )

    ideas = []
    hp = inv / "ideas_history.jsonl"
    if hp.exists():
        ideas = [json.loads(ln) for ln in open(hp, encoding="utf-8", errors="replace") if ln.strip()]
    if ideas:
        lines.append(f"посл. идея: «{ideas[-1].get('title','?')}»")

    rec = last_jsonl(inv / "attempts_history.jsonl")
    if rec:
        m = rec.get("metrics") or {}
        lines.append(
            f"посл. оценка: цикл {rec.get('cycle_index','?')} попытка {rec.get('attempt_number','?')} → "
            f"{str(rec.get('attempt_status','?')).upper()} "
            f"(score={m.get('combined_score','?')}, correct={m.get('correct','?')})"
        )

    # --- база и продвижения за период ---
    bsf = HERE / ".baseline_score"
    base = bsf.read_text(encoding="utf-8").strip() if bsf.exists() else "?"
    bm = last_jsonl(inv / "best_program_manifest.json")
    if bm:
        lines.append(
            f"скор  : {bm.get('combined_score','?')} (correct={bm.get('correct','?')}) | база {base}"
        )
    if d_prom > 0:
        pl = HERE / ".promotions.log"
        last_prom = [ln for ln in open(pl, encoding="utf-8", errors="replace") if ln.strip()][-1]
        try:
            r = json.loads(last_prom)
            lines.append(f"★ ПРОДВИЖЕНИЕ: {r.get('score_old')} -> {r.get('score_new')} ({r.get('timestamp','')[:19]})")
        except ValueError:
            lines.append("★ ПРОДВИЖЕНИЕ (см. .promotions.log)")

    # --- релей ---
    plog = inv / ".agent_home" / "zen_pacer.log"
    relay_ok = None
    if plog.exists():
        text = open(plog, encoding="utf-8", errors="replace").read()
        ok = text.count("-> 200")
        bad = text.count("retryable")
        a = age_str(plog)
        relay_ok = a is not None and a < 300
        lines.append(f"релей : 200 x{ok} | 429-волны x{bad} | активность {human_age(a)}")

    # --- события за период ---
    ep = inv / "events.jsonl"
    if ep.exists():
        all_events = [ln for ln in open(ep, encoding="utf-8", errors="replace") if ln.strip()]
        prev = int(state.get("events", 0))
        if not new_run and prev <= len(all_events):
            fresh = all_events[prev:]
            if fresh:
                shown = []
                for ln in fresh[-10:]:
                    try:
                        d = json.loads(ln)
                        f = d.get("fields", {})
                        t = str(d.get("timestamp", ""))[11:16]
                        tags = [str(f.get(k)) for k in ("cycle",) if k in f]
                        shown.append(f"{t} {d.get('event','?')}" + (f"({','.join(tags)})" if tags else ""))
                    except ValueError:
                        continue
                if shown:
                    lines.append("события: " + " | ".join(shown))
        state["events"] = len(all_events)

    print("\n".join(lines))

    # --- уведомление ---
    cyc = ost.get("current_cycle", "?") if ost else "?"
    msg = f"цикл {cyc} | идей {n_ideas} | оценок {n_att} | скоp {bm.get('combined_score','?') if bm else '?'}"
    if d_prom > 0:
        msg = "★ УЛУЧШЕНИЕ! " + msg
    msg += " | релей " + ("OK" if relay_ok else "штормит")
    if not pids:
        msg = "⚠ ПАЙПЛАЙН НЕ РАБОТАЕТ | " + msg
    notify(msg)

    # --- состояние ---
    state.update({
        "ts": now.isoformat(timespec="seconds"),
        "run": str(run),
        "ideas": n_ideas,
        "attempts": n_att,
        "promotions": n_prom,
        "next_due": (now + dt.timedelta(minutes=30)).isoformat(timespec="seconds"),
    })
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
