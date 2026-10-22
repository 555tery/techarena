#!/opt/homebrew/bin/bash
# Бесконечный исследовательский контур для Pipes.
#   прогон -> продвижение победителя в базу -> пауза -> прогон -> ...
#
# Остановка: создать файл-флаг .research_loop.stop (контур завершит текущую
# итерацию и остановится), либо снять процесс контура (kill $(cat .research_loop.pid)).
# Состояние: .research_loop.log, .research_loop.run.out, .promotions.log
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

LOOP_LOG="$ROOT/.research_loop.log"
RUN_OUT="$ROOT/.research_loop.run.out"
STOP_FLAG="$ROOT/.research_loop.stop"
PID_FILE="$ROOT/.research_loop.pid"
COOLDOWN=300  # пауза между прогонами, секунд

log() { printf '[loop %s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOOP_LOG"; }

# --- единственный экземпляр ---
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  log "контур уже запущен (pid $(cat "$PID_FILE")) — выхожу"
  exit 0
fi
echo $$ > "$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT

log "контур стартовал (pid $$): бесконечный режим; стоп-флаг: $STOP_FLAG"

# --- дождаться завершения уже идущего прогона, чтобы не пересекаться ---
while pgrep -f "agsci run" >/dev/null 2>&1; do
  sleep 30
done
log "активных прогонов нет — начинаю цикл"

# --- бесконечный цикл ---
while true; do
  if [ -f "$STOP_FLAG" ]; then
    log "найден стоп-флаг — завершаюсь"
    break
  fi

  before_file="$(mktemp)"
  after_file="$(mktemp)"
  ls -d "$ROOT"/runs/pipes/opencode/*/ 2>/dev/null | sort > "$before_file" || true

  log "=== запускаю прогон ==="
  "$ROOT/run_pipes.sh" --run >> "$RUN_OUT" 2>&1
  rc=$?
  log "прогон завершён, rc=$rc"

  # находим каталог только что завершённого прогона
  ls -d "$ROOT"/runs/pipes/opencode/*/ 2>/dev/null | sort > "$after_file" || true
  new_dir="$(comm -13 "$before_file" "$after_file" | head -1)"
  rm -f "$before_file" "$after_file"
  if [ -z "$new_dir" ]; then
    new_dir="$(ls -dt "$ROOT"/runs/pipes/opencode/*/ 2>/dev/null | head -1 || true)"
    [ -n "$new_dir" ] && log "каталог особым способом: ${new_dir%/}"
  fi

  if [ -n "$new_dir" ]; then
    log "разбираю результат прогона: ${new_dir%/}"
    python3 "$ROOT/promote_best.py" --run-dir "${new_dir%/}" 2>&1 | tee -a "$LOOP_LOG" || true
  else
    log "каталог прогона не найден — промоушен пропущен"
  fi

  # пауза перед следующей итерацией (с проверкой стоп-флага)
  log "пауза ${COOLDOWN}s"
  elapsed=0
  while [ "$elapsed" -lt "$COOLDOWN" ]; do
    [ -f "$STOP_FLAG" ] && break
    sleep 10
    elapsed=$((elapsed + 10))
  done
done

log "контур остановлен"
