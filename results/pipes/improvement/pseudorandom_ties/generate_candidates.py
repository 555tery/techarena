from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "results/pipes/final/solution.cpp"

source = BASE.read_text()

field_marker = "    std::size_t mcRolloutsRun = 0;\n"
assert source.count(field_marker) == 1
source = source.replace(
    field_marker,
    field_marker
    + "    std::uint64_t observedCommandHash = 0x243f6a8885a308d3ULL;\n"
    + "    std::size_t pseudoHashChoices = 0;\n"
    + "    std::size_t pseudoHashChangedChoices = 0;\n"
    + "    std::size_t pseudoHashMaxCandidates = 0;\n",
)

public_marker = "    void remove(std::int64_t pid) {\n"
assert source.count(public_marker) == 1
source = source.replace(
    public_marker,
    "    void observeCommand(std::int64_t command) {\n"
    "        observedCommandHash = mix64(observedCommandHash ^\n"
    "            mix64(static_cast<std::uint64_t>(command) + 0x9e3779b97f4a7c15ULL));\n"
    "    }\n\n"
    + public_marker,
)

start = source.index("    StartIter bestFittingGapFromSet(\n")
end = source.index("    bool hasSameLengthRecentRun(", start)
new_function = r'''    StartIter bestFittingGapFromSet(
        const std::set<std::pair<std::int64_t, std::int64_t>>& gaps,
        int length,
        bool highSide) {
        auto it = gaps.lower_bound({length, 0});
        if (it == gaps.end()) return freeByStart.end();
        if (recentLengths.empty()) return freeByStart.find(it->second);

        const std::int64_t historySize = static_cast<std::int64_t>(recentLengths.size());
        std::int64_t bestScore = std::numeric_limits<std::int64_t>::max();
        StartIter deterministicBest = freeByStart.end();
        std::vector<std::pair<std::int64_t, std::int64_t>> eligibleSizes;
        while (it != gaps.end()) {
            const std::int64_t gapLength = it->first;
            const std::int64_t slack = gapLength - length;
            std::int64_t score = slack * historySize;
            if (slack > 0 && slack <= 40) {
                int misses = 0;
                for (int request = static_cast<int>(slack) + 1; request <= 40; ++request) {
                    misses += recentFrequency[static_cast<std::size_t>(request)];
                }
                score += kUnfitPenaltyScale * misses;
            }

            if (score < bestScore ||
                (score == bestScore && deterministicBest != freeByStart.end() &&
                 ((highSide && it->second > deterministicBest->first) ||
                  (!highSide && it->second < deterministicBest->first)))) {
                bestScore = score;
                deterministicBest = freeByStart.find(it->second);
            }
            eligibleSizes.emplace_back(gapLength, score);
            if (slack > 40) break;
            const std::int64_t currentSize = it->first;
            it = gaps.upper_bound({currentSize, std::numeric_limits<std::int64_t>::max()});
        }
        if (deterministicBest == freeByStart.end()) return deterministicBest;

        const std::int64_t allowedExtra = historySize * kPseudorandomBandMeters;
        std::int64_t selectedHash = std::numeric_limits<std::int64_t>::max();
        std::int64_t selectedStart = deterministicBest->first;
        std::size_t candidateCount = 0;
        for (const auto& [gapLength, score] : eligibleSizes) {
            if (score - bestScore > allowedExtra) continue;
            const auto first = gaps.lower_bound({gapLength, 0});
            const auto after = gaps.upper_bound(
                {gapLength, std::numeric_limits<std::int64_t>::max()});
            if (first == after) continue;
            std::array<std::int64_t, 8> representativeStarts{};
            std::size_t representativeCount = 0;
            auto low = first;
            for (std::size_t i = 0; i < 4 && low != after; ++i, ++low) {
                representativeStarts[representativeCount++] = low->second;
            }
            auto high = after;
            for (std::size_t i = 0; i < 4 && high != first; ++i) {
                --high;
                const std::int64_t start = high->second;
                bool alreadyIncluded = false;
                for (std::size_t j = 0; j < representativeCount; ++j) {
                    if (representativeStarts[j] == start) alreadyIncluded = true;
                }
                if (!alreadyIncluded) representativeStarts[representativeCount++] = start;
            }
            for (std::size_t i = 0; i < representativeCount; ++i) {
                const std::int64_t start = representativeStarts[i];
                ++candidateCount;
                std::uint64_t key = observedCommandHash;
                key = mix64(key ^ mix64(static_cast<std::uint64_t>(pipes.size())));
                key = mix64(key ^ mix64(static_cast<std::uint64_t>(length)));
                key = mix64(key ^ mix64(static_cast<std::uint64_t>(start)));
                key = mix64(key ^ mix64(static_cast<std::uint64_t>(gapLength)));
                key = mix64(key ^ mix64(static_cast<std::uint64_t>(trenchLength)));
                key = mix64(key ^ static_cast<std::uint64_t>(highSide));
                if (key < static_cast<std::uint64_t>(selectedHash)) {
                    selectedHash = static_cast<std::int64_t>(key & 0x7fffffffffffffffULL);
                    selectedStart = start;
                }
            }
        }
        pseudoHashMaxCandidates = std::max(pseudoHashMaxCandidates, candidateCount);
        if (candidateCount > 1) {
            ++pseudoHashChoices;
            if (selectedStart != deterministicBest->first) ++pseudoHashChangedChoices;
        }
        return freeByStart.find(selectedStart);
    }

'''
source = source[:start] + new_function + source[end:]

private_marker = "private:\n    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;\n"
assert source.count(private_marker) == 1
source = source.replace(
    private_marker,
    private_marker
    + "\n    static std::uint64_t mix64(std::uint64_t value) {\n"
    + "        value += 0x9e3779b97f4a7c15ULL;\n"
    + "        value = (value ^ (value >> 30U)) * 0xbf58476d1ce4e5b9ULL;\n"
    + "        value = (value ^ (value >> 27U)) * 0x94d049bb133111ebULL;\n"
    + "        return value ^ (value >> 31U);\n"
    + "    }\n",
)

main_placement = "            allocator.place(static_cast<int>(command));\n"
main_removal = "            allocator.remove(-command);\n"
assert source.count(main_placement) == 1 and source.count(main_removal) == 1
source = source.replace(main_placement, main_placement + "            allocator.observeCommand(command);\n")
source = source.replace(main_removal, main_removal + "            allocator.observeCommand(command);\n")

terminator = "        if (command == 0) {\n"
assert source.count(terminator) == 1
source = source.replace(
    terminator,
    terminator
    + "#if defined(PSEUDORANDOM_TIE_DIAGNOSTICS)\n"
    + "            std::cerr << \"pseudo_hash_choices=\" << allocator.pseudoHashChoices\n"
    + "                      << \" changed=\" << allocator.pseudoHashChangedChoices\n"
    + "                      << \" max_candidates=\" << allocator.pseudoHashMaxCandidates << '\\n';\n"
    + "#endif\n",
)

for band, name in [(0, "exact"), (1, "near1"), (2, "near2")]:
    candidate = source.replace(
        "namespace {\n",
        f"namespace {{\n\nconstexpr std::int64_t kPseudorandomBandMeters = {band};\n",
        1,
    )
    target = OUT / "source" / f"pseudorandom_{name}.cpp"
    target.write_text(candidate)
    print(target)
