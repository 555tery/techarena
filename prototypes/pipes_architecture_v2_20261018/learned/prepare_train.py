#!/usr/bin/env python3
"""Validate input hashes and seal provenance before the single native training run."""
import hashlib
import json
from pathlib import Path

base = Path(__file__).resolve().parent
manifest_path = base.parent / 'data/train/manifest.json'
manifest = json.loads(manifest_path.read_text())
assert manifest['count'] == 24
rows = []
for s in manifest['streams']:
    assert s['n'] == 2000
    assert hashlib.sha256(Path(s['path']).read_bytes()).hexdigest() == s['sha256']
    rows.append('\t'.join([s['family'], s['path'], s['sha256']]))
(base / 'training/streams.tsv').write_text('\n'.join(rows) + '\n')
sources = [base / 'src/allocator.hpp', base / 'src/policy.hpp', base / 'src/train.cpp',
           base / 'src/solver.cpp', base / 'src/check.cpp', base / 'export.py',
           base / 'prepare_train.py', base / 'README.md']
provenance = {
    'architecture': '24->4 tanh->1', 'parameters': 105,
    'optimizer': 'diagonal CEM parameter-space trajectory optimization; not RL',
    'reward': 'terminal F/T minus action-independent same-input BF control F/T',
    'generations': 8, 'population': 8, 'elites': 2, 'families_per_candidate': 6,
    'placements_per_actor_decision': 4, 'max_actions': 16,
    'initial_mean': 0, 'initial_std': 0.35, 'std_floor': 0.06, 'smoothing_new': 0.35,
    'seed': 2026101802, 'planned_training_episodes': 408,
    'selection': 'dev max family-macro F/T among CEM means at gen4/gen8; exact tie gen4',
    'training_command': ['./bin/train', 'training/streams.tsv', 'training'],
    'compiler_command': ['c++', '-std=c++20', '-O3', '-DNDEBUG', '-Isrc', 'src/train.cpp', '-o', 'bin/train'],
    'source_sha256': {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    'input_manifest': str(manifest_path),
    'input_manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    'inputs': manifest['streams'],
    'future_features': False, 'forced_action_labels': False,
    'incumbent_specialized_routes': False,
}
(base / 'training/provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
