from pathlib import Path


root = Path("results/pipes/improvement/case15_fast_candidates/phase_micro")
source = Path("results/pipes/improvement/archive_mix_screen/gated_causal/pid46_rearm_geometric_gate1.cpp").read_text()

place_anchor = """        auto gap = bestFittingGap(length, highSide, sizeCohort);
        if (gap != freeByStart.end()) {
"""
place_replacement = """        auto gap = bestFittingGap(length, highSide, sizeCohort);
        if (gap != freeByStart.end() && shouldPreserveLargeGap(length)) {
            const std::int64_t meanNumerator = recentSizeSum();
            const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
            const std::int64_t maxSmallGap =
                (2 * meanNumerator + historySize - 1) / historySize - 1;
            StartIter smallGap = smallestFitUpTo(length, highSide, sizeCohort, maxSmallGap);
            if (smallGap != freeByStart.end() &&
                smallGap->second - smallGap->first < gap->second - gap->first) {
                gap = smallGap;
            }
        }
        if (gap != freeByStart.end()) {
"""

helper_anchor = """    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {
"""
helpers = """    std::int64_t recentSizeSum() const {
        std::int64_t sum = 0;
        for (int size = 1; size <= 40; ++size) {
            sum += static_cast<std::int64_t>(size) *
                recentFrequency[static_cast<std::size_t>(size)];
        }
        return sum;
    }

    bool shouldPreserveLargeGap(int length) const {
        if (recentLengths.size() < 128) return false;
        const std::int64_t count = static_cast<std::int64_t>(recentLengths.size());
        const std::int64_t sum = recentSizeSum();
        // During a low-mean regime, do not consume a gap at least twice the
        // observed mean for a request no larger than that mean.
        return sum <= 10 * count && static_cast<std::int64_t>(length) * count <= sum;
    }

    StartIter smallestFitInSetUpTo(
        const std::set<std::pair<std::int64_t, std::int64_t>>& gaps,
        int length, std::int64_t maxGapLength, bool highSide) {
        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end() || it->first > maxGapLength) return freeByStart.end();
        const std::int64_t smallestLength = it->first;
        StartIter best = freeByStart.end();
        while (it != gaps.end() && it->first == smallestLength) {
            if (best == freeByStart.end() ||
                (highSide && it->second > best->first) ||
                (!highSide && it->second < best->first)) {
                best = freeByStart.find(it->second);
            }
            ++it;
        }
        return best;
    }

    StartIter smallestFitUpTo(int length, bool highSide, int sizeCohort,
                              std::int64_t maxGapLength) {
        if (parityCohortMode) {
            const auto& preferred = freeBySizeCohort[static_cast<std::size_t>(sizeCohort)];
            StartIter fit = smallestFitInSetUpTo(preferred, length, maxGapLength, highSide);
            if (fit != freeByStart.end()) return fit;
            return smallestFitInSetUpTo(freeBySizeShared, length, maxGapLength, highSide);
        }
        return smallestFitInSetUpTo(freeBySize, length, maxGapLength, highSide);
    }

"""

assert source.count(place_anchor) == 1
assert source.count(helper_anchor) == 1
source = source.replace(place_anchor, place_replacement).replace(helper_anchor, helpers + helper_anchor)
(root / "source/preserve_large_gaps_on_champion.cpp").write_text(source)

