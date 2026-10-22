from pathlib import Path


ROOT = Path("results/pipes/improvement/case9_hole_first_cohorts")
BASE = ROOT / "source/hole_first_survivor_cohorts.cpp"
OUT = ROOT / "source/hole_first_survivor_cohorts_plus_lifo_gate.cpp"
source = BASE.read_text()


def replace_once(old: str, new: str) -> None:
    global source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected one anchor, found {count}: {old[:120]!r}")
    source = source.replace(old, new, 1)


replace_once(
    "    std::size_t mcDecisionsUsed = 0;\n"
    "    std::size_t mcRolloutsRun = 0;\n",
    "    std::size_t mcDecisionsUsed = 0;\n"
    "    std::size_t mcRolloutsRun = 0;\n"
    "    std::deque<int> recentDeleteRanksPermille;\n"
    "    bool lifoLaneDisabledForScale = false;\n\n"
    "    bool useLifoStackLane(int currentLength) const {\n"
    "        if (lifoLaneDisabledForScale || activePipeCount < 128 ||\n"
    "            currentLength > 8 || recentDeleteRanksPermille.size() < 48) return false;\n"
    "        std::size_t topFivePercent = 0;\n"
    "        for (int rank : recentDeleteRanksPermille) {\n"
    "            if (rank <= 50) ++topFivePercent;\n"
    "        }\n"
    "        if (topFivePercent * 100 < recentDeleteRanksPermille.size() * 80) return false;\n"
    "        std::size_t shortPlacements = 0;\n"
    "        for (int length : recentLengths) {\n"
    "            if (length <= 8) ++shortPlacements;\n"
    "        }\n"
    "        return recentLengths.size() >= 64 &&\n"
    "            shortPlacements * 100 >= recentLengths.size() * 90;\n"
    "    }\n",
)

replace_once(
    "        const int sizeCohort = static_cast<int>(\n"
    "            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);\n\n",
    "        const int sizeCohort = static_cast<int>(\n"
    "            lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);\n"
    "        if (activePipeCount > kMcMaxActivePipes) lifoLaneDisabledForScale = true;\n"
    "        const bool lifoStackLane = length > kRightEdgeMaxPipeLength &&\n"
    "            useLifoStackLane(length);\n\n",
)

replace_once(
    "        bool highSide = runLeftActive\n"
    "            ? (rearmReverse ? sizeCohort == 0 : (pipes.size() & 1U) == 0U)\n"
    "            : (alternatingDeleteMode\n"
    "                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)\n"
    "                : (parityCohortMode\n"
    "                    ? sizeCohort == 0\n"
    "                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))));\n",
    "        bool highSide = lifoStackLane || (runLeftActive\n"
    "            ? (rearmReverse ? sizeCohort == 0 : (pipes.size() & 1U) == 0U)\n"
    "            : (alternatingDeleteMode\n"
    "                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)\n"
    "                : (parityCohortMode\n"
    "                    ? sizeCohort == 0\n"
    "                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length)))));\n",
)

replace_once(
    "            if (geometricLaneActive) {\n"
    "                highSide = trendAlignedHighSide(recentLengths, length,\n"
    "                                                gap->first, gap->second, highSide);\n"
    "            }\n"
    "            const std::int64_t selectedStart = chooseGapWithRollout(\n",
    "            if (geometricLaneActive) {\n"
    "                highSide = trendAlignedHighSide(recentLengths, length,\n"
    "                                                gap->first, gap->second, highSide);\n"
    "            }\n"
    "            if (lifoStackLane) highSide = true;\n"
    "            const std::int64_t selectedStart = chooseGapWithRollout(\n",
)

replace_once(
    "    void recordObservation(const Observation& event) {\n"
    "        observedHistory.push_back(event);\n"
    "        if (observedHistory.size() > kMcHistory) observedHistory.pop_front();\n"
    "    }\n",
    "    void recordObservation(const Observation& event) {\n"
    "        observedHistory.push_back(event);\n"
    "        if (observedHistory.size() > kMcHistory) observedHistory.pop_front();\n"
    "        if (event.kind < 0) {\n"
    "            recentDeleteRanksPermille.push_back(event.value);\n"
    "            if (recentDeleteRanksPermille.size() > 64) recentDeleteRanksPermille.pop_front();\n"
    "        }\n"
    "    }\n",
)

OUT.write_text(source)
print("wrote", OUT)
