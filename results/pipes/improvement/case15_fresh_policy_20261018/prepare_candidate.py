from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
BASELINE = ROOT / "results/pipes/improvement/case15_expansion_edge_cf/source/lifo_young_offset_scale_gt4096.cpp"
OUTPUT = Path(__file__).resolve().parent / "source/coalescence_option_value.cpp"

source = BASELINE.read_text()

def replace_once(old: str, new: str) -> None:
    global source
    if source.count(old) != 1:
        raise RuntimeError(f"expected one occurrence, got {source.count(old)}: {old[:100]!r}")
    source = source.replace(old, new, 1)


replace_once(
    "    std::map<std::int64_t, int> activeByEnd;\n",
    "    std::map<std::int64_t, int> activeByEnd;\n"
    "    std::map<std::int64_t, int> activeByStart;\n",
)
replace_once(
    "    std::uint64_t expansionGatePasses = 0;\n",
    "    std::uint64_t expansionGatePasses = 0;\n"
    "    std::uint64_t coalescenceChecks = 0;\n"
    "    std::uint64_t coalescenceProtected = 0;\n"
    "    std::uint64_t coalescenceSkips = 0;\n",
)
replace_once(
    "\n            activeByEnd.emplace(start + length, pid);\n",
    "\n            activeByEnd.emplace(start + length, pid);\n"
    "            activeByStart.emplace(start, pid);\n",
)
replace_once(
    "        auto gap = bestFittingGap(length, highSide, sizeCohort);\n"
    "        if (gap != freeByStart.end()) {\n",
    "        auto gap = bestFittingGap(length, highSide, sizeCohort);\n"
    "        bool coalescenceOverride = false;\n"
    "        if (gap != freeByStart.end()) {\n"
    "            coalescenceOverride = divertFromSoonCoalescingGap(\n"
    "                gap, length, highSide, sizeCohort);\n"
    "        }\n"
    "        if (gap != freeByStart.end()) {\n",
)
replace_once(
    "            const std::int64_t selectedStart = additiveNextAlignment\n"
    "                ? gap->first\n"
    "                : chooseGapWithRollout(length, highSide, sizeCohort, gap);\n",
    "            const std::int64_t selectedStart = additiveNextAlignment || coalescenceOverride\n"
    "                ? gap->first\n"
    "                : chooseGapWithRollout(length, highSide, sizeCohort, gap);\n",
)
replace_once(
    "\n        activeByEnd.emplace(start + length, pid);\n",
    "\n        activeByEnd.emplace(start + length, pid);\n"
    "        activeByStart.emplace(start, pid);\n",
)
replace_once(
    "        activeByEnd.erase(pipe.start + pipe.length);\n",
    "        activeByEnd.erase(pipe.start + pipe.length);\n"
    "        activeByStart.erase(pipe.start);\n",
)

anchor = "    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {\n"
mechanism = r'''    int recentLifoSharePermille() const {
        if (activePipeCount < 128 || recentDeleteRanksPermille.size() < 48) return 0;
        std::size_t newestFivePercent = 0;
        for (int rank : recentDeleteRanksPermille) {
            if (rank <= 50) ++newestFivePercent;
        }
        const std::size_t count = recentDeleteRanksPermille.size();
        if (newestFivePercent * 100 < count * 80) return 0;
        return static_cast<int>(newestFivePercent * 1000 / count);
    }

    std::int64_t coalescenceOptionPenalty(std::int64_t gapStart,
                                         std::int64_t gapEnd) const {
        const int lifoShare = recentLifoSharePermille();
        if (lifoShare == 0) return 0;
        const std::int64_t gapLength = gapEnd - gapStart;
        int bestPenalty = 0;
        const auto inspectNeighbor = [&](int pid) {
            if (rankFromNewestPermille(pid) > 50) return;
            const int neighborLength = pipes[static_cast<std::size_t>(pid)].length;
            const std::int64_t mergedCapacity = std::min<std::int64_t>(
                40, gapLength + neighborLength);
            int recentRequestsUnlockedByMerge = 0;
            for (std::int64_t request = gapLength + 1;
                 request <= mergedCapacity; ++request) {
                recentRequestsUnlockedByMerge +=
                    recentFrequency[static_cast<std::size_t>(request)];
            }
            // Value the chance that this exact boundary pipe is deleted soon:
            // observed newest-5% deletion share times its relative position
            // within that cohort. This only protects capacity unlocked by the
            // boundary's removal; it is not a generic large-gap reserve.
            const int distanceWeight = 50 - rankFromNewestPermille(pid);
            const std::int64_t penalty =
                static_cast<std::int64_t>(kUnfitPenaltyScale) *
                recentRequestsUnlockedByMerge * lifoShare * distanceWeight /
                (1000 * 50);
            bestPenalty = std::max(bestPenalty, static_cast<int>(penalty));
        };

        const auto left = activeByEnd.find(gapStart);
        if (left != activeByEnd.end()) inspectNeighbor(left->second);
        const auto right = activeByStart.find(gapEnd);
        if (right != activeByStart.end()) inspectNeighbor(right->second);
        return bestPenalty;
    }

    bool divertFromSoonCoalescingGap(StartIter& selected, int length,
                                     bool highSide, int sizeCohort) {
        bool diverted = false;
        for (int attempt = 0; attempt < 2; ++attempt) {
            ++coalescenceChecks;
            const std::int64_t penalty =
                coalescenceOptionPenalty(selected->first, selected->second);
            if (penalty <= 0) break;
            ++coalescenceProtected;
            StartIter alternative = bestFittingGapExcept(
                length, highSide, sizeCohort, selected->first);
            if (alternative == freeByStart.end()) break;
            const std::int64_t selectedCost =
                scoreGap(selected->second - selected->first, length);
            const std::int64_t alternativeCost =
                scoreGap(alternative->second - alternative->first, length);
            if (alternativeCost > selectedCost + penalty) break;
            selected = alternative;
            ++coalescenceSkips;
            diverted = true;
        }
        return diverted;
    }

    StartIter bestFittingGapExcept(int length, bool highSide, int sizeCohort,
                                   std::int64_t excludedStart) {
        if (parityCohortMode) {
            const auto& cohortGaps = freeBySizeCohort[static_cast<std::size_t>(sizeCohort)];
            StartIter preferred = bestFittingGapFromSetExcept(
                cohortGaps, length, highSide, excludedStart);
            if (preferred != freeByStart.end()) return preferred;
            return bestFittingGapFromSetExcept(
                freeBySizeShared, length, highSide, excludedStart);
        }
        return bestFittingGapFromSetExcept(freeBySize, length, highSide, excludedStart);
    }

    StartIter bestFittingGapFromSetExcept(
        const std::set<std::pair<std::int64_t, std::int64_t>>& gaps,
        int length, bool highSide, std::int64_t excludedStart) {
        auto it = gaps.lower_bound({length, 0});
        StartIter best = freeByStart.end();
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        while (it != gaps.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            if (slack > 40) break;
            const auto groupEnd = gaps.upper_bound(
                {gapLength, std::numeric_limits<std::int64_t>::max()});
            auto candidate = highSide ? std::prev(groupEnd) : it;
            if (candidate->second == excludedStart) {
                if (highSide) {
                    if (candidate == it) candidate = groupEnd;
                    else --candidate;
                } else {
                    ++candidate;
                }
            }
            if (candidate != groupEnd && candidate->first == gapLength) {
                const std::int64_t score = scoreGap(gapLength, length);
                if (score < bestScore ||
                    (score == bestScore && best != freeByStart.end() &&
                     ((highSide && candidate->second > best->first) ||
                      (!highSide && candidate->second < best->first)))) {
                    bestScore = score;
                    best = freeByStart.find(candidate->second);
                }
            }
            it = groupEnd;
        }
        return best;
    }

'''
if source.count(anchor) != 1:
    raise RuntimeError("best-fitting insertion anchor not unique")
source = source.replace(anchor, mechanism + anchor, 1)

replace_once(
    '                      << " expansion_gate_passes=" << allocator.expansionGatePasses << \'\\n\';\n',
    '                      << " expansion_gate_passes=" << allocator.expansionGatePasses\n'
    '                      << " coalescence_checks=" << allocator.coalescenceChecks\n'
    '                      << " coalescence_protected=" << allocator.coalescenceProtected\n'
    '                      << " coalescence_skips=" << allocator.coalescenceSkips << \'\\n\';\n',
)

OUTPUT.write_text(source)
print(OUTPUT)
