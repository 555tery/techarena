#!/usr/bin/env python3
"""Audit cumulative quiet-prefix lengths against causal plain Best-Fit."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / 'geometry_prefix_scan.json'
sys.path.insert(0, str(ROOT / 'prototypes/pipes_open15_adversary_20261019'))
from construct import decode

TARGET = ROOT / 'prototypes/pipes_v5_graves_20261019/target'
PROBE = ROOT / 'prototypes/pipes_prefix_shock_20261019/allocator-probe'
TAPE = ROOT / 'prototypes/pipes_prefix_shock_20261019/tape.txt'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tables = decode(TARGET / 'solution.cpp')
    cases = []
    for case, (commands, positions) in enumerate(tables, 1):
        response = subprocess.run(
            [str(PROBE), 'bestfit', str(TAPE)],
            input='\n'.join(map(str, commands + [0])) + '\n',
            text=True, capture_output=True, check=True, timeout=30,
        ).stdout.splitlines()
        target_T = bf_T = 0
        live = {}
        pid = 0
        live_volume = 0
        safe_cut = 0
        max_ratio = 1.0
        first_violation = None
        safe_metrics = {'target_T_m': 0, 'plain_BF_T_m': 0,
                        'live_volume_m': 0, 'live_pids': 0}
        for step, (command, position, line) in enumerate(zip(commands, positions, response), 1):
            if command > 0:
                pid += 1
                live[pid] = command
                live_volume += command
                target_T = max(target_T, ((position + command + 19) // 20) * 20)
                digs, _ = map(int, line.split())
                bf_T += 20 * digs
            else:
                live_volume -= live.pop(-command)
            ratio = target_T / bf_T if bf_T else 1.0
            max_ratio = max(max_ratio, ratio)
            if first_violation is None and ratio > 1.25:
                first_violation = {'step': step, 'ratio': ratio,
                                   'target_T_m': target_T, 'plain_BF_T_m': bf_T}
            if first_violation is None:
                safe_cut = step
                safe_metrics = {'target_T_m': target_T, 'plain_BF_T_m': bf_T,
                                'live_volume_m': live_volume, 'live_pids': len(live)}
        cases.append({
            'open_case': case,
            'command_count': len(commands),
            'first_violation_over_1_25': first_violation,
            'longest_cumulative_quiet_prefix': safe_cut,
            'metrics_at_safe_cut': safe_metrics,
            'global_max_step_ratio': max_ratio,
        })
    payload = {
        'target_source_sha256': sha(TARGET / 'solution.cpp'),
        'definition': 'A prefix is safe only if T_target/T_plain_BF <= 1.25 at every step from the start through its final command.',
        'bestfit_source': 'prototypes/pipes_prefix_shock_20261019/allocator-probe, mode=bestfit; decisions are causal.',
        'cases': cases,
        'selected_test': 'geometry_quiet_open1.in: all 6 commands of Open1 are a cumulative quiet prefix with ratio 1.0 at every step.'
    }
    OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'scan': str(OUT), 'safe_prefixes': [
        (r['open_case'], r['longest_cumulative_quiet_prefix']) for r in cases
    ]}, indent=2))


if __name__ == '__main__':
    main()
