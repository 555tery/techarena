#!/usr/bin/env python3
"""Compose unchanged current online core with frozen cautious replay wrapper."""
from pathlib import Path
import hashlib
import subprocess
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CURRENT = ROOT / 'prototypes/pipes_online_patterns_20261020/release/solution.cpp'
OLD = ROOT / 'prototypes/pipes_closed_ready_20261020/release/solution.cpp'
EXPECTED = {
    CURRENT: 'f7b285eee9d59f443b015de581c4622668dd1a321e0cb9ef00d4baf10412f5db',
    OLD: '48a44fb0ccad7e6560055245a3096f892c23b5a98c4ab77468c87968e23054c1',
}
for path, digest in EXPECTED.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path
current, old = CURRENT.read_text(), OLD.read_text()
start_marker = 'namespace fallback_online {'
end_marker = '}  // namespace'
cs = current.index(start_marker)
ce = current.index(end_marker, cs) + len(end_marker)
os = old.index(start_marker)
oe = old.index(end_marker, os) + len(end_marker)
composed = old[:os] + current[cs:ce] + old[oe:]
assert composed[:os] == old[:os]
assert composed[os:os + ce - cs] == current[cs:ce]
assert composed[os + ce - cs:] == old[oe:]
solution = HERE / 'solution.cpp'
solution.write_text(composed)
subprocess.run(['c++', '-O2', '-std=c++17', str(solution), '-o', str(HERE / 'solution')], check=True)
manifest = {
    'current_online_sha256': EXPECTED[CURRENT],
    'frozen_hybrid_sha256': EXPECTED[OLD],
    'solution_sha256': hashlib.sha256(solution.read_bytes()).hexdigest(),
    'composition': 'frozen cautious wrapper with namespace fallback_online replaced byte-for-byte by current online namespace',
    'compile': 'c++ -O2 -std=c++17 solution.cpp -o solution',
}
(HERE / 'build.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
