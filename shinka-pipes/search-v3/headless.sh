#!/bin/sh
SHINKA_V3_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$SHINKA_V3_DIR/../.venv/bin/python" -B "$SHINKA_V3_DIR/headless_bridge.py" "$@"
