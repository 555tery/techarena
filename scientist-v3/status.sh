#!/usr/bin/env bash
# Статус research-прогона AI-Scientist (Pipes) — всё важное одной командой.
# Запуск из папки scientist-v3:   ./status.sh
# (или непрерывно:    while :; do clear; ./status.sh; sleep 60; done )
set -u
cd "$(dirname "$0")" || exit 1

RUN=$(ls -td runs/pipes/opencode/*/ 2>/dev/null | head -1)
RUN=${RUN%/}

echo "════════ СТАТУС ($(date '+%H:%M:%S')) ════════"

if [ -n "$RUN" ]; then
  echo "прогон: ${RUN#runs/pipes/opencode/}"
else
  echo "прогон: ❌ не найден"
fi

if pgrep -f "agsci run" >/dev/null 2>&1; then
  echo "пайп :  ЖИВ (pid $(pgrep -f 'agsci run' | head -1))"
else
  echo "пайп :  не запущен"
fi
if [ -f .research_loop.pid ] && kill -0 "$(cat .research_loop.pid)" 2>/dev/null; then
  nprom=$(cat .promotions.log 2>/dev/null | wc -l | tr -d ' ')
  echo "контур: ЖИВ (pid $(cat .research_loop.pid)) | продвижений: ${nprom:-0}"
else
  echo "контур: не запущен"
fi
[ -f .research_loop.log ] && echo "        $(tail -1 .research_loop.log)"
if [ -f .report_watch.pid ] && kill -0 "$(cat .report_watch.pid)" 2>/dev/null; then
  nd=$(python3 -c "import json;print(json.load(open('.report_state.json')).get('next_due',''))" 2>/dev/null | cut -c12-16)
  echo "отчёт : ЖИВ (pid $(cat .report_watch.pid)) | следующий ~${nd:-?}"
else
  echo "отчёт : не запущен"
fi

echo ""

[ -z "$RUN" ] && exit 0

python3 - "$RUN" <<'PY'
import json, os, sys, time
run = sys.argv[1]

def age(path):
    if not os.path.exists(path): return None
    return int(time.time() - os.path.getmtime(path))

def stamp(a):
    if a is None: return "нет данных"
    if a < 130: return f"живой ({a} с)"
    if a < 300: return f"⚠️ {a} с назад"
    return f"🔴 молчит {a//60}м{a%60:02d}с"

def last_jsonl(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0: return None
    lines = [l for l in open(path, errors="replace") if l.strip()]
    if not lines: return None
    try: return json.loads(lines[-1])
    except Exception: return None

# фаза верхнего уровня
pe = os.path.join(run, "pipeline_events.jsonl")
d = last_jsonl(pe)
if d:
    f = d.get("fields", {})
    print(f"фаза : {f.get('phase_name','?')} — {f.get('label','')} (идёт {f.get('elapsed','?')}) | пульс: {stamp(age(pe))}")

# текущий шаг investigation
ev = os.path.join(run, "investigation/events.jsonl")
d = last_jsonl(ev)
if d:
    f = d.get("fields", {})
    extra = " | ".join(f"{k}={f[k]}" for k in ("step", "cycle", "generation_attempt") if k in f)
    print(f"шаг  : {extra or d.get('event','?')} | пульс: {stamp(age(ev))}")

# главные счетчики
ost = os.path.join(run, "investigation/outer_state.json")
if os.path.exists(ost):
    s = json.load(open(ost))
    total = None
    if os.path.exists(ev):
        with open(ev, errors="replace") as _f:
            for _l in _f.read().splitlines()[-50:]:
                try:
                    total = json.loads(_l).get("fields", {}).get("total_cycles") or total
                except Exception:
                    pass
    print(f"цикл : {s.get('current_cycle','?')}/{total or '?'} | неудач подряд: {s.get('failure_streak','?')}")

ih = os.path.join(run, "investigation/ideas_history.jsonl")
ideas = []
if os.path.exists(ih):
    ideas = [json.loads(l) for l in open(ih, errors="replace") if l.strip()]
print(f"идеи : {len(ideas)}" + (f" | последняя: «{ideas[-1].get('title','?')}»" if ideas else ""))

fl = os.path.join(run, "investigation/idea_generation_failures.jsonl")
n = sum(1 for l in open(fl, errors="replace") if l.strip()) if os.path.exists(fl) else 0
print(f"сбои : {n} (генерация идей)")

# журнал оценок кандидатов
ah = os.path.join(run, "investigation/attempts_history.jsonl")
atts = [json.loads(l) for l in open(ah, errors="replace") if l.strip()] if os.path.exists(ah) else []
if atts:
    r = atts[-1]
    line = (f"оценки: {len(atts)} попыток | последняя: цикл {r.get('cycle_index','?')}, "
            f"попытка {r.get('attempt_number','?')} → {r.get('attempt_status','?')}")
    if r.get("best_updated"):
        line += " ★ обновила лучший скор"
    print(line)
    m = r.get("metrics") or {}
    nums = {k: v for k, v in m.items() if isinstance(v, (int, float))}
    if nums:
        print("        метрики: " + ", ".join(f"{k}={v}" for k, v in list(nums.items())[:4]))

# лучший результат против базы
bm = os.path.join(run, "investigation/best_program_manifest.json")
if os.path.exists(bm):
    m = json.load(open(bm))
    print(f"скор : {m.get('combined_score','?')} (correct={m.get('correct','?')}) | обновлён: {str(m.get('updated_at',''))[:19]}")

# пейсер / релей
pl = os.path.join(run, "investigation/.agent_home/zen_pacer.log")
if os.path.exists(pl):
    lines = open(pl, errors="replace").read().splitlines()
    ok = sum(1 for l in lines if "-> 200" in l)
    bad = sum(1 for l in lines if "retryable" in l)
    print(f"релей: 200 x{ok} | 429-волны x{bad} | {stamp(age(pl))}")
    if lines:
        print(f"        {lines[-1][-100:]}")
# текущая база (обновляется контуром при продвижении победителя)
bsf = ".baseline_score"
if os.path.exists(bsf):
    print(f"база : {open(bsf).read().strip()} (.baseline_score)")
plog = ".promotions.log"
if os.path.exists(plog):
    lines = [l for l in open(plog, errors="replace") if l.strip()]
    if lines:
        try:
            r = json.loads(lines[-1])
            print(f"промо: {r.get('score_old')} -> {r.get('score_new')} в {str(r.get('timestamp',''))[:19]}")
        except Exception:
            pass
PY

echo ""
echo "── контейнеры ──"
docker ps --format '{{.Names}}  {{.Status}}' 2>/dev/null | grep -E 'agentic-opencode|keepalive' || echo "(нет)"