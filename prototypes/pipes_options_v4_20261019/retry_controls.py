"""One bounded infrastructure retry; immutable binaries and identical inputs."""
import json
from pathlib import Path
import shutil
import evaluate as e

e.quota()
e.verify_freeze()
checker = e.REPO / 'prototypes/pipes_architecture_v2_20261018/checker/native_runner'
info = json.loads(checker.with_name('build.json').read_text())
assert e.sha(checker) == info['binary_sha256']
assert e.sha(e.NATIVE / 'native_runner.cpp') == info['adapter_sha256']
incident = {
    'status': 'retrying',
    'affected_batches': ['train/bf_rollin', 'train/bf'],
    'facts': 'Each batch has two empty native reports without solver PID/output/usage, then 94 skipped cases. Final/dev/repeat for the same solver binaries passed.',
    'cause': 'Not established. Native startup failure is suspected; original harness did not retain the checker exit code.',
    'retry_policy': 'Use pinned existing checker binary without overwriting it between batches. Same 96 inputs and frozen solvers; original failed reports preserved.',
    'checker_sha256': e.sha(checker),
}
e.save(e.ROOT / 'infrastructure-incident.json', incident)
dest = e.ROOT / 'data/train_retry'
dest.mkdir(exist_ok=False)
for p in (e.ROOT / 'data/train').glob('*.in'):
    shutil.copy2(p, dest / p.name)
    assert e.sha(p) == e.sha(dest / p.name)
assert len(list(dest.glob('*.in'))) == 96
e.prepare_checker = lambda: checker
for label in ['bf_rollin', 'bf']:
    e.verify_freeze()
    e.evaluate(label, 'train_retry', 2)
    m = json.loads((e.ROOT / 'evaluations/train_retry' / label / 'manifest.json').read_text())
    if not m['correct']:
        raise RuntimeError('Retry failed; no further retry: ' + label)
incident['status'] = 'recovered_exact_inputs_and_binaries'
e.save(e.ROOT / 'infrastructure-incident.json', incident)
e.verify_freeze()
