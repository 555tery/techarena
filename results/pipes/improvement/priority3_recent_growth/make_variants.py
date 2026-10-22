from pathlib import Path

ROOT = Path(__file__).resolve().parent
baseline = (ROOT / "source" / "baseline.cpp").read_text()

old_budget = "constexpr std::size_t kMcDecisionBudget = 32;"
assert baseline.count(old_budget) == 1
(ROOT / "source" / "mc_budget64.cpp").write_text(
    baseline.replace(old_budget, "constexpr std::size_t kMcDecisionBudget = 64;")
)

potential = baseline
potential = potential.replace(
    """struct GapCandidate {
    std::int64_t start = 0;
    std::int64_t score = 0;
};""",
    """struct GapCandidate {
    std::int64_t start = 0;
    std::int64_t score = 0;
    std::int64_t residualPotential = 0;
};""",
)
old_fit = """    std::int64_t fitScore(std::int64_t gapLength, int length) const {
        const std::int64_t slack = gapLength - static_cast<std::int64_t>(length);
        std::int64_t score = slack * static_cast<std::int64_t>(recentLengths.size());
        if (slack > 0 && slack <= 40) {
            int misses = 0;
            for (int request = static_cast<int>(slack) + 1; request <= 40; ++request) {
                misses += recentFrequency[static_cast<std::size_t>(request)];
            }
            score += kUnfitPenaltyScale * misses;
        }
        return score;
    }"""
new_fit = old_fit + """

    std::int64_t residualPotential(std::int64_t slack) const {
        if (slack <= 0) return 0;
        std::int64_t value = 0;
        for (int request = 1; request <= 40; ++request) {
            value += static_cast<std::int64_t>(recentFrequency[static_cast<std::size_t>(request)]) *
                (slack / request);
        }
        return value;
    }"""
assert potential.count(old_fit) == 1
potential = potential.replace(old_fit, new_fit)
old_best_gap = """        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        // The real allocator indexes free spans by (length, start) and
        // evaluates only the lowest-address span for each distinct length.
        // This simulator is keyed by start, so suppress later equal-length
        // spans after seeing their first eligible (lowest-address) member."""
new_best_gap = """        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        std::int64_t bestPotential = -1;
        // The real allocator indexes free spans by (length, start) and
        // evaluates only the lowest-address span for each distinct length.
        // This simulator is keyed by start, so suppress later equal-length
        // spans after seeing their first eligible (lowest-address) member."""
assert potential.count(old_best_gap) == 1
potential = potential.replace(old_best_gap, new_best_gap)
old_best_condition = """            const std::int64_t score = fitScore(gapLength, length);
            if (!found || score < bestScore ||
                (score == bestScore &&
                 ((highSide && start > bestStart) || (!highSide && start < bestStart)))) {
                found = true;
                bestStart = start;
                bestScore = score;
            }"""
new_best_condition = """            const std::int64_t score = fitScore(gapLength, length);
            const std::int64_t potential = residualPotential(gapLength - length);
            if (!found || score < bestScore ||
                (score == bestScore &&
                 (potential > bestPotential ||
                  (potential == bestPotential &&
                   ((highSide && start > bestStart) || (!highSide && start < bestStart)))))) {
                found = true;
                bestStart = start;
                bestScore = score;
                bestPotential = potential;
            }"""
assert potential.count(old_best_condition) == 1
potential = potential.replace(old_best_condition, new_best_condition)
old_score_gap = """    std::int64_t scoreGap(std::int64_t gapLength, int length) const {
        const std::int64_t slack = gapLength - static_cast<std::int64_t>(length);
        std::int64_t score = slack * static_cast<std::int64_t>(recentLengths.size());
        if (slack > 0 && slack <= 40) {
            int misses = 0;
            for (int request = static_cast<int>(slack) + 1; request <= 40; ++request) {
                misses += recentFrequency[static_cast<std::size_t>(request)];
            }
            score += kUnfitPenaltyScale * misses;
        }
        return score;
    }"""
new_score_gap = old_score_gap + """

    std::int64_t residualPotential(std::int64_t slack) const {
        if (slack <= 0) return 0;
        std::int64_t value = 0;
        for (int request = 1; request <= 40; ++request) {
            value += static_cast<std::int64_t>(recentFrequency[static_cast<std::size_t>(request)]) *
                (slack / request);
        }
        return value;
    }"""
assert potential.count(old_score_gap) == 1
potential = potential.replace(old_score_gap, new_score_gap)
old_candidate_push = "candidates.push_back(GapCandidate{it->second, scoreGap(gapLength, length)});"
new_candidate_push = "candidates.push_back(GapCandidate{it->second, scoreGap(gapLength, length),\n+                residualPotential(gapLength - length)});"
assert potential.count(old_candidate_push) == 1
potential = potential.replace(old_candidate_push, new_candidate_push)
old_sort = """        std::sort(candidates.begin(), candidates.end(), [highSide](
            const GapCandidate& lhs, const GapCandidate& rhs) {
            if (lhs.score != rhs.score) return lhs.score < rhs.score;
            return highSide ? lhs.start > rhs.start : lhs.start < rhs.start;
        });"""
new_sort = """        std::sort(candidates.begin(), candidates.end(), [highSide](
            const GapCandidate& lhs, const GapCandidate& rhs) {
            if (lhs.score != rhs.score) return lhs.score < rhs.score;
            if (lhs.residualPotential != rhs.residualPotential) {
                return lhs.residualPotential > rhs.residualPotential;
            }
            return highSide ? lhs.start > rhs.start : lhs.start < rhs.start;
        });"""
assert potential.count(old_sort) == 1
potential = potential.replace(old_sort, new_sort)
old_alloc_score = """        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        StartIter best = freeByStart.end();
        while (it != gaps.end()) {"""
new_alloc_score = """        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        std::int64_t bestPotential = -1;
        StartIter best = freeByStart.end();
        while (it != gaps.end()) {"""
assert potential.count(old_alloc_score) == 1
potential = potential.replace(old_alloc_score, new_alloc_score)
old_alloc_condition = """            // Iteration is by size and then start, so keeping the first tie
            // implements the smaller-gap, then lower-address tie-break.
            if (score < bestScore ||
                (score == bestScore && best != freeByStart.end() &&
                 ((highSide && it->second > best->first) ||
                  (!highSide && it->second < best->first)))) {
                bestScore = score;
                best = freeByStart.find(it->second);
            }"""
new_alloc_condition = """            const std::int64_t potential = residualPotential(slack);
            const bool preferredTie = potential > bestPotential ||
                (potential == bestPotential && best != freeByStart.end() &&
                 (highSide ? it->second > best->first : it->second < best->first));
            if (score < bestScore || (score == bestScore && preferredTie)) {
                bestScore = score;
                bestPotential = potential;
                best = freeByStart.find(it->second);
            }"""
assert potential.count(old_alloc_condition) == 1
potential = potential.replace(old_alloc_condition, new_alloc_condition)
(ROOT / "source" / "history_potential_tiebreak.cpp").write_text(potential)

stratified = baseline
old_rng = """    std::uint32_t nextRandom(std::uint32_t& state) const {
        state ^= state << 13U;
        state ^= state >> 17U;
        state ^= state << 5U;
        return state;
    }

    std::array<Observation, kMcDepth> sampleScenario(std::uint32_t& randomState) const {"""
new_rng = """    std::array<Observation, kMcDepth> sampleScenario(std::size_t trialIndex) const {"""
assert stratified.count(old_rng) == 1
stratified = stratified.replace(old_rng, new_rng)
old_sample = """        const std::size_t start = starts[static_cast<std::size_t>(
            nextRandom(randomState) % static_cast<std::uint32_t>(starts.size()))];"""
new_sample = """        const std::size_t selected = std::min(
            starts.size() - 1,
            ((2 * trialIndex + 1) * starts.size()) / (2 * kMcTrials));
        const std::size_t start = starts[selected];"""
assert stratified.count(old_sample) == 1
stratified = stratified.replace(old_sample, new_sample)
old_seed = """        std::uint32_t randomState = 0x9e3779b9U ^
            static_cast<std::uint32_t>(pipes.size() * 0x85ebca6bU) ^
            (static_cast<std::uint32_t>(length) * 0xc2b2ae35U) ^
            static_cast<std::uint32_t>(trenchLength);
        if (randomState == 0) randomState = 1;

        std::array<std::array<Observation, kMcDepth>, kMcTrials> scenarios{};
        for (std::size_t trial = 0; trial < kMcTrials; ++trial) {
            scenarios[trial] = sampleScenario(randomState);
        }"""
new_seed = """        std::array<std::array<Observation, kMcDepth>, kMcTrials> scenarios{};
        for (std::size_t trial = 0; trial < kMcTrials; ++trial) {
            scenarios[trial] = sampleScenario(trial);
        }"""
assert stratified.count(old_seed) == 1
stratified = stratified.replace(old_seed, new_seed)
(ROOT / "source" / "stratified_history_beam.cpp").write_text(stratified)

print("Wrote: mc_budget64, history_potential_tiebreak, stratified_history_beam")
