#!/opt/homebrew/bin/bash
# Autorun wrapper: launch the pipeline; on failure retry up to 3 attempts
# with a 5-minute cooldown. Runs are guarded end-to-end by the in-container
# Zen pacer (>=60 s between every provider request, auto-retry on 429/5xx).
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
for i in 1 2 3; do
  echo "[autorun $(date '+%H:%M:%S')] run attempt $i/3 starting" >> .autorun.log
  ./run_pipes.sh --run > .pipeline_last.out 2>&1
  rc=$?
  echo "[autorun $(date '+%H:%M:%S')] pipeline exited rc=$rc" >> .autorun.log
  if [ "$rc" -eq 0 ]; then
    exit 0
  fi
  if [ "$i" -lt 3 ]; then
    echo "[autorun $(date '+%H:%M:%S')] cooling down 300s before next attempt" >> .autorun.log
    sleep 300
  fi
done
echo "[autorun $(date '+%H:%M:%S')] all 3 attempts exhausted" >> .autorun.log
exit 1
