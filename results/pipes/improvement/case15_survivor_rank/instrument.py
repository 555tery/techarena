from pathlib import Path

root = Path.cwd()
out = root / "results/pipes/improvement/case15_survivor_rank"
source = (root / "results/pipes/final/solution.cpp").read_text()

source = source.replace(
    "#include <iostream>\n",
    "#include <iostream>\n#include <fstream>\n#include <cstdlib>\n#include <stdexcept>\n",
    1,
)
source = source.replace(
    "struct GapCandidate {\n    std::int64_t start = 0;\n    std::int64_t score = 0;\n};\n",
    "struct GapCandidate {\n    std::int64_t start = 0;\n    std::int64_t score = 0;\n};\n\n#if defined(EOF_SURVIVOR_DIAG)\nstruct DiagTarget {\n    int op = 0;\n    int gapId = 0;\n    std::int64_t start = 0;\n    std::int64_t end = 0;\n    int length = 0;\n    int birthOp = 0;\n    int request = 0;\n};\n#endif\n",
    1,
)
anchor = "class Allocator {\npublic:\n"
replacement = """class Allocator {
public:
#if defined(EOF_SURVIVOR_DIAG)
    std::size_t operationIndex = 0;
    std::map<int, std::vector<DiagTarget>> diagTargets;

    Allocator() {
        const char* path = std::getenv("PIPE_SURVIVOR_TARGETS");
        if (path == nullptr) throw std::runtime_error("PIPE_SURVIVOR_TARGETS is unset");
        std::ifstream input(path);
        if (!input) throw std::runtime_error("cannot open target pair list");
        DiagTarget target;
        while (input >> target.op >> target.gapId >> target.start >> target.end
                     >> target.length >> target.birthOp >> target.request) {
            diagTargets[target.op].push_back(target);
        }
        if (!input.eof()) throw std::runtime_error("malformed target pair list");
        std::cerr << "SVDIAG_HEADER op gap_id request start end gap_len birth_op current_gap "
                     "cohort cohort_eligible mode request_cohort high_side pool eligibility representative_start target_score target_rank "
                     "pool_size baseline_start baseline_score selected_start selected_score selected_rank "
                     "rollout_count mc_decisions free_gaps active_pipes history_size\\n";
    }
#endif
"""
assert anchor in source
source = source.replace(anchor, replacement, 1)
old = """        std::int64_t start = -1;
        auto gap = bestFittingGap(length, highSide, sizeCohort);
        if (gap != freeByStart.end()) {
            const std::int64_t selectedStart = chooseGapWithRollout(
                length, highSide, sizeCohort, gap);
            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);
        }
"""
new = """        std::int64_t start = -1;
        auto gap = bestFittingGap(length, highSide, sizeCohort);
        auto selectedGap = gap;
        const std::size_t rolloutsBefore = mcRolloutsRun;
        if (gap != freeByStart.end()) {
            const std::int64_t selectedStart = chooseGapWithRollout(
                length, highSide, sizeCohort, gap);
            if (selectedStart >= 0) selectedGap = freeByStart.find(selectedStart);
        }
#if defined(EOF_SURVIVOR_DIAG)
        diagnosticCapture(length, highSide, sizeCohort, gap, selectedGap,
                          mcRolloutsRun - rolloutsBefore);
#endif
        if (selectedGap != freeByStart.end()) {
            start = consumeAtSide(selectedGap, length, highSide);
        }
"""
assert old in source
source = source.replace(old, new, 1)
private_anchor = """private:
    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;

    void fenwickAdd(int index, int delta) {
"""
private_new = """private:
    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;

#if defined(EOF_SURVIVOR_DIAG)
    std::vector<GapCandidate> diagnosticCandidates(
        const std::set<std::pair<std::int64_t, std::int64_t>>& index,
        int length, bool highSide) const {
        std::vector<GapCandidate> candidates;
        auto it = index.lower_bound({length, 0});
        while (it != index.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            if (!recentLengths.empty() && slack > 40) break;
            candidates.push_back(GapCandidate{it->second,
                recentLengths.empty() ? 0 : scoreGap(gapLength, length)});
            it = index.upper_bound({gapLength, std::numeric_limits<std::int64_t>::max()});
        }
        if (!recentLengths.empty()) {
            std::sort(candidates.begin(), candidates.end(), [highSide](
                const GapCandidate& lhs, const GapCandidate& rhs) {
                if (lhs.score != rhs.score) return lhs.score < rhs.score;
                return highSide ? lhs.start > rhs.start : lhs.start < rhs.start;
            });
        }
        return candidates;
    }

    void diagnosticCapture(int length, bool highSide, int sizeCohort,
                           StartIter baseline, StartIter selected,
                           std::size_t rolloutCount) const {
        const auto event = diagTargets.find(static_cast<int>(operationIndex));
        if (event == diagTargets.end()) return;

        std::vector<GapCandidate> candidates;
        std::string poolName = "all";
        const std::set<std::pair<std::int64_t, std::int64_t>>* selectedIndex = &freeBySize;
        if (parityCohortMode) {
            selectedIndex = &freeBySizeCohort[static_cast<std::size_t>(sizeCohort)];
            const auto preferred = diagnosticCandidates(
                *selectedIndex, length, highSide);
            if (!preferred.empty()) {
                candidates = preferred;
                poolName = "preferred";
            } else {
                selectedIndex = &freeBySizeShared;
                candidates = diagnosticCandidates(freeBySizeShared, length, highSide);
                poolName = "shared";
            }
        } else {
            candidates = diagnosticCandidates(freeBySize, length, highSide);
        }

        const std::int64_t baselineStart = baseline == freeByStart.end() ? -1 : baseline->first;
        const std::int64_t baselineScore = baseline == freeByStart.end() ? -1
            : scoreGap(baseline->second - baseline->first, length);
        const std::int64_t selectedStart = selected == freeByStart.end() ? -1 : selected->first;
        const std::int64_t selectedScore = selected == freeByStart.end() ? -1
            : scoreGap(selected->second - selected->first, length);
        int selectedRank = -1;
        for (std::size_t i = 0; i < candidates.size(); ++i)
            if (candidates[i].start == selectedStart) selectedRank = static_cast<int>(i + 1);

        for (const DiagTarget& target : event->second) {
            if (target.request != length || target.length < length)
                throw std::runtime_error("target pair/input mismatch");
            const auto actual = freeByStart.find(target.start);
            const bool sameGap = actual != freeByStart.end() && actual->second == target.end;
            const int targetCohort = sameGap ? gapCohort.at(target.start) : -9;
            const bool cohortEligible = sameGap && (!parityCohortMode ||
                targetCohort == sizeCohort || (targetCohort == -1 && poolName == "shared"));
            const std::int64_t targetScore = sameGap
                ? scoreGap(target.end - target.start, length) : -1;
            std::int64_t representativeStart = -1;
            if (sameGap) {
                auto representative = selectedIndex->lower_bound({target.length, 0});
                if (representative != selectedIndex->end() && representative->first == target.length)
                    representativeStart = representative->second;
            }
            int targetRank = -1;
            for (std::size_t i = 0; i < candidates.size(); ++i)
                if (candidates[i].start == target.start) targetRank = static_cast<int>(i + 1);

            std::string eligibility;
            if (!sameGap) {
                eligibility = "not_same_gap";
            } else if (!cohortEligible) {
                eligibility = poolName == "preferred" && targetCohort == -1
                    ? "shared_blocked_by_preferred" : "foreign_cohort";
            } else if (targetRank >= 0) {
                eligibility = "evaluated";
            } else if (representativeStart >= 0 && representativeStart != target.start) {
                eligibility = "same_size_shadowed";
            } else if (!recentLengths.empty() && target.end - target.start - length > 40) {
                eligibility = "slack_limit";
            } else {
                eligibility = "not_in_candidate_loop";
            }

            std::cerr << "SVDIAG " << operationIndex << ' ' << target.gapId << ' '
                      << length << ' ' << target.start << ' ' << target.end << ' '
                      << target.length << ' ' << target.birthOp << ' ' << sameGap << ' '
                      << targetCohort << ' ' << cohortEligible << ' ' << parityCohortMode << ' ' << sizeCohort << ' '
                      << highSide << ' ' << poolName << ' ' << eligibility << ' ' << representativeStart << ' '
                      << targetScore << ' ' << targetRank << ' ' << candidates.size() << ' '
                      << baselineStart << ' ' << baselineScore << ' ' << selectedStart << ' '
                      << selectedScore << ' ' << selectedRank << ' ' << rolloutCount << ' '
                      << mcDecisionsUsed << ' ' << freeByStart.size() << ' '
                      << activePipeCount << ' ' << observedHistory.size() << '\\n';
        }
    }
#endif

    void fenwickAdd(int index, int delta) {
"""
assert private_anchor in source
source = source.replace(private_anchor, private_new, 1)
main_old = """        if (command > 0) {
            allocator.place(static_cast<int>(command));
        } else {
            allocator.remove(-command);
        }
"""
main_new = """#if defined(EOF_SURVIVOR_DIAG)
        ++allocator.operationIndex;
#endif
        if (command > 0) {
            allocator.place(static_cast<int>(command));
        } else {
            allocator.remove(-command);
        }
"""
assert main_old in source
source = source.replace(main_old, main_new, 1)
(out / "survivor_rank_replay.cpp").write_text(source)
