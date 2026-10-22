#!/usr/bin/env python3
"""Emit a single-file submission from the reviewed Cangjie package."""
from pathlib import Path
import hashlib
import json

BASE = Path(__file__).resolve().parents[1]
names = ['common.cj', 'models.cj', 'allocator.cj', 'main.cj']
imports = []
bodies = []
hashes = {}
for name in names:
    p = BASE / 'src' / name
    hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    body = []
    for line in p.read_text().splitlines():
        if line.startswith('package '):
            assert line == 'package pipes'
        elif line.startswith('import '):
            if line not in imports: imports.append(line)
        else: body.append(line)
    bodies.append('// Source: ' + name + '\n' + '\n'.join(body).strip() + '\n')
release = BASE / 'release'
release.mkdir(exist_ok=True)
source = 'package pipes\n\n' + '\n'.join(imports) + '\n\n' + '\n'.join(bodies)
(release/'solution.cj').write_text(source)
(release/'source_manifest.json').write_text(json.dumps({'parts': hashes, 'single_file_sha256': hashlib.sha256(source.encode()).hexdigest(), 'algorithm_language': 'Cangjie', 'cpp_ffi': False},indent=2)+'\n')
print(release/'solution.cj')
