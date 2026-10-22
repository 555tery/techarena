from pathlib import Path
root = Path('results/pipes/improvement/case15_fast_candidates/archive_transfer/source')
base = Path('results/pipes/improvement/case15_fast_candidates/archive_transfer/source/transition_model_overlay.cpp').read_text()
old = '''        bool transitionReserveSelected = false;
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
'''
new_reserve = '''        bool pairReserveSelected = false;
        const int predictedNext = predictNextLength(length);
        const int predictedSecond = predictedNext > 0
            ? predictNextLength(predictedNext) : 0;
        const int pairReserve = predictedNext + predictedSecond;
        if (gap != freeByStart.end() && predictedNext > 0 && predictedSecond > 0) {
            const std::int64_t bestSlack = gap->second - gap->first - length;
            if (bestSlack < pairReserve) {
                StartIter reserve = smallestGapAtLeast(length + pairReserve, sizeCohort);
                if (reserve != freeByStart.end()) {
                    const std::int64_t reserveSlack = reserve->second - reserve->first - length;
                    if (reserveSlack <= bestSlack + kMaxReservePenalty) {
                        gap = reserve;
                        pairReserveSelected = true;
                    }
                }
            }
        }
'''
assert base.count(old) == 1
pair_reserve = base.replace(old, new_reserve)
pair_reserve = pair_reserve.replace('''            const std::int64_t selectedStart = transitionReserveSelected ? gap->first :
''', '''            const std::int64_t selectedStart = pairReserveSelected ? gap->first :
''')
(root / 'pair_class_reserve.cpp').write_text(pair_reserve)

new_split = '''        bool pairSplitSelected = false;
        const int predictedNext = predictNextLength(length);
        const int predictedSecond = predictedNext > 0
            ? predictNextLength(predictedNext) : 0;
        const int pairReserve = predictedNext + predictedSecond;
        if (gap != freeByStart.end() && predictedNext > 0 && predictedSecond > 0) {
            std::int64_t slack = gap->second - gap->first - length;
            if (slack < pairReserve) {
                StartIter reserve = smallestGapAtLeast(length + pairReserve, sizeCohort);
                if (reserve != freeByStart.end()) {
                    const std::int64_t reserveSlack = reserve->second - reserve->first - length;
                    if (reserveSlack <= slack + kMaxReservePenalty) {
                        gap = reserve;
                        slack = reserveSlack;
                    }
                }
            }
            if (slack >= pairReserve) pairSplitSelected = true;
        }
'''
pair_split = base.replace(old, new_split)
pair_split = pair_split.replace('''            const std::int64_t selectedStart = transitionReserveSelected ? gap->first :
                chooseGapWithRollout(length, highSide, sizeCohort, gap);
            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);
''', '''            if (pairSplitSelected) {
                start = consumeAtOffset(gap, length, predictedNext);
            } else {
                const std::int64_t selectedStart =
                    chooseGapWithRollout(length, highSide, sizeCohort, gap);
                if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
                start = consumeAtSide(gap, length, highSide);
            }
''')
assert pair_split != base
anchor = '''    std::int64_t consumeAtSide(StartIter it, int length, bool highSide) {
'''
helper = '''    std::int64_t consumeAtOffset(StartIter it, int length, int leftGapLength) {
        const std::int64_t start = it->first;
        const std::int64_t end = it->second;
        const int cohort = gapCohort.at(start);
        const std::int64_t placement = start + leftGapLength;
        eraseGap(it);
        if (start < placement) addFreeGap(start, placement, cohort);
        const std::int64_t placementEnd = placement + length;
        if (placementEnd < end) addFreeGap(placementEnd, end, cohort);
        return placement;
    }

'''
assert pair_split.count(anchor) == 1
pair_split = pair_split.replace(anchor, helper + anchor)
(root / 'pair_class_split.cpp').write_text(pair_split)
