#!/usr/bin/env python3
"""Check clean EOF termination before input and after one live command."""

from __future__ import annotations

import argparse
import os
import select
import subprocess
from pathlib import Path


def finish_cleanly(binary: Path, send_command: bool) -> dict:
    proc = subprocess.Popen(
        [str(binary.resolve())], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, bufsize=0,
    )
    response = b""
    if send_command:
        assert proc.stdin is not None and proc.stdout is not None
        proc.stdin.write(b"20\n")
        proc.stdin.flush()
        ready, _, _ = select.select([proc.stdout], [], [], 2.0)
        if not ready:
            proc.kill()
            proc.wait()
            raise TimeoutError("no flushed response before EOF check")
        while b"\n" not in response:
            chunk = os.read(proc.stdout.fileno(), 4096)
            if not chunk:
                proc.kill()
                proc.wait()
                raise ValueError(f"stdout closed before a complete response: {response!r}")
            response += chunk
        line, remainder = response.split(b"\n", 1)
        tokens = line.split()
        if len(tokens) != 2:
            proc.kill()
            proc.wait()
            raise ValueError(f"expected two integers for placement, received {line!r}")
        int(tokens[0])
        int(tokens[1])
        if remainder:
            proc.kill()
            proc.wait()
            raise ValueError(f"unexpected stdout before EOF: {remainder!r}")
        proc.stdin.close()
    else:
        assert proc.stdin is not None
        proc.stdin.close()

    try:
        return_code = proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise TimeoutError("solver did not exit after stdin EOF")
    assert proc.stdout is not None and proc.stderr is not None
    trailing = proc.stdout.read()
    stderr = proc.stderr.read()
    if return_code != 0:
        raise ValueError(f"solver returned {return_code}")
    if trailing:
        raise ValueError(f"unexpected stdout after EOF: {trailing!r}")
    return {"input": "one placement then EOF" if send_command else "EOF before commands",
            "verdict": "OK", "response": response.decode("ascii").rstrip() if response else "",
            "return_code": return_code, "trailing_stdout_bytes": 0,
            "stderr_bytes": len(stderr)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    args = parser.parse_args()
    results = []
    for send_command in (False, True):
        result = finish_cleanly(args.binary, send_command)
        results.append(result)
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
