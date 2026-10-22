"""Small bounded causal-core experiments; never edit previous releases."""
import datetime, hashlib, json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT/'prototypes/pipes_closed_ready_20261020'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def build(name, source, description):
    dest = HERE/'candidates'/name
    dest.mkdir(parents=True, exist_ok=True)
    path = dest/'solution.cpp'
    if path.exists():
        assert path.read_text() == source, 'Do not replace a measured candidate'
    path.write_text(source)
    cmd = ['clang++', '-std=c++17', '-O2', '-DNDEBUG', str(path), '-o', str(dest/'solver')]
    subprocess.run(cmd, check=True)
    (dest/'build.json').write_text(json.dumps(dict(source_sha256=sha(path), binary_sha256=sha(dest/'solver'),
        command=cmd, description=description), indent=2)+'\n')

if __name__ == '__main__':
    plan = dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='Local only; no platform actions; no edits to previous frozen sources.',
        evidence_before_this_file='Agent DEV results for parity_decay64 and primal_window256 already observed. No new calibration/final policy outcomes observed.',
        development='Previous closed-ready calibration64+final128 are DEV192, not independent. Open15 is an explicit weighted objective, not hidden validation.',
        search_budget='At most 4 core hypotheses total (2 agent + 2 primary), and at most 1 causal combination. No threshold grid. One metadata handoff repair is tracked separately.',
        hypotheses=['bounded parity confidence', 'short primal demand window', 'primal opportunity cost at moderate population', 'one evidence-driven primary hypothesis if needed'],
        fresh_data={g:sha(HERE/'evaluation'/g/'manifest.json') for g in ['calibration','final','stress']},
        gates=dict(correctness='All cases valid; CPU<5s and RSS<256MiB on local one-worker interactive evaluation. Target Windows/G5420 remains unverified.',
            development='Reject a core with any DEV KPI loss >0.10 or negative ordinary mean. Select at most 2 core candidates for calibration.',
            calibration='Require ordinary family-macro improvement >=0.001, prefix macro >= baseline-0.002, and no individual relative retention <0.85. Compare weighted Open15+84*macro at prefix mix 0 and 1; minimax regret with 0.05 tie toward simpler online.',
            freeze='Select at most one core and online/hybrid policy before opening final outcomes. No changes after final.',
            final='Confirm positive ordinary family-macro, prefix macro >= baseline-0.002, no retention <0.85, positive equal-stratum mean, and positive total-score sensitivity at both prefix endpoints relative to previous online. Otherwise no core promotion.',
            uncertainty='Synthetic evidence only, not official hidden-score proof. Report paired family bootstrap, per-stratum outcomes, worst losses, and Open15 tradeoffs.'),
        controls=['previous fast online', 'previous fast hybrid'], independent_generator='closed_inputs; no candidate/result access')
    p = HERE/'experiment.json'
    assert not p.exists()
    p.write_text(json.dumps(plan, indent=2)+'\n')
    online = (OLD/'candidates-fast/online/solution.cpp').read_text()
    hybrid = (OLD/'candidates-fast/hybrid/solution.cpp').read_text()
    build('baseline', online, 'Previous fast online, unchanged.')
    build('old_hybrid', hybrid, 'Previous fast cautious hybrid, unchanged.')
    before = '''const bool ordinaryLargeMode = !parityCohortMode &&
            activePipeCount > kMcMaxActivePipes;'''
    after = '''// The opportunity-cost DP needs observed demand and deletion evidence,
        // not thousands of live objects. Keep the established large-population path.
        const bool ordinaryLargeMode = !parityCohortMode &&
            (activePipeCount > kMcMaxActivePipes ||
             (activePipeCount >= 128 && primalEventHistory.size() >= 256 &&
              primalRecentDeletes >= 32));'''
    assert online.count(before) == 1
    build('primal_moderate', online.replace(before, after),
          'Enable existing gap opportunity-cost DP at >=128 live, >=256 events and >=32 observed deletions; no public fingerprints.')
