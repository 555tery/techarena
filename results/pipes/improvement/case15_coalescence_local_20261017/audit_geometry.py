#!/usr/bin/env python3
"""Replay saved answers and audit final free cells; never invokes a solver."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = next(p for p in ROOT.parents if (p / 'tools/pipes_harness.py').exists())


def audit(row):
    input_path = Path(row['test_file'])
    output_path = Path(row['judge_output_file'])
    if not output_path.is_absolute():
        output_path = PROJECT / output_path
    tokens = input_path.read_text().split()
    count = int(tokens[1])
    commands = list(map(int, tokens[2:2 + count]))
    answers = output_path.read_text().splitlines()
    assert len(answers) == count
    # 0 = occupied; 1 = never occupied expansion cell; 2 = last freed by deletion.
    # This measures last physical freeing event per cell, not propagated lineage.
    cells = bytearray()
    live = {}
    pid = 0
    for command, answer in zip(commands, answers):
        values = list(map(int, answer.split()))
        if command > 0:
            assert len(values) == 2
            digs, start = values
            assert digs >= 0 and start >= 0
            cells.extend(b'\x01' * (digs * 20))
            assert start + command <= len(cells)
            assert 0 not in cells[start:start + command]
            cells[start:start + command] = b'\x00' * command
            pid += 1
            live[pid] = (start, command)
        else:
            assert len(values) == 1
            start, length = live.pop(-command)
            assert values[0] == start
            assert cells[start:start + length] == b'\x00' * length
            cells[start:start + length] = b'\x02' * length
    assert len(cells) == int(row['trench_length_m'])
    occupied = sum(length for _, length in live.values())
    assert occupied == int(row['occupied_length_m'])
    histogram = Counter()
    deletion_m = 0
    never_occupied_m = 0
    small_deletion_m = 0
    position = 0
    while position < len(cells):
        if not cells[position]:
            position += 1
            continue
        end = position + 1
        while end < len(cells) and cells[end]:
            end += 1
        length = end - position
        histogram[length] += 1
        freed = cells[position:end].count(2)
        deletion_m += freed
        never_occupied_m += length - freed
        if length <= 7:
            small_deletion_m += freed
        position = end
    free = len(cells) - occupied
    assert deletion_m + never_occupied_m == free
    return {
        'case': row['case'], 'trench_m': len(cells), 'occupied_m': occupied,
        'free_m': free, 'free_gap_count': sum(histogram.values()),
        'small_gap_count_le7': sum(n for length, n in histogram.items() if length <= 7),
        'small_gap_m_le7': sum(length * n for length, n in histogram.items() if length <= 7),
        'small_gap_last_deleted_m': small_deletion_m,
        'free_cells_last_deleted_m': deletion_m,
        'free_cells_never_occupied_m': never_occupied_m,
        'gap_length_histogram': dict(sorted(histogram.items())),
        'input_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(),
        'output_sha256': hashlib.sha256(output_path.read_bytes()).hexdigest(),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run')
    parser.add_argument('--case', default='15')
    args = parser.parse_args()
    rows = list(csv.DictReader((ROOT / 'runs' / args.run / 'cases.csv').open()))
    row = next(r for r in rows if r['case'] == args.case)
    result = audit(row)
    (ROOT / f'geometry_{args.run}_{args.case}.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'gap_length_histogram'}, indent=2))
