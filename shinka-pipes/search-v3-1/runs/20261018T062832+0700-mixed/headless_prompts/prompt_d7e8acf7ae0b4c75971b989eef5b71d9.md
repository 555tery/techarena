# System Instructions

Improve a causal online dynamic storage allocator in self-contained C++20.
Propose code in your response; do not edit files or run tools/experiments.
Change only EVOLVE-BLOCK regions. Preserve immediate flushing and the protocol.
Inserts have exact length 1..40; deletes name a live PID; 0 exits.
Live pipes never move; trench grows in sections of 20 and never shrinks.
Use only past observations: no future commands, test IDs, fingerprints,
raw inputs, filesystem, network, subprocesses or other project results.
Every case must be correct with solver CPU <5 seconds and RSS <256 MiB.

Fitness is the arithmetic mean of F/T on the fixed SEARCH-v3.1 MAIN corpus:
152 cases, 38 equally weighted families with 4 equally weighted cases each.
F is final live pipe length; T is the actual final trench length.
B=20*ceil(peak_live_volume/20) is a volume lower bound, not the optimum.
B/T and T/B-1 are diagnostic only and must not replace the F/T objective.
CPU is recorded separately and has no penalty term in this fitness.
Main retains 64 broad prior and 64 expanded cases, plus 24 micro cases.
Micro cases cover early fragmentation, small remainders, neighbor releases,
size shifts and repeated reuse in workloads constructively fitting 1..3 sections.
Their short histories make cold-start decisions important; no future is available.
Most traces end near the peak; others have moderate drain or short-horizon rounding.
Parameters and mixtures do not match Open15 frequencies; hidden workloads are unknown.
Re-evaluate the eventual selected seed on this entire corpus before evolution.
Scores from earlier corpora cannot be carried over.

STRESS is a separate diagnostic corpus. It is excluded from fitness,
selection, archive decisions and model feedback, and is not run automatically.
Validation and Open15 are also excluded. Do not inspect their files/results.
This is a search corpus, not evidence of hidden-test generalization.

Propose one algorithmic mechanism per candidate. Explain its overlap with
the supplied parent, complexity, failure mode and a same-parent ablation.
Parameter tuning alone does not satisfy this research objective. Prepared
literature and malloc/jemalloc/mimalloc hypotheses may motivate mechanisms;
they do not establish improvements. Keep global fitting-gap fallback before
growth and exact pipe lengths; avoid speculative reserved trench.

RESEARCH MEMORY. Each proposal includes a compact ledger of completed ideas,
same-parent deltas and important regressions. Descriptions are author claims,
not established causal explanations. Review the history before choosing a patch.
Give the mechanism a stable NAME and state the actual behavioral difference
from earlier attempts in DESCRIPTION; renaming code is not a new mechanism.
Retrying a mechanism is allowed when fixing a bug, changing an interaction or
testing a materially different assumption. Explain that reason explicitly.
Historical SEARCH-v2 B/T evidence is not a ranking on this SEARCH-v3.1 F/T corpus.
Paired feedback compares against the actual parent and the leader frozen at
proposal time. These diagnostics never replace the fitness or correctness gates.
Parent selection additionally retains one champion per family, independently
of the scalar archive. A five-proposal cycle uses three ordinary score draws,
one regression-aware draw and one family-specialist draw, within the same island.
Regression loss is max(0, fixed gen0 F/T minus candidate F/T) per case; report
the mean of its worst ceil(10% of cases), including zero losses. A robust draw
considers candidates within 0.005 mean F/T of the island leader. A specialist
may have a lower overall mean. Preserve its useful mechanism and address its
regressions; overall best and primary fitness remain mean F/T. These selection
defaults are engineering choices, not experimentally established optimal weights.
Exact source duplicates of correct programs in THIS run are returned as repair
feedback before evaluation. Supply a meaningful new change for the same parent;
duplicate corrections share the existing three attempts with patch repairs.
Similar names, equal scores and equal finite result vectors are advisory only.

If a patch fails to apply, use exact error feedback and return the complete
corrected proposal for the SAME parent and hypothesis, including all blocks.
The exact-duplicate rejection above permits a different mechanism for that parent.
Preserve exact SEARCH whitespace. At most three total apply attempts stay
within one generation. Failed apply attempts must not enter the archive or
consume an evaluated-generation slot. Exhausted proposals are retained in a
separate bounded failure ledger; the next proposal may choose another parent.
Runtime, request and repeated infrastructure-error limits remain enforced.


# Potential Recommendations
The following are potential recommendations for the next program generation:

**Добавьте один кандидат, сохраняющий место под крупный прогнозируемый запрос.** Если остатки минимального и следующего подходящих размеров меньше `q_hi = quantiles[6]`, рассмотрите также `sizes_.lower_bound({length+q_hi, 0})`, ограничив общее число уникальных размещений четырьмя. Оценивайте его существующим трёхшаговым прогнозом и допускайте только строгий выигрыш относительно fallback: это адресно расширяет успешный ограниченный поиск, избегая широкого перебора gen62.

RESEARCH MEMORY — measured evidence, descriptions are unverified author claims.
Past failures are not universal bans. Explain changed behavior/assumptions when retrying.
Do not rename an already tested policy and present it as a new mechanism.
No equivalence is inferred from a shared score or a shared finite case vector.
CURRENT SEARCH-v3.1 (F/T):
Same complete saved trench vector: generations [9, 38, 55]. Advisory only, not equivalence.
Same complete saved trench vector: generations [14, 67]. Advisory only, not equivalence.
Same complete saved trench vector: generations [31, 54]. Advisory only, not equivalence.
appendable_wilderness: attempts=2; score_range=0.854861671..0.855164355
Best-Fit: attempts=1; score_range=0.857332383..0.857332383
First-Fit: attempts=1; score_range=0.847432251..0.847432251
Independent 1: attempts=1; score_range=0.856788966..0.856788966
Independent 2: attempts=1; score_range=0.857536047..0.857536047
Independent 3: attempts=1; score_range=0.857564053..0.857564053
Independent 4: attempts=1; score_range=0.856555151..0.856555151
SEARCH-v2 generation 27: attempts=1; score_range=0.855381088..0.855381088
adjacent_release_edge: attempts=1; score_range=0.858287247..0.858287247
age_conditioned_neighbor_release: attempts=1; score_range=0.854363465..0.854363465
age_conditioned_release_edge: attempts=1; score_range=0.848500142..0.848500142
appendable_wilderness_single_front: attempts=1; score_range=0.854469278..0.854469278
gen45 prefix_growth_tiebreak; correct=True; parent=18; delta_F/T=+0.000393930; claim=Предлагаю учитывать время прогнозируемого расширения при равенстве исходного score. Родитель сравнивает суммарное число секций после восьми прогнозных вставок. Новый механизм дополнительно минимизирует сумму накопленного
  improved/regressed/tied=36/33/83
  regression s31_030_size_lifetimes: delta_F/T=-0.071836735
  regression s31_086_tiny_churn: delta_F/T=-0.046773176
gen61 stratified_growth_horizon; correct=True; parent=37; delta_F/T=+0.001747828; claim=Новый механизм — ограниченное моделирование упаковки трёх следующих вставок. Восемь синтетических сценариев строятся по сглаженной гистограмме уже наблюдённых длин. Для родительского размещения, другого из двух ближайших
  improved/regressed/tied=42/27/83
  regression s31_041_drifting_sizes: delta_F/T=-0.036501025
  regression s31_039_distribution_switch: delta_F/T=-0.024810924
gen69 scarce_capacity_exchange; correct=True; parent=24; delta_F/T=-0.000957521; claim=Предлагаю учитывать дефицит свободной вместимости при сравнении родительской дыры с Best-Fit. Для каждого размера k поддерживается C[k] — количество труб размера k, помещающихся в текущие свободные интервалы, включая уже
  improved/regressed/tied=20/29/103
  regression s31_039_distribution_switch: delta_F/T=-0.046892992
  regression s31_063_size_biased_deletion: delta_F/T=-0.040963203
gen68 scarcity_weighted_coalescence; correct=True; parent=0; delta_F/T=-0.000801127; claim=Предлагаю один исследуемый механизм: дополнительную премию за слияние остатка с освобождаемым соседом, нормированную на число альтернативных подходящих дыр.
Для остатка r и освобождаемого участка a учитываются только раз
  improved/regressed/tied=37/47/68
  regression s31_086_tiny_churn: delta_F/T=-0.085639663
  regression s31_085_tiny_churn: delta_F/T=-0.041403162
gen67 zero_growth_tail_exchange; correct=True; parent=6; delta_F/T=-0.000318501; claim=Один механизм: выбор между внутренней дырой, найденной родителем, и уже выделенным хвостом по ожидаемой стоимости одной следующей вставки.
Если текущая труба помещается в хвост без расширения, сравниваются два состояния:
  improved/regressed/tied=23/28/101
  regression s31_008_short_heavy: delta_F/T=-0.047813195
  regression s31_049_geometric_cohorts: delta_F/T=-0.039689922
gen66 dual_strata_growth_gate; correct=True; parent=52; delta_F/T=-0.000752429; claim=Предлагаю проверять устойчивость короткого прогноза перед изменением родительского выбора между внутренним отверстием и хвостом. Оба размещения уже должны вмещать текущую трубу.
Механизм развивает направление gen61: гори
  improved/regressed/tied=18/27/107
  regression s31_063_size_biased_deletion: delta_F/T=-0.062943459
  regression s31_041_drifting_sizes: delta_F/T=-0.023199023
gen65 fifo_guarded_release_placement; correct=True; parent=37; delta_F/T=+0.000641019; claim=Один механизм: причинный FIFO gate для marginal_release_coalescence. На каждом удалении учитывается, принадлежал ли PID старейшей живой трубе. Счётчик так
[Memory shortened; complete ledger remains in run/research-memory.json.]
PARENT SELECTION: mode=score; specialist families=[]; fixed-baseline tail loss=0.034875508; maximum case loss=0.081203008. Retain useful mechanisms while improving mean F/T and addressing the listed regressions.
You MUST respond using an edit name, description, and the exact SEARCH/REPLACE diff format shown below to indicate changes:

<NAME>
A shortened name summarizing the edit you are proposing. Lowercase, no spaces, underscores allowed.
</NAME>

<DESCRIPTION>
A description and argumentation process of the edit you are proposing.
</DESCRIPTION>

<DIFF>
<<<<<<< SEARCH
# Original code to find and replace (must match exactly including indentation)
=======
# New replacement code
>>>>>>> REPLACE

</DIFF>


Example of a valid diff format:
<DIFF>
<<<<<<< SEARCH
for i in range(m):
    for j in range(p):
        for k in range(n):
            C[i, j] += A[i, k] * B[k, j]
=======
# Reorder loops for better memory access pattern
for i in range(m):
    for k in range(n):
        for j in range(p):
            C[i, j] += A[i, k] * B[k, j]
>>>>>>> REPLACE

</DIFF>

* You may only modify text that lies below a line containing "EVOLVE-BLOCK-START" and above the next "EVOLVE-BLOCK-END". Everything outside those markers is read-only.
* Do not repeat the markers "EVOLVE-BLOCK-START" and "EVOLVE-BLOCK-END" in the SEARCH/REPLACE blocks.  
* Every block’s SEARCH section must be copied **verbatim** from the current file, including indentation.
* You can propose multiple independent edits. SEARCH/REPLACE blocks follow one after another. DO NOT ADD ANY OTHER TEXT BETWEEN THESE BLOCKS.
* Make sure the file still runs after your changes.

# Previous Messages

[]

# User Request


# Current program

Here is the current program we are trying to improve (you will need to propose a modification to it below):

```cpp
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <utility>
#include <vector>

// EVOLVE-BLOCK-START
#include <bit>
namespace {
using Coordinate = std::int64_t;
using SizeKey =
    std::pair<Coordinate, std::pair<std::uint64_t, Coordinate>>;
constexpr Coordinate kSectionLength = 20;
constexpr std::size_t kFastWindow = 128;
constexpr std::size_t kSlowWindow = 2048;
constexpr bool kUseGlobalPackingForecast = true;
constexpr int kForecastHorizon = 8;
constexpr int kForecastScenarios = 4;
constexpr int kForecastCapacity = 40 * kForecastHorizon;
constexpr int kMaskWords = kForecastCapacity / 64 + 1;
constexpr int kDistinctCandidateSizes = 8;
constexpr int kMaximumCandidates = 12;
struct Pipe {
    Coordinate start = 0;
    int length = 0;
    bool active = false;
};
struct Gap {
    Coordinate end = 0;
    std::uint64_t freeSince = 0;
};
struct Candidate {
    Coordinate start = 0;
    Coordinate span = 0;
    std::uint64_t freeSince = 0;
    bool tail = false;
};
struct Change {
    int capacity = 0;
    int delta = 0;
};
// Capacities above the complete forecast volume are interchangeable:
// any one of them can accommodate the entire remaining forecast.
struct Inventory {
    std::array<int, kForecastCapacity + 1> count{};
    std::array<std::uint64_t, kMaskWords> mask{};
    void change(int capacity, int delta) {
        if (capacity <= 0) return;
        int& value = count[static_cast<std::size_t>(capacity)];
        value += delta;
        const std::size_t word =
            static_cast<std::size_t>(capacity >> 6);
        const std::uint64_t bit =
            std::uint64_t{1} << (capacity & 63);
        if (value == 0) {
            mask[word] &= ~bit;
        } else {
            mask[word] |= bit;
        }
    }
    int firstFit(int length) const {
        int word = length >> 6;
        std::uint64_t available =
            mask[static_cast<std::size_t>(word)] &
            (~std::uint64_t{0} << (length & 63));
        while (true) {
            if (available != 0) {
                return word * 64 +
                    static_cast<int>(std::countr_zero(available));
            }
            ++word;
            if (word >= kMaskWords) return 0;
            available = mask[static_cast<std::size_t>(word)];
        }
    }
};
class Allocator {
public:
    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        ++tick_;
        const bool newlyObservedLength =
            fastFrequency_[static_cast<std::size_t>(length)] == 0;
        observeLength(length);
        refreshModel(newlyObservedLength);
        Coordinate digs = 0;
        Coordinate chosenStart = 0;
        // Growth is allowed only after checking the complete size index.
        const auto firstFit = bySize_.lower_bound({length, {0, 0}});
        if (firstFit == bySize_.end()) {
            ++expansionGateOpportunities;
            Coordinate start = trenchLength_;
            std::uint64_t freeSince = tick_;
            const auto tail = tailGap();
            if (tail != gaps_.end()) {
                start = tail->first;
                freeSince = tail->second.freeSince;
                eraseGap(tail);
            }
            const Coordinate available = trenchLength_ - start;
            const Coordinate deficit =
                std::max<Coordinate>(0, length - available);
            digs =
                (deficit + kSectionLength - 1) / kSectionLength;
            trenchLength_ += digs * kSectionLength;
            insertGap(start, trenchLength_, freeSince);
            chosenStart = start;
        } else {
            chosenStart = chooseGap(length);
        }
        const auto selected = gaps_.find(chosenStart);
        const Gap gap = selected->second;
        eraseGap(selected);
        // The vector index is the insertion PID.
        pipes_.push_back(Pipe{chosenStart, length, true});
        // Exact-length allocation, anchored at the low end.
        insertGap(
            chosenStart + length, gap.end, gap.freeSince);
        std::cout << digs << ' ' << chosenStart << '\n' << std::flush;
    }
    void remove(Coordinate pidValue) {
        if (pidValue <= 0 ||
            static_cast<std::uint64_t>(pidValue) >= pipes_.size()) {
            printInvalidPid();
            return;
        }
        const std::size_t pid = static_cast<std::size_t>(pidValue);
        if (!pipes_[pid].active) {
            printInvalidPid();
            return;
        }
        ++tick_;
        const Pipe pipe = pipes_[pid];
        Coordinate start = pipe.start;
        Coordinate end = pipe.start + pipe.length;
        auto right = gaps_.lower_bound(start);
        if (right != gaps_.begin()) {
            const auto left = std::prev(right);
            if (left->second.end == start) {
                start = left->first;
                eraseGap(left);
            }
        }
        right = gaps_.lower_bound(end);
        if (right != gaps_.end() && right->first == end) {
            end = right->second.end;
            eraseGap(right);
        }
        pipes_[pid].active = false;
        insertGap(start, end, tick_);
        std::cout << pipe.start << '\n' << std::flush;
    }
private:
    using GapMap = std::map<Coordinate, Gap>;
    using GapIterator = GapMap::iterator;
    using Scenarios = std::array<
        std::array<int, kForecastHorizon>, kForecastScenarios>;
    GapMap gaps_;
    std::set<SizeKey> bySize_;
    std::vector<Pipe> pipes_{Pipe{}};
    // The expandable tail is represented separately during forecasts.
    Inventory interiorInventory_;
    Coordinate trenchLength_ = 0;
    std::uint64_t tick_ = 0;
    std::uint64_t modelTick_ = 0;
    bool haveModel_ = false;
    std::deque<int> recentLengths_;
    std::array<int, 41> fastFrequency_{};
    std::array<int, 41> slowFrequency_{};
    std::array<double, 41> requestPrefix_{};
    // Internal sampling state; independent of case identifiers or raw input.
    std::uint64_t randomState_ = 0x243f6a8885a308d3ULL;
    static int capacityBucket(Coordinate capacity) {
        return static_cast<int>(
            std::min<Coordinate>(capacity, kForecastCapacity));
    }
    static bool candidateLess(
        const Candidate& a, const Candidate& b) {
        if (a.span != b.span) return a.span < b.span;
        if (a.tail != b.tail) return !a.tail;
        if (a.freeSince != b.freeSince) {
            return a.freeSince < b.freeSince;
        }
        return a.start < b.start;
    }
    GapIterator tailGap() {
        if (gaps_.empty()) return gaps_.end();
        const auto last = std::prev(gaps_.end());
        return last->second.end == trenchLength_
            ? last : gaps_.end();
    }
    void insertGap(
        Coordinate start, Coordinate end,
        std::uint64_t freeSince) {
        if (start >= end) return;
        gaps_.emplace(start, Gap{end, freeSince});
        bySize_.insert({end - start, {freeSince, start}});
        if (end != trenchLength_) {
            interiorInventory_.change(
                capacityBucket(end - start), 1);
        }
    }
    void eraseGap(GapIterator position) {
        const Coordinate start = position->first;
        const Gap gap = position->second;
        const Coordinate span = gap.end - start;
        if (gap.end != trenchLength_) {
            interiorInventory_.change(capacityBucket(span), -1);
        }
        bySize_.erase({span, {gap.freeSince, start}});
        gaps_.erase(position);
    }
    void observeLength(int length) {
        if (recentLengths_.size() >= kFastWindow) {
            const std::size_t expired =
                recentLengths_.size() - kFastWindow;
            --fastFrequency_[static_cast<std::size_t>(
                recentLengths_[expired])];
        }
        recentLengths_.push_back(length);
        ++fastFrequency_[static_cast<std::size_t>(length)];
        ++slowFrequency_[static_cast<std::size_t>(length)];
        if (recentLengths_.size() > kSlowWindow) {
            --slowFrequency_[static_cast<std::size_t>(
                recentLengths_.front())];
            recentLengths_.pop_front();
        }
    }
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) {
            return;
        }
        haveModel_ = true;
        modelTick_ = tick_;
        const double fastCount = static_cast<double>(
            std::min(kFastWindow, recentLengths_.size()));
        const double slowCount =
            static_cast<double>(recentLengths_.size());
        requestPrefix_[0] = 0.0;
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index =
                static_cast<std::size_t>(length);
            const double probability =
                0.98 * (
                    0.75 * fastFrequency_[index] / fastCount +
                    0.25 * slowFrequency_[index] / slowCount) +
                0.02 / 40.0;
            requestPrefix_[index] =
                requestPrefix_[index - 1] + probability;
        }
        requestPrefix_[40] = 1.0;
    }
    std::uint64_t nextRandom() {
        randomState_ += 0x9e3779b97f4a7c15ULL;
        std::uint64_t value = randomState_;
        value = (value ^ (value >> 30)) *
            0xbf58476d1ce4e5b9ULL;
        value = (value ^ (value >> 27)) *
            0x94d049bb133111ebULL;
        return value ^ (value >> 31);
    }
    double unitRandom() {
        return static_cast<double>(nextRandom() >> 11) *
            (1.0 / 9007199254740992.0);
    }
    int sampleLength(double quantile) const {
        const auto found = std::lower_bound(
            requestPrefix_.begin() + 1,
            requestPrefix_.end(), quantile);
        return static_cast<int>(
            found - requestPrefix_.begin());
    }
    Scenarios makeScenarios() {
        Scenarios scenarios{};
        // Stratification reduces sampling noise. Every candidate receives
        // exactly the same scenarios for this real insertion.
        for (int step = 0; step < kForecastHorizon; ++step) {
            std::array<int, kForecastScenarios> order{};
            for (int i = 0; i < kForecastScenarios; ++i) {
                order[static_cast<std::size_t>(i)] = i;
            }
            for (int i = kForecastScenarios - 1; i > 0; --i) {
                const int j = static_cast<int>(
                    nextRandom() %
                    static_cast<std::uint64_t>(i + 1));
                std::swap(
                    order[static_cast<std::size_t>(i)],
                    order[static_cast<std::size_t>(j)]);
            }
            for (int stratum = 0;
                 stratum < kForecastScenarios; ++stratum) {
                const double quantile =
                    (stratum + unitRandom()) /
                    static_cast<double>(kForecastScenarios);
                const int scenario =
                    order[static_cast<std::size_t>(stratum)];
                scenarios[static_cast<std::size_t>(scenario)]
                         [static_cast<std::size_t>(step)] =
                    sampleLength(quantile);
            }
        }
        return scenarios;
    }
    static void recordChange(
        Inventory& inventory, int capacity, int delta,
        Change* undo, int& undoCount) {
        if (capacity <= 0) return;
        inventory.change(capacity, delta);
        undo[undoCount++] = Change{capacity, delta};
    }
    static void restore(
        Inventory& inventory, const Change* undo,
        int undoCount) {
        while (undoCount > 0) {
            const Change change = undo[--undoCount];
            inventory.change(change.capacity, -change.delta);
        }
    }
    static unsigned forecastGrowth(
        Inventory& inventory, int tailCapacity,
        const std::array<int, kForecastHorizon>& requests) {
        std::array<Change, 2 * kForecastHorizon> undo{};
        int undoCount = 0;
        // At most two sections per request. Terminal growth must
        // dominate every possible prefix-area difference summed
        // across all scenarios; timing only breaks terminal ties.
        constexpr unsigned primaryScale =
            1U + static_cast<unsigned>(
                kForecastScenarios * kForecastHorizon *
                (kForecastHorizon + 1));
        unsigned sections = 0;
        unsigned prefixArea = 0;
        for (int length : requests) {
            const int capacity = inventory.firstFit(length);
            // Virtual successor policy: global best-fit, preferring an
            // interior gap when its capacity ties the expandable tail.
            if (capacity != 0 &&
                (tailCapacity < length ||
                 capacity <= tailCapacity)) {
                recordChange(
                    inventory, capacity, -1,
                    undo.data(), undoCount);
                recordChange(
                    inventory, capacity - length, 1,
                    undo.data(), undoCount);
            } else if (tailCapacity >= length) {
                tailCapacity -= length;
            } else {
                const int deficit = length - tailCapacity;
                const int digs =
                    (deficit + static_cast<int>(kSectionLength) - 1) /
                    static_cast<int>(kSectionLength);
                sections += static_cast<unsigned>(digs);
                tailCapacity +=
                    digs * static_cast<int>(kSectionLength) - length;
            }
            prefixArea += sections;
        }
        restore(inventory, undo.data(), undoCount);
        return sections * primaryScale + prefixArea;
    }
    Coordinate chooseGap(int length) {
        std::array<Candidate, kMaximumCandidates> candidates{};
        int candidateCount = 0;
        const auto addCandidate = [&](Coordinate start) {
            for (int i = 0; i < candidateCount; ++i) {
                if (candidates[static_cast<std::size_t>(i)].start ==
                    start) {
                    return;
                }
            }
            if (candidateCount == kMaximumCandidates) return;
            const auto found = gaps_.find(start);
            if (found == gaps_.end()) return;
            const Coordinate span = found->second.end - start;
            if (span < length) return;
            candidates[static_cast<std::size_t>(candidateCount++)] =
                Candidate{
                    start, span, found->second.freeSince,
                    found->second.end == trenchLength_};
        };
        // Equal-span interior gaps are equivalent to the forecast.
        // Retain the oldest representative, plus the distinct tail case.
        const auto addSizeRepresentatives =
            [&](std::set<SizeKey>::const_iterator position) {
                if (position == bySize_.end()) return;
                addCandidate(position->second.second);
                const auto gap = gaps_.find(position->second.second);
                if (gap->second.end == trenchLength_) {
                    const auto next = std::next(position);
                    if (next != bySize_.end() &&
                        next->first == position->first) {
                        addCandidate(next->second.second);
                    }
                }
            };
        auto current = bySize_.lower_bound({length, {0, 0}});
        const Coordinate fallback = current->second.second;
        for (int count = 0;
             current != bySize_.end() &&
             count < kDistinctCandidateSizes; ++count) {
            const Coordinate span = current->first;
            addSizeRepresentatives(current);
            current = bySize_.upper_bound({
                span,
                {std::numeric_limits<std::uint64_t>::max(),
                 std::numeric_limits<Coordinate>::max()}});
        }
        const Coordinate largestSpan = bySize_.rbegin()->first;
        addSizeRepresentatives(
            bySize_.lower_bound({largestSpan, {0, 0}}));
        Coordinate tailSpan = 0;
        const auto tail = tailGap();
        if (tail != gaps_.end()) {
            tailSpan = tail->second.end - tail->first;
            if (tailSpan >= length) addCandidate(tail->first);
        }
        // The complete size index has already established a fitting gap.
        if (candidateCount == 0) return fallback;
        std::sort(
            candidates.begin(),
            candidates.begin() + candidateCount,
            candidateLess);
        if (!kUseGlobalPackingForecast || candidateCount == 1) {
            return candidates[0].start;
        }
        const Scenarios scenarios = makeScenarios();
        Inventory working = interiorInventory_;
        ++mcDecisionsUsed;
        Coordinate chosenStart = candidates[0].start;
        unsigned bestScore =
            std::numeric_limits<unsigned>::max();
        for (int index = 0; index < candidateCount; ++index) {
            const Candidate& candidate =
                candidates[static_cast<std::size_t>(index)];
            std::array<Change, 2> undo{};
            int undoCount = 0;
            int virtualTail = capacityBucket(tailSpan);
            if (candidate.tail) {
                virtualTail =
                    capacityBucket(candidate.span - length);
            } else {
                recordChange(
                    working, capacityBucket(candidate.span), -1,
                    undo.data(), undoCount);
                recordChange(
                    working,
                    capacityBucket(candidate.span - length), 1,
                    undo.data(), undoCount);
            }
            unsigned score = 0;
            // Such a gap alone fits the complete forecast volume.
            const bool forecastFits =
                virtualTail >= kForecastCapacity ||
                working.count[kForecastCapacity] != 0;
            if (!forecastFits) {
                for (const auto& scenario : scenarios) {
                    score += forecastGrowth(
                        working, virtualTail, scenario);
                    ++mcRolloutsRun;
                    // Candidates are already ordered by the tie-break.
                    // Further nonnegative costs cannot rescue this one.
                    if (score >= bestScore) break;
                }
            }
            restore(working, undo.data(), undoCount);
            if (score < bestScore) {
                bestScore = score;
                chosenStart = candidate.start;
            }
            // Zero is the global minimum; later ties are less preferred.
            if (bestScore == 0) break;
        }
        return chosenStart;
    }
    static void printInvalidPid() {
        std::cout << 0 << '\n' << std::flush;
    }
};
}  // namespace
// EVOLVE-BLOCK-END

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    Allocator allocator;
    std::int64_t command;
    while (std::cin >> command) {
        if (command == 0) {
#if defined(MC_ROLLOUT_DIAGNOSTICS)
            std::cerr << "mc_decisions=" << allocator.mcDecisionsUsed
                      << " mc_rollouts=" << allocator.mcRolloutsRun
                      << " expansion_gate_opportunities=" << allocator.expansionGateOpportunities
                      << " expansion_gate_passes=" << allocator.expansionGatePasses
                      << " unit_profile_suppressed_expansions="
                      << allocator.unitProfileSuppressedExpansions << '\n';
#endif
            return 0;
        }
        if (command > 0) {
            allocator.place(static_cast<int>(command));
        } else {
            allocator.remove(-command);
        }
    }
    return 0;
}
```

Here are the performance metrics of the program:

Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 1.16; max_solver_rss_mib: 5.58

Here is additional text feedback about the current program:

Fitness F/T=0.855934858125; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737473286
family=short_phase_churn mean_F/T=0.787295458
family=short_rounding mean_F/T=0.798578833
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.803576047
family=drifting_sizes mean_F/T=0.805194719
family=short_heavy mean_F/T=0.813129206
family=additive_cohorts mean_F/T=0.813267456
family=tiny_churn mean_F/T=0.824960270
family=distribution_switch mean_F/T=0.825384561
family=size_biased_deletion mean_F/T=0.832715387
family=size_lifetimes mean_F/T=0.832990649
family=uniform_churn mean_F/T=0.834983307
family=long_heavy mean_F/T=0.836868225
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.849331290
family=serial_churn mean_F/T=0.856415740
family=large_live_set mean_F/T=0.878956721
family=bimodal mean_F/T=0.879427340
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.881565215
family=hotset_switching mean_F/T=0.883475355
family=section_boundaries mean_F/T=0.885905461
family=fifo mean_F/T=0.888451474
family=soft_recency_growth mean_F/T=0.896197702
family=burst_drain mean_F/T=0.902254811
family=serial_growth mean_F/T=0.915331126
family=long_prefill_recent mean_F/T=0.917690257
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920973630
family=drain_recovery mean_F/T=0.925592784
family=hotset_growth mean_F/T=0.951434211
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955525469
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001503 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001610 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001597 rss_mib=1.328
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001470 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001431 rss_mib=1.328
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001497 rss_mib=1.328
case=s31_118_partial_drain family=partial_drain F/T=0.611378646 F/B=0.646045362 B/T=0.946340121 overrun=0.056703 cpu_s=0.087387 rss_mib=1.984
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.615796039 F/B=0.675406191 B/T=0.911741775 overrun=0.096802 cpu_s=0.351715 rss_mib=3.078
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.353431 rss_mib=2.922
case=s31_060_large_live_set family=large_live_set F/T=0.632347623 F/B=0.641932619 B/T=0.985068533 overrun=0.015158 cpu_s=0.479996 rss_mib=3.672
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001527 rss_mib=1.328
case=s31_040_distribution_switch family=distribution_switch F/T=0.648873874 F/B=0.692548077 B/T=0.936936937 overrun=0.067308 cpu_s=0.019403 rss_mib=1.422
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001441 rss_mib=1.328
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003156 rss_mib=1.375
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.013057 rss_mib=1.500
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002584 rss_mib=1.375
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.425423 rss_mib=3.000
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.753968254 F/B=0.950000000 B/T=0.793650794 overrun=0.260000 cpu_s=0.375649 rss_mib=2.969
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.757530231 F/B=0.950045956 B/T=0.797361671 overrun=0.254136 cpu_s=0.148208 rss_mib=2.000
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002584 rss_mib=1.375
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.353431 rss_mib=2.922
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.700161812 F/B=0.865400000 B/T=0.809061489 overrun=0.236000 cpu_s=0.082575 rss_mib=1.656
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.808163265 F/B=0.990000000 B/T=0.816326531 overrun=0.225000 cpu_s=0.039861 rss_mib=1.516
case=s31_086_tiny_churn family=tiny_churn F/T=0.783450704 F/B=0.959051724 B/T=0.816901408 overrun=0.224138 cpu_s=0.132048 rss_mib=1.844
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.124779 rss_mib=1.844
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001701 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002559 rss_mib=1.359
case=s31_001_uniform_churn family=uniform_churn F/T=0.815384615 F/B=0.963636364 B/T=0.846153846 overrun=0.181818 cpu_s=0.055329 rss_mib=1.516
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.034871 rss_mib=1.516
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.597414 rss_mib=3.297
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.817329427 F/B=0.950170316 B/T=0.860192549 overrun=0.162530 cpu_s=0.139134 rss_mib=1.938
case=s31_102_serial_churn family=serial_churn F/T=0.820923913 F/B=0.950000000 B/T=0.864130435 overrun=0.157233 cpu_s=0.172685 rss_mib=1.906

PAIRED SEARCH EVIDENCE
Against parent gen18: delta mean F/T=+0.000393930; improved/regressed/tied=36/33/83.
family=drifting_sizes delta_F/T=+0.024001624
family=size_lifetimes delta_F/T=-0.020837464
family=distribution_switch delta_F/T=+0.013868665
family=tiny_churn delta_F/T=-0.011693294
family=burst_drain delta_F/T=+0.010275972
family=serial_churn delta_F/T=-0.009196396
Regressions:
s31_030_size_lifetimes: delta_F/T=-0.071836735, delta_T=+80
s31_086_tiny_churn: delta_F/T=-0.046773176, delta_T=+160
s31_055_additive_cohorts: delta_F/T=-0.031938250, delta_T=+40
s31_103_serial_churn: delta_F/T=-0.028844086, delta_T=+40
Gains:
s31_041_drifting_sizes: delta_F/T=+0.084954169, delta_T=-160
s31_039_distribution_switch: delta_F/T=+0.056238095, delta_T=-100
s31_033_burst_drain: delta_F/T=+0.041904762, delta_T=-40
s31_001_uniform_churn: delta_F/T=+0.039774859, delta_T=-40

Against leader gen24: delta mean F/T=-0.002791024; improved/regressed/tied=32/47/73.
family=size_lifetimes delta_F/T=-0.045006683
family=short_rounding delta_F/T=-0.020300752
family=fifo delta_F/T=+0.017184129
family=tiny_churn delta_F/T=-0.011693294
family=burst_drain delta_F/T=-0.009079370
family=distribution_switch delta_F/T=-0.007795972
Regressions:
s31_122_short_rounding: delta_F/T=-0.081203008, delta_T=+40
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_030_size_lifetimes: delta_F/T=-0.071836735, delta_T=+80
s31_086_tiny_churn: delta_F/T=-0.046773176, delta_T=+160
Gains:
s31_024_fifo: delta_F/T=+0.041089202, delta_T=-80
s31_062_size_biased_deletion: delta_F/T=+0.023516677, delta_T=-220
s31_064_size_biased_deletion: delta_F/T=+0.021449690, delta_T=-2620
s31_023_fifo: delta_F/T=+0.017793367, delta_T=-20

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.855934858; mean positive loss on worst 16 cases=0.034875508; max case loss=0.081203008; regressed cases=46; worst family delta F/T=-0.028720639. These are selection diagnostics; primary fitness remains mean F/T.


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
