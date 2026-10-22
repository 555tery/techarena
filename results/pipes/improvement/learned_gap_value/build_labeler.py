#!/usr/bin/env python3
"""Create a diagnostic exact-PID labeler from the frozen solver source."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "results/pipes/final/solution.cpp"
OUT = HERE / "src/label_runner.cpp"


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one anchor, got {count}: {old[:80]!r}")
    return text.replace(old, new, 1)


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    text = replace_once(text, "#include <vector>\n", "#include <vector>\n#include <cmath>\n#include <fstream>\n#include <iomanip>\n#include <sstream>\n#include <string>\n#include <unordered_map>\n")
    text = replace_once(text, "    std::vector<SimPipe> active;\n", "    std::vector<SimPipe> active;\n    std::unordered_map<int, std::size_t> activeIndexByPid;\n    bool fastPidRemoval = false;\n")
    text = replace_once(text, "        active.push_back(SimPipe{nextPid++, start, length, sizeCohort});\n", "        active.push_back(SimPipe{nextPid++, start, length, sizeCohort});\n        activeIndexByPid[active.back().pid] = active.size() - 1;\n")
    text = replace_once(text, "        active.erase(active.begin() + static_cast<std::ptrdiff_t>(index));\n", "        active.erase(active.begin() + static_cast<std::ptrdiff_t>(index));\n        activeIndexByPid.erase(pipe.pid);\n        for (std::size_t update = index; update < active.size(); ++update) {\n            activeIndexByPid[active[update].pid] = update;\n        }\n")
    text = replace_once(text, "            state.active.push_back(SimPipe{static_cast<int>(pid), pipe.start,\n                                           pipe.length, pipe.sizeCohort});\n", "            state.active.push_back(SimPipe{static_cast<int>(pid), pipe.start,\n                                           pipe.length, pipe.sizeCohort});\n            state.activeIndexByPid[static_cast<int>(pid)] = state.active.size() - 1;\n")

    remove_by_pid = r'''    std::optional<std::int64_t> removeByPid(int pid) {
        const auto found = activeIndexByPid.find(pid);
        if (found == activeIndexByPid.end()) return std::nullopt;
        const std::size_t index = found->second;
        const SimPipe pipe = active[index];
        if (fastPidRemoval) {
            const std::size_t last = active.size() - 1;
            if (index != last) {
                active[index] = active[last];
                activeIndexByPid[active[index].pid] = index;
            }
            active.pop_back();
            activeIndexByPid.erase(pid);
        } else {
            active.erase(active.begin() + static_cast<std::ptrdiff_t>(index));
            activeIndexByPid.erase(pid);
            for (std::size_t update = index; update < active.size(); ++update) {
                activeIndexByPid[active[update].pid] = update;
            }
        }
        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);
        recordDeletionPattern(pipe.pid, pipe.length);
        const std::size_t lengthIndex = static_cast<std::size_t>(pipe.length);
        ++removedLengthCohort[lengthIndex][static_cast<std::size_t>(pipe.sizeCohort)];
        const std::int64_t totalForLength =
            removedLengthCohort[lengthIndex][0] + removedLengthCohort[lengthIndex][1];
        const std::int64_t dominantForLength = std::max(
            removedLengthCohort[lengthIndex][0], removedLengthCohort[lengthIndex][1]);
        if (totalForLength >= 8 && dominantForLength * 100 >= totalForLength * 85 &&
            hasSteadySizeTrend()) {
            parityCohortMode = true;
        }
        return pipe.start;
    }

'''
    text = replace_once(text, "    void apply(const Observation& event) {\n", remove_by_pid + "    void apply(const Observation& event) {\n")

    driver = r'''int main(int argc, char** argv) {
    if (argc != 5) {
        std::cerr << "usage: label_runner INPUT BASELINE_REPLIES SPLIT CADENCE\n";
        return 2;
    }
    const std::string inputPath = argv[1];
    const std::string replyPath = argv[2];
    const std::string split = argv[3];
    const int cadence = std::stoi(argv[4]);
    constexpr int kLabelHorizon = 512;
    std::ifstream input(inputPath);
    double weight = 0.0;
    int count = 0;
    if (!(input >> weight >> count) || count <= 0) return 3;
    (void)weight;
    std::vector<int> commands(static_cast<std::size_t>(count));
    for (int& command : commands) {
        if (!(input >> command)) return 4;
    }
    std::ifstream replies(replyPath);
    if (!replies) return 5;
    RolloutState state;
    state.fastPidRemoval = true;
    std::ofstream csv(argv[4][0] == '\0' ? "" : "/dev/null");
    (void)csv;
    return 0;
}
'''
    # The complete driver is kept as a separate template to make the frozen
    # source transformation easy to audit.
    driver = r'''int main(int argc, char** argv) {
    if (argc != 7) {
        std::cerr << "usage: label_runner INPUT BASELINE_REPLIES SPLIT STREAM CADENCE CSV\n";
        return 2;
    }
    const std::string inputPath = argv[1];
    const std::string replyPath = argv[2];
    const std::string split = argv[3];
    const std::string streamName = argv[4];
    const int cadence = std::stoi(argv[5]);
    const std::string outputPath = argv[6];
    constexpr int kLabelHorizon = 512;
    std::ifstream input(inputPath);
    double weight = 0.0;
    int count = 0;
    if (!(input >> weight >> count) || count <= 0) return 3;
    (void)weight;
    std::vector<int> commands(static_cast<std::size_t>(count));
    for (int& command : commands) {
        if (!(input >> command)) return 4;
    }
    std::ifstream replies(replyPath);
    if (!replies) return 5;
    std::vector<std::vector<std::int64_t>> expected;
    std::string line;
    while (std::getline(replies, line)) {
        std::istringstream parser(line);
        std::vector<std::int64_t> reply;
        std::int64_t value = 0;
        while (parser >> value) reply.push_back(value);
        if (!reply.empty()) expected.push_back(reply);
    }
    if (expected.size() != commands.size()) {
        std::cerr << "reply count mismatch: " << expected.size() << " vs " << commands.size() << '\n';
        return 6;
    }
    std::ofstream output(outputPath);
    if (!output) return 7;
    output << std::setprecision(12);
    RolloutState state;
    state.fastPidRemoval = true;
    output << "stream,state_id,command_index,candidate_rank,baseline_action,target_growth_m";
    for (std::size_t feature = 0; feature < 180; ++feature) output << ",f" << feature;
    output << '\n';

    for (int index = 0; index < count; ++index) {
        const int command = commands[static_cast<std::size_t>(index)];
        if (command > 0) {
            const int length = command;
            if (index >= 360 && index % cadence == 0 && index + kLabelHorizon < count) {
                const int sizeCohort = static_cast<int>(
                    state.lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
                if (state.hasSmoothSizeTrendWith(length)) state.runLeftDisabledBySmoothTrend = true;
                const bool runLeftActive = !state.runLeftDisabledBySmoothTrend &&
                    state.hasSameLengthRecentRun(length);
                const bool highSide = runLeftActive
                    ? sizeCohort != 0
                    : (state.alternatingDeleteMode
                        ? ((state.nextPid & 1) != state.predictedDeletedParity)
                        : (state.parityCohortMode
                            ? sizeCohort == 0
                            : (length <= 4 || state.hasSameLengthRecentRun(length))));
                const auto baselineStart = state.bestGap(length, highSide, sizeCohort);
                if (baselineStart.has_value()) {
                    struct Candidate { std::int64_t start; std::int64_t score; };
                    std::vector<Candidate> candidates;
                    bool hasPreferred = false;
                    if (state.parityCohortMode) {
                        for (const auto& [start, gap] : state.gaps) {
                            if (gap.end - start >= length && gap.cohort == sizeCohort) {
                                hasPreferred = true;
                                break;
                            }
                        }
                    }
                    for (const auto& [start, gap] : state.gaps) {
                        const std::int64_t gapLength = gap.end - start;
                        if (gapLength < length || gapLength - length > 40) continue;
                        if (state.parityCohortMode &&
                            (hasPreferred ? gap.cohort != sizeCohort : gap.cohort >= 0)) continue;
                        candidates.push_back(Candidate{start, state.fitScore(gapLength, length)});
                    }
                    std::sort(candidates.begin(), candidates.end(), [highSide](
                        const Candidate& lhs, const Candidate& rhs) {
                        if (lhs.score != rhs.score) return lhs.score < rhs.score;
                        return highSide ? lhs.start > rhs.start : lhs.start < rhs.start;
                    });
                    if (candidates.size() > 3) candidates.resize(3);
                    if (candidates.size() >= 2 && candidates.front().start == *baselineStart) {
                        for (std::size_t rank = 0; rank < candidates.size(); ++rank) {
                            const std::int64_t candidateStart = candidates[rank].start;
                            const auto gapIt = state.gaps.find(candidateStart);
                            if (gapIt == state.gaps.end()) return 8;
                            const std::int64_t originalGapLength = gapIt->second.end - candidateStart;
                            const int originalCohort = gapIt->second.cohort;
                            const bool candidateIsTail = !state.gaps.empty() &&
                                std::prev(state.gaps.end())->first == candidateStart &&
                                std::prev(state.gaps.end())->second.end == state.trenchLength;
                            RolloutState after = state;
                            after.placeAtCandidate(candidateStart, length, highSide);
                            std::array<double, 180> features{};
                            std::array<int, 85> histogram{};
                            for (const auto& [gapStart, gap] : after.gaps) {
                                const std::int64_t gapLength = gap.end - gapStart;
                                const std::size_t bin = gapLength <= 80
                                    ? static_cast<std::size_t>(gapLength - 1)
                                    : (gapLength <= 100 ? 80U : gapLength <= 140 ? 81U :
                                       gapLength <= 200 ? 82U : gapLength <= 400 ? 83U : 84U);
                                ++histogram[bin];
                            }
                            for (std::size_t i = 0; i < histogram.size(); ++i)
                                features[i] = static_cast<double>(histogram[i]);
                            const double historyDenominator = static_cast<double>(
                                std::max<std::size_t>(1, state.recentLengths.size()));
                            for (std::size_t request = 1; request <= 40; ++request) {
                                features[84 + request] = static_cast<double>(
                                    state.recentFrequency[request]) / historyDenominator;
                                if (static_cast<int>(request) == length) features[124 + request] = 1.0;
                            }
                            std::int64_t occupied = 0;
                            for (const SimPipe& pipe : state.active) occupied += pipe.length;
                            std::int64_t tailLength = 0;
                            if (!after.gaps.empty()) {
                                const auto& tail = *std::prev(after.gaps.end());
                                if (tail.second.end == after.trenchLength)
                                    tailLength = after.trenchLength - tail.first;
                            }
                            const double trenchDenominator = static_cast<double>(
                                std::max<std::int64_t>(1, state.trenchLength));
                            const std::array<double, 15> summary = {
                                std::log1p(static_cast<double>(state.active.size())) / 10.0,
                                std::log1p(static_cast<double>(after.gaps.size())) / 10.0,
                                static_cast<double>(state.trenchLength) / 1'000'000.0,
                                static_cast<double>(occupied) / trenchDenominator,
                                static_cast<double>(std::min<std::int64_t>(tailLength, 400)) / 400.0,
                                static_cast<double>(candidateStart) / trenchDenominator,
                                static_cast<double>(std::min<std::int64_t>(originalGapLength, 400)) / 400.0,
                                static_cast<double>(originalGapLength - length) / 40.0,
                                candidateIsTail ? 1.0 : 0.0,
                                highSide ? 1.0 : 0.0,
                                static_cast<double>(originalCohort),
                                static_cast<double>(sizeCohort),
                                state.parityCohortMode ? 1.0 : 0.0,
                                state.alternatingDeleteMode ? 1.0 : 0.0,
                                static_cast<double>(rank) / 2.0,
                            };
                            std::copy(summary.begin(), summary.end(), features.begin() + 165);
                            const std::int64_t initialTrench = after.trenchLength;
                            for (int step = 1; step <= kLabelHorizon; ++step) {
                                const int future = commands[static_cast<std::size_t>(index + step)];
                                if (future > 0) {
                                    after.place(future);
                                } else if (future < 0) {
                                    if (!after.removeByPid(-future).has_value()) return 9;
                                } else {
                                    return 10;
                                }
                            }
                            const std::int64_t target = after.trenchLength - initialTrench;
            output << split << '-' << streamName << ','
                   << split << '-' << streamName << '-' << index << ',' << index << ',' << rank << ','
                                   << (candidateStart == *baselineStart ? 1 : 0) << ',' << target;
                            for (double feature : features) output << ',' << feature;
                            output << '\n';
                        }
                    }
                }
            }
            const std::int64_t oldTrench = state.trenchLength;
            state.place(length);
            const std::int64_t digs = (state.trenchLength - oldTrench) / kDigLength;
            const std::int64_t start = state.active.back().start;
            const auto& reply = expected[static_cast<std::size_t>(index)];
            if (reply.size() != 2 || reply[0] != digs || reply[1] != start) {
                std::cerr << "baseline placement mismatch at " << index << ": expected "
                          << (reply.empty() ? -1 : reply[0]) << ' '
                          << (reply.size() < 2 ? -1 : reply[1]) << " got " << digs << ' ' << start << '\n';
                return 11;
            }
        } else if (command < 0) {
            const auto found = state.activeIndexByPid.find(-command);
            if (found == state.activeIndexByPid.end()) return 12;
            const std::int64_t start = state.active[found->second].start;
            const auto removed = state.removeByPid(-command);
            const auto& reply = expected[static_cast<std::size_t>(index)];
            if (!removed.has_value() || reply.size() != 1 || reply[0] != start || *removed != start) {
                std::cerr << "baseline removal mismatch at " << index << '\n';
                return 13;
            }
        }
    }
    return 0;
}
'''
    main_at = text.find("int main() {")
    if main_at < 0:
        raise RuntimeError("could not locate final solver main")
    text = text[:main_at] + driver
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} from {SOURCE.relative_to(ROOT)}")
    print(f"source_sha256={hashlib.sha256(SOURCE.read_bytes()).hexdigest()}")
    print(f"labeler_sha256={hashlib.sha256(OUT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
