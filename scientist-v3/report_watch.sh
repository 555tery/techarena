#!/opt/homebrew/bin/bash
# Репортёр: каждые 30 минут пишет отчёт (report_now.py) в reports.log
# и шлёт macOS-уведомление. Остановка: файл .report_watch.stop
# или kill $(cat .report_watch.pid).
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

INTERVAL=1800            # 30 минут
PID_FILE="$ROOT/.report_watch.pid"
STOP_FLAG="$ROOT/.report_watch.stop"

log() { printf '[report %s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> reports.log; }

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  log "репортёр уже запущен (pid $(cat "$PID_FILE")) — выхожу"
  exit 0
fi
echo $$ > "$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT

log "репортёр стартовал (pid $$): отчёты каждые $((INTERVAL/60)) мин"

while true; do
  elapsed=0
  while [ "$elapsed" -lt "$INTERVAL" ]; do
    [ -f "$STOP_FLAG" ] && break 2
    sleep 60
    elapsed=$((elapsed + 60))
  done
  [ -f "$STOP_FLAG" ] && break
  python3 "$ROOT/report_now.py" >> reports.log 2>&1 || log "ошибка генерации отчёта (rc=$?)"
done

log "репортёр остановлен"
