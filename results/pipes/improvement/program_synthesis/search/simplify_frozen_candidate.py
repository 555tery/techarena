#!/usr/bin/env python3
"""Flatten the selected depth-2 tree to its exact equivalent causal predicate."""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parents[0].parent
SOURCE = HERE / "src/tree_033_frozen.cpp"
OUTPUT = HERE / "src/tree_033_simplified.cpp"


def main():
    source = SOURCE.read_text()
    source = source.replace("#include <cstdlib>\n", "")
    table_start = source.index("struct PolicyTree {")
    table_end = source.index("struct Pipe {", table_start)
    source = source[:table_start] + source[table_end:]
    source = source.replace("    std::map<std::int64_t, int> activePipeByStart;\n", "")
    source = source.replace("    std::map<std::int64_t, int> activePipeByEnd;\n", "")
    source = source.replace("        activePipeByStart.emplace(start, pid);\n", "")
    source = source.replace("        activePipeByEnd.emplace(start + length, pid);\n", "")
    source = source.replace("        activePipeByStart.erase(pipe.start);\n", "")
    source = source.replace("        activePipeByEnd.erase(pipe.start + pipe.length);\n", "")
    start = source.index("    static int synthesisPolicyId()")
    end = source.index("    std::int64_t chooseGapWithRollout(", start)
    predicate = r'''    bool synthesisTreeAllows(int length, StartIter baselineGap) const {
        (void)length;
        (void)baselineGap;
        const std::size_t sampleCount = std::min<std::size_t>(64, recentLengths.size());
        std::size_t longCount = 0;
        std::size_t offset = 0;
        for (auto it = recentLengths.rbegin(); it != recentLengths.rend() && offset < sampleCount; ++it, ++offset) {
            if (*it >= 21) ++longCount;
        }
        return longCount <= 32;
    }

'''
    source = source[:start] + predicate + source[end:]
    OUTPUT.write_text(source)
    print(OUTPUT)


if __name__ == "__main__":
    main()
