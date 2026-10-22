#!/usr/bin/env python3
"""Tiny hand-designed protocol/invariant/prefix/determinism tests; no official inputs."""
import argparse
import json
import select
import subprocess


def fixture():
    commands = []
    next_pid = 1
    live = []
    for phase in range(12):
        cohort = []
        for j in range(8):
            commands.append(1 + (phase * 11 + j * 7) % 40)
            cohort.append(next_pid)
            live.append(next_pid)
            next_pid += 1
        for pid in cohort[:6]:
            commands.append(-pid)
            live.remove(pid)
    for j in range(16):
        commands.append(1 + (j * 13) % 40)
    return commands


def run(binary, commands):
    result = subprocess.run([binary], input="\n".join(map(str, commands + [0])) + "\n", text=True,
                            capture_output=True, timeout=20, check=True)
    lines = result.stdout.splitlines()
    assert len(lines) == len(commands), (len(lines), len(commands), result.stderr)
    trench = 0
    pipes = {}
    pid = 0
    for command, line in zip(commands, lines):
        values = list(map(int, line.split()))
        if command > 0:
            assert len(values) == 2
            digs, start = values
            assert digs >= 0 and start >= 0
            assert digs == (max(0, start + command - trench) + 19) // 20
            trench += 20 * digs
            assert start + command <= trench <= 100_000_000
            for left, right in pipes.values():
                assert start + command <= left or right <= start
            pid += 1
            pipes[pid] = (start, start + command)
        else:
            assert len(values) == 1
            assert values[0] == pipes[-command][0]
            del pipes[-command]
    assert "H1 ERROR" not in result.stderr
    return lines, result.stderr, trench


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--on", required=True)
    parser.add_argument("--off", required=True)
    args = parser.parse_args()
    commands = fixture()
    report = {}
    for name, binary in [("on", args.on), ("off", args.off)]:
        first, stderr, trench = run(binary, commands)
        repeat, repeat_stderr, _ = run(binary, commands)
        assert first == repeat and stderr == repeat_stderr
        prefix = commands[:103]
        left, _, _ = run(binary, prefix + [1, 2, 3])
        right, _, _ = run(binary, prefix + [40, 39, 38, 37])
        assert left[:len(prefix)] == right[:len(prefix)] == first[:len(prefix)]
        # End-of-input protocol: zero immediately produces no stdout.
        empty = subprocess.run([binary], input="0\n", text=True, capture_output=True, check=True)
        assert empty.stdout == ""
        # A true handshake verifies a newline/flush before the next command.
        process = subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, bufsize=1)
        for command, expected in zip(commands[:48], first[:48]):
            process.stdin.write(str(command) + "\n")
            process.stdin.flush()
            assert select.select([process.stdout], [], [], 3)[0], "missing immediate reply/flush"
            assert process.stdout.readline().rstrip("\n") == expected
        process.stdin.write("0\n")
        process.stdin.flush()
        process.stdin.close()
        assert process.wait(timeout=5) == 0
        assert process.stdout.read() == ""
        process.stdout.close()
        process.stderr.close()
        report[name] = {"commands": len(commands), "legal": True, "deterministic": True,
                        "prefix_causal": True, "interactive_flush": True,
                        "tiny_trench": trench, "telemetry": stderr.splitlines()}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
