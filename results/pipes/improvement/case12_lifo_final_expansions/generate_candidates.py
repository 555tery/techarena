from pathlib import Path

BASE = Path("results/pipes/improvement/pid_lane_run48_factorial/sources/pid_run46.cpp")
OUT = Path("results/pipes/improvement/case12_lifo_final_expansions/source")
source = BASE.read_text()

helper_anchor = "struct SimPipe {\n"
helper = """constexpr std::size_t kRecentDeleteWindow = 64;
constexpr std::size_t kRecentDeleteMin = 24;
constexpr int kRecentLifoRankPermille = 200;
constexpr std::size_t kRecentLifoSharePercent = 70;

bool recentLifoSignal(const std::deque<int>& ranks) {
    if (ranks.size() < kRecentDeleteMin) return false;
    std::size_t nearNewest = 0;
    for (const int rank : ranks) {
        if (rank <= kRecentLifoRankPermille) ++nearNewest;
    }
    return nearNewest * 100 >= ranks.size() * kRecentLifoSharePercent;
}

"""
assert source.count(helper_anchor) == 1
source = source.replace(helper_anchor, helper + helper_anchor)

# Track only already-observed removal ranks, and carry the same feature into MC.
assert source.count("    std::deque<int> recentLengths;\n") == 2
source = source.replace(
    "    std::deque<int> recentLengths;\n",
    "    std::deque<int> recentLengths;\n    std::deque<int> recentDeleteRanks;\n",
)

rollout_remove_anchor = """        active.erase(active.begin() + static_cast<std::ptrdiff_t>(index));
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);
"""
rollout_remove_new = """        active.erase(active.begin() + static_cast<std::ptrdiff_t>(index));
        recentDeleteRanks.push_back(rankFromNewestPermille);
        if (recentDeleteRanks.size() > kRecentDeleteWindow) recentDeleteRanks.pop_front();
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);
"""
assert source.count(rollout_remove_anchor) == 1
source = source.replace(rollout_remove_anchor, rollout_remove_new)

record_anchor = """    void recordObservation(const Observation& event) {
        observedHistory.push_back(event);
        if (observedHistory.size() > kMcHistory) observedHistory.pop_front();
    }
"""
record_new = """    void recordObservation(const Observation& event) {
        observedHistory.push_back(event);
        if (observedHistory.size() > kMcHistory) observedHistory.pop_front();
        if (event.kind < 0) {
            recentDeleteRanks.push_back(event.value);
            if (recentDeleteRanks.size() > kRecentDeleteWindow) recentDeleteRanks.pop_front();
        }
    }
"""
assert source.count(record_anchor) == 1
source = source.replace(record_anchor, record_new)

copy_anchor = """        state.recentLengths = recentLengths;
        state.recentFrequency = recentFrequency;
"""
copy_new = """        state.recentLengths = recentLengths;
        state.recentDeleteRanks = recentDeleteRanks;
        state.recentFrequency = recentFrequency;
"""
assert source.count(copy_anchor) == 1
source = source.replace(copy_anchor, copy_new)

# Build one causal high-side variant. It uses the current rolling removal-rank signal.
high = source
rollout_side_anchor = """        const bool highSide = runLeftActive
            ? ((nextPid & 1) == 0)
            : (alternatingDeleteMode
                ? ((nextPid & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));
"""
rollout_side_new = """        bool highSide = runLeftActive
            ? ((nextPid & 1) == 0)
            : (alternatingDeleteMode
                ? ((nextPid & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));
        if (recentLifoSignal(recentDeleteRanks)) highSide = true;
"""
assert high.count(rollout_side_anchor) == 1
high = high.replace(rollout_side_anchor, rollout_side_new)
allocator_side_anchor = """        const bool highSide = runLeftActive
            ? ((pipes.size() & 1U) == 0U)
            : (alternatingDeleteMode
                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));
"""
allocator_side_new = """        bool highSide = runLeftActive
            ? ((pipes.size() & 1U) == 0U)
            : (alternatingDeleteMode
                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)
                : (parityCohortMode
                    ? sizeCohort == 0
                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));
        if (recentLifoSignal(recentDeleteRanks)) highSide = true;
"""
assert high.count(allocator_side_anchor) == 1
high = high.replace(allocator_side_anchor, allocator_side_new)
(OUT / "lifo_high_side.cpp").write_text(high)

# Build an independent causal largest-fit variant under the same LIFO signal.
largest = source
rollout_score_anchor = """            const std::int64_t score = fitScore(gapLength, length);
            if (!found || score < bestScore ||
"""
rollout_score_new = """            const std::int64_t score = recentLifoSignal(recentDeleteRanks)
                ? -gapLength : fitScore(gapLength, length);
            if (!found || score < bestScore ||
"""
assert largest.count(rollout_score_anchor) == 1
largest = largest.replace(rollout_score_anchor, rollout_score_new)

live_best_anchor = """        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (recentLengths.empty()) return freeByStart.find(it->second);

        const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
"""
live_best_new = """        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (recentLifoSignal(recentDeleteRanks)) {
            StartIter largest = freeByStart.end();
            std::int64_t largestLength = -1;
            for (; it != gaps.end(); ++it) {
                const std::int64_t gapLength = it->first;
                if (gapLength > largestLength ||
                    (gapLength == largestLength && largest != freeByStart.end() &&
                     ((highSide && it->second > largest->first) ||
                      (!highSide && it->second < largest->first)))) {
                    largestLength = gapLength;
                    largest = freeByStart.find(it->second);
                }
            }
            return largest;
        }
        if (recentLengths.empty()) return freeByStart.find(it->second);

        const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
"""
assert largest.count(live_best_anchor) == 1
largest = largest.replace(live_best_anchor, live_best_new)

candidate_anchor = """            const std::int64_t slack = gapLength - length;
            if (slack > 40) break;
            candidates.push_back(GapCandidate{it->second, scoreGap(gapLength, length)});
"""
candidate_new = """            const std::int64_t slack = gapLength - length;
            const bool lifoLargeGap = recentLifoSignal(recentDeleteRanks);
            if (!lifoLargeGap && slack > 40) break;
            const std::int64_t score = lifoLargeGap ? -gapLength : scoreGap(gapLength, length);
            candidates.push_back(GapCandidate{it->second, score});
"""
assert largest.count(candidate_anchor) == 1
largest = largest.replace(candidate_anchor, candidate_new)
(OUT / "lifo_largest_gap.cpp").write_text(largest)

# Build a third, final causal contrast: under the same LIFO signal, use ordinary
# smallest-fit rather than the adaptive history-weighted gap score.
smallest = source
smallest_rollout_score_anchor = """            const std::int64_t score = fitScore(gapLength, length);
            if (!found || score < bestScore ||
"""
smallest_rollout_score_new = """            const std::int64_t score = recentLifoSignal(recentDeleteRanks)
                ? (gapLength - length) : fitScore(gapLength, length);
            if (!found || score < bestScore ||
"""
assert smallest.count(smallest_rollout_score_anchor) == 1
smallest = smallest.replace(smallest_rollout_score_anchor, smallest_rollout_score_new)

smallest_live_anchor = """        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (recentLengths.empty()) return freeByStart.find(it->second);

        const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
"""
smallest_live_new = """        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (recentLifoSignal(recentDeleteRanks)) {
            const std::int64_t smallestLength = it->first;
            StartIter smallest = freeByStart.end();
            while (it != gaps.end() && it->first == smallestLength) {
                if (smallest == freeByStart.end() ||
                    (highSide && it->second > smallest->first) ||
                    (!highSide && it->second < smallest->first)) {
                    smallest = freeByStart.find(it->second);
                }
                ++it;
            }
            return smallest;
        }
        if (recentLengths.empty()) return freeByStart.find(it->second);

        const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
"""
assert smallest.count(smallest_live_anchor) == 1
smallest = smallest.replace(smallest_live_anchor, smallest_live_new)

smallest_candidate_anchor = """            const std::int64_t slack = gapLength - length;
            if (slack > 40) break;
            candidates.push_back(GapCandidate{it->second, scoreGap(gapLength, length)});
"""
smallest_candidate_new = """            const std::int64_t slack = gapLength - length;
            if (slack > 40) break;
            const std::int64_t score = recentLifoSignal(recentDeleteRanks)
                ? slack : scoreGap(gapLength, length);
            candidates.push_back(GapCandidate{it->second, score});
"""
assert smallest.count(smallest_candidate_anchor) == 1
smallest = smallest.replace(smallest_candidate_anchor, smallest_candidate_new)
(OUT / "lifo_smallest_fit.cpp").write_text(smallest)
