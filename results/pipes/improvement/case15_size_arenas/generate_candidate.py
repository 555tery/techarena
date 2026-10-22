from pathlib import Path


ROOT = Path("results/pipes/improvement/case15_size_arenas")
BASE = Path("results/pipes/improvement/case9_causal_profiles/source/champion_cohort_slabs.cpp")
source = BASE.read_text()


def replace_once(old: str, new: str) -> None:
    global source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected one anchor, found {count}: {old[:90]!r}")
    source = source.replace(old, new, 1)


def replace_last(old: str, new: str) -> None:
    global source
    position = source.rfind(old)
    if position < 0:
        raise RuntimeError(f"missing anchor: {old[:90]!r}")
    if source.find(old) != position:
        # Replacing the final allocator implementation is intentional: this
        # source also contains a small rollout simulator with similarly named
        # helpers, which remains unchanged.
        pass
    source = source[:position] + new + source[position + len(old):]


replace_once(
    "constexpr std::int64_t kDigLength = 20;\n",
    "constexpr std::int64_t kDigLength = 20;\n"
    "constexpr std::size_t kSizeArenaClassCount = 3;\n",
)

replace_once(
    "struct Pipe {\n"
    "    std::int64_t start = 0;\n"
    "    int length = 0;\n"
    "    bool active = false;\n"
    "    int sizeCohort = 0;\n"
    "};",
    "struct Pipe {\n"
    "    std::int64_t start = 0;\n"
    "    int length = 0;\n"
    "    bool active = false;\n"
    "    int sizeCohort = 0;\n"
    "    int sizeArenaClass = 0;\n"
    "};",
)

replace_once(
    "    std::map<std::int64_t, int> gapCohort;\n"
    "    std::array<std::set<std::pair<std::int64_t, std::int64_t>>, 2> freeBySizeCohort;\n"
    "    std::set<std::pair<std::int64_t, std::int64_t>> freeBySizeShared;\n",
    "    std::map<std::int64_t, int> gapCohort;\n"
    "    std::array<std::set<std::pair<std::int64_t, std::int64_t>>, 2> freeBySizeCohort;\n"
    "    std::set<std::pair<std::int64_t, std::int64_t>> freeBySizeShared;\n"
    "    std::map<std::int64_t, int> gapSizeArenaOwner;\n"
    "    std::array<std::set<std::pair<std::int64_t, std::int64_t>>, kSizeArenaClassCount>\n"
    "        freeBySizeArenaClass;\n"
    "    std::set<std::pair<std::int64_t, std::int64_t>> freeBySizeArenaShared;\n",
)

replace_last(
    "    std::deque<int> recentLengths;\n"
    "    std::array<int, 41> recentFrequency{};\n"
    "    std::array<std::int64_t, 41> lengthOccurrenceCount{};\n",
    "    std::deque<int> recentLengths;\n"
    "    std::array<int, 41> recentFrequency{};\n"
    "    std::array<std::size_t, kSizeArenaClassCount> recentArenaClassCount{};\n"
    "    std::array<std::int64_t, 41> lengthOccurrenceCount{};\n",
)

replace_last(
    "        const int sizeCohort = static_cast<int>(\n"
    "            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);\n",
    "        const int sizeCohort = static_cast<int>(\n"
    "            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);\n"
    "        const int sizeArenaClass = arenaClassForLength(length);\n",
)

replace_once(
    "                if (occupiedEnd < trenchLength) addFreeGap(occupiedEnd, trenchLength, -1);",
    "                if (occupiedEnd < trenchLength) {\n"
    "                    addFreeGap(occupiedEnd, trenchLength, -1, sizeArenaClass);\n"
    "                }",
)

replace_once(
    "            pipes.push_back(Pipe{start, length, true, sizeCohort});",
    "            pipes.push_back(Pipe{start, length, true, sizeCohort, sizeArenaClass});",
)

place_anchor = (
    "        std::int64_t start = -1;\n"
    "        auto gap = bestFittingGap(length, highSide, sizeCohort);\n"
    "        if (gap != freeByStart.end()) {\n"
    "            if (geometricLaneActive) {\n"
    "                highSide = trendAlignedHighSide(recentLengths, length,\n"
    "                                                gap->first, gap->second, highSide);\n"
    "            }\n"
    "            const std::int64_t selectedStart = chooseGapWithRollout(\n"
    "                length, highSide, sizeCohort, gap);\n"
)
place_replacement = (
    "        std::int64_t start = -1;\n"
    "        auto gap = bestFittingGap(length, highSide, sizeCohort);\n"
    "        bool sizeArenaChangedGap = false;\n"
    "        if (!parityCohortMode && sizeArenaModeActive()) {\n"
    "            StartIter arenaGap = bestFittingGapForArena(\n"
    "                length, highSide, sizeArenaClass);\n"
    "            if (arenaGap != freeByStart.end()) {\n"
    "                sizeArenaChangedGap = gap == freeByStart.end() ||\n"
    "                    arenaGap->first != gap->first;\n"
    "                gap = arenaGap;\n"
    "            }\n"
    "        }\n"
    "        if (gap != freeByStart.end()) {\n"
    "            if (geometricLaneActive) {\n"
    "                highSide = trendAlignedHighSide(recentLengths, length,\n"
    "                                                gap->first, gap->second, highSide);\n"
    "            }\n"
    "            const std::int64_t selectedStart = sizeArenaChangedGap\n"
    "                ? gap->first\n"
    "                : chooseGapWithRollout(length, highSide, sizeCohort, gap);\n"
)
replace_once(place_anchor, place_replacement)

tail_anchor = (
    "            const std::int64_t tailStart =\n"
    "                tail == freeByStart.end() || preserveForeignTail\n"
    "                    ? trenchLength : tail->first;\n"
)
tail_replacement = tail_anchor + (
    "            int tailArenaClass = sizeArenaClass;\n"
    "            if (tail != freeByStart.end() && !preserveForeignTail) {\n"
    "                tailArenaClass = mergeArenaClasses(\n"
    "                    gapSizeArenaOwner.at(tail->first), sizeArenaClass);\n"
    "            }\n"
)
replace_once(tail_anchor, tail_replacement)

replace_last(
    "                if (tailStart < start) addFreeGap(tailStart, start, tailCohort);",
    "                if (tailStart < start) {\n"
    "                    addFreeGap(tailStart, start, tailCohort, tailArenaClass);\n"
    "                }",
)
replace_last(
    "                    addFreeGap(remainderStart, trenchLength, tailCohort);",
    "                    addFreeGap(remainderStart, trenchLength, tailCohort, tailArenaClass);",
)

replace_last(
    "        pipes.push_back(Pipe{start, length, true, sizeCohort});",
    "        pipes.push_back(Pipe{start, length, true, sizeCohort, sizeArenaClass});",
)

replace_once(
    "        const Pipe pipe = pipes[index];\n"
    "        std::cout << pipe.start << '\\n' << std::flush;\n"
    "        pipes[index].active = false;\n"
    "        fenwickAdd(static_cast<int>(index), -1);\n"
    "        --activePipeCount;\n"
    "        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);",
    "        const Pipe pipe = pipes[index];\n"
    "        std::cout << pipe.start << '\\n' << std::flush;\n"
    "        pipes[index].active = false;\n"
    "        fenwickAdd(static_cast<int>(index), -1);\n"
    "        --activePipeCount;\n"
    "        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort,\n"
    "                    pipe.sizeArenaClass);",
)

arena_helpers = (
    "    static int arenaClassForLength(int length) {\n"
    "        if (length <= 10) return 0;\n"
    "        if (length <= 20) return 1;\n"
    "        return 2;\n"
    "    }\n\n"
    "    static int mergeArenaClasses(int lhs, int rhs) {\n"
    "        return lhs == rhs ? lhs : -1;\n"
    "    }\n\n"
    "    bool sizeArenaModeActive() const {\n"
    "        const std::size_t historySize = recentLengths.size();\n"
    "        if (historySize < 128) return false;\n"
    "        std::size_t supportedClasses = 0;\n"
    "        for (const std::size_t count : recentArenaClassCount) {\n"
    "            if (count >= 16 && count * 8U >= historySize) ++supportedClasses;\n"
    "        }\n"
    "        return supportedClasses >= 2;\n"
    "    }\n\n"
    "    StartIter bestFittingGapForArena(int length, bool highSide, int arenaClass) {\n"
    "        const auto& owned =\n"
    "            freeBySizeArenaClass[static_cast<std::size_t>(arenaClass)];\n"
    "        StartIter preferred = bestFittingGapFromSet(owned, length, highSide);\n"
    "        if (preferred != freeByStart.end()) return preferred;\n"
    "        return bestFittingGapFromSet(freeBySizeArenaShared, length, highSide);\n"
    "    }\n\n"
)
replace_once(
    "    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {\n",
    arena_helpers + "    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {\n",
)

replace_last(
    "    std::int64_t consumeAtSide(StartIter it, int length, bool highSide) {\n"
    "        const std::int64_t start = it->first;\n"
    "        const std::int64_t end = it->second;\n"
    "        const int cohort = gapCohort.at(start);\n"
    "        const std::int64_t placementStart = highSide\n"
    "            ? end - static_cast<std::int64_t>(length) : start;\n"
    "        eraseGap(it);\n"
    "        if (start < placementStart) addFreeGap(start, placementStart, cohort);\n"
    "        const std::int64_t placementEnd = placementStart + static_cast<std::int64_t>(length);\n"
    "        if (placementEnd < end) addFreeGap(placementEnd, end, cohort);\n"
    "        return placementStart;\n"
    "    }",
    "    std::int64_t consumeAtSide(StartIter it, int length, bool highSide) {\n"
    "        const std::int64_t start = it->first;\n"
    "        const std::int64_t end = it->second;\n"
    "        const int cohort = gapCohort.at(start);\n"
    "        const int arenaClass = gapSizeArenaOwner.at(start);\n"
    "        const std::int64_t placementStart = highSide\n"
    "            ? end - static_cast<std::int64_t>(length) : start;\n"
    "        eraseGap(it);\n"
    "        if (start < placementStart) {\n"
    "            addFreeGap(start, placementStart, cohort, arenaClass);\n"
    "        }\n"
    "        const std::int64_t placementEnd = placementStart + static_cast<std::int64_t>(length);\n"
    "        if (placementEnd < end) {\n"
    "            addFreeGap(placementEnd, end, cohort, arenaClass);\n"
    "        }\n"
    "        return placementStart;\n"
    "    }",
)

replace_last(
    "    void recordLength(int length) {\n"
    "        recentLengths.push_back(length);\n"
    "        ++recentFrequency[static_cast<std::size_t>(length)];\n"
    "        if (recentLengths.size() > kHistoryWindow) {\n"
    "            --recentFrequency[static_cast<std::size_t>(recentLengths.front())];\n"
    "            recentLengths.pop_front();\n"
    "        }\n"
    "    }",
    "    void recordLength(int length) {\n"
    "        recentLengths.push_back(length);\n"
    "        ++recentFrequency[static_cast<std::size_t>(length)];\n"
    "        ++recentArenaClassCount[static_cast<std::size_t>(arenaClassForLength(length))];\n"
    "        if (recentLengths.size() > kHistoryWindow) {\n"
    "            const int oldLength = recentLengths.front();\n"
    "            --recentFrequency[static_cast<std::size_t>(oldLength)];\n"
    "            --recentArenaClassCount[static_cast<std::size_t>(arenaClassForLength(oldLength))];\n"
    "            recentLengths.pop_front();\n"
    "        }\n"
    "    }",
)

replace_last(
    "    void eraseGap(StartIter it) {\n"
    "        const std::int64_t start = it->first;\n"
    "        const std::int64_t end = it->second;\n"
    "        const std::int64_t gapLength = end - start;\n"
    "        const int cohort = gapCohort.at(start);\n"
    "        freeBySize.erase({gapLength, start});\n"
    "        if (cohort >= 0 && cohort <= 1) {\n"
    "            freeBySizeCohort[static_cast<std::size_t>(cohort)].erase({gapLength, start});\n"
    "        } else {\n"
    "            freeBySizeShared.erase({gapLength, start});\n"
    "        }\n"
    "        gapCohort.erase(start);\n"
    "        freeByStart.erase(it);\n"
    "    }",
    "    void eraseGap(StartIter it) {\n"
    "        const std::int64_t start = it->first;\n"
    "        const std::int64_t end = it->second;\n"
    "        const std::int64_t gapLength = end - start;\n"
    "        const int cohort = gapCohort.at(start);\n"
    "        const int arenaClass = gapSizeArenaOwner.at(start);\n"
    "        freeBySize.erase({gapLength, start});\n"
    "        if (cohort >= 0 && cohort <= 1) {\n"
    "            freeBySizeCohort[static_cast<std::size_t>(cohort)].erase({gapLength, start});\n"
    "        } else {\n"
    "            freeBySizeShared.erase({gapLength, start});\n"
    "        }\n"
    "        if (arenaClass >= 0 && arenaClass < static_cast<int>(kSizeArenaClassCount)) {\n"
    "            freeBySizeArenaClass[static_cast<std::size_t>(arenaClass)].erase(\n"
    "                {gapLength, start});\n"
    "        } else {\n"
    "            freeBySizeArenaShared.erase({gapLength, start});\n"
    "        }\n"
    "        gapCohort.erase(start);\n"
    "        gapSizeArenaOwner.erase(start);\n"
    "        freeByStart.erase(it);\n"
    "    }",
)

old_add_gap = (
    "    void addFreeGap(std::int64_t start, std::int64_t end, int cohort) {\n"
    "        if (start >= end) return;\n"
    "        auto it = freeByStart.lower_bound(start);\n"
    "        if (it != freeByStart.begin()) {\n"
    "            auto previous = std::prev(it);\n"
    "            if (previous->second >= start) {\n"
    "                if (gapCohort.at(previous->first) != cohort) cohort = -1;\n"
    "                start = previous->first;\n"
    "                end = std::max(end, previous->second);\n"
    "                eraseGap(previous);\n"
    "                it = freeByStart.lower_bound(start);\n"
    "            }\n"
    "        }\n"
    "        while (it != freeByStart.end() && it->first <= end) {\n"
    "            if (gapCohort.at(it->first) != cohort) cohort = -1;\n"
    "            end = std::max(end, it->second);\n"
    "            auto next = it++;\n"
    "            eraseGap(next);\n"
    "        }\n"
    "        freeByStart.emplace(start, end);\n"
    "        const std::int64_t gapLength = end - start;\n"
    "        freeBySize.emplace(gapLength, start);\n"
    "        gapCohort.emplace(start, cohort);\n"
    "        if (cohort >= 0 && cohort <= 1) {\n"
    "            freeBySizeCohort[static_cast<std::size_t>(cohort)].emplace(gapLength, start);\n"
    "        } else {\n"
    "            freeBySizeShared.emplace(gapLength, start);\n"
    "        }\n"
    "    }"
)
new_add_gap = (
    "    void addFreeGap(std::int64_t start, std::int64_t end, int cohort,\n"
    "                    int arenaClass = -1) {\n"
    "        if (start >= end) return;\n"
    "        auto it = freeByStart.lower_bound(start);\n"
    "        if (it != freeByStart.begin()) {\n"
    "            auto previous = std::prev(it);\n"
    "            if (previous->second >= start) {\n"
    "                if (gapCohort.at(previous->first) != cohort) cohort = -1;\n"
    "                arenaClass = mergeArenaClasses(\n"
    "                    gapSizeArenaOwner.at(previous->first), arenaClass);\n"
    "                start = previous->first;\n"
    "                end = std::max(end, previous->second);\n"
    "                eraseGap(previous);\n"
    "                it = freeByStart.lower_bound(start);\n"
    "            }\n"
    "        }\n"
    "        while (it != freeByStart.end() && it->first <= end) {\n"
    "            if (gapCohort.at(it->first) != cohort) cohort = -1;\n"
    "            arenaClass = mergeArenaClasses(gapSizeArenaOwner.at(it->first), arenaClass);\n"
    "            end = std::max(end, it->second);\n"
    "            auto next = it++;\n"
    "            eraseGap(next);\n"
    "        }\n"
    "        freeByStart.emplace(start, end);\n"
    "        const std::int64_t gapLength = end - start;\n"
    "        freeBySize.emplace(gapLength, start);\n"
    "        gapCohort.emplace(start, cohort);\n"
    "        gapSizeArenaOwner.emplace(start, arenaClass);\n"
    "        if (cohort >= 0 && cohort <= 1) {\n"
    "            freeBySizeCohort[static_cast<std::size_t>(cohort)].emplace(gapLength, start);\n"
    "        } else {\n"
    "            freeBySizeShared.emplace(gapLength, start);\n"
    "        }\n"
    "        if (arenaClass >= 0 && arenaClass < static_cast<int>(kSizeArenaClassCount)) {\n"
    "            freeBySizeArenaClass[static_cast<std::size_t>(arenaClass)].emplace(\n"
    "                gapLength, start);\n"
    "        } else {\n"
    "            freeBySizeArenaShared.emplace(gapLength, start);\n"
    "        }\n"
    "    }"
)
replace_last(old_add_gap, new_add_gap)

(ROOT / "source/coarse_size_class_arenas.cpp").write_text(source)
print("wrote", ROOT / "source/coarse_size_class_arenas.cpp")
