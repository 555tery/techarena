#!/usr/bin/env python3
"""Build a bounded depth-2 policy-tree search binary from the frozen final."""

from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parents[0].parent
BASELINE = ROOT / "results/pipes/final/solution.cpp"
SOURCE = HERE / "src/policy_search.cpp"
SPECS = HERE / "search/tree_specs.csv"

# Features are computed from only the current request, current gap layout and
# bounded rolling history. Each tree has one root test, two child tests, and
# four binary leaves deciding whether this opportunity may consume MC budget.
THRESHOLDS = {
    0: [2, 4, 8, 12, 16, 24, 32],
    1: [0, 1, 2, 4, 8, 12, 16, 24, 40],
    2: [1, 2, 4, 8, 16, 32, 64, 128, 256, 512],
    3: [8, 32, 64, 128, 256, 512, 1024, 2048, 4096],
    4: [0, 1, 2, 4, 8, 16, 24, 40, 80, 160],
    5: [1, 2, 3, 4, 5, 8, 12, 16, 24, 32],
    6: [1, 2, 4, 8, 12, 16, 24, 32, 46, 64],
    7: [0, 1, 2, 4, 8, 16, 40, 80, 160, 320, 640, 1280, 2560, 5120],
    8: [0, 1, 2, 4, 8, 16, 32, 48, 64],
    9: [0, 1, 2, 4, 8, 16, 24, 32, 40, 48, 64],
    10: [0, 1, 2, 4, 8, 12, 16, 24, 32, 40],
    11: [0, 1, 2, 4, 8, 12, 16, 24, 32, 40],
}


def make_specs(count: int = 64, seed: int = 20261017):
    rng = random.Random(seed)
    rows = []
    for _ in range(count):
        fs = [rng.randrange(len(THRESHOLDS)) for _ in range(3)]
        ts = [rng.choice(THRESHOLDS[f]) for f in fs]
        mask = rng.randrange(1, 15)
        rows.append((fs[0], ts[0], fs[1], ts[1], fs[2], ts[2], mask))
    # Include simple interpretable gates at fixed IDs for sanity checks.
    rows[:8] = [
        (0, 4, 1, 0, 2, 32, 1),
        (0, 4, 1, 0, 2, 32, 2),
        (1, 4, 2, 64, 4, 16, 3),
        (5, 4, 6, 8, 7, 160, 5),
        (3, 512, 2, 64, 8, 16, 7),
        (7, 160, 0, 8, 4, 40, 11),
        (9, 16, 5, 8, 6, 16, 13),
        (8, 16, 1, 8, 7, 640, 14),
    ]
    return rows


def build_source(rows):
    source = BASELINE.read_text()
    source = source.replace("#include <cstdint>\n", "#include <cstdint>\n#include <cstdlib>\n")
    table = "\nstruct PolicyTree { int rootFeature; int rootThreshold; int leftFeature; int leftThreshold; int rightFeature; int rightThreshold; int leafMask; };\n"
    table += f"constexpr std::array<PolicyTree, {len(rows)}> kPolicyTrees{{{{\n"
    table += ",\n".join("    PolicyTree{%d, %d, %d, %d, %d, %d, %d}" % row for row in rows)
    table += "\n}};\n"
    source = source.replace("struct Pipe {", table + "\nstruct Pipe {")
    source = source.replace(
        "    std::vector<Pipe> pipes{Pipe{}};  // PID is the vector index.\n",
        "    std::vector<Pipe> pipes{Pipe{}};  // PID is the vector index.\n"
        "    std::map<std::int64_t, int> activePipeByStart;\n"
        "    std::map<std::int64_t, int> activePipeByEnd;\n")
    source = source.replace(
        "        pipes.push_back(Pipe{start, length, true, sizeCohort});\n",
        "        pipes.push_back(Pipe{start, length, true, sizeCohort});\n"
        "        activePipeByStart.emplace(start, pid);\n"
        "        activePipeByEnd.emplace(start + length, pid);\n")
    source = source.replace(
        "        pipes[index].active = false;\n",
        "        pipes[index].active = false;\n"
        "        activePipeByStart.erase(pipe.start);\n"
        "        activePipeByEnd.erase(pipe.start + pipe.length);\n")
    marker = "    std::int64_t chooseGapWithRollout(\n"
    method = r'''    static int synthesisPolicyId() {
        static const int id = [] {
            const char* raw = std::getenv("PIPES_POLICY_ID");
            if (raw == nullptr || *raw == '\0') return 0;
            char* end = nullptr;
            const long parsed = std::strtol(raw, &end, 10);
            if (end == raw || *end != '\0' || parsed < 0 || parsed > static_cast<long>(kPolicyTrees.size())) return 0;
            return static_cast<int>(parsed);
        }();
        return id;
    }

    std::array<std::int64_t, 12> synthesisFeatures(int length, StartIter gap) const {
        const std::int64_t end = gap->second;
        const std::int64_t gapLength = end - gap->first;
        const std::size_t sampleCount = std::min<std::size_t>(64, recentLengths.size());
        std::array<bool, 41> seen{};
        std::size_t distinct = 0;
        std::size_t sameLength = 0;
        std::size_t shortCount = 0;
        std::size_t longCount = 0;
        std::size_t offset = 0;
        for (auto it = recentLengths.rbegin(); it != recentLengths.rend() && offset < sampleCount; ++it, ++offset) {
            if (!seen[static_cast<std::size_t>(*it)]) {
                seen[static_cast<std::size_t>(*it)] = true;
                ++distinct;
            }
            if (*it == length) ++sameLength;
            if (*it <= 4) ++shortCount;
            if (*it >= 21) ++longCount;
        }
        std::int64_t tailLength = 0;
        if (!freeByStart.empty()) {
            const auto tail = std::prev(freeByStart.end());
            if (tail->second == trenchLength) tailLength = trenchLength - tail->first;
        }
        const std::int64_t distanceToTail = std::max<std::int64_t>(0, trenchLength - end);
        std::int64_t leftNeighborLength = 0;
        const auto leftNeighbor = activePipeByEnd.find(gap->first);
        if (leftNeighbor != activePipeByEnd.end()) {
            leftNeighborLength = pipes[static_cast<std::size_t>(leftNeighbor->second)].length;
        }
        std::int64_t rightNeighborLength = 0;
        const auto rightNeighbor = activePipeByStart.find(end);
        if (rightNeighbor != activePipeByStart.end()) {
            rightNeighborLength = pipes[static_cast<std::size_t>(rightNeighbor->second)].length;
        }
        return {static_cast<std::int64_t>(length),
                gapLength - length,
                static_cast<std::int64_t>(freeByStart.size()),
                static_cast<std::int64_t>(activePipeCount),
                tailLength,
                static_cast<std::int64_t>(distinct),
                static_cast<std::int64_t>(sameLength),
                distanceToTail,
                static_cast<std::int64_t>(shortCount),
                static_cast<std::int64_t>(longCount),
                leftNeighborLength,
                rightNeighborLength};
    }

    bool synthesisTreeAllows(int length, StartIter baselineGap) const {
        const int id = synthesisPolicyId();
        if (id == 0) return true;
        const PolicyTree& tree = kPolicyTrees[static_cast<std::size_t>(id - 1)];
        const auto x = synthesisFeatures(length, baselineGap);
        const bool root = x[static_cast<std::size_t>(tree.rootFeature)] <= tree.rootThreshold;
        const bool branch = root
            ? x[static_cast<std::size_t>(tree.leftFeature)] <= tree.leftThreshold
            : x[static_cast<std::size_t>(tree.rightFeature)] <= tree.rightThreshold;
        const int leaf = root ? (branch ? 0 : 1) : (branch ? 2 : 3);
        return ((tree.leafMask >> leaf) & 1) != 0;
    }

'''
    if marker not in source:
        raise RuntimeError("chooseGapWithRollout marker not found")
    source = source.replace(marker, method + marker)
    gate = """        if (mcDecisionsUsed >= kMcDecisionBudget ||
            observedHistory.size() < 32 || freeByStart.size() > kMcMaxGaps ||
            activePipeCount > kMcMaxActivePipes) {
            return baselineGap->first;
        }
"""
    replacement = gate + "        if (!synthesisTreeAllows(length, baselineGap)) return baselineGap->first;\n"
    if gate not in source:
        raise RuntimeError("MC budget gate not found")
    source = source.replace(gate, replacement, 1)
    SOURCE.write_text(source)


def main():
    rows = make_specs()
    with SPECS.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["policy_id", "root_feature", "root_threshold", "left_feature", "left_threshold", "right_feature", "right_threshold", "leaf_mask"])
        for i, row in enumerate(rows, 1):
            writer.writerow([i, *row])
    build_source(rows)
    print(f"wrote {len(rows)} bounded depth-2 trees and {SOURCE}")


if __name__ == "__main__":
    main()
