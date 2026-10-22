#!/usr/bin/env python3
"""Build an isolated frozen-final variant with an offline learned Q forest."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BASELINE = ROOT / "results/pipes/final/solution.cpp"
OUTPUT = HERE / "src/learned_gap_value.cpp"


def main() -> None:
    source = BASELINE.read_text(encoding="utf-8")
    source = source.replace("#include <cstdint>\n", "#include <cstdint>\n#include <cmath>\n#include \"learned_model.hpp\"\n", 1)
    start = source.index("    std::int64_t chooseGapWithRollout(")
    end = source.index("    bool hasSteadySizeTrend() const {", start)
    replacement = r'''    std::array<double, learned_gap_value::kFeatureCount> learnedFeatures(
        const RolloutState& before,
        const RolloutState& after,
        int length,
        const GapCandidate& candidate,
        bool highSide,
        std::size_t rank) const {
        std::array<double, learned_gap_value::kFeatureCount> features{};
        std::array<int, 85> histogram{};
        for (const auto& [start, gap] : after.gaps) {
            const std::int64_t gapLength = gap.end - start;
            const std::size_t bin = gapLength <= 80
                ? static_cast<std::size_t>(gapLength - 1)
                : (gapLength <= 100 ? 80U : gapLength <= 140 ? 81U :
                   gapLength <= 200 ? 82U : gapLength <= 400 ? 83U : 84U);
            ++histogram[bin];
        }
        for (std::size_t i = 0; i < histogram.size(); ++i) {
            features[i] = static_cast<double>(histogram[i]);
        }

        const double historyDenominator = static_cast<double>(
            std::max<std::size_t>(1, before.recentLengths.size()));
        for (std::size_t request = 1; request <= 40; ++request) {
            features[84 + request] = static_cast<double>(before.recentFrequency[request]) /
                historyDenominator;
            if (static_cast<int>(request) == length) features[124 + request] = 1.0;
        }

        const auto originalGap = before.gaps.find(candidate.start);
        if (originalGap == before.gaps.end()) return features;
        const std::int64_t originalGapLength = originalGap->second.end - candidate.start;
        const int originalCohort = originalGap->second.cohort;
        const bool candidateIsTail = !before.gaps.empty() &&
            std::prev(before.gaps.end())->first == candidate.start &&
            std::prev(before.gaps.end())->second.end == before.trenchLength;
        std::int64_t occupied = 0;
        for (const SimPipe& pipe : before.active) occupied += pipe.length;
        std::int64_t tailLength = 0;
        if (!after.gaps.empty()) {
            const auto& tail = *std::prev(after.gaps.end());
            if (tail.second.end == after.trenchLength) tailLength = after.trenchLength - tail.first;
        }
        const double trenchDenominator = static_cast<double>(
            std::max<std::int64_t>(1, before.trenchLength));
        const std::array<double, 15> summary = {
            std::log1p(static_cast<double>(before.active.size())) / 10.0,
            std::log1p(static_cast<double>(after.gaps.size())) / 10.0,
            static_cast<double>(before.trenchLength) / 1'000'000.0,
            static_cast<double>(occupied) / trenchDenominator,
            static_cast<double>(std::min<std::int64_t>(tailLength, 400)) / 400.0,
            static_cast<double>(candidate.start) / trenchDenominator,
            static_cast<double>(std::min<std::int64_t>(originalGapLength, 400)) / 400.0,
            static_cast<double>(originalGapLength - length) / 40.0,
            candidateIsTail ? 1.0 : 0.0,
            highSide ? 1.0 : 0.0,
            static_cast<double>(originalCohort),
            static_cast<double>(before.lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2),
            before.parityCohortMode ? 1.0 : 0.0,
            before.alternatingDeleteMode ? 1.0 : 0.0,
            static_cast<double>(rank) / 2.0,
        };
        std::copy(summary.begin(), summary.end(), features.begin() + 165);
        return features;
    }

    std::int64_t chooseGapWithRollout(
        int length, bool highSide, int sizeCohort, StartIter baselineGap) {
        if (mcDecisionsUsed >= kMcDecisionBudget ||
            observedHistory.size() < 32 || freeByStart.size() > kMcMaxGaps ||
            activePipeCount > kMcMaxActivePipes) {
            return baselineGap->first;
        }
        const auto candidates = topGapCandidates(length, highSide, sizeCohort);
        if (candidates.size() < 2 || candidates.front().start != baselineGap->first) {
            return baselineGap->first;
        }

        ++mcDecisionsUsed;
        const RolloutState before = makeRolloutState();
        std::size_t best = 0;
        double bestValue = std::numeric_limits<double>::infinity();
        for (std::size_t rank = 0; rank < candidates.size(); ++rank) {
            RolloutState after = before;
            after.placeAtCandidate(candidates[rank].start, length, highSide);
            const auto features = learnedFeatures(
                before, after, length, candidates[rank], highSide, rank);
            const double value = learned_gap_value::predict(features);
            if (value < bestValue) {
                best = rank;
                bestValue = value;
            }
        }
        if (best != 0) {
            const RolloutState baselineAfter = [&]() {
                RolloutState copy = before;
                copy.placeAtCandidate(candidates[0].start, length, highSide);
                return copy;
            }();
            const auto baselineFeatures = learnedFeatures(
                before, baselineAfter, length, candidates[0], highSide, 0);
            if (bestValue < learned_gap_value::predict(baselineFeatures)) {
                return candidates[best].start;
            }
        }
        return baselineGap->first;
    }

'''
    source = source[:start] + replacement + source[end:]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(source, encoding="utf-8")
    print(f"baseline_sha256={hashlib.sha256(BASELINE.read_bytes()).hexdigest()}")
    print(f"candidate_sha256={hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
