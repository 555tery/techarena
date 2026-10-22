"""Coordinator's independent cell-map oracle. No benchmark inputs are read."""
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import random
import selectors
import subprocess

ROOT = Path(__file__).resolve().parent


def oracle(commands, policy):
    cells, pipes, replies = [], {}, []
    next_pid = 0
    for command in commands:
        if command < 0:
            start, length = pipes.pop(-command)
            assert all(x == -command for x in cells[start:start + length])
            cells[start:start + length] = [0] * length
            replies.append(str(start))
            continue
        next_pid += 1
        gaps = []
        i = 0
        while i < len(cells):
            if cells[i]:
                i += 1
                continue
            end = i + 1
            while end < len(cells) and not cells[end]:
                end += 1
            gaps.append((i, end - i))
            i = end
        fit = [(s, h) for s, h in gaps if h >= command]
        dig = 0
        if fit:
            if policy == 'bf':
                start, length = min(fit, key=lambda z: (z[1], z[0]))
            else:
                # Recompute full Phi for every candidate; independent of
                # incremental formulas/heaps in the optimized implementation.
                scores = []
                for start, length in fit:
                    after = [h for s, h in gaps if s != start]
                    if length > command:
                        after.append(length - command)
                    counts = Counter(after)
                    scores.append((sum(v * v for v in counts.values()), length, start))
                _, length, start = min(scores)
        else:
            tail = gaps[-1][1] if gaps and sum(gaps[-1]) == len(cells) else 0
            start = len(cells) - tail
            dig = (command - tail + 19) // 20
            assert dig > 0
            cells += [0] * (20 * dig)
        assert len(cells) % 20 == 0
        assert all(x == 0 for x in cells[start:start + command])
        cells[start:start + command] = [next_pid] * command
        pipes[next_pid] = start, command
        replies.append(f'{dig} {start}')
    return replies


def fixtures():
    cases = []
    # Covers every legal size, tail reuse, complete drain and PID progression.
    cases.append(list(itertools.chain.from_iterable((length, -(i + 1)) for i, length in enumerate(range(1, 41)))))
    cases += [[7, 7, 6, -2, 5, -1, -3, 15, -4, -5],
              [40, 1, -1, 20, 20, -3, -4, -2, 40],
              [5, 5, 5, 5, -1, -3, 4, 4, -2, -4, 6, 6]]
    # Independent random legality tests, changing sizes and deletion ranks.
    for seed in range(124):
        rng = random.Random(0xD51A000 + seed)
        active, commands, pid = [], [], 0
        for step in range(240):
            if active and rng.random() < (.25 if step < 80 else .63 if step < 160 else .45):
                rank = rng.randrange(len(active))
                commands.append(-active.pop(rank))
            else:
                length = rng.choice([1, 2, 3, 7, 10, 19, 20, 21, 39, 40]) if seed % 2 else rng.randint(1, 40)
                pid += 1
                active.append(pid)
                commands.append(length)
        cases.append(commands)
    return cases


def main():
    cases = fixtures()
    audit = {'method': 'independent cell-map full-Phi oracle; no benchmark access',
             'streams_per_solver': len(cases), 'commands_per_solver': sum(map(len, cases)),
             'solvers': {}}
    for policy in ('bf', 'ss'):
        binary = ROOT / 'builds' / policy / 'solver'
        for index, commands in enumerate(cases):
            expected = oracle(commands, policy)
            run = subprocess.run([str(binary)], input='\n'.join(map(str, commands + [0]))+'\n',
                                 text=True, capture_output=True, timeout=5)
            got = run.stdout.strip().splitlines()
            if run.returncode or got != expected:
                mismatch = next((i for i, (a,b) in enumerate(zip(got, expected)) if a != b), min(len(got),len(expected)))
                raise AssertionError((policy, index, mismatch, got[mismatch:mismatch+1], expected[mismatch:mismatch+1], run.stderr))
        # Only one command is provided at a time: answers must be flushed before
        # another command or the terminator becomes available.
        commands = cases[3]
        p = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, bufsize=1)
        sel = selectors.DefaultSelector()
        sel.register(p.stdout, selectors.EVENT_READ)
        try:
            for command, answer in zip(commands, oracle(commands, policy)):
                p.stdin.write(str(command)+'\n'); p.stdin.flush()
                if not sel.select(2):
                    raise AssertionError((policy, 'did not flush response'))
                assert p.stdout.readline().strip() == answer
            p.stdin.write('0\n'); p.stdin.flush(); p.stdin.close()
            assert p.wait(timeout=2) == 0
            assert p.stdout.read() == ''
        finally:
            sel.close()
            if p.poll() is None:
                p.kill(); p.wait()
        audit['solvers'][policy] = {'passed': True, 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                                   'interactive_flush_passed': True}
    (ROOT / 'independent-baseline-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    # Sixteen tiny official fixtures, three algorithms: 48 preflight runs.
    out = ROOT / 'data/preflight'
    out.mkdir(parents=True, exist_ok=False)
    for i, commands in enumerate(cases[:16]):
        (out/f'{i:02d}.in').write_text('1\n'+str(len(commands))+'\n'+'\n'.join(map(str, commands))+'\n')
    print(json.dumps(audit))


if __name__ == '__main__':
    main()
