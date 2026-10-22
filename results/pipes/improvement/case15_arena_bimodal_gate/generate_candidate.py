from pathlib import Path


ROOT = Path("results/pipes/improvement/case15_arena_bimodal_gate")
BASE = Path("results/pipes/improvement/case15_size_arenas/source/coarse_size_class_arenas.cpp")
source = BASE.read_text()


def replace_once(old: str, new: str) -> None:
    global source
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected one anchor, found {count}: {old[:100]!r}")
    source = source.replace(old, new, 1)


replace_once(
    "constexpr std::size_t kSizeArenaClassCount = 3;\n",
    "constexpr std::size_t kSizeArenaClassCount = 3;\n"
    "constexpr std::size_t kArenaShapeWindow = 512;\n",
)

replace_once(
    "    std::array<std::size_t, kSizeArenaClassCount> recentArenaClassCount{};\n",
    "    std::array<std::size_t, kSizeArenaClassCount> recentArenaClassCount{};\n"
    "    std::deque<int> recentArenaShapeLengths;\n"
    "    std::array<std::size_t, kSizeArenaClassCount> recentArenaShapeCount{};\n"
    "    std::deque<int> recentArenaOperationKinds;\n"
    "    std::size_t recentArenaDeletionCount = 0;\n",
)

replace_once(
    "    bool sizeArenaModeActive() const {\n"
    "        const std::size_t historySize = recentLengths.size();\n"
    "        if (historySize < 128) return false;\n"
    "        std::size_t supportedClasses = 0;\n"
    "        for (const std::size_t count : recentArenaClassCount) {\n"
    "            if (count >= 16 && count * 8U >= historySize) ++supportedClasses;\n"
    "        }\n"
    "        return supportedClasses >= 2;\n"
    "    }",
    "    bool sizeArenaModeActive() const {\n"
    "        const std::size_t sampleSize = recentArenaShapeLengths.size();\n"
    "        const std::size_t operationCount = recentArenaOperationKinds.size();\n"
    "        if (sampleSize < 128 || operationCount < 128 ||\n"
    "            recentArenaDeletionCount * 4U < operationCount) {\n"
    "            return false;\n"
    "        }\n"
    "        const std::size_t small = recentArenaShapeCount[0];\n"
    "        const std::size_t middle = recentArenaShapeCount[1];\n"
    "        const std::size_t large = recentArenaShapeCount[2];\n"
    "        const std::size_t minorityOuter = std::min(small, large);\n"
    "        return small * 8U >= sampleSize && large * 8U >= sampleSize &&\n"
    "            middle * 2U < minorityOuter;\n"
    "    }",
)

replace_once(
    "    void recordObservation(const Observation& event) {\n"
    "        observedHistory.push_back(event);\n"
    "        if (observedHistory.size() > kMcHistory) observedHistory.pop_front();\n"
    "    }",
    "    void recordObservation(const Observation& event) {\n"
    "        recentArenaOperationKinds.push_back(event.kind);\n"
    "        if (event.kind == -1) ++recentArenaDeletionCount;\n"
    "        if (recentArenaOperationKinds.size() > kArenaShapeWindow) {\n"
    "            if (recentArenaOperationKinds.front() == -1) --recentArenaDeletionCount;\n"
    "            recentArenaOperationKinds.pop_front();\n"
    "        }\n"
    "        observedHistory.push_back(event);\n"
    "        if (observedHistory.size() > kMcHistory) observedHistory.pop_front();\n"
    "    }",
)

replace_once(
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
    "        recentArenaShapeLengths.push_back(length);\n"
    "        ++recentArenaShapeCount[static_cast<std::size_t>(arenaClassForLength(length))];\n"
    "        if (recentArenaShapeLengths.size() > kArenaShapeWindow) {\n"
    "            const int shapeOldLength = recentArenaShapeLengths.front();\n"
    "            --recentArenaShapeCount[static_cast<std::size_t>(arenaClassForLength(shapeOldLength))];\n"
    "            recentArenaShapeLengths.pop_front();\n"
    "        }\n"
    "    }",
)

(ROOT / "source/bimodal_churn_gate.cpp").write_text(source)
print("wrote", ROOT / "source/bimodal_churn_gate.cpp")
