#!/bin/sh
set -eu
SEARCH_V2_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$SEARCH_V2_ROOT/../.venv/bin/python" "$SEARCH_V2_ROOT/manage.py" "$@"
