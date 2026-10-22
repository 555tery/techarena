"""Transfer trial84's exact two-request capacity certificate into strong22."""
import hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
parent = ROOT / 'releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp'
donor = ROOT / 'proposals/trial_0084/candidate_0.cpp'
assert hashlib.sha256(parent.read_bytes()).hexdigest() == '988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4'
assert hashlib.sha256(donor.read_bytes()).hexdigest() == '75926e1248ca0bae7abf2b77744b62842d4bd74638a36deabb0cd2311cba884c'
text = parent.read_text()
helpers = donor.read_text().split('constexpr int kMaxLength=40;', 1)[1].split('\nint main()', 1)[0]
helpers = 'constexpr int kMaxLength=40;' + helpers
helpers = helpers.replace('kMaxLength', 'kParetoMaxLength').replace('kPairLimit', 'kParetoPairLimit')
helpers = helpers.replace('using CarryMasks=', 'using ParetoCarryMasks=').replace('CarryMasks', 'ParetoCarryMasks')
# The last replacement also renames makeCarryMasks; use its resulting name.
helpers = helpers.replace('using ParetoParetoCarryMasks=', 'using ParetoCarryMasks=')
helpers = helpers.replace('I g,I h,I length', 'std::int64_t g,std::int64_t h,std::int64_t length')
helpers = helpers.replace('const I ', 'const std::int64_t ').replace('std::min<I>', 'std::min<std::int64_t>')
helpers = helpers.replace('strictlyDominatesPairs', 'strictlyDominatesParetoPairs')
anchor = 'class Allocator {\n'
assert text.count(anchor) == 1
text = text.replace(anchor, helpers + '\n' + anchor)

def replace(old, new):
    global text
    assert text.count(old) == 1, old[:100]
    text = text.replace(old, new, 1)

replace('    CensoredLifetimeModel lifetimeModel;\n', '''    CensoredLifetimeModel lifetimeModel;
    const ParetoCarryMasks paretoCarryMasks = makeParetoCarryMasks();
    std::uint64_t paretoPairProbes = 0, paretoPairCertificates = 0;
    std::uint64_t paretoHomogeneousVetoes = 0, paretoPairChanges = 0;
''')
replace('''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);
''', '''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            if (!parityCohortMode && !alternatingDeleteMode && !runLeftActive &&
                !additiveNextAlignment && !counterfactualCapacityChoice && !lifoStackLane) {
                gap = chooseParetoPairGap(gap, length, highSide);
            }
            start = consumeAtSide(gap, length, highSide);
''')
replace('    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {\n', '''    StartIter chooseParetoPairGap(StartIter baseline, int length, bool highSide) {
        std::int64_t selectedWidth = baseline->second - baseline->first;
        if (selectedWidth <= length || selectedWidth >= kParetoPairLimit) return baseline;
        auto selected = baseline;
        const bool recycleRecent = activePipeCount > kMcMaxActivePipes && hasLifoDeletionConfidence();
        const bool confidentAddress = highSide && !lifoLaneDisabledForScale && hasLifoDeletionConfidence();
        auto it = freeBySize.upper_bound({selectedWidth, std::numeric_limits<std::int64_t>::max()});
        while (it != freeBySize.end() && it->first < kParetoPairLimit) {
            const std::int64_t width = it->first;
            ++paretoPairProbes;
            if (strictlyDominatesParetoPairs(selectedWidth, width, length)) {
                ++paretoPairCertificates;
                const auto gained = paretoCarryMasks[static_cast<std::size_t>(selectedWidth)][length];
                const auto lost = paretoCarryMasks[static_cast<std::size_t>(width)][length];
                if ((lost & ~gained) != 0) {
                    ++paretoHomogeneousVetoes;
                } else {
                    std::int64_t representative = it->second;
                    if (confidentAddress) representative = std::prev(freeBySize.upper_bound({width,
                        std::numeric_limits<std::int64_t>::max()}))->second;
                    if (recycleRecent) representative = std::get<2>(*std::prev(freeBySizeAge.upper_bound({width,
                        std::numeric_limits<std::uint64_t>::max(),
                        std::numeric_limits<std::int64_t>::max()})));
                    selected = freeByStart.find(representative);
                    selectedWidth = width;
                }
            }
            it = freeBySize.upper_bound({width, std::numeric_limits<std::int64_t>::max()});
        }
        if (selected != baseline) ++paretoPairChanges;
        return selected;
    }

    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {
''')
replace('            std::cerr << "recency_different_selections="\n', '''            std::cerr << "pareto_pair_probes=" << allocator.paretoPairProbes
                      << " certificates=" << allocator.paretoPairCertificates
                      << " homogeneous_vetoes=" << allocator.paretoHomogeneousVetoes
                      << " changed_placements=" << allocator.paretoPairChanges << '\\n';
            std::cerr << "recency_different_selections="
''')
destination = Path(__file__).with_name('solution.cpp')
assert not destination.exists()
destination.write_text(text)
print(hashlib.sha256(destination.read_bytes()).hexdigest())
