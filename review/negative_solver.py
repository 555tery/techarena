#!/usr/bin/env python3
"""Tiny deliberately invalid solvers used only to sanity-check the harness."""

import sys


mode = sys.argv[1]
pipe_count = 0
while True:
    line = sys.stdin.readline()
    if not line:
        break
    command = int(line)
    if command == 0:
        if mode == "extra-after-zero":
            print("unexpected diagnostic", flush=True)
        break
    if command > 0:
        pipe_count += 1
        if mode == "empty":
            print("", flush=True)
        elif mode in ("overlap", "wrong-pid", "extra-after-zero"):
            print("1 0" if pipe_count == 1 else "0 0", flush=True)
        else:
            raise SystemExit("unknown negative-control mode")
    elif command < 0:
        if mode == "wrong-pid":
            print("1", flush=True)
        elif mode in ("overlap", "extra-after-zero"):
            print("0", flush=True)
        else:
            raise SystemExit("unexpected removal in this negative control")
