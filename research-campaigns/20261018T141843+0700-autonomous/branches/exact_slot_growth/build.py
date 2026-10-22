from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
prefix, s = (ROOT / 'branches/primal_transfer/primal_gap_dp.cpp').read_text().split('class Allocator {', 1)

def change(old, new):
    global s
    assert s.count(old) == 1, (old[:80], s.count(old))
    s = s.replace(old, new)

change('    std::uint64_t primalFirstActivationEvent = 0;', '''    std::uint64_t primalFirstActivationEvent = 0;
    std::array<std::vector<std::int64_t>, 41> exactFreedSlots;
    std::int64_t exactSlotFrontier = 0;
    std::uint64_t exactSlotReuses = 0;
    std::uint64_t exactSlotAppends = 0;
    std::uint64_t exactSlotStale = 0;''')
change('        auto gap = bestFittingGap(length, highSide, sizeCohort);', '''        const bool exactSlotMode = !runLeftActive && !additiveNextAlignment &&
            !parityCohortMode && !alternatingDeleteMode &&
            predictedNextClass <= length && exactSlotGrowthConfidence();
        auto gap = exactSlotMode ? freeByStart.end()
                                 : bestFittingGap(length, highSide, sizeCohort);''')
change('''        std::int64_t digs = 0;
        if (start < 0) {''', '''        std::int64_t digs = 0;
        if (exactSlotMode) {
            const auto result = placeInExactSlot(length);
            digs = result.first;
            start = result.second;
        }
        if (start < 0) {''')
change('        const Pipe pipe = pipes[index];', '''        const Pipe pipe = pipes[index];
        exactFreedSlots[static_cast<std::size_t>(pipe.length)].push_back(pipe.start);''')
change('    void recordPrimalEvent(int event) {', '''    void recordPrimalEvent(int event) {
        if (event > 0) exactSlotFrontier = std::max(
            exactSlotFrontier, pipes.back().start + pipes.back().length);''')
methods = '''    bool exactSlotGrowthConfidence() const {
        if (activePipeCount < 128 || recentLengths.size() < 128 ||
            recentDeleteRanksPermille.size() < 48 || unitDominantRecentProfile()) {
            return false;
        }
        std::size_t young = 0;
        for (int rank : recentDeleteRanksPermille) if (rank <= 50) ++young;
        if (young * 100 < recentDeleteRanksPermille.size() * 80) return false;
        int adds = 0;
        for (int count : primalRecentRequests) adds += count;
        return adds > primalRecentDeletes;
    }

    std::int64_t consumeExactAddress(StartIter gap, std::int64_t address, int length) {
        const auto begin = gap->first, end = gap->second;
        const int cohort = gapCohort.at(begin);
        const auto freedAt = gapFreedAt.at(begin);
        eraseGap(gap);
        addFreeGap(begin, address, cohort, freedAt);
        addFreeGap(address + length, end, cohort, freedAt);
        return address;
    }

    std::pair<std::int64_t, std::int64_t> placeInExactSlot(int length) {
        // A cached footprint is usable only if it is entirely free NOW.
        // General placements between cache phases may have invalidated it.
        auto& slots = exactFreedSlots[static_cast<std::size_t>(length)];
        while (!slots.empty()) {
            const std::int64_t address = slots.back();
            slots.pop_back();
            auto gap = freeByStart.upper_bound(address);
            if (gap != freeByStart.begin()) {
                --gap;
                if (gap->first <= address && address + length <= gap->second) {
                    ++exactSlotReuses;
                    return {0, consumeExactAddress(gap, address, length)};
                }
            }
            ++exactSlotStale;
        }
        // Frontier is the maximum endpoint ever allocated, not the rounded
        // trench boundary. Unassigned section padding is shared by all sizes.
        const std::int64_t address = exactSlotFrontier;
        const std::int64_t missing = std::max<std::int64_t>(
            0, address + length - trenchLength);
        const std::int64_t digs = (missing + kDigLength - 1) / kDigLength;
        trenchLength += digs * kDigLength;
        addFreeGap(address, trenchLength, -1);
        auto gap = freeByStart.upper_bound(address);
        --gap;
        ++exactSlotAppends;
        return {digs, consumeExactAddress(gap, address, length)};
    }

'''
change('    bool hasRecentPrimalDemand() const {', methods + '    bool hasRecentPrimalDemand() const {')
change('            std::cerr << "primal_dp_scored_decisions="', '''            std::cerr << "exact_slot_reuses=" << allocator.exactSlotReuses
                      << " appends=" << allocator.exactSlotAppends
                      << " stale=" << allocator.exactSlotStale << '\\n';
            std::cerr << "primal_dp_scored_decisions="''')
(HERE / 'solution.cpp').write_text(prefix + 'class Allocator {' + s)
print(HERE / 'solution.cpp')
