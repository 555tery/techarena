from pathlib import Path


ROOT = Path("results/pipes/improvement/case9_hole_first_cohorts")
BASE = Path("results/pipes/improvement/case9_causal_profiles/source/champion_cohort_slabs.cpp")
source = BASE.read_text()


def replace_once(old: str, new: str) -> None:
    global source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected one anchor, found {count}: {old[:100]!r}")
    source = source.replace(old, new, 1)


replace_once(
    "    int cohortSlabDeleteCount = 0;\n"
    "    int cohortSlabDeletedUsed = 0;\n"
    "    int cohortSlabSurvivorUsed = 0;\n",
    "    int cohortSlabDeleteCount = 0;\n"
    "    int cohortSlabDeletedUsed = 0;\n"
    "    int cohortSlabSurvivorUsed = 0;\n"
    "    int cohortSlabGapSinkRemaining = 0;\n"
    "    int cohortSlabTailPipeCount = 0;\n",
)

branch_start = "        if (cohortSlabActive && cohortSlabUsed < cohortSlabExpectedCount) {\n"
branch_end = "            printPlacement(digs, start);\n"
if source.count(branch_start) != 1:
    raise RuntimeError("expected one cohort placement branch")
start = source.index(branch_start)
end = source.index(branch_end, start) + len(branch_end)
replacement = (
    "        if (cohortSlabActive && cohortSlabUsed < cohortSlabExpectedCount) {\n"
    "            const int pid = static_cast<int>(pipes.size());\n"
    "            const bool predictedDeleted = (pid & 1) == cohortSlabDeleteParity;\n"
    "            std::int64_t start = -1;\n"
    "            bool tailPlacement = true;\n"
    "            if (!predictedDeleted && cohortSlabGapSinkRemaining > 0) {\n"
    "                StartIter reusableGap = bestFittingGapBefore(\n"
    "                    length, false, sizeCohort, cohortSlabBase);\n"
    "                if (reusableGap != freeByStart.end()) {\n"
    "                    start = consumeAtSide(reusableGap, length, false);\n"
    "                    --cohortSlabGapSinkRemaining;\n"
    "                    tailPlacement = false;\n"
    "                }\n"
    "            }\n"
    "            if (tailPlacement) {\n"
    "                if (predictedDeleted) {\n"
    "                    start = cohortSlabBase +\n"
    "                        static_cast<std::int64_t>(cohortSlabDeletedUsed) * length;\n"
    "                    ++cohortSlabDeletedUsed;\n"
    "                } else {\n"
    "                    start = cohortSlabBase +\n"
    "                        static_cast<std::int64_t>(cohortSlabDeleteCount +\n"
    "                                                  cohortSlabSurvivorUsed) * length;\n"
    "                    ++cohortSlabSurvivorUsed;\n"
    "                }\n"
    "            }\n"
    "\n"
    "            std::int64_t digs = 0;\n"
    "            if (tailPlacement && !cohortSlabExpanded) {\n"
    "                const std::int64_t missing = cohortSlabEnd - trenchLength;\n"
    "                digs = missing > 0\n"
    "                    ? (missing + kDigLength - 1) / kDigLength : 0;\n"
    "                trenchLength += digs * kDigLength;\n"
    "                cohortSlabExpanded = true;\n"
    "                const std::int64_t occupiedEnd = cohortSlabBase +\n"
    "                    static_cast<std::int64_t>(cohortSlabTailPipeCount) * length;\n"
    "                if (occupiedEnd < trenchLength) addFreeGap(occupiedEnd, trenchLength, -1);\n"
    "            }\n"
    "            printPlacement(digs, start);\n"
)
source = source[:start] + replacement + source[end:]

replace_once(
    "        const std::int64_t predictedFutureCapacity =\n"
    "            static_cast<std::int64_t>(deleteCount) * length / predictedNextSize;\n",
    "        const int survivorCount = expectedCount - deleteCount;\n"
    "        std::int64_t reusableCapacity = 0;\n"
    "        if (!parityCohortMode) {\n"
    "            for (const auto& [gapStart, gapEnd] : freeByStart) {\n"
    "                const std::int64_t gapCapacity = (gapEnd - gapStart) / length;\n"
    "                reusableCapacity = std::min<std::int64_t>(\n"
    "                    survivorCount, reusableCapacity + gapCapacity);\n"
    "                if (reusableCapacity >= survivorCount) break;\n"
    "            }\n"
    "        }\n"
    "        const int survivorGapCount = static_cast<int>(reusableCapacity);\n"
    "        const int tailPipeCount = expectedCount - survivorGapCount;\n"
    "        const std::int64_t predictedFutureCapacity =\n"
    "            static_cast<std::int64_t>(deleteCount) * length / predictedNextSize;\n",
)

replace_once(
    "        const std::int64_t rawLength = static_cast<std::int64_t>(expectedCount) * length;\n",
    "        const std::int64_t rawLength = static_cast<std::int64_t>(tailPipeCount) * length;\n",
)

replace_once(
    "        cohortSlabDeleteCount = deleteCount;\n"
    "        cohortSlabDeletedUsed = 0;\n"
    "        cohortSlabSurvivorUsed = 0;\n"
    "        cohortSlabUsed = 0;\n"
    "        cohortSlabBase = trenchLength;\n",
    "        cohortSlabDeleteCount = deleteCount;\n"
    "        cohortSlabDeletedUsed = 0;\n"
    "        cohortSlabSurvivorUsed = 0;\n"
    "        cohortSlabGapSinkRemaining = survivorGapCount;\n"
    "        cohortSlabTailPipeCount = tailPipeCount;\n"
    "        cohortSlabUsed = 0;\n"
    "        cohortSlabBase = trenchLength;\n",
)

helper_anchor = "    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {\n"
helper = (
    "    StartIter bestFittingGapBefore(\n"
    "        int length, bool highSide, int sizeCohort, std::int64_t endLimit) {\n"
    "        StartIter best = freeByStart.end();\n"
    "        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();\n"
    "        for (auto it = freeByStart.begin(); it != freeByStart.end(); ++it) {\n"
    "            if (it->second > endLimit || it->second - it->first < length) continue;\n"
    "            if (parityCohortMode) {\n"
    "                const int owner = gapCohort.at(it->first);\n"
    "                if (owner >= 0 && owner != sizeCohort) continue;\n"
    "            }\n"
    "            const std::int64_t score = scoreGap(it->second - it->first, length);\n"
    "            if (score < bestScore ||\n"
    "                (score == bestScore && best != freeByStart.end() &&\n"
    "                 ((highSide && it->first > best->first) ||\n"
    "                  (!highSide && it->first < best->first)))) {\n"
    "                bestScore = score;\n"
    "                best = it;\n"
    "            }\n"
    "        }\n"
    "        return best;\n"
    "    }\n\n"
)
replace_once(helper_anchor, helper + helper_anchor)

(ROOT / "source/hole_first_survivor_cohorts.cpp").write_text(source)
print("wrote", ROOT / "source/hole_first_survivor_cohorts.cpp")
