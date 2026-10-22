from pathlib import Path
src=Path('results/pipes/final/solution.cpp').read_text()
# Add the online PID-recency deletion regime detector.
old='''[[maybe_unused]] constexpr std::int64_t kMcMinimumMeanSavingM = 1;'''
new='''[[maybe_unused]] constexpr std::int64_t kMcMinimumMeanSavingM = 1;\nconstexpr std::size_t kRecentDeleteRankWindow = 128;\nconstexpr std::size_t kRecentDeleteRankMinimum = 64;\nconstexpr int kRecentDeleteRankCutoffPermille = 50;\nconstexpr int kRecentDeleteRankEnablePercent = 80;\nconstexpr int kRecentDeleteRankDisablePercent = 60;\nconstexpr std::size_t kRecentNeighborCount = 64;'''
assert src.count(old)==1
src=src.replace(old,new)
old='''struct GapCandidate {\n    std::int64_t start = 0;\n    std::int64_t score = 0;\n};'''
new='''struct GapCandidate {\n    std::int64_t start = 0;\n    std::int64_t score = 0;\n};\n\nstruct RecentGapCandidate {\n    std::int64_t start = 0;\n    std::int64_t score = 0;\n    std::size_t recency = 0;\n    bool highSide = false;\n};'''
assert src.count(old)==1
src=src.replace(old,new)
class_i=src.index('class Allocator {')
prefix,body=src[:class_i],src[class_i:]
old='''    std::size_t activePipeCount = 0;\n    std::deque<Observation> observedHistory;'''
new='''    std::size_t activePipeCount = 0;\n    int newestActivePid = 0;\n    std::deque<int> recentRemovalRanks;\n    std::size_t nearNewestRemovalCount = 0;\n    bool recencyClusterMode = false;\n    std::deque<Observation> observedHistory;'''
assert body.count(old)==1
body=body.replace(old,new)
old='''        const bool highSide = alternatingDeleteMode\n            ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)\n            : (!runLeftActive && (parityCohortMode\n                ? sizeCohort == 0\n                : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));\n        std::int64_t start = -1;'''
new='''        const bool highSide = alternatingDeleteMode\n            ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)\n            : (!runLeftActive && (parityCohortMode\n                ? sizeCohort == 0\n                : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));\n        if (recencyClusterMode) {\n            const auto recentGap = bestRecentAdjacentGap(length);\n            if (recentGap.has_value()) {\n                const std::int64_t start = consumeAtSide(\n                    freeByStart.find(recentGap->start), length, recentGap->highSide);\n                printPlacement(0, start);\n                const int pid = static_cast<int>(pipes.size());\n                pipes.push_back(Pipe{start, length, true, sizeCohort});\n                fenwickAdd(pid, 1);\n                newestActivePid = pid;\n                ++activePipeCount;\n                ++lengthOccurrenceCount[static_cast<std::size_t>(length)];\n                recordLength(length);\n                recordObservation(Observation{1, length});\n                return;\n            }\n        }\n        std::int64_t start = -1;'''
assert body.count(old)==1
body=body.replace(old,new)
# Update the detector from observed removal rank.
old='''        const int rankPermille = rankFromNewestPermille(static_cast<int>(index));\n\n        const Pipe pipe = pipes[index];'''
new='''        const int rankPermille = rankFromNewestPermille(static_cast<int>(index));\n        recordRecentRemovalRank(rankPermille);\n\n        const Pipe pipe = pipes[index];'''
assert body.count(old)==1
body=body.replace(old,new)
# Maintain the maximum active PID in placement/removal paths.
old='''        pipes.push_back(Pipe{start, length, true, sizeCohort});\n        fenwickAdd(pid, 1);\n        ++activePipeCount;'''
new='''        pipes.push_back(Pipe{start, length, true, sizeCohort});\n        fenwickAdd(pid, 1);\n        newestActivePid = pid;\n        ++activePipeCount;'''
assert body.count(old)==1
body=body.replace(old,new)
old='''        fenwickAdd(static_cast<int>(index), -1);\n        --activePipeCount;\n        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);'''
new='''        fenwickAdd(static_cast<int>(index), -1);\n        --activePipeCount;\n        if (static_cast<int>(index) == newestActivePid) {\n            while (newestActivePid > 0 &&\n                   !pipes[static_cast<std::size_t>(newestActivePid)].active) {\n                --newestActivePid;\n            }\n        }\n        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);'''
assert body.count(old)==1
body=body.replace(old,new)
# Add methods after StartIter.
anchor='''private:\n    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;\n\n'''
methods='''private:\n    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;\n\n    void recordRecentRemovalRank(int rankPermille) {\n        const bool nearNewest = rankPermille <= kRecentDeleteRankCutoffPermille;\n        recentRemovalRanks.push_back(nearNewest ? 1 : 0);\n        if (nearNewest) ++nearNewestRemovalCount;\n        if (recentRemovalRanks.size() > kRecentDeleteRankWindow) {\n            nearNewestRemovalCount -= static_cast<std::size_t>(recentRemovalRanks.front());\n            recentRemovalRanks.pop_front();\n        }\n        if (recentRemovalRanks.size() < kRecentDeleteRankMinimum) return;\n        const std::size_t n = recentRemovalRanks.size();\n        if (!recencyClusterMode && nearNewestRemovalCount * 100 >=\n            n * static_cast<std::size_t>(kRecentDeleteRankEnablePercent)) {\n            recencyClusterMode = true;\n        } else if (recencyClusterMode && nearNewestRemovalCount * 100 <\n            n * static_cast<std::size_t>(kRecentDeleteRankDisablePercent)) {\n            recencyClusterMode = false;\n        }\n    }\n\n    std::optional<RecentGapCandidate> bestRecentAdjacentGap(int length) const {\n        std::optional<RecentGapCandidate> best;\n        std::size_t recency = 0;\n        int pid = newestActivePid;\n        while (pid > 0 && recency < kRecentNeighborCount) {\n            const Pipe& pipe = pipes[static_cast<std::size_t>(pid)];\n            if (pipe.active) {\n                auto it = freeByStart.lower_bound(pipe.start);\n                if (it != freeByStart.begin()) {\n                    auto left = std::prev(it);\n                    if (left->second == pipe.start &&\n                        left->second - left->first >= length) {\n                        const std::int64_t gapLength = left->second - left->first;\n                        const std::int64_t score = scoreGap(gapLength, length);\n                        const RecentGapCandidate candidate{left->first, score, recency, true};\n                        if (!best.has_value() || candidate.score +\n                            static_cast<std::int64_t>(candidate.recency * 64) <\n                            best->score + static_cast<std::int64_t>(best->recency * 64)) {\n                            best = candidate;\n                        }\n                    }\n                }\n                const std::int64_t pipeEnd = pipe.start + pipe.length;\n                auto right = freeByStart.lower_bound(pipeEnd);\n                if (right != freeByStart.end() && right->first == pipeEnd &&\n                    right->second - right->first >= length) {\n                    const std::int64_t gapLength = right->second - right->first;\n                    const std::int64_t score = scoreGap(gapLength, length);\n                    const RecentGapCandidate candidate{right->first, score, recency, false};\n                    if (!best.has_value() || candidate.score +\n                        static_cast<std::int64_t>(candidate.recency * 64) <\n                        best->score + static_cast<std::int64_t>(best->recency * 64)) {\n                        best = candidate;\n                    }\n                }\n                ++recency;\n            }\n            --pid;\n        }\n        return best;\n    }\n\n'''
assert body.count(anchor)==1
body=body.replace(anchor,methods)
Path('results/pipes/improvement/case15_next/source/recent_pid_adjacency.cpp').write_text(prefix+body)
