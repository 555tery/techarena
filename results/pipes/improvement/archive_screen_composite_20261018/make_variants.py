from pathlib import Path

root = Path(__file__).resolve().parent
base = (root / "source/composite_base.cpp").read_text()

# Narrow PID-parity transfer: change only the re-arm reverse lane selector,
# keeping the current composite's case-9 geometric lane and all other logic.
pid = base.replace(
    "rearmReverse ? sizeCohort == 0 : (nextPid & 1) == 0",
    "rearmReverse ? (nextPid & 1) == 0 : (nextPid & 1) == 0",
    1,
)
pid = pid.replace(
    "rearmReverse ? sizeCohort == 0 : (pipes.size() & 1U) == 0U",
    "rearmReverse ? (pipes.size() & 1U) == 0U : (pipes.size() & 1U) == 0U",
    1,
)
assert pid != base
(root / "source/pid_parity_rearm.cpp").write_text(pid)

# Historical live-mean/PID-parity overlay, applied to the current composite.
mean = base
mean = mean.replace(
    "    std::size_t activePipeCount = 0;\n    std::deque<Observation> observedHistory;",
    "    std::size_t activePipeCount = 0;\n    std::int64_t activePipeLength = 0;\n    bool liveMeanParityMode = true;\n    std::deque<Observation> observedHistory;",
    1,
)
mean = mean.replace(
    "    void place(int length) {\n        if (observedRunLength != length) {",
    "    void place(int length) {\n        if (activePipeCount > 0 && activePipeLength > 0) {\n"
    "            const std::int64_t lhs = static_cast<std::int64_t>(length) *\n"
    "                static_cast<std::int64_t>(activePipeCount);\n"
    "            if (liveMeanParityMode && lhs * 5 >= activePipeLength * 12) {\n"
    "                liveMeanParityMode = false;\n"
    "            } else if (!liveMeanParityMode && lhs * 10 <= activePipeLength * 21) {\n"
    "                liveMeanParityMode = true;\n"
    "            }\n"
    "        }\n"
    "        if (observedRunLength != length) {",
    1,
)
mean = mean.replace(
    "            ++activePipeCount;\n            ++lengthOccurrenceCount",
    "            ++activePipeCount;\n            activePipeLength += length;\n            ++lengthOccurrenceCount",
    1,
)
mean = mean.replace(
    "        bool highSide = lifoStackLane || (runLeftActive\n            ? (rearmReverse ? sizeCohort == 0 : (pipes.size() & 1U) == 0U)",
    "        bool highSide = liveMeanParityMode\n            ? ((pipes.size() & 1U) != 0U)\n            : (lifoStackLane || (runLeftActive\n            ? (rearmReverse ? sizeCohort == 0 : (pipes.size() & 1U) == 0U)",
    1,
)
mean = mean.replace(
    "                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length)))));",
    "                    : (length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length))))));",
    1,
)
mean = mean.replace(
    "            if (parityCohortMode && highSide && !preserveForeignTail) {",
    "            if ((parityCohortMode || liveMeanParityMode) && highSide && !preserveForeignTail) {",
    1,
)
# The first match is the rollout clone, which does not track active length.
mean = mean.replace(
    "            if ((parityCohortMode || liveMeanParityMode) && highSide && !preserveForeignTail) {",
    "            if (parityCohortMode && highSide && !preserveForeignTail) {",
    1,
)
needle = "            if (parityCohortMode && highSide && !preserveForeignTail) {"
index = mean.rfind(needle)
assert index >= 0
mean = mean[:index] + mean[index:].replace(
    needle,
    "            if ((parityCohortMode || liveMeanParityMode) && highSide && !preserveForeignTail) {",
    1,
)
mean = mean.replace(
    "        ++activePipeCount;\n        ++lengthOccurrenceCount",
    "        ++activePipeCount;\n        activePipeLength += length;\n        ++lengthOccurrenceCount",
    1,
)
mean = mean.replace(
    "        --activePipeCount;\n        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);",
    "        --activePipeCount;\n        activePipeLength -= pipe.length;\n        addFreeGap(pipe.start, pipe.start + pipe.length, pipe.sizeCohort);",
    1,
)
assert mean != base and "activePipeLength" in mean and "liveMeanParityMode" in mean
(root / "source/live_mean_parity_overlay.cpp").write_text(mean)

# Section-phase rule transferred onto all normal allocator/rollout gap edges.
phase = base
marker = "struct GapCandidate {\n    std::int64_t start = 0;\n    std::int64_t score = 0;\n};\n"
func = marker + "\nstd::int64_t sectionBoundaryDistance(std::int64_t coordinate) {\n"
func += "    std::int64_t phase = coordinate % kDigLength;\n"
func += "    if (phase < 0) phase += kDigLength;\n"
func += "    return std::min(phase, kDigLength - phase);\n}\n\n"
func += "bool sectionAlignedHighSide(std::int64_t gapStart, std::int64_t gapEnd,\n"
func += "                            int length, bool baselineHighSide) {\n"
func += "    const std::int64_t slack = gapEnd - gapStart - static_cast<std::int64_t>(length);\n"
func += "    if (slack <= 0) return baselineHighSide;\n"
func += "    const std::int64_t lowSidePenalty =\n"
func += "        sectionBoundaryDistance(gapStart + static_cast<std::int64_t>(length)) +\n"
func += "        sectionBoundaryDistance(gapEnd);\n"
func += "    const std::int64_t highSidePenalty =\n"
func += "        sectionBoundaryDistance(gapStart) +\n"
func += "        sectionBoundaryDistance(gapEnd - static_cast<std::int64_t>(length));\n"
func += "    if (highSidePenalty < lowSidePenalty) return true;\n"
func += "    if (lowSidePenalty < highSidePenalty) return false;\n"
func += "    return baselineHighSide;\n}\n"
assert phase.count(marker) == 1
phase = phase.replace(marker, func, 1)
phase = phase.replace(
    "        const std::int64_t start = placementStart(it->second, gapStart, length, highSide);\n"
    "        const int cohort = it->second.cohort;\n"
    "        splitGap(gapStart, length, highSide);",
    "        const bool selectedHighSide = sectionAlignedHighSide(\n"
    "            it->first, it->second.end, length, highSide);\n"
    "        const std::int64_t start = placementStart(\n"
    "            it->second, gapStart, length, selectedHighSide);\n"
    "        const int cohort = it->second.cohort;\n"
    "        splitGap(gapStart, length, selectedHighSide);",
    1,
)
phase = phase.replace(
    "            const bool selectedHighSide = geometricLaneActive\n"
    "                ? trendAlignedHighSide(recentLengths, length, it->first,\n"
    "                                       it->second.end, highSide)\n"
    "                : highSide;",
    "            const bool trendHighSide = geometricLaneActive\n"
    "                ? trendAlignedHighSide(recentLengths, length, it->first,\n"
    "                                       it->second.end, highSide)\n"
    "                : highSide;\n"
    "            const bool selectedHighSide = sectionAlignedHighSide(\n"
    "                it->first, it->second.end, length, trendHighSide);",
    1,
)
phase = phase.replace(
    "            start = consumeAtSide(gap, length, highSide);",
    "            const bool placementHighSide = sectionAlignedHighSide(\n"
    "                gap->first, gap->second, length, highSide);\n"
    "            start = consumeAtSide(gap, length, placementHighSide);",
    1,
)
assert phase != base and phase.count("sectionAlignedHighSide(") >= 4
(root / "source/section_phase_overlay.cpp").write_text(phase)
