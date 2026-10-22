import json,hashlib,subprocess
from pathlib import Path
root=Path('/Users/555tery/techarena')
base=root/'prototypes/pipes_closed_ready_20261020/candidates-fast/online/solution.cpp'
here=Path(__file__).resolve().parent
s=base.read_text()
a=s.replace('    std::array<std::array<std::int64_t, 2>, 41> removedLengthCohort{};', '    std::array<std::array<std::int64_t, 2>, 41> removedLengthCohort{};\n    std::array<std::deque<int>, 41> recentDeletedCohorts;')
needle='        ++removedLengthCohort[lengthIndex][static_cast<std::size_t>(pipe.sizeCohort)];'
assert a.count(needle)==2
a=a.replace(needle,'''        // Confidence describes at most the last 64 deletions of this size.
        auto& recent = recentDeletedCohorts[lengthIndex];
        recent.push_back(pipe.sizeCohort);
        ++removedLengthCohort[lengthIndex][static_cast<std::size_t>(pipe.sizeCohort)];
        if (recent.size() > 64) {
            --removedLengthCohort[lengthIndex][static_cast<std::size_t>(recent.front())];
            recent.pop_front();
        }''')
needle='''        if (totalForLength >= 8 && dominantForLength * 100 >= totalForLength * 85 &&
            hasSteadySizeTrend()) {'''
assert a.count(needle)==2
a=a.replace(needle,'''        // Hysteresis requires actual contradictory deletions before relaxing
        // ownership; historical confidence is never a permanent latch.
        if (totalForLength >= 16 && dominantForLength * 100 < totalForLength * 70) {
            parityCohortMode = false;
        }
'''+needle)
a=a.replace('        state.removedLengthCohort = removedLengthCohort;', '        state.removedLengthCohort = removedLengthCohort;\n        state.recentDeletedCohorts = recentDeletedCohorts;')
b=s.replace('std::array<int, kHistoryWindow> primalEventHistory{};', 'std::array<int, 256> primalEventHistory{};')
needle='(2.0 * static_cast<double>(kHistoryWindow)))'
assert b.count(needle)==1
b=b.replace(needle,'(2.0 * static_cast<double>(primalEventHistory.size())))')
manifest={'base':str(base),'base_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'variants':{}}
for name,source in [('parity_decay64',a),('primal_window256',b)]:
    folder=here/name;folder.mkdir(exist_ok=True)
    (folder/'solution.cpp').write_text(source)
    p=subprocess.run(['clang++','-std=c++17','-O2','-DNDEBUG',str(folder/'solution.cpp'),'-o',str(folder/'solver')],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    manifest['variants'][name]={'source_sha256':hashlib.sha256((folder/'solution.cpp').read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256((folder/'solver').read_bytes()).hexdigest()}
(here/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
