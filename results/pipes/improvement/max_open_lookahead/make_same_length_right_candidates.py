#!/usr/bin/env python3
"""Generate small T variants from the frozen adaptive right4 baseline."""

from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / "candidate_adaptive_right4_w2048_s60_baseline.cpp"
if not BASE.exists():
    original = HERE.parent / "max_open_sequence/candidate_adaptive_right4_w2048_s60.cpp"
    BASE.write_text(original.read_text(encoding="utf-8"), encoding="utf-8")

template = BASE.read_text(encoding="utf-8")
constant_anchor = "constexpr int kRightEdgeMaxPipeLength = 4;"
placement_anchor = "const std::int64_t placementStart = length <= kRightEdgeMaxPipeLength\n            ? end - static_cast<std::int64_t>(length) : start;"
method_anchor = "    std::int64_t consumeAtStart(StartIter it, int length) {\n"
for label, anchor in (("constant", constant_anchor), ("placement", placement_anchor), ("method", method_anchor)):
    if template.count(anchor) != 1:
        raise SystemExit(f"expected exactly one {label} anchor")

for threshold in (8, 16, 20, 24, 28, 32, 36, 40, 43, 44, 45, 46, 47, 48, 49, 50, 52, 56, 64, 72):
    source = template.replace(
        constant_anchor,
        constant_anchor + f"\nconstexpr std::size_t kSameLengthRightRun = {threshold};",
    )
    source = source.replace(
        placement_anchor,
        "const std::int64_t placementStart = (length <= kRightEdgeMaxPipeLength\n"
        "            || hasSameLengthRecentRun(length))\n"
        "            ? end - static_cast<std::int64_t>(length) : start;",
    )
    source = source.replace(
        method_anchor,
        "    bool hasSameLengthRecentRun(int length) const {\n"
        "        if (recentLengths.size() < kSameLengthRightRun) return false;\n"
        "        auto it = recentLengths.rbegin();\n"
        "        for (std::size_t seen = 0; seen < kSameLengthRightRun; ++seen, ++it) {\n"
        "            if (*it != length) return false;\n"
        "        }\n"
        "        return true;\n"
        "    }\n\n"
        + method_anchor,
    )
    target = HERE / f"candidate_adaptive_right4_w2048_s60_recent{threshold}_right.cpp"
    target.write_text(source, encoding="utf-8")
    print(target)
