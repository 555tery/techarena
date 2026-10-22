#!/usr/bin/env python3
"""Create isolated C++ sources from audited frozen/learned templates."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OLD = ROOT / "results/pipes/improvement/learned_gap_value"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    candidate_template = OLD / "src/learned_gap_value.cpp"
    candidate = candidate_template.read_text(encoding="utf-8")
    candidate = replace_once(candidate, '#include "learned_model.hpp"',
                              '#include "ranker_model.hpp"', "candidate model include")
    (HERE / "src/ranker_candidate.cpp").write_text(candidate, encoding="utf-8")

    label_template = OLD / "src/label_runner.cpp"
    labeler = label_template.read_text(encoding="utf-8")
    labeler = replace_once(labeler, "    constexpr int kLabelHorizon = 512;\n", "",
                           "remove fixed label horizon")
    labeler = replace_once(
        labeler,
        "if (index >= 360 && index % cadence == 0 && index + kLabelHorizon < count) {",
        "if (index >= 360 && index % cadence == 0 && index + 1 < count) {",
        "sample before nonempty suffix",
    )
    labeler = replace_once(
        labeler,
        """                            for (int step = 1; step <= kLabelHorizon; ++step) {
                                const int future = commands[static_cast<std::size_t>(index + step)];
                                if (future > 0) {
                                    after.place(future);
                                } else if (future < 0) {
                                    if (!after.removeByPid(-future).has_value()) return 9;
                                } else {
                                    return 10;
                                }
                            }
""",
        """                            for (int futureIndex = index + 1; futureIndex < count; ++futureIndex) {
                                const int future = commands[static_cast<std::size_t>(futureIndex)];
                                if (future > 0) {
                                    after.place(future);
                                } else if (future < 0) {
                                    if (!after.removeByPid(-future).has_value()) return 9;
                                }
                            }
""",
        "replay exact suffix through EOF",
    )

    old_advance = """            const std::int64_t oldTrench = state.trenchLength;
            state.place(length);
            const std::int64_t digs = (state.trenchLength - oldTrench) / kDigLength;
            const std::int64_t start = state.active.back().start;
            const auto& reply = expected[static_cast<std::size_t>(index)];
            if (reply.size() != 2 || reply[0] != digs || reply[1] != start) {
                std::cerr << "baseline placement mismatch at " << index << ": expected "
                          << (reply.empty() ? -1 : reply[0]) << ' '
                          << (reply.size() < 2 ? -1 : reply[1]) << " got " << digs << ' ' << start << '\\n';
                return 11;
            }
"""
    new_advance = """            const auto& reply = expected[static_cast<std::size_t>(index)];
            if (reply.size() != 2) return 11;
            RolloutState baselineAfter = state;
            const std::int64_t oldTrench = baselineAfter.trenchLength;
            baselineAfter.place(length);
            const std::int64_t baselineDigs = (baselineAfter.trenchLength - oldTrench) / kDigLength;
            const std::int64_t baselineStart = baselineAfter.active.back().start;
            if (reply[0] == baselineDigs && reply[1] == baselineStart) {
                state = std::move(baselineAfter);
            } else {
                if (state.hasSmoothSizeTrendWith(length)) state.runLeftDisabledBySmoothTrend = true;
                const int cohort = static_cast<int>(
                    state.lengthOccurrenceCount[static_cast<std::size_t>(length)] % 2);
                const bool runLeftActive = !state.runLeftDisabledBySmoothTrend &&
                    state.hasSameLengthRecentRun(length);
                const bool highSide = runLeftActive
                    ? cohort != 0
                    : (state.alternatingDeleteMode
                        ? ((state.nextPid & 1) != state.predictedDeletedParity)
                        : (state.parityCohortMode
                            ? cohort == 0
                            : (length <= 4 || state.hasSameLengthRecentRun(length))));
                bool matchedCandidate = false;
                if (reply[0] == 0) {
                    for (const auto& [gapStart, gap] : state.gaps) {
                        if (gap.end - gapStart < length) continue;
                        const std::int64_t expectedStart = highSide
                            ? gap.end - static_cast<std::int64_t>(length) : gapStart;
                        if (reply[1] == expectedStart) {
                            state.placeAtCandidate(gapStart, length, highSide);
                            matchedCandidate = true;
                            break;
                        }
                    }
                }
                if (!matchedCandidate) {
                    std::cerr << "trajectory reply cannot be replayed at " << index
                              << ": got " << reply[0] << ' ' << reply[1]
                              << ", greedy expected " << baselineDigs << ' ' << baselineStart << '\\n';
                    return 11;
                }
            }
"""
    labeler = replace_once(labeler, old_advance, new_advance,
                           "advance along supplied baseline or candidate trajectory")
    target = HERE / "src/full_suffix_labeler.cpp"
    target.write_text(labeler, encoding="utf-8")

    manifest = {
        "frozen_source_sha256": sha256(ROOT / "results/pipes/final/solution.cpp"),
        "canonical_source_sha256": sha256(ROOT / "src/pipes.cpp"),
        "candidate_template_sha256": sha256(candidate_template),
        "labeler_template_sha256": sha256(label_template),
        "candidate_source_sha256": sha256(HERE / "src/ranker_candidate.cpp"),
        "labeler_source_sha256": sha256(target),
    }
    (HERE / "source_manifest.json").write_text(__import__("json").dumps(manifest, indent=2) + "\n",
                                                encoding="utf-8")
    print(f"candidate={manifest['candidate_source_sha256']}")
    print(f"labeler={manifest['labeler_source_sha256']}")


if __name__ == "__main__":
    main()
