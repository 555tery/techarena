#!/usr/bin/env python3
"""Build a small quiet-prefix geometry grave for frozen release-v5."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'prototypes/pipes_open15_adversary_20261019'))
sys.path.insert(0, str(ROOT / 'tools'))
from construct import decode
from pipes_harness import parse_test

TARGET = ROOT / 'prototypes/pipes_v5_graves_20261019/target'
PROBE = ROOT / 'prototypes/pipes_prefix_shock_20261019/allocator-probe'
TAPE_SEED = ROOT / 'prototypes/pipes_prefix_shock_20261019/tape.txt'
OPEN1 = ROOT / 'data/pipes/open/1.in'
TEST = OUT / 'geometry_quiet_open1.in'
TAPE = OUT / 'geometry_quiet_open1.tape'
PROVENANCE = OUT / 'geometry_quiet_open1.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_probe(mode, tape, commands):
    p = subprocess.run(
        [str(PROBE), mode, str(tape)],
        input='\n'.join(map(str, commands + [0])) + '\n',
        text=True, capture_output=True, check=True, timeout=20,
    )
    return p.stdout.splitlines(), p.stderr.strip()


def main():
    tables = decode(TARGET / 'solution.cpp')
    public_commands, public_positions = tables[0]
    commands = public_commands + [-4, 5]
    assert public_commands == [1, 4, 15, -2, 3, -1]
    assert public_positions == [0, 16, 1, None, 16, None]
    TEST.write_text('1\n8\n' + '\n'.join(map(str, commands)) + '\n', encoding='ascii')
    TEST_META = parse_test(TEST)

    # The first six commands match Open1 exactly. Decode all embedded tables
    # to ensure the next command invalidates every still-active replay branch.
    shared = []
    possible_next = []
    for case, (cmds, poses) in enumerate(tables, 1):
        if cmds[:len(public_commands)] == public_commands:
            shared.append(case)
            if len(cmds) > len(public_commands):
                possible_next.append({'case': case, 'command': cmds[len(public_commands)]})
    assert shared == [1]
    assert possible_next == []

    # Causal generic Best-Fit baseline for the whole test.
    bf_lines, _ = run_probe('bestfit', TAPE_SEED, commands)
    bf_T = 0
    bf_trace = []
    for command, line in zip(commands, bf_lines):
        if command > 0:
            digs, pos = map(int, line.split())
            bf_T += 20 * digs
            bf_trace.append({'command': command, 'placement_m': pos, 'T_m': bf_T})
        else:
            bf_trace.append({'command': command, 'T_m': bf_T})

    # Guarded table replay through Open1, then causal Best-Fit on mismatch.
    tape_rows = [(c, -1 if p is None else p) for c, p in zip(public_commands, public_positions)]
    TAPE.write_text(str(len(tape_rows)) + '\n' + ''.join(f'{c} {p}\n' for c, p in tape_rows), encoding='ascii')
    guarded_lines, guarded_stderr = run_probe('guarded', TAPE, commands)
    target_T = 0
    target_trace = []
    for command, line in zip(commands, guarded_lines):
        if command > 0:
            digs, pos = map(int, line.split())
            target_T += 20 * digs
            target_trace.append({'command': command, 'placement_m': pos, 'T_m': target_T})
        else:
            target_trace.append({'command': command, 'T_m': target_T})

    # Check every common-prefix trench ratio; the suffix is deliberately where
    # the target's fragmented physical state produces the penalty.
    ratios = []
    bt = tt = 0
    for i, command in enumerate(public_commands):
        if command > 0:
            bt += 20 * int(bf_lines[i].split()[0])
            tt = max(tt, ((public_positions[i] + command + 19) // 20) * 20)
        ratios.append({'step': i + 1, 'T_target_m': tt, 'T_plain_BF_m': bt,
                       'ratio': tt / bt if bt else 1.0})
    assert all(row['ratio'] <= 1.25 for row in ratios)
    assert all(row['T_target_m'] == row['T_plain_BF_m'] == 20 for row in ratios)
    assert target_T == 40 and bf_T == 20
    assert TEST_META['final_occupied_length_m'] == 20
    assert TEST_META['minimum_trench_lower_bound_m'] == 20

    payload = {
        'title': 'Quiet-prefix geometry grave for release-v5',
        'scope': 'Local diagnostic input only; frozen target and platform untouched.',
        'target': {
            'version': 'release-v5',
            'source': str((TARGET / 'solution.cpp').relative_to(ROOT)),
            'source_sha256': sha(TARGET / 'solution.cpp'),
            'binary': str((TARGET / 'solver').relative_to(ROOT)),
            'binary_sha256': sha(TARGET / 'solver'),
            'runtime_guard': 'exact Open15-prefix matching; on first mismatch all replay branches are invalidated; subsequent positive placements use Best-Fit from current physical state.'
        },
        'test': {
            'file': str(TEST.relative_to(ROOT)),
            'sha256': sha(TEST),
            **TEST_META,
            'commands': commands,
            'validity': 'All PIDs exist when deleted; pipe lengths are in 1..40; 8 commands.'
        },
        'shared_prefix': {
            'open_case': 1,
            'open_input': str(OPEN1.relative_to(ROOT)),
            'open_input_sha256': sha(OPEN1),
            'prefix_length': len(public_commands),
            'commands': public_commands,
            'decoded_target_positions_m': public_positions,
            'other_open_tables_sharing_full_prefix': shared,
            'matching_open_continuations_after_prefix': possible_next,
            'max_T_target_over_T_plain_BF': max(r['ratio'] for r in ratios),
            'per_step': ratios,
        },
        'suffix_mechanism': {
            'commands': [-4, 5],
            'first_mismatch_step': 7,
            'first_fallback_placement_step': 8,
            'explanation': 'After deleting PID 4, plain BF has one free interval [0,5), while the replay state has separate free intervals [0,1) and [16,20). The new length-5 pipe fits in plain BF at 0; the target has no 5 m gap and extends the trench to 40 m.'
        },
        'expected_comparison_from_diagnostic_allocator': {
            'plain_best_fit': {'final_trench_m': bf_T, 'final_live_volume_m': 20,
                               'KPI': 20 / bf_T, 'trace': bf_trace},
            'release_v5_replay_then_fallback': {'final_trench_m': target_T,
                                                 'final_live_volume_m': 20,
                                                 'KPI': 20 / target_T,
                                                 'trace': target_trace,
                                                 'probe_stderr': guarded_stderr},
            'target_KPI_ratio_to_plain_BF': (20 / target_T) / (20 / bf_T)
        },
        'reproducibility_inputs': {
            'diagnostic_allocator_probe': str(PROBE.relative_to(ROOT)),
            'diagnostic_allocator_probe_sha256': sha(PROBE),
            'replay_probe_tape': str(TAPE.relative_to(ROOT)),
            'replay_probe_tape_sha256': sha(TAPE),
            'cumulative_prefix_scan': str((OUT / 'geometry_prefix_scan.json').relative_to(ROOT)),
            'cumulative_prefix_scan_sha256': sha(OUT / 'geometry_prefix_scan.json') if (OUT / 'geometry_prefix_scan.json').exists() else None
        },
        'verification_boundary': 'Derived from decoded frozen plan plus the local causal allocator probe. Official interactor final check is assigned to the coordinating agent.'
    }
    PROVENANCE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'test': str(TEST), 'sha256': sha(TEST), 'provenance': str(PROVENANCE),
                      'prefix_max_ratio': max(r['ratio'] for r in ratios),
                      'plain_BF_T': bf_T, 'target_T': target_T,
                      'BF_KPI': 20 / bf_T, 'target_KPI': 20 / target_T,
                      'target_vs_BF': (20 / target_T) / (20 / bf_T)}, indent=2))


if __name__ == '__main__':
    main()
