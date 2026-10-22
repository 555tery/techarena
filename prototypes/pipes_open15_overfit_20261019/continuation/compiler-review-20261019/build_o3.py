"""Reproduce the local Clang O3 comparison; not a GCC/Windows build."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'speed-v13'
OUT = HERE / 'o3'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE / 'solution.cpp') == '065707442c1d303ae148b30282f421536a9350505dd8aead5cbc6f3a77043cd3'
OUT.mkdir(exist_ok=False)
shutil.copy2(BASE / 'solution.cpp', OUT / 'solution.cpp')
flags = ['-O3', '-std=c++17', '-Wall', '-Wextra']
result = subprocess.run(['/usr/bin/clang++', *flags, str(OUT / 'solution.cpp'), '-o', str(OUT / 'solver')], capture_output=True, text=True)
(OUT / 'compile.log').write_text(result.stdout + result.stderr)
result.check_returncode()
build = json.loads((BASE / 'build.json').read_text())
build.update(flags=flags, binary_sha256=sha(OUT / 'solver'), binary_bytes=(OUT / 'solver').stat().st_size)
(OUT / 'build.json').write_text(json.dumps(build, indent=2) + '\n')
