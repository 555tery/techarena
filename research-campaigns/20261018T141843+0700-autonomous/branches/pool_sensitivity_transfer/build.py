"""Transfer trial44's pool-routing sensitivity onto frozen trial22."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parent = ROOT / 'releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp'
donor = ROOT / 'proposals/trial_0044/candidate_0.cpp'
assert hashlib.sha256(parent.read_bytes()).hexdigest() == '988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4'
assert hashlib.sha256(donor.read_bytes()).hexdigest() == 'ca11b3857ecfc753bbecd951900455494352706d21bf2e80f8cdccacfb300e12'
text = parent.read_text()

def replace(old, new):
    global text
    assert text.count(old) == 1, old[:100]
    text = text.replace(old, new, 1)

replace('    CensoredLifetimeModel lifetimeModel;\n', '''    CensoredLifetimeModel lifetimeModel;
    static constexpr int poolCapacity = 2 * 40;
    using PoolDerivative = std::array<double, 41>;
    std::array<PoolDerivative, poolCapacity + 1> poolDerivative{};
    PoolDerivative poolAggregate{};
    bool poolReady = false;
    std::uint64_t poolComparisons = 0, poolOverrides = 0;
    std::uint64_t poolNonzeroCredits = 0;
''')
replace('    void rebuildPrimalGapValues(int maxGap) {\n', '''    void updatePoolDerivative(std::int64_t width, double sign) {
        if (!poolReady) return;
        const auto& derivative = poolDerivative[static_cast<std::size_t>(
            std::min<std::int64_t>(width, poolCapacity))];
        for (int request = 1; request <= std::min<std::int64_t>(width, 40); ++request) {
            poolAggregate[request] += sign * derivative[request];
        }
    }

    void rebuildPoolSensitivity(const std::array<double, 41>& rate, double expiry) {
        poolReady = false;
        poolAggregate.fill(0.0);
        for (auto& derivative : poolDerivative) derivative.fill(0.0);
        if (!(expiry > 0.0)) return;
        std::array<double, poolCapacity + 1> value{};
        for (int capacity = 1; capacity <= poolCapacity; ++capacity) {
            const int count = std::min(capacity, 40);
            std::array<std::pair<double, double>, 40> offers{};
            for (int length = 1; length <= count; ++length) {
                offers[length - 1] = {length + value[capacity - length], rate[length]};
            }
            std::sort(offers.begin(), offers.begin() + count,
                [](const auto& a, const auto& b) { return a.first > b.first; });
            double numerator = 0.0, denominator = expiry;
            for (int j = 0; j < count; ++j) {
                if (offers[j].first * denominator <= numerator) break;
                numerator += offers[j].second * offers[j].first;
                denominator += offers[j].second;
            }
            value[capacity] = numerator / denominator;
            auto& derivative = poolDerivative[capacity];
            double derivativeDenominator = expiry;
            for (int length = 1; length <= count; ++length) {
                const double benefit = length + value[capacity - length] - value[capacity];
                if (benefit <= 0.0 || rate[length] == 0.0) continue;
                derivativeDenominator += rate[length];
                const auto& previous = poolDerivative[capacity - length];
                for (int request = 1; request <= std::min(capacity - length, 40); ++request) {
                    derivative[request] += rate[length] * previous[request];
                }
                derivative[length] += rate[length] * benefit;
            }
            for (int request = 1; request <= count; ++request) {
                derivative[request] /= derivativeDenominator;
            }
        }
        poolReady = true;
        for (int width = 1; width <= kPrimalGapValueCap + 1; ++width) {
            if (primalGapCounts[width] != 0) {
                updatePoolDerivative(width, static_cast<double>(primalGapCounts[width]));
            }
        }
    }

    void rebuildPrimalGapValues(int maxGap) {
''')
replace('        ++primalModelRebuilds;\n', '''        ++primalModelRebuilds;
        rebuildPoolSensitivity(rate, expiry);
''')
replace('        --primalGapCounts[bucket];\n', '''        --primalGapCounts[bucket];
        updatePoolDerivative(gapLength, -1.0);
''')
replace('        ++primalGapCounts[bucket];\n', '''        ++primalGapCounts[bucket];
        updatePoolDerivative(gapLength, 1.0);
''')
replace('    double primalGapLoss(std::int64_t gapLength, int length) const {\n', '''    StartIter choosePoolSensitivityGap(
        const std::vector<std::pair<std::int64_t, std::int64_t>>& candidates,
        int length, bool highSide, StartIter baseline) {
        if (!poolReady || alternatingDeleteMode ||
            observedRunCount >= static_cast<int>(kSameLengthRightRun) ||
            predictEarlyNextGeometricSize(length) > length || candidates.size() < 2) return baseline;
        auto challenger = freeByStart.end();
        double runnerScore = std::numeric_limits<double>::infinity();
        for (const auto& [width, start] : candidates) {
            if (start == baseline->first) continue;
            const double score = primalGapLoss(width, length);
            const bool better = score + 1e-9 < runnerScore;
            const bool tied = !(runnerScore + 1e-9 < score) && !(score + 1e-9 < runnerScore);
            const bool address = challenger != freeByStart.end() &&
                (highSide ? start > challenger->first : start < challenger->first);
            if (challenger == freeByStart.end() || better || (tied && address)) {
                runnerScore = score; challenger = freeByStart.find(start);
            }
        }
        if (challenger == freeByStart.end()) return baseline;
        const std::int64_t width = baseline->second - baseline->first;
        const std::int64_t otherWidth = challenger->second - challenger->first;
        if (width > poolCapacity || otherWidth > poolCapacity) return baseline;
        std::array<double, 41> shift{};
        std::int64_t fitting = 0;
        for (int s = kPrimalGapValueCap + 1; s >= 1; --s) {
            fitting += primalGapCounts[s];
            if (s <= 40 && fitting > 1) shift[s] = std::log1p(1.0 / (fitting - 1));
        }
        const auto credit = [&](std::int64_t capacity) {
            const auto remainder = capacity - length;
            if (remainder >= 40) return 0.0;
            const auto& before = poolDerivative[static_cast<std::size_t>(capacity)];
            const auto& after = poolDerivative[static_cast<std::size_t>(remainder)];
            double total = 0.0;
            for (int request = static_cast<int>(remainder) + 1;
                 request <= std::min<std::int64_t>(capacity, 40); ++request) {
                total += std::max(0.0, poolAggregate[request] - before[request] + after[request]) * shift[request];
            }
            if (total > 1e-9) ++poolNonzeroCredits;
            return total;
        };
        const int modelLimit = static_cast<int>(std::max(width, otherWidth));
        const double freshRisk = causalRiskReady ? lifetimeModel.newRisk(length) : 1.0;
        const double parentCost = causalRiskReady
            ? causalPrimalLoss(baseline, length, highSide, modelLimit, freshRisk)
            : primalGapLoss(width, length);
        const double challengerCost = causalRiskReady
            ? causalPrimalLoss(challenger, length, highSide, modelLimit, freshRisk)
            : primalGapLoss(otherWidth, length);
        ++poolComparisons;
        if (challengerCost - credit(otherWidth) + 1e-9 < parentCost - credit(width)) {
            ++poolOverrides; return challenger;
        }
        return baseline;
    }

    double primalGapLoss(std::int64_t gapLength, int length) const {
''')
replace('''                    primalBest = chooseCausalLifetimeGap(
                        candidates, length, highSide, primalBest);
''', '''                    primalBest = chooseCausalLifetimeGap(
                        candidates, length, highSide, primalBest);
                    primalBest = choosePoolSensitivityGap(
                        candidates, length, highSide, primalBest);
''')
replace('''            std::cerr << "recency_different_selections="
''', '''            std::cerr << "pool_sensitivity_comparisons=" << allocator.poolComparisons
                      << " nonzero_credits=" << allocator.poolNonzeroCredits
                      << " overrides=" << allocator.poolOverrides << '\\n';
            std::cerr << "recency_different_selections="
''')
destination = Path(__file__).with_name('solution.cpp')
assert not destination.exists(), 'Do not modify a registered candidate'
destination.write_text(text)
print(hashlib.sha256(destination.read_bytes()).hexdigest())
