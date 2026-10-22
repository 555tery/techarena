#!/usr/bin/env python3
"""Add SHA256 to every retained episode without executing any simulator."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

base = Path(__file__).resolve().parent
directory = base / 'training'
provenance = json.loads((directory / 'provenance.json').read_text())
sources = provenance['source_sha256']
assert all(hashlib.sha256((base / p).read_bytes()).hexdigest() == sha for p, sha in sources.items())
policies = {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (directory / 'policies').glob('*.weights')}
rows = list(csv.DictReader((directory / 'episodes.csv').open()))
assert len(rows) == 408
assert sum(r['generation'] == '0' for r in rows) == 24
totals = defaultdict(int)
with (directory / 'episodes.jsonl').open('w') as output:
    for row in rows:
        assert row['legal'] == 'true'
        record = dict(row)
        for field in ['episode', 'generation', 'candidate', 'F', 'T', 'placements', 'eligible',
                      'decisions', 'changed', 'candidates', 'interior', 'tail', 'right_endpoint']:
            record[field] = int(record[field])
        for field in ['reward', 'control_reward', 'paired_delta']:
            record[field] = float(record[field])
        record['legal'] = True
        record['policy_sha256'] = policies[record['policy_file']]
        record['source_sha256'] = sources
        record['scope'] = 'complete own-policy training trajectory'
        assert abs(record['reward'] - record['F'] / record['T']) < 1e-14
        for key in ['placements', 'eligible', 'decisions', 'changed', 'candidates', 'interior', 'tail', 'right_endpoint']:
            if record['generation'] > 0:
                totals[key] += record[key]
        output.write(json.dumps(record, sort_keys=True) + '\n')
provenance['completed_training_episodes'] = len(rows)
provenance['control_episodes'] = 24
provenance['own_policy_training_episodes'] = 384
provenance['policy_sha256'] = policies
provenance['checkpoint_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in directory.glob('checkpoint_gen*.weights')}
provenance['activation_totals_own_policy_episodes'] = dict(totals)
provenance['training_binary_sha256'] = hashlib.sha256((base / 'bin/train').read_bytes()).hexdigest()
provenance['episodes_sha256'] = hashlib.sha256((directory / 'episodes.jsonl').read_bytes()).hexdigest()
(directory / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
print(json.dumps({'complete_episodes': len(rows), 'activation': dict(totals)}, sort_keys=True))
