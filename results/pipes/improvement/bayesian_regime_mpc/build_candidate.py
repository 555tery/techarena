#!/usr/bin/env python3
"""Generate an isolated frozen-final variant with BOCPD MPC forecasts."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
FROZEN = REPO / "results/pipes/final/solution.cpp"
FROZEN_SHA = "c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991"
PARAMS = json.loads((ROOT / "model_params.json").read_text(encoding="utf-8"))
CLANGXX = shutil.which("clang++")
FLAGS = ["-O2", "-std=c++20", "-pipe", "-Wall", "-Wextra", "-Wconversion",
         "-Wshadow", "-pedantic", "-Werror"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


REGIME_CLASS = r'''
class BayesianRegimeModel {
    static constexpr std::size_t kCategories = 48;
    static constexpr std::size_t kMaxRunLength = 128;
    static constexpr double kHazard = @HAZARD@;
    static constexpr double kConcentration = @CONCENTRATION@;
    inline static constexpr std::array<double, kCategories> kBasePrior = {
        @PRIOR@
    };

    std::array<double, kMaxRunLength + 1> runProbability_{};
    std::array<int, kMaxRunLength> history_{};
    std::size_t historyCount_ = 0;
    std::size_t historyNext_ = 0;

    static std::uint32_t nextRandom(std::uint32_t& state) {
        state ^= state << 13U;
        state ^= state >> 17U;
        state ^= state << 5U;
        return state;
    }

    static double randomUnit(std::uint32_t& state) {
        return static_cast<double>(nextRandom(state)) / 4294967296.0;
    }

    std::size_t sampleRunLength(std::uint32_t& state) const {
        const double target = randomUnit(state);
        double cumulative = 0.0;
        for (std::size_t run = 0; run <= kMaxRunLength; ++run) {
            cumulative += runProbability_[run];
            if (target < cumulative) return run;
        }
        return kMaxRunLength;
    }

    int sampleCategory(std::uint32_t& state, bool onlyInsertions,
                       const std::array<int, kCategories>& counts) const {
        const std::size_t limit = onlyInsertions ? 40U : kCategories;
        double total = 0.0;
        for (std::size_t category = 0; category < limit; ++category) {
            total += static_cast<double>(counts[category]) +
                     kConcentration * kBasePrior[category];
        }
        double target = randomUnit(state) * total;
        for (std::size_t category = 0; category < limit; ++category) {
            const double weight = static_cast<double>(counts[category]) +
                                  kConcentration * kBasePrior[category];
            if (target < weight) return static_cast<int>(category);
            target -= weight;
        }
        return static_cast<int>(limit - 1U);
    }

    static int rankPermilleForBucket(std::size_t bucket) {
        if (bucket == 0U) return 0;
        if (bucket == 7U) return 1000;
        const std::size_t numerator = (2U * bucket + 1U) * 1000U;
        return static_cast<int>(numerator / 16U);
    }

    void observe(int symbol) {
        const std::size_t category = static_cast<std::size_t>(symbol);
        std::array<int, kMaxRunLength + 1> suffixCount{};
        int count = 0;
        for (std::size_t run = 1; run <= kMaxRunLength; ++run) {
            if (run <= historyCount_) {
                const std::size_t index =
                    (historyNext_ + kMaxRunLength - run) % kMaxRunLength;
                if (history_[index] == symbol) ++count;
            }
            suffixCount[run] = count;
        }

        std::array<double, kMaxRunLength + 1> likelihood{};
        likelihood[0] = kBasePrior[category];
        for (std::size_t run = 1; run <= kMaxRunLength; ++run) {
            likelihood[run] =
                (static_cast<double>(suffixCount[run]) +
                 kConcentration * kBasePrior[category]) /
                (static_cast<double>(run) + kConcentration);
        }

        double probabilitySum = 0.0;
        for (const double probability : runProbability_) probabilitySum += probability;
        std::array<double, kMaxRunLength + 1> updated{};
        updated[0] = kHazard * kBasePrior[category] * probabilitySum;
        for (std::size_t run = 0; run < kMaxRunLength; ++run) {
            updated[run + 1U] +=
                (1.0 - kHazard) * runProbability_[run] * likelihood[run];
        }
        updated[kMaxRunLength] +=
            (1.0 - kHazard) * runProbability_[kMaxRunLength] *
            likelihood[kMaxRunLength];
        double normalizer = 0.0;
        for (const double probability : updated) normalizer += probability;
        for (std::size_t run = 0; run <= kMaxRunLength; ++run) {
            runProbability_[run] = updated[run] / normalizer;
        }

        history_[historyNext_] = symbol;
        historyNext_ = (historyNext_ + 1U) % kMaxRunLength;
        if (historyCount_ < kMaxRunLength) ++historyCount_;
    }

public:
    BayesianRegimeModel() { runProbability_[0] = 1.0; }

    void observeInsertion(int length) { observe(length - 1); }

    void observeRemoval(int rankPermille) {
        const int rank = std::clamp(rankPermille, 0, 1000);
        const std::size_t bucket = std::min(
            static_cast<std::size_t>(7U),
            static_cast<std::size_t>(rank) * 8U / 1001U);
        observe(40 + static_cast<int>(bucket));
    }

    std::array<Observation, kMcDepth> sampleScenario(
        std::uint32_t& randomState, std::size_t initialActive) const {
        std::array<Observation, kMcDepth> result{};
        std::array<int, kCategories> counts{};
        const std::size_t sampledRun =
            std::min(sampleRunLength(randomState), historyCount_);
        const std::size_t first =
            (historyNext_ + kMaxRunLength - sampledRun) % kMaxRunLength;
        for (std::size_t offset = 0; offset < sampledRun; ++offset) {
            const std::size_t index = (first + offset) % kMaxRunLength;
            ++counts[static_cast<std::size_t>(history_[index])];
        }

        int active = static_cast<int>(initialActive);
        for (std::size_t step = 0; step < kMcDepth; ++step) {
            if (randomUnit(randomState) < kHazard) counts.fill(0);
            const int symbol = sampleCategory(randomState, active == 0, counts);
            if (symbol < 40) {
                result[step] = Observation{1, symbol + 1};
                ++active;
            } else {
                const std::size_t bucket = static_cast<std::size_t>(symbol - 40);
                result[step] = Observation{-1, rankPermilleForBucket(bucket)};
                if (active > 0) --active;
            }
            ++counts[static_cast<std::size_t>(symbol)];
        }
        return result;
    }
};
'''


def main() -> None:
    if CLANGXX is None:
        raise SystemExit("clang++ is required for the registered native build")
    if sha(FROZEN) != FROZEN_SHA:
        raise SystemExit("frozen final changed; refusing to generate candidate")
    if PARAMS.get("train_stream_count") != 8:
        raise SystemExit("unexpected training matrix")
    prior = PARAMS["base_prior"]
    if len(prior) != 48 or abs(sum(prior) - 1.0) > 1e-10:
        raise SystemExit("invalid fitted base prior")

    source_dir = ROOT / "source"
    binary_dir = ROOT / "bin"
    source_dir.mkdir(parents=True, exist_ok=True)
    binary_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FROZEN, source_dir / "frozen_final.cpp")
    source = FROZEN.read_text(encoding="utf-8")
    class_code = REGIME_CLASS.replace("@HAZARD@", format(PARAMS["selected_hazard"], ".17g"))
    class_code = class_code.replace("@CONCENTRATION@",
                                    format(PARAMS["selected_concentration"], ".17g"))
    formatted_prior = ",\n        ".join(format(value, ".17g") for value in prior)
    class_code = class_code.replace("@PRIOR@", formatted_prior)

    anchor = "\nstruct Pipe {\n"
    if source.count(anchor) != 1:
        raise SystemExit("expected a unique Pipe declaration anchor")
    source = source.replace(anchor, "\n" + class_code + anchor, 1)
    source = source.replace(
        "    std::size_t mcRolloutsRun = 0;\n\n    void place(int length) {",
        "    std::size_t mcRolloutsRun = 0;\n"
        "    BayesianRegimeModel regimeModel;\n\n"
        "    void place(int length) {\n"
        "        regimeModel.observeInsertion(length);", 1)
    source = source.replace(
        "        const int rankPermille = rankFromNewestPermille(static_cast<int>(index));\n\n"
        "        const Pipe pipe = pipes[index];",
        "        const int rankPermille = rankFromNewestPermille(static_cast<int>(index));\n"
        "        regimeModel.observeRemoval(rankPermille);\n\n"
        "        const Pipe pipe = pipes[index];", 1)
    source = source.replace(
        "            scenarios[trial] = sampleScenario(randomState);",
        "            scenarios[trial] = regimeModel.sampleScenario(\n"
        "                randomState, activePipeCount + 1U);", 1)
    if source.count("regimeModel.observeInsertion(length);") != 1:
        raise SystemExit("insertion model hook was not installed")
    if source.count("regimeModel.observeRemoval(rankPermille);") != 1:
        raise SystemExit("deletion model hook was not installed")
    if "regimeModel.sampleScenario(" not in source:
        raise SystemExit("Bayesian scenario sampler was not installed")

    candidate_source = source_dir / "bayesian_regime_mpc.cpp"
    candidate_source.write_text(source, encoding="utf-8")
    print(f"frozen_source_sha256={sha(source_dir / 'frozen_final.cpp')}")
    print(f"candidate_source_sha256={sha(candidate_source)}")
    for name, input_source in (("frozen", source_dir / "frozen_final.cpp"),
                               ("bayesian", candidate_source)):
        binary = binary_dir / name
        command = [CLANGXX, *FLAGS, str(input_source), "-o", str(binary)]
        print("build:", " ".join(command))
        subprocess.run(command, cwd=REPO, check=True)
        print(f"{name}_binary_sha256={sha(binary)}")


if __name__ == "__main__":
    main()
