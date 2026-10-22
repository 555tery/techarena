#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPSTREAM="$ROOT/upstream"
REVISION="2b8aa39285c35aaca3b0e06dd121061ef8a2d854"
REV_SHORT="${REVISION:0:8}"

actual_revision="$(git -C "$UPSTREAM" rev-parse HEAD)"
if [[ "$actual_revision" != "$REVISION" ]]; then
  printf 'Unexpected upstream revision: %s\nExpected: %s\n' "$actual_revision" "$REVISION" >&2
  exit 2
fi

if ! docker info >/dev/null 2>&1; then
  printf 'Docker daemon is unavailable. Start Docker Desktop, then rerun this script.\n' >&2
  exit 2
fi

docker build \
  -t "agentic-scientist/agent-cli:$REV_SHORT" \
  -f "$UPSTREAM/src/docker/agent-cli/Dockerfile" \
  "$UPSTREAM"

docker build \
  --build-arg "BASE_IMAGE=agentic-scientist/agent-cli:$REV_SHORT" \
  -t "agentic-scientist/pipes-cpp:$REV_SHORT" \
  -f "$ROOT/Dockerfile" \
  "$ROOT"
