#!/bin/sh
# Adapter for tools/pipes_harness.py's current invocation. The official
# interactor expects an already-existing optional answer file, as the original
# runner.py creates before starting it.
if [ "$#" -ge 3 ]; then
    : > "$3"
fi
exec /Users/555tery/techarena/tools/interactor "$@"
