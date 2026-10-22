#!/usr/bin/env python3
"""Reproduce a self-contained candidate from an exact archived baseline."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'case9_push_20261018/residual_slack/source/latest_leader_plus_c2.cpp'
EXPECTED = 'c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c'
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED
text = BASE.read_text()

def replace(old, new, count=1):
    global text
    assert text.count(old) == count, (old[:80], text.count(old), count)
    text = text.replace(old, new)

replace('namespace {\n', '''#ifndef COALESCENCE_POLICY
#define COALESCENCE_POLICY 1
#endif

namespace {
''')
replace('    int lastCompletedDeleteRelativeParity = -1;', '''    // Training labels are admitted only after their full observation window.
    static constexpr int seamTrainingWindow = 256;
    static constexpr int seamHorizon = 64;
    int seamClock = 0;
    std::vector<int> seamBirth{0};
    std::vector<int> seamDeath{0};
    std::deque<int> seamPending;
    std::array<std::array<int, 257>, 41> seamCdf{};
    std::uint64_t seamEligible = 0;
    std::uint64_t seamScored = 0;
    std::uint64_t seamChanges = 0;
    std::uint64_t seamGapChanges = 0;

    int lastCompletedDeleteRelativeParity = -1;''')
replace('    void place(int length) {\n        if (observedRunLength', '''    void place(int length) {
        advanceSeamClock();
        if (observedRunLength''')
replace('pipes.push_back(Pipe{start, length, true, sizeCohort});', '''pipes.push_back(Pipe{start, length, true, sizeCohort});
            recordSeamBirth();''', count=2)
replace('    void remove(std::int64_t pid) {\n', '''    void remove(std::int64_t pid) {
        advanceSeamClock();
''')
replace('        const Pipe pipe = pipes[index];\n        activeByEnd.erase', '''        const Pipe pipe = pipes[index];
        seamDeath[index] = seamClock;
        activeByEnd.erase''')
replace('            start = consumeAtSide(gap, length, highSide);\n        }', '''            if (!parityCohortMode && !sameSizeRun &&
                !additiveNextAlignment && !counterfactualCapacityChoice) {
                const auto seam = chooseDeletionSeam(length, gap, highSide);
                gap = seam.first;
                highSide = seam.second;
            }
            start = consumeAtSide(gap, length, highSide);
        }''')

methods = r'''
    void advanceSeamClock() {
        ++seamClock;
        while (!seamPending.empty()) {
            const int pid = seamPending.front();
            const std::size_t index = static_cast<std::size_t>(pid);
            if (seamBirth[index] + seamTrainingWindow > seamClock) break;
            seamPending.pop_front();
            const int death = seamDeath[index];
            const int life = death > 0
                ? std::min(seamTrainingWindow, death - seamBirth[index])
                : seamTrainingWindow;
            const std::size_t length = static_cast<std::size_t>(pipes[index].length);
            for (int age = life; age <= seamTrainingWindow; ++age) {
                ++seamCdf[length][static_cast<std::size_t>(age)];
                ++seamCdf[0][static_cast<std::size_t>(age)];
            }
        }
    }

    void recordSeamBirth() {
        const int pid = static_cast<int>(pipes.size()) - 1;
        seamBirth.push_back(seamClock);
        seamDeath.push_back(0);
        seamPending.push_back(pid);
    }

    double seamReleaseProbability(int pid) const {
        if (pid <= 0) return 0.0;
        const std::size_t index = static_cast<std::size_t>(pid);
        const int age = seamClock - seamBirth[index];
        if (age < 0 || age + seamHorizon >= seamTrainingWindow) return 0.0;
        const std::size_t a = static_cast<std::size_t>(age);
        const std::size_t b = static_cast<std::size_t>(age + seamHorizon);
        const auto& local = seamCdf[static_cast<std::size_t>(pipes[index].length)];
        const auto& global = seamCdf[0];
        const int localRisk = local[256] - local[a];
        const int globalRisk = global[256] - global[a];
        if (localRisk < 16 || globalRisk < 128) return 0.0;
        const double prior = static_cast<double>(global[b] - global[a]) /
            static_cast<double>(globalRisk);
        return (static_cast<double>(local[b] - local[a]) + 32.0 * prior) /
            (static_cast<double>(localRisk) + 32.0);
    }

    double seamWaste(std::int64_t gapLength) const {
        if (gapLength <= 0 || gapLength >= 40 || recentLengths.empty()) return 0.0;
        int misses = 0;
        for (int size = static_cast<int>(gapLength) + 1; size <= 40; ++size) {
            misses += recentFrequency[static_cast<std::size_t>(size)];
        }
        return static_cast<double>(gapLength) * static_cast<double>(misses) /
            static_cast<double>(recentLengths.size());
    }

    double seamBenefit(StartIter gap, int length, bool highSide) const {
        const std::int64_t remainder = gap->second - gap->first - length;
        if (remainder <= 0 || remainder >= 40) return 0.0;
        int pid = 0;
        std::int64_t outerLength = 0;
        if (highSide) {
            const auto boundary = activeByEnd.find(gap->first);
            if (boundary == activeByEnd.end()) return 0.0;
            pid = boundary->second;
            const auto& pipe = pipes[static_cast<std::size_t>(pid)];
            auto outer = freeByStart.lower_bound(pipe.start);
            if (outer != freeByStart.begin()) {
                --outer;
                if (outer->second == pipe.start) outerLength = outer->second - outer->first;
            }
        } else {
            const auto boundary = activeByEnd.upper_bound(gap->second);
            if (boundary == activeByEnd.end()) return 0.0;
            pid = boundary->second;
            const auto& pipe = pipes[static_cast<std::size_t>(pid)];
            if (pipe.start != gap->second) return 0.0;
            const auto outer = freeByStart.find(pipe.start + pipe.length);
            if (outer != freeByStart.end()) outerLength = outer->second - outer->first;
        }
        const double probability = seamReleaseProbability(pid);
        const std::int64_t freed = pipes[static_cast<std::size_t>(pid)].length + outerLength;
        return probability * (seamWaste(remainder) + seamWaste(freed) -
                              seamWaste(remainder + freed));
    }

    std::pair<StartIter, bool> chooseDeletionSeam(
        int length, StartIter baseline, bool baselineHighSide) {
        if (COALESCENCE_POLICY == 0 || recentLengths.size() < 128 ||
            seamCdf[0][256] < 128) return {baseline, baselineHighSide};
        const std::int64_t gapLength = baseline->second - baseline->first;
        const std::int64_t remainder = gapLength - length;
        if (remainder <= 0 || remainder >= 40) return {baseline, baselineHighSide};
        ++seamEligible;
        const double baseValue = seamBenefit(baseline, length, baselineHighSide);
        double bestValue = baseValue;
        StartIter best = baseline;
        bool bestHighSide = baselineHighSide;
        const auto consider = [&](StartIter candidate) {
            for (bool high : {false, true}) {
                ++seamScored;
                const double value = seamBenefit(candidate, length, high);
                if (value > bestValue + 1e-12) {
                    bestValue = value;
                    best = candidate;
                    bestHighSide = high;
                }
            }
        };
        consider(baseline);
        if (COALESCENCE_POLICY == 2) {
            const auto first = freeBySize.lower_bound({gapLength, 0});
            const auto after = freeBySize.upper_bound(
                {gapLength, std::numeric_limits<std::int64_t>::max()});
            auto it = first;
            for (int count = 0; count < 4 && it != after; ++count, ++it) {
                if (it->second != baseline->first) consider(freeByStart.find(it->second));
            }
            auto rev = std::make_reverse_iterator(after);
            const auto rend = std::make_reverse_iterator(first);
            for (int count = 0; count < 4 && rev != rend; ++count, ++rev) {
                if (rev->second != baseline->first) consider(freeByStart.find(rev->second));
            }
        }
        if (bestValue - baseValue < 1.0) return {baseline, baselineHighSide};
        if (best != baseline) ++seamGapChanges;
        ++seamChanges;
        return {best, bestHighSide};
    }

public:
    void printSeamDiagnostics() const {
        std::int64_t smallGapMeters = 0;
        std::size_t smallGapCount = 0;
        for (const auto& [start, end] : freeByStart) {
            if (end - start <= 7) {
                smallGapMeters += end - start;
                ++smallGapCount;
            }
        }
        std::cerr << "seam_policy=" << COALESCENCE_POLICY
                  << " mature=" << seamCdf[0][256]
                  << " eligible=" << seamEligible
                  << " scored=" << seamScored
                  << " changes=" << seamChanges
                  << " gap_changes=" << seamGapChanges
                  << " small_gap_count=" << smallGapCount
                  << " small_gap_m=" << smallGapMeters << '\n';
    }

private:
'''
replace('    void fenwickAdd(int index, int delta) {', methods + '\n    void fenwickAdd(int index, int delta) {')
replace('        if (command == 0) {\n', '''        if (command == 0) {
            allocator.printSeamDiagnostics();
''')
out = ROOT / 'src/deletion_seam.cpp'
out.write_text(text)
print(out)
print(hashlib.sha256(out.read_bytes()).hexdigest())
