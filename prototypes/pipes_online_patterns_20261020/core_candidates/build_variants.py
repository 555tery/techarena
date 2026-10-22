from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('/Users/555tery/techarena')
HERE=Path(__file__).resolve().parent
BASE=ROOT/'prototypes/pipes_online_core_20261020/release/solution.cpp'
s=BASE.read_text()
assert hashlib.sha256(BASE.read_bytes()).hexdigest()=='57c047da7ae9939d9d86dfb050458f22e1a189ec43c5fb621c578bee324821d9'
needle='    std::array<int, 41> primalRecentRequests{};'
assert s.count(needle)==1
common=s.replace(needle,needle+'''
    // An observed 64-event suffix; no future pattern is extrapolated.
    std::array<int, 41> primalShortRequests{};
    int primalShortDeletes = 0;''')
needle='''        const int old = primalEventHistory[primalEventPosition];'''
assert common.count(needle)==1
common=common.replace(needle,'''        const std::size_t shortIndex =
            (primalEventPosition + primalEventHistory.size() - 64) %
            primalEventHistory.size();
        const int shortOld = primalEventHistory[shortIndex];
        if (shortOld > 0) {
            if (--primalShortRequests[static_cast<std::size_t>(shortOld)] == 0)
                primalModelDirty = true;
        } else if (shortOld < 0) {
            if (--primalShortDeletes == 0) primalModelDirty = true;
        }
        if (event > 0) {
            if (primalShortRequests[static_cast<std::size_t>(event)]++ == 0)
                primalModelDirty = true;
        } else if (event < 0) {
            if (primalShortDeletes++ == 0) primalModelDirty = true;
        }
'''+needle)
a=common
# Pure gate variant leaves the original DP rebuild schedule intact.
a=a.replace('if (--primalShortRequests[static_cast<std::size_t>(shortOld)] == 0)\n                primalModelDirty = true;', '--primalShortRequests[static_cast<std::size_t>(shortOld)];')
a=a.replace('if (--primalShortDeletes == 0) primalModelDirty = true;', '--primalShortDeletes;')
a=a.replace('if (primalShortRequests[static_cast<std::size_t>(event)]++ == 0)\n                primalModelDirty = true;', '++primalShortRequests[static_cast<std::size_t>(event)];')
a=a.replace('if (primalShortDeletes++ == 0) primalModelDirty = true;', '++primalShortDeletes;')
needle='    bool ensurePrimalGapValues(int maxGap) {'
assert a.count(needle)==1
a=a.replace(needle,'''    bool hasStablePrimalDemand() const {
        int shortTotal = 0;
        int olderTotal = 0;
        for (std::size_t length = 1; length < primalRecentRequests.size(); ++length) {
            shortTotal += primalShortRequests[length];
            olderTotal += primalRecentRequests[length] - primalShortRequests[length];
        }
        if (shortTotal < 16 || olderTotal < 16) return false;
        int overlap = 0;
        for (std::size_t length = 1; length < primalRecentRequests.size(); ++length) {
            overlap += std::min(primalShortRequests[length] * olderTotal,
                (primalRecentRequests[length] - primalShortRequests[length]) * shortTotal);
        }
        // TV <= 1/2 between the short suffix and its preceding history.
        return overlap * 2 >= shortTotal * olderTotal;
    }

'''+needle+'''
        if (!hasStablePrimalDemand()) return false;''')
b=common
needle='''static_cast<double>(primalRecentRequests[static_cast<std::size_t>(gap)])'''
assert b.count(needle)==1
b=b.replace(needle,'''(0.5 * static_cast<double>(primalRecentRequests[static_cast<std::size_t>(gap)]) +
                     2.0 * static_cast<double>(primalShortRequests[static_cast<std::size_t>(gap)]))''')
needle='''const double expiry = 2.0 * static_cast<double>(primalRecentDeletes) /'''
assert b.count(needle)==1
b=b.replace(needle,'''const double expiry = 2.0 *
            (0.5 * static_cast<double>(primalRecentDeletes) +
             2.0 * static_cast<double>(primalShortDeletes)) /''')
needle='primalStep - primalModelStep >= 64'
assert b.count(needle)==1
b=b.replace(needle,'primalStep - primalModelStep >= 16')
manifest={'base_source':str(BASE),'base_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'variants':{}}
for name,source in [('dp_stability_gate',a),('dp_recency_mix',b)]:
    folder=HERE/name;folder.mkdir(exist_ok=True)
    path=folder/'solution.cpp';path.write_text(source)
    cmd=['clang++','-std=c++17','-O2','-DNDEBUG',str(path),'-o',str(folder/'solver')]
    p=subprocess.run(cmd,capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    manifest['variants'][name]={'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256((folder/'solver').read_bytes()).hexdigest(),'compile_command':cmd}
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
