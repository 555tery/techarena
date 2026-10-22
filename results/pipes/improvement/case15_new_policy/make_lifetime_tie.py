from pathlib import Path

s = Path('results/pipes/improvement/case15_new_policy/source/baseline.cpp').read_text()

s = s.replace(
'''struct Pipe {
    std::int64_t start = 0;
    int length = 0;
    bool active = false;
    int sizeCohort = 0;
};''',
'''struct Pipe {
    std::int64_t start = 0;
    int length = 0;
    bool active = false;
    int sizeCohort = 0;
    std::size_t bornPlacement = 0;
};''', 1)

needle = '''    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
'''
replacement = '''    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
    std::size_t placementCount = 0;
    std::map<std::int64_t, int> activeByStart;
    static constexpr std::size_t kLifeRing = 32;
    std::array<std::array<std::uint32_t, kLifeRing>, 41> lifeSamples{};
    std::array<std::size_t, 41> lifeSampleCount{};
    std::array<std::size_t, 41> lifeSampleNext{};
'''
assert needle in s
s=s.replace(needle,replacement,1)

old = '''        auto gap = bestFittingGap(length, highSide, sizeCohort);
        if (gap != freeByStart.end()) {
            const std::int64_t selectedStart = chooseGapWithRollout(
                length, highSide, sizeCohort, gap);
            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);
        }'''
new = '''        auto gap = bestFittingGap(length, highSide, sizeCohort);
        if (gap != freeByStart.end()) {
            const std::int64_t selectedStart = chooseGapWithRollout(
                length, highSide, sizeCohort, gap);
            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            gap = chooseLifetimeCompatibleTie(length, highSide, sizeCohort, gap);
            start = consumeAtSide(gap, length, highSide);
        }'''
assert old in s
s=s.replace(old,new,1)

old = '''        pipes.push_back(Pipe{start, length, true, sizeCohort});
        fenwickAdd(pid, 1);
        ++activePipeCount;
        ++lengthOccurrenceCount[static_cast<std::size_t>(length)];'''
new = '''        pipes.push_back(Pipe{start, length, true, sizeCohort, placementCount});
        activeByStart.emplace(start, pid);
        fenwickAdd(pid, 1);
        ++activePipeCount;
        ++placementCount;
        ++lengthOccurrenceCount[static_cast<std::size_t>(length)];'''
assert old in s
s=s.replace(old,new,1)

old = '''        const Pipe pipe = pipes[index];
        std::cout << pipe.start << '\\n' << std::flush;
        pipes[index].active = false;
        fenwickAdd(static_cast<int>(index), -1);'''
new = '''        const Pipe pipe = pipes[index];
        std::cout << pipe.start << '\\n' << std::flush;
        recordLifetime(pipe.length, placementCount - pipe.bornPlacement);
        pipes[index].active = false;
        activeByStart.erase(pipe.start);
        fenwickAdd(static_cast<int>(index), -1);'''
assert old in s
s=s.replace(old,new,1)

marker = '''    bool observationKeyEqual(const Observation& lhs, const Observation& rhs) const {'''
methods = '''    void recordLifetime(int length, std::size_t age) {
        const std::size_t index = static_cast<std::size_t>(length);
        const std::size_t slot = lifeSampleNext[index];
        lifeSamples[index][slot] = static_cast<std::uint32_t>(age);
        lifeSampleNext[index] = (slot + 1U) % kLifeRing;
        lifeSampleCount[index] = std::min(kLifeRing, lifeSampleCount[index] + 1U);
    }

    bool medianLifetime(int length, std::uint32_t& median) const {
        const std::size_t index = static_cast<std::size_t>(length);
        const std::size_t count = lifeSampleCount[index];
        if (count < 16U) return false;
        std::array<std::uint32_t, kLifeRing> sorted = lifeSamples[index];
        std::sort(sorted.begin(), sorted.begin() + static_cast<std::ptrdiff_t>(count));
        median = sorted[count / 2U];
        return true;
    }

    std::uint32_t remainingLifetime(const Pipe& pipe, std::uint32_t median) const {
        const std::size_t age = placementCount - pipe.bornPlacement;
        if (age >= median) return 0U;
        return median - static_cast<std::uint32_t>(age);
    }

    bool adjacentLifetimeDifference(std::int64_t gapStart, std::int64_t gapEnd,
                                    int length, bool highSide,
                                    std::uint32_t incomingMedian,
                                    std::uint32_t& difference) const {
        bool found = false;
        difference = std::numeric_limits<std::uint32_t>::max();
        const auto consider = [&](std::int64_t pipeStart) {
            const auto active = activeByStart.find(pipeStart);
            if (active == activeByStart.end()) return;
            const Pipe& neighbor = pipes[static_cast<std::size_t>(active->second)];
            std::uint32_t neighborMedian = 0;
            if (!medianLifetime(neighbor.length, neighborMedian)) return;
            const std::uint32_t neighborRemaining = remainingLifetime(neighbor, neighborMedian);
            const std::uint32_t delta = incomingMedian >= neighborRemaining
                ? incomingMedian - neighborRemaining
                : neighborRemaining - incomingMedian;
            if (!found || delta < difference) {
                difference = delta;
                found = true;
            }
        };

        if (!highSide || gapEnd - gapStart == length) {
            auto it = activeByStart.lower_bound(gapStart);
            if (it != activeByStart.begin()) {
                --it;
                const Pipe& pipe = pipes[static_cast<std::size_t>(it->second)];
                if (it->first + pipe.length == gapStart) consider(it->first);
            }
        }
        if (highSide || gapEnd - gapStart == length) {
            auto it = activeByStart.find(gapEnd);
            if (it != activeByStart.end()) consider(it->first);
        }
        return found;
    }

    StartIter chooseLifetimeCompatibleTie(
        int length, bool highSide, int sizeCohort, StartIter selected) {
        std::uint32_t incomingMedian = 0;
        if (!medianLifetime(length, incomingMedian)) return selected;

        std::uint32_t baselineDifference = 0;
        if (!adjacentLifetimeDifference(selected->first, selected->second,
                                        length, highSide, incomingMedian,
                                        baselineDifference)) {
            return selected;
        }

        const std::set<std::pair<std::int64_t, std::int64_t>>* candidateSet = &freeBySize;
        if (parityCohortMode) {
            const int cohort = gapCohort.at(selected->first);
            candidateSet = cohort == sizeCohort
                ? &freeBySizeCohort[static_cast<std::size_t>(sizeCohort)]
                : &freeBySizeShared;
        }
        const std::int64_t bestScore = scoreGap(selected->second - selected->first, length);
        StartIter best = selected;
        std::uint32_t bestDifference = baselineDifference;
        auto it = candidateSet->lower_bound({length, 0});
        while (it != candidateSet->end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            if (slack > 40) break;
            if (scoreGap(gapLength, length) == bestScore) {
                auto group = candidateSet->lower_bound({gapLength, 0});
                const auto groupEnd = candidateSet->upper_bound(
                    {gapLength, std::numeric_limits<std::int64_t>::max()});
                std::array<std::int64_t, 8> starts{};
                std::size_t startCount = 0;
                auto first = group;
                for (int i = 0; i < 4 && first != groupEnd; ++i, ++first) {
                    starts[startCount++] = first->second;
                }
                auto last = groupEnd;
                for (int i = 0; i < 4 && last != group; ++i) {
                    --last;
                    const bool duplicate = std::find(
                        starts.begin(), starts.begin() + static_cast<std::ptrdiff_t>(startCount),
                        last->second) != starts.begin() + static_cast<std::ptrdiff_t>(startCount);
                    if (!duplicate) starts[startCount++] = last->second;
                }
                for (std::size_t i = 0; i < startCount; ++i) {
                    const auto gap = freeByStart.find(starts[i]);
                    if (gap == freeByStart.end()) continue;
                    std::uint32_t difference = 0;
                    if (adjacentLifetimeDifference(gap->first, gap->second,
                                                   length, highSide, incomingMedian,
                                                   difference) &&
                        difference + 16U < bestDifference) {
                        best = gap;
                        bestDifference = difference;
                    }
                }
            }
            it = candidateSet->upper_bound(
                {gapLength, std::numeric_limits<std::int64_t>::max()});
        }
        return best;
    }

'''
assert marker in s
s=s.replace(marker,methods+marker,1)

Path('results/pipes/improvement/case15_new_policy/source/lifetime_equal_cost_ties.cpp').write_text(s)
