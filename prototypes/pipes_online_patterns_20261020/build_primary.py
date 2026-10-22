"""Diagnostic-driven, fixed causal variants; old sources remain immutable."""
import datetime, hashlib, json, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build(name,source,description):
    d=HERE/'candidates'/name;d.mkdir(parents=True,exist_ok=True);p=d/'solution.cpp'
    assert not p.exists() or p.read_text()==source
    p.write_text(source);cmd=['clang++','-std=c++17','-O2','-DNDEBUG',str(p),'-o',str(d/'solver')]
    subprocess.run(cmd,check=True)
    (d/'build.json').write_text(json.dumps(dict(source_sha256=sha(p),binary_sha256=sha(d/'solver'),description=description,command=cmd),indent=2)+'\n')

def support_guard(s):
    old='''(activePipeCount >= 128 && primalStep >= 256 &&
              primalRecentDeletes >= 32));'''
    new='''(activePipeCount >= 128 && primalStep >= 256 &&
              primalRecentDeletes >= 32 &&
              primalEventHistory.size() - primalRecentDeletes >= 32));'''
    assert s.count(old)==1
    # primalStep>=256 guarantees this 256-slot event ring is fully populated.
    return s.replace(old,new)

def seed_tie(s):
    old='''                if (primalBest != freeByStart.end()) {
                    primalBest = chooseCausalLifetimeGap('''
    new='''                if (primalBest != freeByStart.end()) {
                    // Equal model value is not evidence to change the legacy
                    // layout. Keep its seed with the existing numerical tolerance.
                    if (legacyBest != freeByStart.end() &&
                        primalGapLoss(legacyBest->second - legacyBest->first, length)
                            <= primalBestScore + 1e-9) {
                        primalBest = legacyBest;
                    }
                    primalBest = chooseCausalLifetimeGap('''
    assert s.count(old)==1
    return s.replace(old,new)

if __name__=='__main__':
    base=(HERE/'candidates/baseline/solution.cpp').read_text()
    assert sha(HERE/'candidates/baseline/solution.cpp')=='57c047da7ae9939d9d86dfb050458f22e1a189ec43c5fb621c578bee324821d9'
    (HERE/'diagnostic-plan-update.json').write_text(json.dumps(dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        new_fresh_outcomes_observed=False,
        evidence='All23 first action differences occur in DP, with no MC execution there. MC-off while DP active diagnostic is21 ties/1better/1worse, total trench difference0. Forced fresh is mixed. Some decision windows have254 deletions and only1 previous placement; other changes have equal DP value.',
        substitution='Within the five-hypothesis budget, replace unpromising MC-abstention and forced-refresh proposals with sparse-demand confidence and equal-value legacy seed preservation. These choices use only observed old DEV traces.',
        fixed_variants=['sufficient_demand: >=32 placements in the full256 event ring for the new moderate-population DP path','stable_ties: keep legacy gap when its DP loss <= best+existing1e-9 tolerance'],
        unused_optional_hypothesis='Shrunk conditional demand from size transitions; only if these fixed variants do not suffice before calibration.'),indent=2)+'\n')
    build('sufficient_demand',support_guard(base),'Demand/deletion confidence symmetric at32 observed events; only moderate-population DP branch.')
    build('stable_ties',seed_tie(base),'Preserve legacy seed on equal DP model value; no parameter sweep and no test identities.')
