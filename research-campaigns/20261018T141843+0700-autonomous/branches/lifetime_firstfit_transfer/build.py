"""Address First-Fit for supported low-risk births using parent's lifetime model."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parent = ROOT / 'releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp'
donor = ROOT / 'proposals/trial_0072/candidate_0.cpp'
assert hashlib.sha256(parent.read_bytes()).hexdigest() == '988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4'
assert hashlib.sha256(donor.read_bytes()).hexdigest() == 'a168536919f96a30ebcf30cc91b13fec250fa27484493e360343a634cfc458d7'
text = parent.read_text()

def replace(old, new):
    global text
    assert text.count(old) == 1, old[:100]
    text = text.replace(old, new, 1)

replace('    CensoredLifetimeModel lifetimeModel;\n', '''    CensoredLifetimeModel lifetimeModel;
    std::array<std::set<std::int64_t>, 41> gapsByCappedWidth;
    std::uint64_t firstFitQueries = 0, firstFitSupported = 0;
    std::uint64_t firstFitChanges = 0;
''')
replace('''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);
''', '''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            if (activePipeCount > kMcMaxActivePipes && !parityCohortMode &&
                !alternatingDeleteMode && !runLeftActive && !additiveNextAlignment &&
                !counterfactualCapacityChoice && !lifoStackLane) {
                const auto first = lifetimeFirstFit(gap, length, highSide);
                if (first != freeByStart.end()) { gap = first; highSide = false; }
            }
            start = consumeAtSide(gap, length, highSide);
''')
replace('    std::int64_t consumeAtSide(StartIter it, int length, bool highSide) {\n', '''    StartIter lifetimeFirstFit(StartIter baseline, int length, bool highSide) {
        const auto physical = freeBySize.lower_bound({length, 0});
        if (!causalRiskReady || physical == freeBySize.end() || physical->first == length) {
            return freeByStart.end();
        }
        ++firstFitQueries;
        // The existing model returns1 when uncertainty hides the direction.
        // No new survival thresholds or class labels are introduced here.
        if (!(lifetimeModel.newRisk(length) < 1.0)) return freeByStart.end();
        ++firstFitSupported;
        std::int64_t address = std::numeric_limits<std::int64_t>::max();
        for (int width = length; width <= 40; ++width) {
            const auto& bucket = gapsByCappedWidth[static_cast<std::size_t>(width)];
            if (!bucket.empty()) address = std::min(address, *bucket.begin());
        }
        if (address == std::numeric_limits<std::int64_t>::max()) return freeByStart.end();
        const auto first = freeByStart.find(address);
        const std::int64_t parentAddress = highSide ? baseline->second - length : baseline->first;
        if (address != parentAddress) ++firstFitChanges;
        return first;
    }

    std::int64_t consumeAtSide(StartIter it, int length, bool highSide) {
''')
replace('        freeBySize.erase({gapLength, start});\n', '''        freeBySize.erase({gapLength, start});
        gapsByCappedWidth[static_cast<std::size_t>(std::min<std::int64_t>(gapLength, 40))].erase(start);
''')
replace('        freeBySize.emplace(gapLength, start);\n', '''        freeBySize.emplace(gapLength, start);
        gapsByCappedWidth[static_cast<std::size_t>(std::min<std::int64_t>(gapLength, 40))].insert(start);
''')
replace('''            std::cerr << "recency_different_selections="
''', '''            std::cerr << "lifetime_firstfit_queries=" << allocator.firstFitQueries
                      << " supported=" << allocator.firstFitSupported
                      << " changed_placements=" << allocator.firstFitChanges << '\\n';
            std::cerr << "recency_different_selections="
''')
destination = Path(__file__).with_name('solution.cpp')
assert not destination.exists(), 'Do not overwrite a registered candidate'
destination.write_text(text)
print(hashlib.sha256(destination.read_bytes()).hexdigest())
