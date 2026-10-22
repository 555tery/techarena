"""Reuse freed footprints without reserving space or forcing excavation."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parent = ROOT / 'releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp'
donor = ROOT / 'proposals/trial_0066/candidate_0.cpp'
assert hashlib.sha256(parent.read_bytes()).hexdigest() == '988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4'
assert hashlib.sha256(donor.read_bytes()).hexdigest() == '108036e709472d9b4f680111c2cb9a28ecbccc5b12c24f6391ea800c1cb79905'
text = parent.read_text()

def replace(old, new):
    global text
    assert text.count(old) == 1, old[:100]
    text = text.replace(old, new, 1)

replace('    CensoredLifetimeModel lifetimeModel;\n', '''    CensoredLifetimeModel lifetimeModel;
    std::array<std::vector<std::int64_t>, 41> freedFootprints;
    std::uint64_t footprintQueries = 0, footprintHits = 0;
    std::uint64_t footprintStale = 0, footprintChanges = 0;
    std::uint64_t footprintInteriorChanges = 0;
''')
replace('''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);
''', '''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            if (activePipeCount > kMcMaxActivePipes && !parityCohortMode &&
                !alternatingDeleteMode && !runLeftActive && !additiveNextAlignment &&
                !counterfactualCapacityChoice && !lifoStackLane) {
                start = tryFreedFootprint(gap, length, highSide);
            }
            if (start < 0) start = consumeAtSide(gap, length, highSide);
''')
replace('''        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort, ++releaseEpoch);
''', '''        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort, ++releaseEpoch);
        freedFootprints[static_cast<std::size_t>(pipe.length)].push_back(pipe.start);
''')
replace('    std::int64_t consumeAtSide(StartIter it, int length, bool highSide) {\n', '''    std::int64_t tryFreedFootprint(StartIter baseline, int length, bool highSide) {
        // Retain the parent's physical exact-fit priority. Cached spans do not
        // remove or reserve anything from the physical free-space indices.
        const auto physical = freeBySize.lower_bound({length, 0});
        if (physical == freeBySize.end() || physical->first == length) return -1;
        ++footprintQueries;
        auto& stack = freedFootprints[static_cast<std::size_t>(length)];
        while (!stack.empty()) {
            const std::int64_t address = stack.back();
            stack.pop_back();
            auto after = freeByStart.upper_bound(address);
            if (after == freeByStart.begin()) { ++footprintStale; continue; }
            auto gap = std::prev(after);
            if (gap->first > address || gap->second < address + length) {
                ++footprintStale; continue;
            }
            ++footprintHits;
            const std::int64_t parentAddress = highSide
                ? baseline->second - length : baseline->first;
            if (address != parentAddress) ++footprintChanges;
            const std::int64_t begin = gap->first, end = gap->second;
            if (address > begin && address + length < end) ++footprintInteriorChanges;
            const int owner = gapCohort.at(begin);
            const auto freedAt = gapFreedAt.at(begin);
            eraseGap(gap);
            if (begin < address) addFreeGap(begin, address, owner, freedAt);
            if (address + length < end) addFreeGap(address + length, end, owner, freedAt);
            return address;
        }
        return -1;
    }

    std::int64_t consumeAtSide(StartIter it, int length, bool highSide) {
''')
replace('''            std::cerr << "recency_different_selections="
''', '''            std::cerr << "footprint_queries=" << allocator.footprintQueries
                      << " hits=" << allocator.footprintHits
                      << " stale=" << allocator.footprintStale
                      << " changed_placements=" << allocator.footprintChanges
                      << " interior_changes=" << allocator.footprintInteriorChanges << '\\n';
            std::cerr << "recency_different_selections="
''')
destination = Path(__file__).with_name('solution.cpp')
assert not destination.exists(), 'Do not overwrite a registered candidate'
destination.write_text(text)
print(hashlib.sha256(destination.read_bytes()).hexdigest())
