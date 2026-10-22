from pathlib import Path


ROOT = Path("results/pipes/improvement/case15_fast_candidates/phase_micro")
BASE = Path("results/pipes/final/solution.cpp").read_text()
ROOT.joinpath("source").mkdir(parents=True, exist_ok=True)

field_anchor = """    std::size_t mcRolloutsRun = 0;
"""
fields = field_anchor + """    int phaseDirection = 0;  // +1: recent sizes rose; -1: they fell.
"""

place_anchor = """        std::int64_t start = -1;
        auto gap = bestFittingGap(length, highSide, sizeCohort);
"""
place_replacement = """        const int detectedDirection = detectRecentSizeShift(length);
        if (detectedDirection != 0) phaseDirection = detectedDirection;
        std::int64_t start = -1;
        auto gap = bestFittingGap(length, highSide, sizeCohort);
"""

helper_anchor = """    bool hasSameLengthRecentRun(int length) const {
"""
helper = """    int detectRecentSizeShift(int currentLength) const {
        constexpr std::size_t kRecentWindow = 16;
        constexpr std::size_t kReferenceWindow = 256;
        if (recentLengths.size() < kRecentWindow + kReferenceWindow) return 0;

        auto it = recentLengths.rbegin();
        std::int64_t recentSum = currentLength;
        for (std::size_t i = 1; i < kRecentWindow; ++i, ++it) {
            recentSum += *it;
        }
        std::int64_t referenceSum = 0;
        for (std::size_t i = 0; i < kReferenceWindow; ++i, ++it) {
            referenceSum += *it;
        }

        // Require a large mean shift so a few noisy requests do not switch policy.
        if (recentSum * 64 > referenceSum * 7) return 1;
        if (recentSum * 28 < referenceSum) return -1;
        return 0;
    }

"""

assert BASE.count(field_anchor) == 1
assert BASE.count(place_anchor) == 1
assert BASE.count(helper_anchor) == 2

common = BASE.replace(field_anchor, fields).replace(place_anchor, place_replacement)
helper_pos = common.rfind(helper_anchor)
common = common[:helper_pos] + helper + common[helper_pos:]

high_address = common.replace(
    """        auto gap = bestFittingGap(length, highSide, sizeCohort);
""",
    """        const bool tieHighSide = phaseDirection == 0 ? highSide : phaseDirection > 0;
        auto gap = bestFittingGap(length, tieHighSide, sizeCohort);
""",
    1,
)
(ROOT / "source/phase_high_address_tie.cpp").write_text(high_address)

small_gap_anchor = """            if (score < bestScore ||
                (score == bestScore && best != freeByStart.end() &&
                 ((highSide && it->second > best->first) ||
                  (!highSide && it->second < best->first)))) {
                bestScore = score;
                best = freeByStart.find(it->second);
            }
"""
small_gap_replacement = """            bool betterTie = false;
            if (score == bestScore && best != freeByStart.end()) {
                if (phaseDirection == 0) {
                    betterTie = (highSide && it->second > best->first) ||
                        (!highSide && it->second < best->first);
                } else {
                    const std::int64_t bestLength =
                        freeByStart.at(best->first) - best->first;
                    betterTie = gapLength < bestLength ||
                        (gapLength == bestLength &&
                         ((phaseDirection > 0 && it->second > best->first) ||
                          (phaseDirection < 0 && it->second < best->first)));
                }
            }
            if (score < bestScore || betterTie) {
                bestScore = score;
                best = freeByStart.find(it->second);
            }
"""
assert common.count(small_gap_anchor) == 1
small_gap = common.replace(small_gap_anchor, small_gap_replacement)
(ROOT / "source/phase_small_gap_tie.cpp").write_text(small_gap)

