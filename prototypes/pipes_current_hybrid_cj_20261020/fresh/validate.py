#!/usr/bin/env python3
"""Independent input-only revalidation; no policy or score output is consumed."""
import hashlib
import importlib.util
import json
import struct
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
m = json.loads((HERE / 'manifest.json').read_text())
spec = importlib.util.spec_from_file_location('parser', ROOT / 'tools/pipes_harness.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert digest(HERE / 'generator.py') == m['generator_sha256']
assert digest(ROOT / m['parser_path']) == m['parser_sha256']
for source in m['public_sources'] + m['inventory_sources']:
    assert digest(ROOT / source['path']) == source['sha256']
inventory = set()
def gather(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if k == 'canonical_sha256' and isinstance(v, str):
                inventory.add(v)
            else:
                gather(v)
    elif isinstance(x, list):
        for item in x:
            gather(item)
inventory_files = sorted((ROOT / 'prototypes/pipes_test_inventory_20261020').glob('*.json'))
for p in inventory_files:
    gather(json.loads(p.read_text()))
seen = set()
records = []
for case in m['cases']:
    p = HERE / case['path']
    parsed = module.parse_test(p)
    words = p.read_text().split()
    n = int(words[1])
    commands = list(map(int, words[2:]))
    assert len(commands) == n and 0 < n <= 200000
    # One bulk pack is deliberately separate from generator's incremental hashing.
    canon = hashlib.sha256(struct.pack('<I', n) + struct.pack('<' + 'i' * n, *commands)).hexdigest()
    assert canon == case['canonical_sha256'] and digest(p) == case['sha256']
    assert canon not in seen and canon not in inventory
    assert parsed['final_occupied_length_m'] > 0
    assert parsed['kpi_upper_bound_from_live_volume'] >= 0.85
    if case['kind'] == 'public_prefix':
        source = ROOT / f"data/pipes/open/{case['public_input']}.in"
        tokens = source.read_text().split()
        k = case['parameters']['prefix_length']
        assert commands[:k] == list(map(int, tokens[2:2 + k]))
    seen.add(canon)
    records.append({'path': case['path'], 'canonical_sha256': canon, 'parser_accepted': True})
assert len(seen) == 96
assert Counter(c['kind'] for c in m['cases']) == {'public_prefix': 60, 'composition': 32, 'stress': 4}
assert all(c['operations'] == 200000 for c in m['cases'] if c['kind'] == 'stress')
assert Counter(c['public_input'] for c in m['cases'] if c['kind'] == 'public_prefix') == {i: 4 for i in range(1, 16)}
result = {'manifest_sha256': digest(HERE / 'manifest.json'), 'cases_checked': 96,
          'parser_accepted': 96, 'inventory_canonical_hashes_checked': len(inventory),
          'inventory_files_checked': [str(p.relative_to(ROOT)) for p in inventory_files],
          'duplicates_with_inventory': 0, 'internal_duplicates': 0,
          'public_prefix_equalities_checked': 60, 'stress_200000_checked': 4,
          'solvers_executed': 0, 'cases': records}
(HERE / 'independent_validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, indent=2))
