"""Isolate forced token-reader inlining and cold error layout at the same O2."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'speed-v13'
OUT = HERE / 'inline'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BASE / 'solution.cpp') == '065707442c1d303ae148b30282f421536a9350505dd8aead5cbc6f3a77043cd3'
OUT.mkdir(exist_ok=False)
prefix = '''// Compiler-only experiment: unchanged Open15 data and I/O protocol.
#if defined(__GNUC__) || defined(__clang__)
#define PIPES_FORCE_INLINE inline __attribute__((always_inline))
#define PIPES_COLD __attribute__((cold, noinline))
#elif defined(_MSC_VER)
#define PIPES_FORCE_INLINE __forceinline
#define PIPES_COLD __declspec(noinline)
#else
#define PIPES_FORCE_INLINE inline
#define PIPES_COLD
#endif
'''
for name in ['solution.cpp', 'solver_runtime.cpp']:
    source = (BASE / name).read_text()
    assert source.count('bool consumeNonzeroToken(){') == 1
    assert source.count('[[noreturn]] void fail(') == 1
    source = source.replace('using namespace std;', prefix + 'using namespace std;')
    source = source.replace('bool consumeNonzeroToken(){', 'PIPES_FORCE_INLINE bool consumeNonzeroToken(){')
    source = source.replace('[[noreturn]] void fail(', '[[noreturn]] PIPES_COLD void fail(')
    (OUT / name).write_text(source)
flags = ['-O2', '-std=c++17', '-Wall', '-Wextra']
result = subprocess.run(['/usr/bin/clang++', *flags, str(OUT / 'solution.cpp'), '-o', str(OUT / 'solver')], capture_output=True, text=True)
(OUT / 'compile.log').write_text(result.stdout + result.stderr)
result.check_returncode()
build = json.loads((BASE / 'build.json').read_text())
build.update(source_sha256=sha(OUT / 'solution.cpp'), binary_sha256=sha(OUT / 'solver'), flags=flags,
             source_bytes=(OUT / 'solution.cpp').stat().st_size, binary_bytes=(OUT / 'solver').stat().st_size,
             experiment='always_inline token consumer + cold/noinline error path',
             base_source_sha256=sha(BASE / 'solution.cpp'))
(OUT / 'build.json').write_text(json.dumps(build, indent=2) + '\n')
print(json.dumps({k: v for k, v in build.items() if k != 'inputs'}, indent=2))
