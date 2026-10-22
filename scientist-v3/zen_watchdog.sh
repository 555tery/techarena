#!/bin/bash
# Rides out transient OpenCode Zen unavailability (server storms: "Unexpected server
# error", "Endpoint is unavailable", silent stream deaths) for the pipes investigation.
# Policy: launch the pipeline only after N consecutive green containerized probes;
# on a failed pipeline run (rc != 0 or "Investigation · failed" in output) retry,
# up to MAX_RUNS runs, re-gating health each time.
set -u

ROOT="/Users/555tery/techarena"
IMAGE="agentic-scientist/pipes-cpp:2b8aa392"
AUTH="$ROOT/scientist-v3/opencode-auth"
LOG="$ROOT/scientist-v3/.zen_watchdog.log"
PIPEOUT="$ROOT/scientist-v3/.pipeline_last.out"
CONSEC_NEEDED=2
MAX_RUNS=6
TMPROOT="/private/var/folders/7t/lxjtvwwx29q0c674m6w5fbsh0000gn/T/opencode"

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "$LOG"; }

probe_once() {
  local ws try_result rc
  ws=$(mktemp -d "$TMPROOT/zen-probe.XXXXXX") || return 1
  docker rm -f zen-probe >/dev/null 2>&1
  docker run -d --rm --init --name zen-probe --network bridge \
    --user "$(id -u):$(id -g)" -e HOME=/home/agent-home -e USER=agent -e LOGNAME=agent \
    -v "$ws":/workspace -v "$AUTH":/home/agent-home -w /workspace "$IMAGE" sleep infinity >/dev/null 2>&1
  try_result=$(docker exec zen-probe env HOME=/home/agent-home bash -c \
    'headless opencode --allow yolo --model opencode/glm-5.3-flash-free --prompt "Reply with exactly: OK" 2>&1; echo RC=$?')
  rc=$(printf '%s' "$try_result" | sed -n 's/^RC=//p' | tail -1)
  local payload
  payload=$(printf '%s' "$try_result" | sed '$d' | tail -1)
  docker rm -f zen-probe >/dev/null 2>&1
  rm -rf "$ws"
  if [ "$rc" = "0" ] && [ "$payload" = "OK" ]; then
    return 0
  fi
  log "probe failed (rc=${rc:-none}): ${payload:-<empty>}"
  return 1
}

wait_healthy() {
  local streak=0
  while true; do
    if probe_once; then
      streak=$((streak + 1))
      log "probe OK (streak $streak/$CONSEC_NEEDED)"
      if [ "$streak" -ge "$CONSEC_NEEDED" ]; then
        return 0
      fi
      # Wide spacing so probes themselves respect the relay rate window.
      sleep 90
    else
      streak=0
      sleep 45
    fi
  done
}

main() {
  rm -f "$PIPEOUT"
  mkdir -p /private/var/folders/7t/lxjtvwwx29q0c674m6w5fbsh0000gn/T/opencode
  local run_index=0 rc
  while [ "$run_index" -lt "$MAX_RUNS" ]; do
    run_index=$((run_index + 1))
    log "=== waiting for Zen health before run $run_index/$MAX_RUNS ==="
    wait_healthy
    log "streak reached — launching pipeline run $run_index/$MAX_RUNS"
    cd "$ROOT"
    ./scientist-v3/run_pipes.sh --run 2>&1 | tee "$PIPEOUT"
    rc=${PIPESTATUS[0]}
    log "pipeline exited rc=$rc"
    if [ "$rc" -eq 0 ] && ! grep -q 'Investigation · failed' "$PIPEOUT" 2>/dev/null; then
      log "pipeline finished OK on run $run_index"
      exit 0
    fi
    log "pipeline run $run_index failed (rc=$rc); cooling down before next health gate"
    sleep 180
  done
  log "all $MAX_RUNS runs failed"
  exit 4
}

main "$@"
