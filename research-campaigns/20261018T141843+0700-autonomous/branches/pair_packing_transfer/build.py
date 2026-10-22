"""Transfer trial54's two-gap Markov packing model onto frozen trial22."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parent = ROOT / 'releases/988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4/solution.cpp'
donor = ROOT / 'proposals/trial_0054/candidate_0.cpp'
assert hashlib.sha256(parent.read_bytes()).hexdigest() == '988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4'
assert hashlib.sha256(donor.read_bytes()).hexdigest() == '26c02b9f101fa75679ed285d393be4c8fd8260447b021a2408e3c1439f2f7ab9'
text = parent.read_text()

def replace(old, new):
    global text
    assert text.count(old) == 1, old[:100]
    text = text.replace(old, new, 1)

replace('class Allocator {\n', '''class PairPackingModel {
    static constexpr int K = 40;
    static constexpr int states = (K + 1) * (K + 2) / 2;
    std::array<std::int64_t, K + 1> frequency{}, outgoing{};
    std::array<std::array<std::int64_t, K + 1>, K + 1> transitions{};
    std::array<std::array<double, K + 1>, states> value{};
    std::int64_t insertions = 0, nextRebuild = 1;
    int previousLength = 0;

    static int index(int a, int b) {
        if (a > b) std::swap(a, b);
        return b * (b + 1) / 2 + a;
    }
    void rebuild() {
        std::array<double, K + 1> marginal{};
        std::array<std::array<double, K + 1>, K + 1> probability{};
        for (int length = 1; length <= K; ++length) {
            marginal[length] = (frequency[length] + 0.5) / (insertions + 0.5 * K);
        }
        for (int last = 1; last <= K; ++last) {
            for (int length = 1; length <= K; ++length) {
                probability[last][length] = (transitions[last][length] + K * marginal[length]) /
                    (outgoing[last] + static_cast<double>(K));
            }
        }
        // The two residual capacities strictly decrease in every transition.
        // Stop at the first request that fits neither gap; no deletion forecast.
        for (int b = 1; b <= K; ++b) {
            for (int a = 0; a <= b; ++a) {
                std::array<double, K + 1> offer{};
                for (int length = 1; length <= b; ++length) {
                    double continuation = value[index(a, b - length)][length];
                    if (length <= a) continuation = std::max(
                        continuation, value[index(a - length, b)][length]);
                    offer[length] = length + continuation;
                }
                for (int last = 1; last <= K; ++last) {
                    double total = 0.0;
                    for (int length = 1; length <= b; ++length) {
                        total += probability[last][length] * offer[length];
                    }
                    value[index(a, b)][last] = total;
                }
            }
        }
    }
public:
    void observe(int event) {
        if (event < 0) { previousLength = 0; return; }
        if (event <= 0 || event > K) return;
        ++insertions; ++frequency[event];
        if (previousLength > 0) {
            ++transitions[previousLength][event]; ++outgoing[previousLength];
        }
        previousLength = event;
        if (insertions == nextRebuild) {
            rebuild();
            nextRebuild += std::min<std::int64_t>(nextRebuild, 1024);
        }
    }
    double after(int a, int b, int currentLength) const {
        return value[index(a, b)][currentLength];
    }
};

class Allocator {
''')
replace('    CensoredLifetimeModel lifetimeModel;\n', '''    CensoredLifetimeModel lifetimeModel;
    PairPackingModel pairPackingModel;
    std::uint64_t pairPackingOpportunities = 0, pairPackingComparisons = 0;
    std::uint64_t pairPackingChanged = 0;
''')
replace('    void recordPrimalEvent(int event) {\n', '''    void recordPrimalEvent(int event) {
        pairPackingModel.observe(event);
''')
replace('''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            start = consumeAtSide(gap, length, highSide);
''', '''            if (selectedStart >= 0) gap = freeByStart.find(selectedStart);
            if (!parityCohortMode && !alternatingDeleteMode && !runLeftActive &&
                !additiveNextAlignment && !counterfactualCapacityChoice && !lifoStackLane) {
                gap = choosePairPackingGap(gap, length, highSide);
            }
            start = consumeAtSide(gap, length, highSide);
''')
replace('    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {\n', '''    StartIter choosePairPackingGap(StartIter baseline, int length, bool highSide) {
        const std::int64_t baseWidth = baseline->second - baseline->first;
        if (baseWidth <= length || baseWidth > 40) return baseline;
        ++pairPackingOpportunities;
        const bool recycleRecent = activePipeCount > kMcMaxActivePipes && hasLifoDeletionConfidence();
        const bool confidentAddress = highSide && !lifoLaneDisabledForScale && hasLifoDeletionConfidence();
        auto selected = baseline;
        double bestGain = 0.0;
        for (auto it = freeBySize.lower_bound({length, 0}); it != freeBySize.end();) {
            const std::int64_t width = it->first;
            if (width > 40) break;
            std::int64_t representative = it->second;
            if (confidentAddress) {
                representative = std::prev(freeBySize.upper_bound({width,
                    std::numeric_limits<std::int64_t>::max()}))->second;
            }
            if (recycleRecent) {
                const auto age = std::prev(freeBySizeAge.upper_bound({width,
                    std::numeric_limits<std::uint64_t>::max(),
                    std::numeric_limits<std::int64_t>::max()}));
                representative = std::get<2>(*age);
            }
            if (width != baseWidth) {
                ++pairPackingComparisons;
                const double parentValue = pairPackingModel.after(
                    static_cast<int>(baseWidth) - length, static_cast<int>(width), length);
                const double alternativeValue = pairPackingModel.after(
                    static_cast<int>(baseWidth), static_cast<int>(width) - length, length);
                const double gain = alternativeValue - parentValue;
                if (gain > bestGain + 1e-10) {
                    bestGain = gain; selected = freeByStart.find(representative);
                }
            }
            it = freeBySize.upper_bound({width, std::numeric_limits<std::int64_t>::max()});
        }
        if (selected != baseline) ++pairPackingChanged;
        return selected;
    }

    StartIter bestFittingGap(int length, bool highSide, int sizeCohort) {
''')
replace('''            std::cerr << "recency_different_selections="
''', '''            std::cerr << "pair_packing_opportunities=" << allocator.pairPackingOpportunities
                      << " comparisons=" << allocator.pairPackingComparisons
                      << " changed_placements=" << allocator.pairPackingChanged << '\\n';
            std::cerr << "recency_different_selections="
''')
destination = Path(__file__).with_name('solution.cpp')
assert not destination.exists(), 'Do not modify a registered candidate'
destination.write_text(text)
print(hashlib.sha256(destination.read_bytes()).hexdigest())
