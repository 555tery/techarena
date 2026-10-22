#!/bin/sh
set -eu
SHINKA_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$SHINKA_ROOT/.venv/bin/python" "$SHINKA_ROOT/manage.py" "$@"
