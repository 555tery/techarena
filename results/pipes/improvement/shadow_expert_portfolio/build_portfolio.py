#!/usr/bin/env python3
"""Create the portfolio solver from immutable frozen and PID/46 sources."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
FROZEN = REPO / "results/pipes/final/solution.cpp"
PID46 = REPO / "results/pipes/improvement/case9_next/preliminary_pid_lane_excluded/source/proactive_pid_lanes_preprobe.cpp"
FROZEN_SHA = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
PID46_SHA = "1a643a2b8a560de5c7dfd7efe0b288dc93785e96400d2ae6fd4ec7eea5f55f59"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one {label} pattern; found {count}")
    return source.replace(old, new, 1)


def replace_once_after(source: str, anchor: str, old: str, new: str,
                       label: str) -> str:
    start = source.find(anchor)
    if start < 0:
        raise SystemExit(f"missing anchor for {label}")
    return source[:start] + replace_once(source[start:], old, new, label)


def main() -> None:
    if digest(FROZEN) != FROZEN_SHA or digest(PID46) != PID46_SHA:
        raise SystemExit("source identity changed; refusing to generate solver")
    source = FROZEN.read_text(encoding="utf-8")

    source = replace_once(
        source,
        "#include <cstdint>\n",
        "#include <cstdint>\n#include <cmath>\n",
        "cmath include",
    )
    source = replace_once(
        source,
        "    std::size_t strideTwoDeleteTransitions = 0;\n\n    bool hasSteadySizeTrend() const {",
        "    std::size_t strideTwoDeleteTransitions = 0;\n"
        "    bool usePidLanePolicy = false;\n\n"
        "    bool hasSteadySizeTrend() const {",
        "rollout policy state",
    )
    source = replace_once(
        source,
        "        const bool highSide = runLeftActive\n"
        "            ? (sizeCohort != 0)\n"
        "            : (alternatingDeleteMode\n"
        "                ? ((nextPid & 1) != predictedDeletedParity)\n",
        "        const bool highSide = runLeftActive\n"
        "            ? (usePidLanePolicy ? ((nextPid & 1) == 0) : (sizeCohort != 0))\n"
        "            : (alternatingDeleteMode\n"
        "                ? ((nextPid & 1) != predictedDeletedParity)\n",
        "rollout PID/46 lane",
    )
    source = replace_once(
        source,
        "class Allocator {\npublic:\n",
        "class Allocator {\npublic:\n"
        "    explicit Allocator(bool pidLanePolicy = false, bool emitOutput = true)\n"
        "        : pidLanePolicy_(pidLanePolicy), emitOutput_(emitOutput),\n"
        "          activeLanePolicy_(pidLanePolicy) {}\n\n",
        "allocator constructor",
    )
    source = replace_once_after(
        source,
        "class Allocator {",
        "    void place(int length) {\n        const int sizeCohort = static_cast<int>(\n",
        "    void place(int length) { placeWithPolicy(length, pidLanePolicy_); }\n\n"
        "    void placeWithPolicy(int length, bool usePidLanePolicy) {\n"
        "        activeLanePolicy_ = usePidLanePolicy;\n"
        "        const int sizeCohort = static_cast<int>(\n",
        "allocator policy dispatch",
    )
    source = replace_once(
        source,
        "        const bool highSide = runLeftActive\n"
        "            ? (sizeCohort != 0)\n"
        "            : (alternatingDeleteMode\n"
        "                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)\n",
        "        const bool highSide = runLeftActive\n"
        "            ? (usePidLanePolicy\n"
        "                ? ((pipes.size() & 1U) == 0U)\n"
        "                : (sizeCohort != 0))\n"
        "            : (alternatingDeleteMode\n"
        "                ? ((static_cast<int>(pipes.size()) & 1) != predictedDeletedParity)\n",
        "real PID/46 lane",
    )
    source = replace_once(
        source,
        "        state.strideTwoDeleteTransitions = strideTwoDeleteTransitions;\n"
        "        state.active.reserve(activePipeCount + 1);",
        "        state.strideTwoDeleteTransitions = strideTwoDeleteTransitions;\n"
        "        state.usePidLanePolicy = activeLanePolicy_;\n"
        "        state.active.reserve(activePipeCount + 1);",
        "rollout mode propagation",
    )
    source = replace_once(
        source,
        "private:\n    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;\n",
        "private:\n"
        "    bool pidLanePolicy_ = false;\n"
        "    bool emitOutput_ = true;\n"
        "    bool activeLanePolicy_ = false;\n"
        "    using StartIter = std::map<std::int64_t, std::int64_t>::iterator;\n",
        "allocator policy fields",
    )
    source = replace_once(
        source,
        "        std::cout << pipe.start << '\\n' << std::flush;\n",
        "        if (emitOutput_) std::cout << pipe.start << '\\n' << std::flush;\n",
        "silent shadow deletion",
    )
    source = replace_once(
        source,
        "    static void printPlacement(std::int64_t digs, std::int64_t start) {\n"
        "        std::cout << digs << ' ' << start << '\\n' << std::flush;\n"
        "    }\n\n"
        "    static void printInvalidPidFallback() {\n"
        "        // Contest inputs guarantee an active PID. This keeps a malformed input\n"
        "        // from causing an out-of-bounds access while preserving protocol shape.\n"
        "        std::cout << 0 << '\\n' << std::flush;\n"
        "    }",
        "    void printPlacement(std::int64_t digs, std::int64_t start) const {\n"
        "        if (!emitOutput_) return;\n"
        "        std::cout << digs << ' ' << start << '\\n' << std::flush;\n"
        "    }\n\n"
        "    void printInvalidPidFallback() const {\n"
        "        if (!emitOutput_) return;\n"
        "        std::cout << 0 << '\\n' << std::flush;\n"
        "    }",
        "output suppression",
    )
    main_anchor = "int main() {\n"
    if source.count(main_anchor) != 1:
        raise SystemExit("expected exactly one original main()")
    main_cpp = r'''int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    constexpr double kEta = 0.05;
    constexpr double kShare = 1.0 / 1024.0;
    std::array<double, 2> weights{0.5, 0.5};
    std::array<std::size_t, 2> actualMcDecisionUse{};
    std::array<std::size_t, 2> selectedCount{};
    std::uint32_t randomState = 0x51A0D00DU;
    std::size_t switches = 0;
    int lastSelected = -1;
    Allocator frozenShadow(false, false);
    Allocator pid46Shadow(true, false);
    Allocator realState(false, true);

    const auto nextRandom = [&randomState]() {
        randomState ^= randomState << 13U;
        randomState ^= randomState >> 17U;
        randomState ^= randomState << 5U;
        return randomState;
    };
    const auto updateWeights = [&weights](double loss0, double loss1) {
        const double raw0 = weights[0] * std::exp(-kEta * loss0);
        const double raw1 = weights[1] * std::exp(-kEta * loss1);
        const double normalizer = raw0 + raw1;
        weights[0] = (1.0 - kShare) * raw0 / normalizer + 0.5 * kShare;
        weights[1] = 1.0 - weights[0];
    };

    std::int64_t command = 0;
    while (std::cin >> command) {
        if (command == 0) {
            std::cerr << "shadow_final_trench=" << frozenShadow.trenchLength
                      << " shadow_pid46_trench=" << pid46Shadow.trenchLength
                      << " real_trench=" << realState.trenchLength
                      << " frozen_picks=" << selectedCount[0]
                      << " pid46_picks=" << selectedCount[1]
                      << " switches=" << switches
                      << " real_mc_rollouts=" << realState.mcRolloutsRun << '\n';
            return 0;
        }
        if (command > 0) {
            const double draw = static_cast<double>(nextRandom()) / 4294967296.0;
            const std::size_t selected = draw < weights[0] ? 0U : 1U;
            if (lastSelected >= 0 && static_cast<std::size_t>(lastSelected) != selected) ++switches;
            lastSelected = static_cast<int>(selected);
            ++selectedCount[selected];
            const std::int64_t before0 = frozenShadow.trenchLength;
            const std::int64_t before1 = pid46Shadow.trenchLength;
            frozenShadow.place(static_cast<int>(command));
            pid46Shadow.place(static_cast<int>(command));
            realState.mcDecisionsUsed = actualMcDecisionUse[selected];
            realState.placeWithPolicy(static_cast<int>(command), selected == 1U);
            actualMcDecisionUse[selected] = realState.mcDecisionsUsed;
            const double loss0 = static_cast<double>(frozenShadow.trenchLength - before0) / 40.0;
            const double loss1 = static_cast<double>(pid46Shadow.trenchLength - before1) / 40.0;
            updateWeights(loss0, loss1);
        } else {
            const std::int64_t pid = -command;
            frozenShadow.remove(pid);
            pid46Shadow.remove(pid);
            realState.remove(pid);
            updateWeights(0.0, 0.0);
        }
    }
    return 0;
}
'''
    source = source[:source.index(main_anchor)] + main_cpp

    source_dir = ROOT / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FROZEN, source_dir / "frozen_final.cpp")
    shutil.copy2(PID46, source_dir / "pid46.cpp")
    output = source_dir / "shadow_portfolio.cpp"
    output.write_text(source, encoding="utf-8")
    print(f"generated {output}")
    print(f"frozen={digest(FROZEN)} pid46={digest(PID46)} "
          f"portfolio={digest(output)}")


if __name__ == "__main__":
    main()
