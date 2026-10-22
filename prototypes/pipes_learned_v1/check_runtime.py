#!/usr/bin/env python3
"""Causal-prefix and model-disabled equivalence checks on train inputs only."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def main():
    manifest = json.loads((ROOT / 'data/manifest.json').read_text())
    selected = {}
    for entry in manifest['artifacts']['train']['files']:
        selected.setdefault(entry['family_id'], entry)
    reports = []
    for family, entry in selected.items():
        path = ROOT / 'data/train' / entry['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
        tokens = path.read_text().split()
        count = int(tokens[1])
        commands = tokens[2:2 + count]

        def run(binary, args, commands):
            result = subprocess.run([str(ROOT / 'bin' / binary), *args],
                input='\n'.join([*commands, '0']) + '\n', text=True,
                capture_output=True, check=True)
            lines = result.stdout.splitlines()
            assert len(lines) == len(commands)
            return lines, result.stderr.strip()

        generic, _ = run('generic', [], commands)
        disabled, _ = run('learned', ['greedy'], commands)
        assert generic == disabled, family
        full, diagnostic = run('learned', [], commands)
        prefix_size = min(2048, len(commands) // 2)
        prefix, _ = run('learned', [], commands[:prefix_size])
        assert prefix == full[:prefix_size], family
        reports.append({'family': family, 'commands': count, 'prefix': prefix_size,
            'input_sha256': entry['sha256'], 'nn_diagnostics': diagnostic})
    preprocessed = subprocess.run(['clang++', '-std=c++20', '-E', '-DUSE_LEARNED',
        str(ROOT / 'src/engine.cpp')], capture_output=True, text=True, check=True).stdout
    assert 'Input readInput(' not in preprocessed
    assert 'int label(int argc' not in preprocessed
    assert 'Meter continuation(State' not in preprocessed
    report = {'cases': reports, 'prefix_independence': True,
        'model_disabled_equals_generic': True, 'offline_reader_excluded': True}
    (ROOT / 'reports/runtime_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
