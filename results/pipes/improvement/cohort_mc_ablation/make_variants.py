from pathlib import Path

BASE = Path('results/pipes/improvement/cohort_mc_ablation/src/base.cpp').read_text()
OUT = Path('results/pipes/improvement/cohort_mc_ablation/src')

# 1. Let the bounded MC compare cohort-owned and shared free spans in one pool.
source = BASE
old_top_setup = '''        const std::set<std::pair<std::int64_t, std::int64_t>>* index = &freeBySize;
        if (parityCohortMode) {
            const auto& preferred = freeBySizeCohort[static_cast<std::size_t>(sizeCohort)];
            auto it = preferred.lower_bound({length, 0});
            if (it != preferred.end()) index = &preferred;
            else index = &freeBySizeShared;
        }
'''
assert source.count(old_top_setup) == 1
source = source.replace(old_top_setup, '''        const std::set<std::pair<std::int64_t, std::int64_t>>* index = &freeBySize;
''')
old_loop = '''            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            if (slack > 40) break;
            candidates.push_back(GapCandidate{it->second, scoreGap(gapLength, length)});
            ++it;
'''
new_loop = '''            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            if (slack > 40) break;
            if (parityCohortMode) {
                const int cohort = gapCohort.at(it->second);
                if (cohort != sizeCohort && cohort != -1) {
                    ++it;
                    continue;
                }
            }
            candidates.push_back(GapCandidate{it->second, scoreGap(gapLength, length)});
            ++it;
'''
assert source.count(old_loop) == 1
source = source.replace(old_loop,new_loop)
old_has = '''        bool hasPreferred = false;
        if (parityCohortMode) {
            for (const auto& [start, gap] : gaps) {
                (void)start;
                if (gap.end - start >= length && gap.cohort == sizeCohort) {
                    hasPreferred = true;
                    break;
                }
            }
        }
'''
assert source.count(old_has) == 1
source = source.replace(old_has,'')
old_filter = '''            if (parityCohortMode &&
                (hasPreferred ? gap.cohort != sizeCohort : gap.cohort >= 0)) continue;
'''
new_filter = '''            if (parityCohortMode && gap.cohort != sizeCohort && gap.cohort != -1) continue;
'''
assert source.count(old_filter) == 1
source = source.replace(old_filter,new_filter)
old_live_mode = '''        if (parityCohortMode) {
            const auto& cohortGaps = freeBySizeCohort[static_cast<std::size_t>(sizeCohort)];
            StartIter preferred = bestFittingGapFromSet(cohortGaps, length, highSide);
            if (preferred != freeByStart.end()) return preferred;
            StartIter shared = bestFittingGapFromSet(freeBySizeShared, length, highSide);
            if (shared != freeByStart.end()) return shared;
            return freeByStart.end();
        }
        return bestFittingGapFromSet(freeBySize, length, highSide);
'''
new_live_mode = '''        if (parityCohortMode) {
            return bestFittingGapFromSet(freeBySize, length, highSide, sizeCohort);
        }
        return bestFittingGapFromSet(freeBySize, length, highSide);
'''
assert source.count(old_live_mode) == 1
source=source.replace(old_live_mode,new_live_mode)
old_signature='''        bool highSide) {
        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (recentLengths.empty()) return freeByStart.find(it->second);
'''
new_signature='''        bool highSide,
        int allowedCohort = -2) {
        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (recentLengths.empty()) {
            while (it != gaps.end()) {
                const int cohort = gapCohort.at(it->second);
                if (allowedCohort < 0 || cohort == allowedCohort || cohort == -1) {
                    return freeByStart.find(it->second);
                }
                ++it;
            }
            return freeByStart.end();
        }
'''
assert source.count(old_signature)==1
source=source.replace(old_signature,new_signature)
old_iter = '''        while (it != gaps.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            std::int64_t score = slack * historySize;
'''
new_iter = '''        while (it != gaps.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            const int cohort = gapCohort.at(it->second);
            if (allowedCohort >= 0 && cohort != allowedCohort && cohort != -1) {
                ++it;
                continue;
            }
            std::int64_t score = slack * historySize;
'''
assert source.count(old_iter)==1
source=source.replace(old_iter,new_iter)
# Replace the old post-candidate slack break so a filtered fit helper can safely continue.
old_post = '''            if (slack > 40) break;
            const std::int64_t currentSize = it->first;
            it = gaps.upper_bound({currentSize, std::numeric_limits<std::int64_t>::max()});
'''
new_post = '''            if (slack > 40) break;
            const std::int64_t currentSize = it->first;
            it = gaps.upper_bound({currentSize, std::numeric_limits<std::int64_t>::max()});
'''
assert source.count(old_post)==1
source=source.replace(old_post,new_post)
(OUT/'shared_mc_pool.cpp').write_text(source)

# 2. Reverse the side assigned to each parity cohort in both live and rollout policies.
source = BASE
old = '''? sizeCohort == 0
            : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length)));'''
assert source.count(old)==2
source=source.replace(old,'''? sizeCohort == 1
            : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length)));''')
(OUT/'flip_cohort_edge.cpp').write_text(source)

# 3. On the expansion fallback only, consume a foreign-owned wilderness tail instead of
# preserving it and digging a separate span. Relabel any mixed old/new remainder shared.
old_rollout = '''            int tailCohort = parityCohortMode ? sizeCohort : -1;
            bool preserveForeignTail = false;
            if (parityCohortMode && tail != gaps.end()) {
                tailCohort = tail->second.cohort;
                preserveForeignTail = tailCohort >= 0 && tailCohort != sizeCohort;
                if (preserveForeignTail) tailCohort = sizeCohort;
            }
            const std::int64_t tailStart =
                tail == gaps.end() || preserveForeignTail ? trenchLength : tail->first;
            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            const std::int64_t digs = (deficit + kDigLength - 1) / kDigLength;
            trenchLength += digs * kDigLength;
            if (tail != gaps.end() && !preserveForeignTail) gaps.erase(tail);
            if (parityCohortMode && highSide && !preserveForeignTail) {
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
new_rollout = '''            const std::int64_t oldTrenchLength = trenchLength;
            int tailCohort = parityCohortMode ? sizeCohort : -1;
            bool foreignTail = false;
            if (parityCohortMode && tail != gaps.end()) {
                tailCohort = tail->second.cohort;
                foreignTail = tailCohort >= 0 && tailCohort != sizeCohort;
            }
            const std::int64_t tailStart = tail == gaps.end() ? trenchLength : tail->first;
            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            const std::int64_t digs = (deficit + kDigLength - 1) / kDigLength;
            trenchLength += digs * kDigLength;
            if (tail != gaps.end()) gaps.erase(tail);
            if (parityCohortMode && highSide) {
                start = trenchLength - length;
                if (tailStart < start) {
                    int remainderCohort = tailCohort;
                    if (foreignTail && tailStart < oldTrenchLength &&
                        start > oldTrenchLength) remainderCohort = -1;
                    addFreeGap(tailStart, start, remainderCohort);
                }
            } else {
                start = tailStart;
                const std::int64_t remainderStart = start + length;
                if (remainderStart < trenchLength) {
                    int remainderCohort = tailCohort;
                    if (foreignTail && digs > 0) {
                        remainderCohort = remainderStart < oldTrenchLength ? -1 : sizeCohort;
                    }
                    addFreeGap(remainderStart, trenchLength, remainderCohort);
                }
            }
'''
assert source.count(old_rollout)==1
source=source.replace(old_rollout,new_rollout)
old_live = '''            int tailCohort = parityCohortMode ? sizeCohort : -1;
            bool preserveForeignTail = false;
            if (parityCohortMode && tail != freeByStart.end()) {
                tailCohort = gapCohort.at(tail->first);
                preserveForeignTail = tailCohort >= 0 && tailCohort != sizeCohort;
                if (preserveForeignTail) tailCohort = sizeCohort;
            }
            const std::int64_t tailStart =
                tail == freeByStart.end() || preserveForeignTail
                    ? trenchLength : tail->first;
            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            digs = (deficit + kDigLength - 1) / kDigLength;

            // At most 200,000 commands can arrive. Each pipe has length at most
            // 40 m, so it can require at most two 20 m sections: total digging
            // is at most 8,000,000 m, below the 100,000,000 m contest cap.
            const std::int64_t newLength = trenchLength + digs * kDigLength;
            if (tail != freeByStart.end() && !preserveForeignTail) eraseGap(tail);
            trenchLength = newLength;
            if (parityCohortMode && highSide && !preserveForeignTail) {
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
new_live = '''            const std::int64_t oldTrenchLength = trenchLength;
            int tailCohort = parityCohortMode ? sizeCohort : -1;
            bool foreignTail = false;
            if (parityCohortMode && tail != freeByStart.end()) {
                tailCohort = gapCohort.at(tail->first);
                foreignTail = tailCohort >= 0 && tailCohort != sizeCohort;
            }
            const std::int64_t tailStart = tail == freeByStart.end() ? trenchLength : tail->first;
            const std::int64_t tailLength = trenchLength - tailStart;
            const std::int64_t deficit = std::max<std::int64_t>(0, length - tailLength);
            digs = (deficit + kDigLength - 1) / kDigLength;

            // At most 200,000 commands can arrive. Each pipe has length at most
            // 40 m, so it can require at most two 20 m sections: total digging
            // is at most 8,000,000 m, below the 100,000,000 m contest cap.
            const std::int64_t newLength = trenchLength + digs * kDigLength;
            if (tail != freeByStart.end()) eraseGap(tail);
            trenchLength = newLength;
            if (parityCohortMode && highSide) {
                start = trenchLength - length;
                if (tailStart < start) {
                    int remainderCohort = tailCohort;
                    if (foreignTail && tailStart < oldTrenchLength &&
                        start > oldTrenchLength) remainderCohort = -1;
                    addFreeGap(tailStart, start, remainderCohort);
                }
            } else {
                start = tailStart;
                const std::int64_t remainderStart = start + length;
                if (remainderStart < trenchLength) {
                    int remainderCohort = tailCohort;
                    if (foreignTail && digs > 0) {
                        remainderCohort = remainderStart < oldTrenchLength ? -1 : sizeCohort;
                    }
                    addFreeGap(remainderStart, trenchLength, remainderCohort);
                }
            }
'''
assert source.count(old_live)==1
source=source.replace(old_live,new_live)
(OUT/'reuse_foreign_tail.cpp').write_text(source)
