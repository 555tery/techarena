#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPSTREAM="$ROOT/upstream"
TASK="$ROOT/tasks/pipes"
RUNS="$ROOT/runs"
TEMP_ROOT="$ROOT/.tmp"
IMAGE="agentic-scientist/pipes-cpp:z193"
ACTION="${1:---dry-run}"

if [[ "$ACTION" != "--dry-run" && "$ACTION" != "--run" ]]; then
  printf 'Usage: %s [--dry-run|--run]\n' "$0" >&2
  exit 2
fi

# Upstream host scripts (idea.sh, run.sh, task.sh) require bash >= 4 (mapfile -d),
# while the stock macOS /bin/bash is 3.2. Prefer a Homebrew bash if present.
if [[ -x /opt/homebrew/bin/bash ]]; then
  export PATH="/opt/homebrew/bin:$PATH"
fi

# OpenCode Zen free tier rejects bursty consecutive agent requests
# ("Unexpected server error" within seconds). Space agent sessions apart.
export AGENTIC_REQUEST_PACING_SECONDS="${AGENTIC_REQUEST_PACING_SECONDS:-90}"

if [[ "$ACTION" == "--run" ]]; then
  if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    printf 'Required image is missing. Run ./scientist-v3/build_images.sh first.\n' >&2
    exit 2
  fi
fi

cd "$UPSTREAM"
mkdir -p "$TEMP_ROOT"
export AGENTIC_TEMP_ROOT="$TEMP_ROOT"
# OpenCode-in-container with the OpenCode Zen "glm-5.3-flash-free" model.
# The agent home is seeded from OPENCODE_AUTH_ROOT, which holds
# .config/opencode/opencode.json with the provider apiKey (no env keys needed).
# Requests are throttled by the Zen pacer (zen_pacer.py inside the container):
# provider "zenpacer" points at 127.0.0.1:8787 — a local proxy forwarding to
# https://opencode.ai/inference/openai/v1 with >=30 s between requests and
# auto-retries on 429/5xx. Provider "opencode" is kept for the aux nano model.
OPENCODE_AUTH_ROOT="$ROOT/opencode-auth"
if [[ ! -f "$OPENCODE_AUTH_ROOT/.config/opencode/opencode.json" ]]; then
  printf 'Missing %s/.config/opencode/opencode.json provisioned with an OpenCode API key.\n' "$OPENCODE_AUTH_ROOT" >&2
  exit 2
fi
cmd=(
  uv run --project "$UPSTREAM" agsci run "$TASK"
  "agent.name=opencode"
  "agent.model=zenpacer/glm-5.3-flash-free"
  "agent.reasoning_effort=xhigh"
  "container.enabled=true"
  "container.image=$IMAGE"
  "container.network=bridge"
  "container.env_file=''"
  "container.auth_root=$OPENCODE_AUTH_ROOT"
  "execution.phases=investigation"
  "investigation.execution.max_idea_cycles=500"
  "investigation.execution.max_program_evals_per_attempt=2"
  "investigation.execution.harness_evaluated_attempts=true"
  "investigation.execution.workers=1"
  "investigation.execution.idea_timeout_seconds=3600"
  "investigation.execution.run_timeout_seconds=86400"
  "paths.results_root=$RUNS"
)

if [[ "$ACTION" == "--dry-run" ]]; then
  cmd+=(--dry-run)
fi

"${cmd[@]}"
