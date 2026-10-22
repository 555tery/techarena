from __future__ import annotations

import json
import random
from pathlib import Path


ROOT = Path("results/pipes/improvement/case9_neighbor_coalescence")
BASE = Path(
    "results/pipes/improvement/case9_hole_first_cohorts/source/"
    "hole_first_survivor_cohorts_plus_lifo_gate.cpp"
)


def add_live_address_index(source: str) -> str:
    anchor = "    std::vector<Pipe> pipes{Pipe{}};  // PID is the vector index.\n"
    assert source.count(anchor) == 1
    source = source.replace(
        anchor,
        anchor + "    std::map<std::int64_t, int> activeByStart;\n",
        1,
    )
    # Index every actual placement, both in slab and ordinary allocation paths.
    anchor = "            pipes.push_back(Pipe{start, length, true, sizeCohort});\n"
    assert source.count(anchor) == 1
    source = source.replace(
        anchor,
        anchor + "            activeByStart.emplace(start, pid);\n",
        1,
    )
    anchor = "\n        pipes.push_back(Pipe{start, length, true, sizeCohort});\n"
    assert source.count(anchor) == 1
    source = source.replace(
        anchor,
        anchor + "        activeByStart.emplace(start, pid);\n",
        1,
    )
    anchor = "        pipes[index].active = false;\n"
    assert source.count(anchor) == 1
    source = source.replace(
        anchor,
        anchor + "        activeByStart.erase(pipe.start);\n",
        1,
    )
    return source


def side_policy(source: str) -> str:
    source = add_live_address_index(source)
    anchor = (
        "                StartIter reusableGap = bestFittingGapBefore(\n"
        "                    length, false, sizeCohort, cohortSlabBase);\n"
        "                if (reusableGap != freeByStart.end()) {\n"
        "                    start = consumeAtSide(reusableGap, length, false);\n"
    )
    replacement = (
        "                StartIter reusableGap = bestFittingGapBefore(\n"
        "                    length, false, sizeCohort, cohortSlabBase);\n"
        "                if (reusableGap != freeByStart.end()) {\n"
        "                    const bool highSide = coalesceSideFor(reusableGap);\n"
        "                    start = consumeAtSide(reusableGap, length, highSide);\n"
    )
    assert source.count(anchor) == 1
    source = source.replace(anchor, replacement, 1)
    anchor = "    StartIter bestFittingGapBefore(\n"
    helper = (
        "    bool coalesceSideFor(StartIter gap) const {\n"
        "        auto left = activeByStart.lower_bound(gap->first);\n"
        "        if (left != activeByStart.begin()) --left;\n"
        "        bool leftDeleted = false;\n"
        "        if (left != activeByStart.end()) {\n"
        "            const Pipe& pipe = pipes[static_cast<std::size_t>(left->second)];\n"
        "            leftDeleted = pipe.start + pipe.length == gap->first &&\n"
        "                alternatingDeleteMode &&\n"
        "                ((left->second & 1) == predictedDeletedParity);\n"
        "        }\n"
        "        auto right = activeByStart.lower_bound(gap->second);\n"
        "        const bool rightDeleted = right != activeByStart.end() &&\n"
        "            right->first == gap->second && alternatingDeleteMode &&\n"
        "            ((right->second & 1) == predictedDeletedParity);\n"
        "        // Leave the residual touching the boundary pipe predicted to be\n"
        "        // removed, so its deletion can coalesce with this residual.\n"
        "        if (leftDeleted != rightDeleted) return leftDeleted;\n"
        "        return false;\n"
        "    }\n\n"
    )
    assert source.count(anchor) == 1
    source = source.replace(anchor, helper + anchor, 1)
    return source


def merge_choice_policy(source: str) -> str:
    source = add_live_address_index(source)
    source = source.replace(
        "    int cohortSlabTailPipeCount = 0;\n",
        "    int cohortSlabTailPipeCount = 0;\n"
        "    int cohortSlabNextSize = 0;\n",
        1,
    )
    source = source.replace(
        "                StartIter reusableGap = bestFittingGapBefore(\n"
        "                    length, false, sizeCohort, cohortSlabBase);\n"
        "                if (reusableGap != freeByStart.end()) {\n"
        "                    start = consumeAtSide(reusableGap, length, false);\n",
        "                bool highSide = false;\n"
        "                StartIter reusableGap = coalescingGapBefore(\n"
        "                    length, sizeCohort, cohortSlabBase, highSide);\n"
        "                if (reusableGap != freeByStart.end()) {\n"
        "                    start = consumeAtSide(reusableGap, length, highSide);\n",
        1,
    )
    anchor = "        cohortSlabTailPipeCount = tailPipeCount;\n"
    assert source.count(anchor) == 1
    source = source.replace(
        anchor,
        anchor + "        cohortSlabNextSize = predictedNextSize;\n",
        1,
    )
    anchor = "    StartIter bestFittingGapBefore(\n"
    helper = (
        "    StartIter coalescingGapBefore(\n"
        "        int length, int sizeCohort, std::int64_t endLimit, bool& highSide) {\n"
        "        StartIter fallback = bestFittingGapBefore(\n"
        "            length, false, sizeCohort, endLimit);\n"
        "        StartIter best = fallback;\n"
        "        std::int64_t bestCapacityGain = 0;\n"
        "        std::int64_t bestFitScore = fallback == freeByStart.end()\n"
        "            ? std::numeric_limits<std::int64_t>::max()\n"
        "            : scoreGap(fallback->second - fallback->first, length);\n"
        "        bool bestHighSide = false;\n"
        "        if (!alternatingDeleteMode || cohortSlabNextSize <= length) {\n"
        "            highSide = false;\n"
        "            return fallback;\n"
        "        }\n"
        "        for (auto it = freeByStart.begin(); it != freeByStart.end(); ++it) {\n"
        "            if (it->second > endLimit || it->second - it->first < length) continue;\n"
        "            if (parityCohortMode) {\n"
        "                const int owner = gapCohort.at(it->first);\n"
        "                if (owner >= 0 && owner != sizeCohort) continue;\n"
        "            }\n"
        "            const std::int64_t slack = it->second - it->first - length;\n"
        "            auto left = activeByStart.lower_bound(it->first);\n"
        "            if (left != activeByStart.begin()) --left;\n"
        "            std::int64_t leftGain = 0;\n"
        "            if (left != activeByStart.end()) {\n"
        "                const Pipe& pipe = pipes[static_cast<std::size_t>(left->second)];\n"
        "                if (pipe.start + pipe.length == it->first &&\n"
        "                    ((left->second & 1) == predictedDeletedParity)) {\n"
        "                    leftGain = (slack + pipe.length) / cohortSlabNextSize -\n"
        "                        slack / cohortSlabNextSize;\n"
        "                }\n"
        "            }\n"
        "            auto right = activeByStart.lower_bound(it->second);\n"
        "            std::int64_t rightGain = 0;\n"
        "            if (right != activeByStart.end() && right->first == it->second &&\n"
        "                ((right->second & 1) == predictedDeletedParity)) {\n"
        "                const Pipe& pipe = pipes[static_cast<std::size_t>(right->second)];\n"
        "                rightGain = (slack + pipe.length) / cohortSlabNextSize -\n"
        "                    slack / cohortSlabNextSize;\n"
        "            }\n"
        "            const bool useHigh = leftGain > rightGain;\n"
        "            const std::int64_t gain = std::max(leftGain, rightGain);\n"
        "            const std::int64_t fitScore = scoreGap(it->second - it->first, length);\n"
        "            if (gain > bestCapacityGain ||\n"
        "                (gain == bestCapacityGain && gain > 0 && fitScore < bestFitScore)) {\n"
        "                bestCapacityGain = gain;\n"
        "                bestFitScore = fitScore;\n"
        "                best = it;\n"
        "                bestHighSide = useHigh;\n"
        "            }\n"
        "        }\n"
        "        highSide = bestCapacityGain > 0 ? bestHighSide : false;\n"
        "        return best;\n"
        "    }\n\n"
    )
    assert source.count(anchor) == 1
    source = source.replace(anchor, helper + anchor, 1)
    return source


def stream(name: str, sizes: list[int], counts: list[int], mode: str, seed: int) -> dict[str, object]:
    rng = random.Random(seed)
    commands: list[int] = []
    next_pid = 1
    for size, count in zip(sizes, counts, strict=True):
        pids = list(range(next_pid, next_pid + count))
        commands.extend([size] * count)
        if mode == "even":
            delete = pids[::2]
        elif mode == "odd":
            delete = pids[1::2]
        elif mode == "biased_even":
            delete = [pid for pid in pids if (pid % 2 == 0 and rng.random() < 0.9) or
                      (pid % 2 == 1 and rng.random() < 0.1)]
        elif mode == "random":
            delete = sorted(rng.sample(pids, count // 2))
        else:
            raise ValueError(mode)
        commands.extend(-pid for pid in delete)
        next_pid += count
    out = ROOT / "synthetic" / f"{name}.in"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join([f"1.0 {len(commands)}", *(str(c) for c in commands)]) + "\n")
    return {
        "name": name, "seed": seed, "sizes": sizes, "counts": counts,
        "deletion": mode, "commands": len(commands), "path": str(out),
    }


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    source = BASE.read_text()
    (ROOT / "source").mkdir(exist_ok=True)
    (ROOT / "source" / "baseline_hole_first_plus_lifo.cpp").write_text(source)
    (ROOT / "source" / "neighbor_boundary_side.cpp").write_text(side_policy(source))
    (ROOT / "source" / "neighbor_merge_capacity.cpp").write_text(merge_choice_policy(source))
    specs = [
        ("fresh_a", [1, 2, 4, 8, 16, 32], [360, 380, 400, 420, 440, 460], "even", 20261022),
        ("fresh_b", [2, 4, 8, 16, 32], [420, 400, 420, 400, 420], "odd", 20261023),
        ("fresh_c", [1, 3, 6, 12, 24], [480, 520, 500, 480, 520], "even", 20261024),
        ("fresh_d", [1, 2, 4, 8, 16, 32], [400, 420, 440, 460, 480, 500], "biased_even", 20261025),
    ]
    metadata = [stream(*spec) for spec in specs]
    (ROOT / "synthetic" / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
