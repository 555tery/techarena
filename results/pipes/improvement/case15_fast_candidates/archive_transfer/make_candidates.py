from pathlib import Path
root = Path('results/pipes/improvement/case15_fast_candidates/archive_transfer')
base = Path('results/pipes/final/solution.cpp').read_text()

# Transfer the causal same-length-run/live-mean sticky mode from the historical
# adaptive allocator into the frozen solver. Test identity and command index are unused.
s = base
field_anchor = '    std::size_t activePipeCount = 0;\n'
fields = '''    std::size_t activePipeCount = 0;
    std::int64_t livePipeLength = 0;
    bool adaptiveStickyMode = false;
    bool stickyValid = false;
    std::int64_t stickyStart = 0;
    std::int64_t stickyEnd = 0;
    int stickyLength = 0;
    int lastRequestLength = 0;
    int sameLengthRun = 0;
'''
assert s.count(field_anchor) == 1
s = s.replace(field_anchor, fields)

mode_anchor = '''        if (hasSmoothSizeTrendWith(length)) runLeftDisabledBySmoothTrend = true;
        const bool runLeftActive = !runLeftDisabledBySmoothTrend &&
            hasSameLengthRecentRun(length);
'''
mode = '''        if (lastRequestLength != length) {
            lastRequestLength = length;
            sameLengthRun = 0;
            stickyValid = false;
        }
        ++sameLengthRun;
        if (activePipeCount > 0 && livePipeLength > 0) {
            const std::int64_t lhs = static_cast<std::int64_t>(length) *
                static_cast<std::int64_t>(activePipeCount);
            if (adaptiveStickyMode && lhs * 5 >= livePipeLength * 12) {
                adaptiveStickyMode = false;
                stickyValid = false;
            } else if (!adaptiveStickyMode && sameLengthRun >= 32 && lhs * 10 <= livePipeLength * 21) {
                adaptiveStickyMode = true;
            }
        } else if (!adaptiveStickyMode && sameLengthRun >= 32) {
            adaptiveStickyMode = true;
        }
        if (hasSmoothSizeTrendWith(length)) runLeftDisabledBySmoothTrend = true;
        const bool runLeftActive = !runLeftDisabledBySmoothTrend &&
            hasSameLengthRecentRun(length);
'''
assert s.count(mode_anchor) == 2
prefix, suffix = s.rsplit(mode_anchor, 1)
s = prefix + mode + suffix

side_old = '''        const bool highSide = runLeftActive
            ? (sizeCohort != 0)
            : (alternatingDeleteMode
                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));
        std::int64_t start = -1;
        auto gap = bestFittingGap(length, highSide, sizeCohort);
'''
side_new = '''        bool highSide = runLeftActive
            ? (sizeCohort != 0)
            : (alternatingDeleteMode
                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));
        if (adaptiveStickyMode)
            highSide = ((pipes.size() % 2U) == 0U);
        std::int64_t start = -1;
        std::int64_t leftoverStart = -1;
        std::int64_t leftoverEnd = -1;
        StartIter gap = freeByStart.end();
        if (adaptiveStickyMode && stickyValid && stickyLength == length) {
            auto it = freeByStart.find(stickyStart);
            if (it != freeByStart.end() && it->second == stickyEnd &&
                it->second - it->first >= length) {
                gap = it;
            } else {
                stickyValid = false;
            }
        } else {
            stickyValid = false;
        }
        if (gap == freeByStart.end()) gap = bestFittingGap(length, highSide, sizeCohort);
'''
assert s.count(side_old) == 1
s = s.replace(side_old, side_new)

selected_old = '''        if (gap != freeByStart.end()) {
            const std::int64_t selectedStart = chooseGapWithRollout(
                length, highSide, sizeCohort, gap);
            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);
        }
'''
selected_new = '''        if (gap != freeByStart.end()) {
            const std::int64_t gapStart = gap->first;
            const std::int64_t gapEnd = gap->second;
            const std::int64_t selectedStart = adaptiveStickyMode ? gapStart :
                chooseGapWithRollout(length, highSide, sizeCohort, gap);
            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);
            if (adaptiveStickyMode) {
                if (highSide) {
                    leftoverStart = gapStart;
                    leftoverEnd = gapEnd - length;
                } else {
                    leftoverStart = gapStart + length;
                    leftoverEnd = gapEnd;
                }
            }
        }
'''
assert s.count(selected_old) == 1
s = s.replace(selected_old, selected_new)

fallback_old = '''            if (parityCohortMode && highSide && !preserveForeignTail) {
                start = trenchLength - length;
                if (tailStart < start) addFreeGap(tailStart, start, tailCohort);
            } else {
                start = tailStart;
                const std::int64_t remainderStart = start + length;
                if (remainderStart < trenchLength) {
                    addFreeGap(remainderStart, trenchLength, tailCohort);
                }
            }
'''
fallback_new = '''            if ((parityCohortMode || adaptiveStickyMode) && highSide && !preserveForeignTail) {
                start = trenchLength - length;
                if (tailStart < start) {
                    addFreeGap(tailStart, start, tailCohort);
                    leftoverStart = tailStart;
                    leftoverEnd = start;
                }
            } else {
                start = tailStart;
                const std::int64_t remainderStart = start + length;
                if (remainderStart < trenchLength) {
                    addFreeGap(remainderStart, trenchLength, tailCohort);
                    leftoverStart = remainderStart;
                    leftoverEnd = trenchLength;
                }
            }
'''
assert s.count(fallback_old) == 2
prefix, suffix = s.rsplit(fallback_old, 1)
s = prefix + fallback_new + suffix

place_final_old = '''        printPlacement(digs, start);
        const int pid = static_cast<int>(pipes.size());
        pipes.push_back(Pipe{start, length, true, sizeCohort});
        fenwickAdd(pid, 1);
        ++activePipeCount;
'''
place_final_new = '''        printPlacement(digs, start);
        if (adaptiveStickyMode && leftoverStart < leftoverEnd) {
            stickyValid = true;
            stickyStart = leftoverStart;
            stickyEnd = leftoverEnd;
            stickyLength = length;
        } else {
            stickyValid = false;
        }
        const int pid = static_cast<int>(pipes.size());
        pipes.push_back(Pipe{start, length, true, sizeCohort});
        fenwickAdd(pid, 1);
        ++activePipeCount;
        livePipeLength += length;
'''
assert s.count(place_final_old) == 1
s = s.replace(place_final_old, place_final_new)
remove_old = '''        --activePipeCount;
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);
'''
remove_new = '''        --activePipeCount;
        livePipeLength -= pipe.length;
        stickyValid = false;
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);
'''
assert s.count(remove_old) == 1
s = s.replace(remove_old, remove_new)
(root / 'source' / 'adaptive_live_mean_overlay.cpp').write_text(s)

# Transfer the historical 128-transition next-length predictor into frozen final.
t = base
const_anchor = '''constexpr std::int64_t kDigLength = 20;
'''
const_text = '''constexpr std::int64_t kDigLength = 20;
constexpr std::size_t kTransitionWindow = 128;
constexpr int kTransitionMinSupport = 4;
constexpr std::int64_t kMaxReservePenalty = 40;
'''
assert t.count(const_anchor) == 1
t = t.replace(const_anchor, const_text)
field_anchor = '''    std::size_t mcRolloutsRun = 0;
'''
field_text = '''    std::size_t mcRolloutsRun = 0;
    std::array<std::array<unsigned short, 41>, 41> transitionCounts{};
    std::deque<std::pair<unsigned char, unsigned char>> transitionWindow;
    int lastPositiveLength = 0;
'''
assert t.count(field_anchor) == 1
t = t.replace(field_anchor, field_text)
place_gap_anchor = '''        auto gap = bestFittingGap(length, highSide, sizeCohort);
        if (gap != freeByStart.end()) {
            const std::int64_t selectedStart = chooseGapWithRollout(
                length, highSide, sizeCohort, gap);
'''
place_gap_new = '''        auto gap = bestFittingGap(length, highSide, sizeCohort);
        bool transitionReserveSelected = false;
        const int predictedNext = predictNextLength(length);
        if (gap != freeByStart.end() && predictedNext > 0) {
            const std::int64_t bestSlack = gap->second - gap->first - length;
            if (bestSlack < predictedNext) {
                StartIter reserve = smallestGapAtLeast(
                    length + predictedNext, sizeCohort);
                if (reserve != freeByStart.end()) {
                    const std::int64_t reserveSlack = reserve->second - reserve->first - length;
                    if (reserveSlack <= bestSlack + kMaxReservePenalty) {
                        gap = reserve;
                        transitionReserveSelected = true;
                    }
                }
            }
        }
        if (gap != freeByStart.end()) {
            const std::int64_t selectedStart = transitionReserveSelected ? gap->first :
                chooseGapWithRollout(length, highSide, sizeCohort, gap);
'''
assert t.count(place_gap_anchor) == 1
t = t.replace(place_gap_anchor, place_gap_new)
observe_anchor = '''        recordObservation(Observation{1, length});
'''
observe_text = '''        recordObservation(Observation{1, length});
        observePositiveLength(length);
'''
assert t.count(observe_anchor) == 1
t = t.replace(observe_anchor, observe_text)
methods_anchor = '''    void recordObservation(const Observation& event) {
'''
methods = '''    StartIter smallestGapAtLeast(int minimumLength, int sizeCohort) {
        if (parityCohortMode) {
            const auto& preferred = freeBySizeCohort[static_cast<std::size_t>(sizeCohort)];
            auto it = preferred.lower_bound({minimumLength, 0});
            if (it != preferred.end()) return freeByStart.find(it->second);
            auto shared = freeBySizeShared.lower_bound({minimumLength, 0});
            return shared == freeBySizeShared.end()
                ? freeByStart.end() : freeByStart.find(shared->second);
        }
        auto it = freeBySize.lower_bound({minimumLength, 0});
        return it == freeBySize.end() ? freeByStart.end() : freeByStart.find(it->second);
    }

    int predictNextLength(int currentLength) const {
        int total = 0;
        int bestLength = 0;
        int bestCount = 0;
        int secondCount = 0;
        for (int nextLength = 1; nextLength <= 40; ++nextLength) {
            const int count = transitionCounts[static_cast<std::size_t>(currentLength)]
                                              [static_cast<std::size_t>(nextLength)];
            total += count;
            if (count > bestCount) {
                secondCount = bestCount;
                bestCount = count;
                bestLength = nextLength;
            } else if (count > secondCount) {
                secondCount = count;
            }
        }
        if (bestCount < kTransitionMinSupport || bestCount <= secondCount) return 0;
        if (bestCount * 5 < total * 4) return 0;
        return bestLength;
    }

    void observePositiveLength(int currentLength) {
        if (lastPositiveLength > 0) {
            if (transitionWindow.size() == kTransitionWindow) {
                const auto oldest = transitionWindow.front();
                transitionWindow.pop_front();
                --transitionCounts[static_cast<std::size_t>(oldest.first)]
                                  [static_cast<std::size_t>(oldest.second)];
            }
            transitionWindow.emplace_back(
                static_cast<unsigned char>(lastPositiveLength),
                static_cast<unsigned char>(currentLength));
            ++transitionCounts[static_cast<std::size_t>(lastPositiveLength)]
                               [static_cast<std::size_t>(currentLength)];
        }
        lastPositiveLength = currentLength;
    }

'''
assert t.count(methods_anchor) == 1
t = t.replace(methods_anchor, methods + methods_anchor)
(root / 'source' / 'transition_model_overlay.cpp').write_text(t)
