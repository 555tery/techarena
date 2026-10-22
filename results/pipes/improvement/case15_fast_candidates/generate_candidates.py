from pathlib import Path

root = Path('results/pipes/improvement/case15_fast_candidates')
final = Path('results/pipes/final/solution.cpp').read_text()

place_anchor = '''        auto gap = bestFittingGap(length, highSide, sizeCohort);
        if (gap != freeByStart.end()) {
            const std::int64_t selectedStart = chooseGapWithRollout(
'''
place_replacement = '''        auto gap = bestFittingGap(length, highSide, sizeCohort);
        if (gap != freeByStart.end() && gap->second == trenchLength) {
            const StartIter interior = bestFittingInteriorGap(length, highSide, sizeCohort);
            if (interior != freeByStart.end()) {
                const std::int64_t tailScore = scoreGap(gap->second - gap->first, length);
                const std::int64_t interiorScore = scoreGap(
                    interior->second - interior->first, length);
                const std::int64_t allowedExtra = TAIL_MARGIN_UNITS *
                    static_cast<std::int64_t>(recentLengths.size());
                if (interiorScore <= tailScore + allowedExtra) gap = interior;
            }
        }
        if (gap != freeByStart.end()) {
            const std::int64_t selectedStart = chooseGapWithRollout(
'''
assert final.count(place_anchor) == 1

interior_method = '''
    StartIter bestFittingInteriorFromSet(
        const std::set<std::pair<std::int64_t, std::int64_t>>& gaps,
        int length,
        bool highSide) {
        auto it = gaps.lower_bound({length, 0});
        StartIter best = freeByStart.end();
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        while (it != gaps.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            if (slack > 40) break;
            auto candidate = freeByStart.find(it->second);
            if (candidate != freeByStart.end() && candidate->second != trenchLength) {
                const std::int64_t score = scoreGap(gapLength, length);
                if (score < bestScore || (score == bestScore && best != freeByStart.end() &&
                    ((highSide && candidate->first > best->first) ||
                     (!highSide && candidate->first < best->first)))) {
                    bestScore = score;
                    best = candidate;
                }
            }
            ++it;
        }
        return best;
    }

    StartIter bestFittingInteriorGap(int length, bool highSide, int sizeCohort) {
        if (parityCohortMode) {
            const auto& cohortGaps = freeBySizeCohort[static_cast<std::size_t>(sizeCohort)];
            StartIter preferred = bestFittingInteriorFromSet(cohortGaps, length, highSide);
            if (preferred != freeByStart.end()) return preferred;
            return bestFittingInteriorFromSet(freeBySizeShared, length, highSide);
        }
        return bestFittingInteriorFromSet(freeBySize, length, highSide);
    }
'''
method_anchor = '''    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {
'''
assert final.count(method_anchor) == 1
for margin, name in [(0, 'tail_tie'), (20, 'tail_20m')]:
    code = final.replace(place_anchor, place_replacement).replace(method_anchor, interior_method + '\n' + method_anchor)
    code = code.replace('TAIL_MARGIN_UNITS', str(margin))
    (root / 'source' / f'{name}.cpp').write_text(code)

age_source = Path('results/pipes/improvement/case15_age_tiebreak/age_tiebreak.cpp').read_text()
age_old = '''    std::int64_t oldestSameSizeStart(const AgeIndex& ageIndex,
                                    std::int64_t gapLength,
                                    bool highSide) const {
        const auto bin = ageIndex.find(gapLength);
        if (bin == ageIndex.end() || bin->second.empty())
            throw std::runtime_error("gap age index is inconsistent");
        const std::size_t oldestBirth = bin->second.begin()->first;
        const auto first = bin->second.lower_bound({oldestBirth,
            std::numeric_limits<std::int64_t>::min()});
        const auto after = bin->second.upper_bound({oldestBirth,
            std::numeric_limits<std::int64_t>::max()});
        return highSide ? std::prev(after)->second : first->second;
    }
'''
age_new = '''    bool useFragmentedAgeTieBreak() const {
        return activePipeCount >= 20000 && freeByStart.size() >= 256;
    }

    std::int64_t oldestSameSizeStart(
        const AgeIndex& ageIndex,
        const std::set<std::pair<std::int64_t, std::int64_t>>& gaps,
        std::int64_t gapLength,
        bool highSide) const {
        const auto bin = ageIndex.find(gapLength);
        if (bin == ageIndex.end() || bin->second.empty())
            throw std::runtime_error("gap age index is inconsistent");
        if (!useFragmentedAgeTieBreak()) {
            auto first = gaps.lower_bound({gapLength,
                std::numeric_limits<std::int64_t>::min()});
            auto after = gaps.upper_bound({gapLength,
                std::numeric_limits<std::int64_t>::max()});
            return highSide ? std::prev(after)->second : first->second;
        }
        const std::size_t oldestBirth = bin->second.begin()->first;
        const auto first = bin->second.lower_bound({oldestBirth,
            std::numeric_limits<std::int64_t>::min()});
        const auto after = bin->second.upper_bound({oldestBirth,
            std::numeric_limits<std::int64_t>::max()});
        return highSide ? std::prev(after)->second : first->second;
    }
'''
assert age_source.count(age_old) == 1
age_source = age_source.replace(age_old, age_new)
age_source = age_source.replace('oldestSameSizeStart(ageIndex, it->first, highSide)',
                                'oldestSameSizeStart(ageIndex, gaps, it->first, highSide)')
age_source = age_source.replace('oldestSameSizeStart(ageIndex, gapLength, highSide)',
                                'oldestSameSizeStart(ageIndex, gaps, gapLength, highSide)')
(root / 'source' / 'age_tie_fragmented_gate.cpp').write_text(age_source)

# The fourth candidate tests whether early rollout choices are helping on case 15.
(root / 'source' / 'mc_disabled.cpp').write_text(final)
