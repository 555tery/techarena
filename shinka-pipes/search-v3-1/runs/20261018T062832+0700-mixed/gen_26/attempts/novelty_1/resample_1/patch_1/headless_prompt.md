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

MIXED-START ISOLATION: use only this lineage's completed candidates and feedback. Do not infer from other lineages or historical memory.
RESEARCH MEMORY — measured evidence, descriptions are unverified author claims.
Past failures are not universal bans. Explain changed behavior/assumptions when retrying.
Do not rename an already tested policy and present it as a new mechanism.
No equivalence is inferred from a shared score or a shared finite case vector.
CURRENT SEARCH-v3.1 (F/T):
SEARCH-v2 generation 27: attempts=1; score_range=0.855381088..0.855381088
global_packing_rollout: attempts=1; score_range=0.855540928..0.855540928
harmonic_fit_inventory: attempts=1; score_range=0.855727244..0.855727244
gen8 harmonic_fit_inventory; correct=True; parent=1; delta_F/T=+0.000346156; claim=Родитель использует окна 128/2048 вставок, смесь частот 0.75/0.25, сглаживание 0.02, potential до 160, десять ближайших различных размеров промежутков и прогноз освобождений по длине, фазе и возрасту. Эти настройки сохра
  improved/regressed/tied=42/38/72
  regression s31_001_uniform_churn: delta_F/T=-0.055465116
  regression s31_087_tiny_churn: delta_F/T=-0.044444444
gen18 global_packing_rollout; correct=True; parent=1; delta_F/T=+0.000159840; claim=Механизм — совместный прогноз упаковки во все свободные промежутки. Для каждого рассматриваемого размещения алгоритм моделирует четыре общих сценария по восемь вставок, используя только распределение уже наблюдавшихся дл
  improved/regressed/tied=45/46/61
  regression s31_122_short_rounding: delta_F/T=-0.081203008
  regression s31_039_distribution_switch: delta_F/T=-0.081049020
gen1 SEARCH-v2 generation 27; correct=True; parent=None; delta_F/T=n/a; claim=Pinned strong/simple seed
  improved/regressed/tied=47/34/71
  regression s31_086_tiny_churn: delta_F/T=-0.082027650
  regression s31_009_long_heavy: delta_F/T=-0.025423729
HISTORICAL SEARCH-v2 (different inputs AND B/T objective; not a v3.1 ranking):
LINEAGE PARENT: mode=lineage-local-score; lineage=1; local mean leader=0.855727244; fixed-baseline tail loss=0.021691462; maximum case loss=0.070939610.
Rewrite the program to improve its performance on the specified metrics.
Provide the complete new program code.
You MUST respond using a short summary name, description and the full code:

<NAME>
A shortened name summarizing the code you are proposing. Lowercase, no spaces, underscores allowed.
</NAME>

<DESCRIPTION>
A description and argumentation process of the code you are proposing.
</DESCRIPTION>

<CODE>
```{language}
# The new rewritten program here.
```
</CODE>

* Keep the markers "EVOLVE-BLOCK-START" and "EVOLVE-BLOCK-END" in the code. Do not change the code outside of these markers.
* Make sure your rewritten program maintains the same inputs and outputs as the original program, but with improved internal implementation.
* Make sure the file still runs after your changes.
* Use the <NAME>, <DESCRIPTION>, and <CODE> delimiters to structure your response. It will be parsed afterwards.

# Previous Messages

[]

# User Request

Here are the performance metrics of a set of previously implemented programs:

# Prior programs

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
#include <cmath>
namespace {
using Coordinate = std::int64_t;
using GapKey = std::pair<Coordinate, Coordinate>;
using GapAgeKey =
    std::pair<Coordinate, std::pair<std::uint64_t, Coordinate>>;
constexpr bool kOldestGapTieBreak = true;
constexpr bool kCoalescingReleaseGeometry = true;
constexpr bool kAgeConditionalReleaseRisk = true;
constexpr int kAgeBandCount = 4;
constexpr Coordinate kSectionLength = 20;
constexpr std::size_t kFastWindow = 128;
constexpr std::size_t kSlowWindow = 2048;
constexpr int kPotentialLimit = 160;
constexpr int kDistinctCandidateSizes = 10;
constexpr int kPhaseCount = 8;
// Exposure includes still-live pipes, so long-lived survivors contribute
// evidence without requiring their eventual deletion.
struct Rate {
    int live = 0;
    double exposure = 0.0;
    double deaths = 0.0;
    std::uint64_t stamp = 0;
    double exposureAt(std::uint64_t now) const {
        return exposure +
            static_cast<double>(now - stamp) * static_cast<double>(live);
    }
    void touch(std::uint64_t now) {
        exposure = exposureAt(now);
        stamp = now;
    }
    void change(std::uint64_t now, int delta, bool removed) {
        touch(now);
        live += delta;
        if (removed) deaths += 1.0;
    }
    void forget(std::uint64_t now) {
        touch(now);
        exposure *= 0.5;
        deaths *= 0.5;
    }
};
struct Pipe {
    Coordinate start = 0;
    std::uint64_t bornTick = 0;
    std::uint64_t ageUnit = 1;
    int length = 0;
    int previous = 0;
    int next = 0;
    unsigned char runPhase = 0;
    unsigned char group = 1;
    unsigned char ageBand = 0;
    bool active = false;
};
struct Gap {
    Coordinate end = 0;
    int left = 0;
    int right = 0;
    std::uint64_t freeSince = 0;
};
struct Choice {
    bool valid = false;
    Coordinate gapStart = 0;
    Coordinate start = 0;
    Coordinate span = 0;
    std::uint64_t freeSince = 0;
    double score = std::numeric_limits<double>::infinity();
};
class Allocator {
public:
    // Preserve the optional diagnostics interface used outside the block.
    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        beginCommand();
        const bool newlyObservedLength =
            fastFrequency_[static_cast<std::size_t>(length)] == 0;
        if (lastPlacementLength_ != length) {
            lastPlacementLength_ = length;
            runOrdinal_ = 0;
        }
        const int runPhase = static_cast<int>(runOrdinal_ & 7U);
        ++runOrdinal_;
        observeLength(length);
        refreshModel(newlyObservedLength);
        const int pid = static_cast<int>(pipes_.size());
        const int globalPhase = pid & 7;
        const double deletionProbability =
            predictDeletion(length, globalPhase, runPhase);
        const int group = classify(deletionProbability);
        peakLiveVolume_ = std::max(
            peakLiveVolume_, liveVolume_ + static_cast<Coordinate>(length));
        // An already available tail can become a two-front arena without
        // requesting any additional excavation.
        if (!arenaActive_ && canSeparate(deletionProbability)) {
            const auto tail = tailGap();
            if (tail != gaps_.end() &&
                tail->second.end - tail->first >= 2LL * length) {
                arenaActive_ = true;
                arenaStart_ = tail->first;
                arenaEnd_ = trenchLength_;
            }
        }
        Choice choice;
        Coordinate digs = 0;
        const auto firstFit = bySize_.lower_bound({length, 0});
        if (firstFit != bySize_.end()) {
            selectCandidates(length, group, deletionProbability, choice);
        } else {
            digs = growFor(length, deletionProbability, choice);
        }
        const auto selected = gaps_.find(choice.gapStart);
        const Coordinate gapStart = selected->first;
        const Gap gap = selected->second;
        eraseGap(selected);
        Pipe pipe;
        pipe.start = choice.start;
        pipe.length = length;
        pipe.previous = gap.left;
        pipe.next = gap.right;
        pipe.runPhase = static_cast<unsigned char>(runPhase);
        pipe.group = static_cast<unsigned char>(group);
        pipe.bornTick = tick_;
        // Freeze only the age-bin scale, never the remaining-life risk.
        pipe.ageUnit = std::max<std::uint64_t>(
            1, static_cast<std::uint64_t>(
                std::min(lifetimeHorizon_, static_cast<double>(tick_))));
        pipe.active = true;
        pipes_.push_back(pipe);
        ageRates_[static_cast<std::size_t>(group)][0].change(
            tick_, 1, false);
        ageEvents_.insert({nextAgeCheckpoint(pipe), pid});
        if (gap.left != 0) pipes_[gap.left].next = pid;
        if (gap.right != 0) {
            pipes_[gap.right].previous = pid;
        } else {
            tailPid_ = pid;
        }
        insertGap(
            gapStart, pipe.start, gap.left, pid, gap.freeSince);
        insertGap(
            pipe.start + length, gap.end, pid, gap.right, gap.freeSince);
        changePopulation(length, globalPhase, runPhase, 1, false);
        ++liveGroups_[static_cast<std::size_t>(group)];
        liveVolume_ += length;
        std::cout << digs << ' ' << pipe.start << '\n' << std::flush;
    }
    void remove(Coordinate pidValue) {
        if (pidValue <= 0 ||
            static_cast<std::uint64_t>(pidValue) >= pipes_.size()) {
            printInvalidPid();
            return;
        }
        const int pid = static_cast<int>(pidValue);
        if (!pipes_[static_cast<std::size_t>(pid)].active) {
            printInvalidPid();
            return;
        }
        beginCommand();
        const Pipe pipe = pipes_[static_cast<std::size_t>(pid)];
        ageRates_[static_cast<std::size_t>(pipe.group)]
                 [static_cast<std::size_t>(pipe.ageBand)].change(
            tick_, -1, true);
        if (static_cast<int>(pipe.ageBand) + 1 < kAgeBandCount) {
            ageEvents_.erase({nextAgeCheckpoint(pipe), pid});
        }
        if (pipe.previous != 0) {
            pipes_[pipe.previous].next = pipe.next;
        }
        if (pipe.next != 0) {
            pipes_[pipe.next].previous = pipe.previous;
        } else {
            tailPid_ = pipe.previous;
        }
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
        pipes_[static_cast<std::size_t>(pid)].active = false;
        insertGap(start, end, pipe.previous, pipe.next, tick_);
        changePopulation(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase), -1, true);
        --liveGroups_[static_cast<std::size_t>(pipe.group)];
        liveVolume_ -= pipe.length;
        if (totalRate_.live == 0) arenaActive_ = false;
        std::cout << pipe.start << '\n' << std::flush;
    }
private:
    using GapMap = std::map<Coordinate, Gap>;
    using GapIterator = GapMap::iterator;
    GapMap gaps_;
    std::set<GapKey> bySize_;
    std::set<GapAgeKey> byAge_;
    std::array<std::set<GapKey>, 3> byBoundaryGroup_;
    std::vector<Pipe> pipes_{Pipe{}};
    int tailPid_ = 0;
    Coordinate trenchLength_ = 0;
    Coordinate liveVolume_ = 0;
    Coordinate peakLiveVolume_ = 0;
    std::array<int, 3> liveGroups_{};
    std::uint64_t tick_ = 0;
    std::uint64_t modelTick_ = 0;
    bool haveModel_ = false;
    int lastPlacementLength_ = -1;
    std::uint64_t runOrdinal_ = 0;
    Rate totalRate_;
    std::array<Rate, 41> lengthRates_{};
    std::array<Rate, kPhaseCount> globalPhaseRates_{};
    std::array<Rate, kPhaseCount> runPhaseRates_{};
    std::array<std::array<Rate, kAgeBandCount>, 3> ageRates_{};
    std::array<std::array<double, kAgeBandCount>, 3> ageMultiplier_{};
    std::set<std::pair<std::uint64_t, int>> ageEvents_;
    double lifetimeHorizon_ = 1.0;
    std::array<double, 41> lengthRisk_{};
    std::array<double, kPhaseCount> globalPhaseRisk_{};
    std::array<double, kPhaseCount> runPhaseRisk_{};
    std::deque<int> recentLengths_;
    std::array<int, 41> fastFrequency_{};
    std::array<int, 41> slowFrequency_{};
    std::array<double, kPotentialLimit + 1> potential_{};
    bool arenaActive_ = false;
    Coordinate arenaStart_ = 0;
    Coordinate arenaEnd_ = 0;
    static double difference(double a, double b) {
        return a >= b ? a - b : b - a;
    }
    static int classify(double probability) {
        if (probability < 1.0 / 3.0) return 0;
        if (probability > 2.0 / 3.0) return 2;
        return 1;
    }
    static std::uint64_t nextAgeCheckpoint(const Pipe& pipe) {
        return pipe.bornTick +
            pipe.ageUnit * (std::uint64_t{1} << pipe.ageBand);
    }
    void beginCommand() {
        ++tick_;
        // One pending event per live pipe, at most three transitions total.
        // Moving a survivor between bands is censoring, not a death.
        while (!ageEvents_.empty() &&
               ageEvents_.begin()->first <= tick_) {
            const auto event = *ageEvents_.begin();
            ageEvents_.erase(ageEvents_.begin());
            Pipe& pipe = pipes_[static_cast<std::size_t>(event.second)];
            auto& rates = ageRates_[static_cast<std::size_t>(pipe.group)];
            rates[static_cast<std::size_t>(pipe.ageBand)].change(
                event.first, -1, false);
            ++pipe.ageBand;
            rates[static_cast<std::size_t>(pipe.ageBand)].change(
                event.first, 1, false);
            if (static_cast<int>(pipe.ageBand) + 1 < kAgeBandCount) {
                ageEvents_.insert({
                    nextAgeCheckpoint(pipe), event.second});
            }
        }
        if ((tick_ & 1023U) == 0) {
            totalRate_.forget(tick_);
            for (Rate& rate : lengthRates_) rate.forget(tick_);
            for (Rate& rate : globalPhaseRates_) rate.forget(tick_);
            for (Rate& rate : runPhaseRates_) rate.forget(tick_);
            for (auto& bands : ageRates_) {
                for (Rate& rate : bands) rate.forget(tick_);
            }
        }
    }
    void changePopulation(
        int length, int globalPhase, int runPhase,
        int delta, bool removed) {
        totalRate_.change(tick_, delta, removed);
        lengthRates_[static_cast<std::size_t>(length)].change(
            tick_, delta, removed);
        globalPhaseRates_[static_cast<std::size_t>(globalPhase)].change(
            tick_, delta, removed);
        runPhaseRates_[static_cast<std::size_t>(runPhase)].change(
            tick_, delta, removed);
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
    void rebuildPhaseRisk(
        const std::array<Rate, kPhaseCount>& observations,
        double globalRate,
        std::array<double, kPhaseCount>& result) {
        // Hierarchical smoothing shares evidence between cyclic positions.
        // No deletion pattern is enabled by a fixed sequence of commands.
        for (int residue = 0; residue < kPhaseCount; ++residue) {
            double rate = globalRate;
            for (int period = 2; period <= kPhaseCount; period *= 2) {
                double exposure = 0.0;
                double deaths = 0.0;
                for (int position = residue % period;
                     position < kPhaseCount; position += period) {
                    const Rate& observation =
                        observations[static_cast<std::size_t>(position)];
                    exposure += observation.exposureAt(tick_);
                    deaths += observation.deaths;
                }
                constexpr double priorDeaths = 8.0;
                rate = (deaths + priorDeaths) /
                    (exposure + priorDeaths / rate);
            }
            result[static_cast<std::size_t>(residue)] =
                std::clamp(rate / globalRate, 0.125, 8.0);
        }
    }
    void rebuildAgeRisk(double globalRate) {
        for (std::size_t group = 0; group < ageRates_.size(); ++group) {
            double exposure = 0.0;
            double deaths = 0.0;
            for (const Rate& observation : ageRates_[group]) {
                exposure += observation.exposureAt(tick_);
                deaths += observation.deaths;
            }
            const double pooledRate =
                (deaths + 4.0) / (exposure + 4.0 / globalRate);
            for (int band = 0; band < kAgeBandCount; ++band) {
                const std::size_t index = static_cast<std::size_t>(band);
                const Rate& observation = ageRates_[group][index];
                const double expectedDeaths =
                    observation.exposureAt(tick_) * pooledRate;
                constexpr double priorDeaths = 8.0;
                double multiplier = 1.0;
                if (observation.deaths >= priorDeaths ||
                    expectedDeaths >= priorDeaths) {
                    // Age-conditioned hazard divided by pooled hazard.
                    // Exposure from survivors can lower this estimate.
                    multiplier =
                        (observation.deaths + priorDeaths) /
                        (expectedDeaths + priorDeaths);
                }
                ageMultiplier_[group][index] = multiplier;
            }
        }
    }
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) return;
        modelTick_ = tick_;
        haveModel_ = true;
        const double globalRate =
            (totalRate_.deaths + 4.0) /
            (totalRate_.exposureAt(tick_) +
             4.0 * static_cast<double>(totalRate_.live + 1));
        lifetimeHorizon_ = 1.0 / globalRate;
        rebuildAgeRisk(globalRate);
        for (int length = 1; length <= 40; ++length) {
            const Rate& observation =
                lengthRates_[static_cast<std::size_t>(length)];
            constexpr double priorDeaths = 4.0;
            const double rate =
                (observation.deaths + priorDeaths) /
                (observation.exposureAt(tick_) +
                 priorDeaths / globalRate);
            lengthRisk_[static_cast<std::size_t>(length)] =
                std::clamp(rate / globalRate, 0.0625, 16.0);
        }
        rebuildPhaseRisk(
            globalPhaseRates_, globalRate, globalPhaseRisk_);
        rebuildPhaseRisk(
            runPhaseRates_, globalRate, runPhaseRisk_);
        std::array<double, 41> probability{};
        std::array<double, 41> prefix{};
        const double fastCount = static_cast<double>(
            std::min(kFastWindow, recentLengths_.size()));
        const double slowCount =
            static_cast<double>(recentLengths_.size());
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index = static_cast<std::size_t>(length);
            probability[index] =
                0.98 * (
                    0.75 * fastFrequency_[index] / fastCount +
                    0.25 * slowFrequency_[index] / slowCount) +
                0.02 / 40.0;
            prefix[index] = prefix[index - 1] + probability[index];
        }
        prefix[40] = 1.0;
        // Renewal reward: at each step, allow up to four observed-distribution
        // requests to find a fitting one, then continue with the remainder.
        potential_[0] = 0.0;
        for (int capacity = 1;
             capacity <= kPotentialLimit; ++capacity) {
            const int maximum = std::min(capacity, 40);
            const double fit = prefix[static_cast<std::size_t>(maximum)];
            const double miss = std::max(0.0, 1.0 - fit);
            const double retryFactor =
                1.0 + miss + miss * miss + miss * miss * miss;
            double reward = 0.0;
            for (int length = 1; length <= maximum; ++length) {
                reward += probability[static_cast<std::size_t>(length)] *
                    (static_cast<double>(length) +
                     potential_[static_cast<std::size_t>(capacity - length)]);
            }
            potential_[static_cast<std::size_t>(capacity)] =
                std::clamp(
                    retryFactor * reward,
                    0.0, static_cast<double>(capacity));
        }
    }
    double predictDeletion(
        int length, int globalPhase, int runPhase) const {
        const double phaseMultiplier = 0.5 * (
            globalPhaseRisk_[static_cast<std::size_t>(globalPhase)] +
            runPhaseRisk_[static_cast<std::size_t>(runPhase)]);
        const double relativeRate = std::clamp(
            lengthRisk_[static_cast<std::size_t>(length)] *
                phaseMultiplier,
            1.0 / 32.0, 32.0);
        // A bounded survival approximation over a typical lifetime horizon.
        return relativeRate / (1.0 + relativeRate);
    }
    double predictDeletion(int pid) const {
        if (pid == 0) return 0.0;
        const Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        const double fallback = predictDeletion(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase));
        // Bookkeeping and model updates are identical in both ablations.
        if (!kAgeConditionalReleaseRisk) return fallback;
        const auto& multipliers =
            ageMultiplier_[static_cast<std::size_t>(pipe.group)];
        double age = static_cast<double>(tick_ - pipe.bornTick);
        double remaining = lifetimeHorizon_;
        double weightedDuration = 0.0;
        bool adjusted = false;
        for (int band = static_cast<int>(pipe.ageBand);
             band < kAgeBandCount && remaining > 0.0; ++band) {
            double duration = remaining;
            if (band + 1 < kAgeBandCount) {
                const double boundary =
                    static_cast<double>(pipe.ageUnit) *
                    static_cast<double>(std::uint64_t{1} << band);
                duration = std::min(
                    remaining, std::max(0.0, boundary - age));
            }
            const double multiplier =
                multipliers[static_cast<std::size_t>(band)];
            weightedDuration += duration * multiplier;
            if (duration > 0.0 && multiplier != 1.0) adjusted = true;
            age += duration;
            remaining -= duration;
        }
        if (!adjusted) return fallback;
        // Conditional survival over [age, age + horizon].
        // Unit multipliers recover the parent's probability exactly.
        const double logSurvival =
            std::log1p(-fallback) *
            (weightedDuration / lifetimeHorizon_);
        return std::clamp(-std::expm1(logSurvival), 0.0, 1.0);
    }
    double utility(Coordinate length) const {
        if (length <= 0) return 0.0;
        if (length <= kPotentialLimit) {
            return potential_[static_cast<std::size_t>(length)];
        }
        return potential_[kPotentialLimit] +
            static_cast<double>(length - kPotentialLimit);
    }
    bool canSeparate(double probability) const {
        return totalRate_.deaths >= 16.0 &&
            liveGroups_[0] >= 2 && liveGroups_[2] >= 2 &&
            (probability < 0.25 || probability > 0.75);
    }
    void considerGap(
        Coordinate gapStart, int length,
        double newDeletion, Choice& best) const {
        const auto found = gaps_.find(gapStart);
        if (found == gaps_.end()) return;
        const Gap& gap = found->second;
        const Coordinate span = gap.end - gapStart;
        if (span < length) return;
        if (gap.end == trenchLength_) {
            // Use the expandable tail only when no interior gap fits.
            // The unique tail can occupy at most one size-index entry.
            auto interior = bySize_.lower_bound({length, 0});
            if (interior != bySize_.end() &&
                interior->second == gapStart) {
                ++interior;
            }
            if (interior != bySize_.end()) return;
        }
        const Coordinate remainder = span - length;
        // On a neighbor's release, its far-side free gap also coalesces.
        // The release loops below include this span only in that event.
        Coordinate leftLength = 0;
        if (gap.left != 0) {
            const Pipe& neighbor =
                pipes_[static_cast<std::size_t>(gap.left)];
            leftLength = neighbor.length;
            const auto next = gaps_.lower_bound(neighbor.start);
            if (next != gaps_.begin()) {
                const auto outside = std::prev(next);
                if (kCoalescingReleaseGeometry &&
                    outside->second.end == neighbor.start) {
                    leftLength += outside->second.end - outside->first;
                }
            }
        }
        Coordinate rightLength = 0;
        if (gap.right != 0) {
            const Pipe& neighbor =
                pipes_[static_cast<std::size_t>(gap.right)];
            rightLength = neighbor.length;
            const auto outside =
                gaps_.find(neighbor.start + neighbor.length);
            if (kCoalescingReleaseGeometry && outside != gaps_.end()) {
                rightLength += outside->second.end - outside->first;
            }
        }
        const double leftDeletion = predictDeletion(gap.left);
        const double rightDeletion = predictDeletion(gap.right);
        const double immediateCost = utility(span) - utility(remainder);
        double futureLow = 0.0;
        double futureHigh = 0.0;
        // Expected opportunity cost conditional on the new pipe surviving.
        // Each neighboring pipe can independently release its occupied span.
        for (int releaseLeft = 0; releaseLeft < 2; ++releaseLeft) {
            const double leftWeight = releaseLeft
                ? leftDeletion : 1.0 - leftDeletion;
            const Coordinate leftFree =
                releaseLeft ? leftLength : 0;
            for (int releaseRight = 0; releaseRight < 2; ++releaseRight) {
                const double rightWeight = releaseRight
                    ? rightDeletion : 1.0 - rightDeletion;
                const double weight = leftWeight * rightWeight;
                if (weight == 0.0) continue;
                const Coordinate rightFree =
                    releaseRight ? rightLength : 0;
                const double whole =
                    utility(span + leftFree + rightFree);
                futureLow += weight * (
                    whole - utility(leftFree) -
                    utility(remainder + rightFree));
                futureHigh += weight * (
                    whole - utility(remainder + leftFree) -
                    utility(rightFree));
            }
        }
        const bool insideArena =
            arenaActive_ && gapStart >= arenaStart_ &&
            gap.end <= arenaEnd_;
        const double futureWeight = 0.5 * (1.0 - newDeletion);
        for (int side = 0; side < 2; ++side) {
            const bool high = side != 0;
            if (high && remainder == 0) continue;
            if (high && gap.end == trenchLength_ && !insideArena) {
                continue;
            }
            const double futureCost = high ? futureHigh : futureLow;
            double score =
                (1.0 - futureWeight) * immediateCost +
                futureWeight * futureCost;
            if (remainder > 0) {
                const int neighbor = high ? gap.right : gap.left;
                if (neighbor != 0) {
                    const double neighborDeletion =
                        high ? rightDeletion : leftDeletion;
                    score += 0.10 * length *
                        difference(newDeletion, neighborDeletion);
                }
                if (insideArena) {
                    // Fast-deleting pipes approach from the low side;
                    // slow-deleting pipes approach from the high side.
                    score += 0.125 * length *
                        (high ? newDeletion : 1.0 - newDeletion);
                }
            } else {
                if (gap.left != 0) {
                    score += 0.05 * length *
                        difference(newDeletion, leftDeletion);
                }
                if (gap.right != 0) {
                    score += 0.05 * length *
                        difference(newDeletion, rightDeletion);
                }
            }
            const Coordinate position =
                high ? gap.end - length : gapStart;
            const bool sameSpanTieBetter =
                (kOldestGapTieBreak && gap.freeSince != best.freeSince)
                    ? gap.freeSince < best.freeSince
                    : position < best.start;
            const bool better =
                !best.valid ||
                score < best.score - 1e-10 ||
                (score <= best.score + 1e-10 &&
                 (span < best.span ||
                  (span == best.span && sameSpanTieBetter)));
            if (better) {
                best.valid = true;
                best.gapStart = gapStart;
                best.start = position;
                best.span = span;
                best.freeSince = gap.freeSince;
                best.score = score;
            }
        }
    }
    void considerOldest(
        Coordinate span, int length,
        double deletionProbability, Choice& choice) const {
        if (span < length) return;
        auto oldest = byAge_.lower_bound({span, {0, 0}});
        if (oldest == byAge_.end() || oldest->first != span) return;
        const auto found = gaps_.find(oldest->second.second);
        if (found->second.end == trenchLength_) {
            // If the oldest is the tail, the next entry of this span
            // is the oldest interior gap. There is only one tail.
            const auto next = std::next(oldest);
            if (next != byAge_.end() && next->first == span) {
                oldest = next;
            }
        }
        // Candidate coverage is identical in both tie-break ablations.
        // considerGap retains the exact interior-before-tail check.
        considerGap(
            oldest->second.second, length, deletionProbability, choice);
    }
    void considerNear(
        const std::set<GapKey>& index, Coordinate minimumSpan,
        int length, double deletionProbability, Choice& choice) const {
        const auto first = index.lower_bound({minimumSpan, 0});
        if (first == index.end()) return;
        considerGap(first->second, length, deletionProbability, choice);
        const auto after = index.upper_bound({
            first->first, std::numeric_limits<Coordinate>::max()});
        const auto last = std::prev(after);
        if (last->second != first->second) {
            considerGap(last->second, length, deletionProbability, choice);
        }
        considerOldest(
            first->first, length, deletionProbability, choice);
    }
    void selectCandidates(
        int length, int group,
        double deletionProbability, Choice& choice) const {
        auto current = bySize_.lower_bound({length, 0});
        for (int count = 0;
             current != bySize_.end() &&
             count < kDistinctCandidateSizes; ++count) {
            const auto after = bySize_.upper_bound({
                current->first,
                std::numeric_limits<Coordinate>::max()});
            considerGap(
                current->second, length, deletionProbability, choice);
            const auto last = std::prev(after);
            if (last->second != current->second) {
                considerGap(
                    last->second, length, deletionProbability, choice);
            }
            considerOldest(
                current->first, length, deletionProbability, choice);
            current = after;
        }
        // Include wider residual-capacity bands even when many small
        // distinct spans precede them.
        for (int offset : {40, 80, 160}) {
            considerNear(
                bySize_, static_cast<Coordinate>(length) + offset,
                length, deletionProbability, choice);
        }
        considerNear(
            byBoundaryGroup_[static_cast<std::size_t>(group)],
            length, length, deletionProbability, choice);
        if (!gaps_.empty()) {
            const auto last = std::prev(gaps_.end());
            if (last->second.end == trenchLength_) {
                considerGap(
                    last->first, length, deletionProbability, choice);
                considerOldest(
                    last->second.end - last->first,
                    length, deletionProbability, choice);
            }
        }
    }
    GapIterator tailGap() {
        if (gaps_.empty()) return gaps_.end();
        const auto last = std::prev(gaps_.end());
        return last->second.end == trenchLength_ ? last : gaps_.end();
    }
    Coordinate growFor(
        int length, double deletionProbability, Choice& choice) {
        Coordinate start = trenchLength_;
        int left = tailPid_;
        const auto tail = tailGap();
        if (tail != gaps_.end()) {
            start = tail->first;
            left = tail->second.left;
            eraseGap(tail);
        }
        const Coordinate available = trenchLength_ - start;
        const Coordinate deficit =
            std::max<Coordinate>(0, length - available);
        Coordinate digs =
            (deficit + kSectionLength - 1) / kSectionLength;
        ++expansionGateOpportunities;
        const bool separate = canSeparate(deletionProbability);
        Coordinate extraDigs = 0;
        if (separate) {
            const Coordinate minimumCapacity =
                available + digs * kSectionLength;
            const Coordinate wantedExtra = std::max<Coordinate>(
                0, 3LL * length - minimumCapacity);
            const Coordinate budgetSections =
                (peakLiveVolume_ / 64) / kSectionLength;
            const Coordinate wantedSections =
                (wantedExtra + kSectionLength - 1) / kSectionLength;
            extraDigs = std::min(budgetSections, wantedSections);
            digs += extraDigs;
        }
        if (extraDigs > 0) ++expansionGatePasses;
        trenchLength_ += digs * kSectionLength;
        arenaActive_ =
            separate && trenchLength_ - start >= 2LL * length;
        if (arenaActive_) {
            arenaStart_ = start;
            arenaEnd_ = trenchLength_;
        }
        insertGap(start, trenchLength_, left, 0, tick_);
        considerGap(start, length, deletionProbability, choice);
        return digs;
    }
    void insertGap(
        Coordinate start, Coordinate end, int left, int right,
        std::uint64_t freeSince) {
        if (start >= end) return;
        gaps_.emplace(start, Gap{end, left, right, freeSince});
        const GapKey key{end - start, start};
        bySize_.insert(key);
        byAge_.insert({key.first, {freeSince, start}});
        const int leftGroup = left == 0
            ? -1 : static_cast<int>(pipes_[left].group);
        const int rightGroup = right == 0
            ? -1 : static_cast<int>(pipes_[right].group);
        if (leftGroup >= 0) {
            byBoundaryGroup_[static_cast<std::size_t>(leftGroup)].insert(key);
        }
        if (rightGroup >= 0 && rightGroup != leftGroup) {
            byBoundaryGroup_[static_cast<std::size_t>(rightGroup)].insert(key);
        }
    }
    void eraseGap(GapIterator position) {
        const Coordinate start = position->first;
        const Gap gap = position->second;
        const GapKey key{gap.end - start, start};
        bySize_.erase(key);
        byAge_.erase({key.first, {gap.freeSince, start}});
        const int leftGroup = gap.left == 0
            ? -1 : static_cast<int>(pipes_[gap.left].group);
        const int rightGroup = gap.right == 0
            ? -1 : static_cast<int>(pipes_[gap.right].group);
        if (leftGroup >= 0) {
            byBoundaryGroup_[static_cast<std::size_t>(leftGroup)].erase(key);
        }
        if (rightGroup >= 0 && rightGroup != leftGroup) {
            byBoundaryGroup_[static_cast<std::size_t>(rightGroup)].erase(key);
        }
        gaps_.erase(position);
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

Performance metrics:
Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 3.06; max_solver_rss_mib: 13.81

Text feedback:
Fitness F/T=0.855381088013; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737759792
family=short_phase_churn mean_F/T=0.774928822
family=tiny_churn mean_F/T=0.775607864
family=short_heavy mean_F/T=0.783624542
family=micro_size_shift mean_F/T=0.802083333
family=drifting_sizes mean_F/T=0.803008716
family=geometric_cohorts mean_F/T=0.803036290
family=additive_cohorts mean_F/T=0.812500629
family=short_rounding mean_F/T=0.818879585
family=size_biased_deletion mean_F/T=0.832590485
family=uniform_churn mean_F/T=0.835364668
family=distribution_switch mean_F/T=0.837041600
family=long_heavy mean_F/T=0.839463574
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.846492912
family=serial_churn mean_F/T=0.865882047
family=fifo mean_F/T=0.869557498
family=size_lifetimes mean_F/T=0.869695280
family=large_live_set mean_F/T=0.880320794
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882286056
family=bimodal mean_F/T=0.882328612
family=hotset_switching mean_F/T=0.892947812
family=soft_recency_growth mean_F/T=0.895561389
family=section_boundaries mean_F/T=0.896919819
family=burst_drain mean_F/T=0.897140926
family=serial_growth mean_F/T=0.913399107
family=long_prefill_recent mean_F/T=0.917877119
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920477572
family=drain_recovery mean_F/T=0.924451510
family=hotset_growth mean_F/T=0.952024691
family=background_ephemeral mean_F/T=0.952733011
family=lifo mean_F/T=0.953245266
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.002215 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.002200 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001874 rss_mib=1.359
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.002488 rss_mib=1.359
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.003169 rss_mib=1.359
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.002771 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.612220998 F/B=0.646045362 B/T=0.947643979 overrun=0.055249 cpu_s=0.211232 rss_mib=2.984
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.616972477 F/B=0.781976744 B/T=0.788990826 overrun=0.267442 cpu_s=0.922343 rss_mib=5.297
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.618012520 F/B=0.675406191 B/T=0.915023474 overrun=0.092868 cpu_s=0.895257 rss_mib=5.750
case=s31_060_large_live_set family=large_live_set F/T=0.632864398 F/B=0.641932619 B/T=0.985873563 overrun=0.014329 cpu_s=1.237171 rss_mib=7.438
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.002610 rss_mib=1.359
case=s31_086_tiny_churn family=tiny_churn F/T=0.635714286 F/B=0.959051724 B/T=0.662857143 overrun=0.508621 cpu_s=0.353338 rss_mib=2.672
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.002393 rss_mib=1.344
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.006516 rss_mib=1.422
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.026164 rss_mib=1.656
case=s31_040_distribution_switch family=distribution_switch F/T=0.660779817 F/B=0.692548077 B/T=0.954128440 overrun=0.048077 cpu_s=0.039810 rss_mib=1.641
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_086_tiny_churn family=tiny_churn F/T=0.635714286 F/B=0.959051724 B/T=0.662857143 overrun=0.508621 cpu_s=0.353338 rss_mib=2.672
case=s31_006_short_heavy family=short_heavy F/T=0.727118644 F/B=0.953333333 B/T=0.762711864 overrun=0.311111 cpu_s=0.861664 rss_mib=5.438
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.730769231 F/B=0.950000000 B/T=0.769230769 overrun=0.300000 cpu_s=0.855163 rss_mib=4.766
case=s31_009_long_heavy family=long_heavy F/T=0.750000000 F/B=0.953125000 B/T=0.786885246 overrun=0.270833 cpu_s=0.796872 rss_mib=5.531
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.616972477 F/B=0.781976744 B/T=0.788990826 overrun=0.267442 cpu_s=0.922343 rss_mib=5.297
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.005484 rss_mib=1.406
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.696875000 F/B=0.857692308 B/T=0.812500000 overrun=0.230769 cpu_s=0.006687 rss_mib=1.391
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.704723127 F/B=0.865400000 B/T=0.814332248 overrun=0.228000 cpu_s=0.208684 rss_mib=2.094
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.775431358 F/B=0.950045956 B/T=0.816204051 overrun=0.225184 cpu_s=0.400456 rss_mib=2.938
case=s31_001_uniform_churn family=uniform_churn F/T=0.795000000 F/B=0.963636364 B/T=0.825000000 overrun=0.212121 cpu_s=0.076319 rss_mib=1.766
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.004582 rss_mib=1.375
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.816304348 F/B=0.950170316 B/T=0.859113712 overrun=0.163990 cpu_s=0.357168 rss_mib=2.844
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.853853356 F/B=0.982097589 B/T=0.869418035 overrun=0.150195 cpu_s=0.276690 rss_mib=5.031
case=s31_030_size_lifetimes family=size_lifetimes F/T=0.860869565 F/B=0.990000000 B/T=0.869565217 overrun=0.150000 cpu_s=0.082364 rss_mib=1.781
case=s31_056_additive_cohorts family=additive_cohorts F/T=0.668820679 F/B=0.768089054 B/T=0.870759289 overrun=0.148423 cpu_s=0.043435 rss_mib=1.703
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.833773087 F/B=0.954682779 B/T=0.873350923 overrun=0.145015 cpu_s=0.106672 rss_mib=1.781

PAIRED SEARCH EVIDENCE
Against parent gen0: delta mean F/T=+0.000399880; improved/regressed/tied=47/34/71.
family=fifo delta_F/T=+0.038548117
family=size_biased_deletion delta_F/T=-0.012569120
family=hotset_switching delta_F/T=+0.010180533
family=tiny_churn delta_F/T=-0.009395801
family=geometric_cohorts delta_F/T=-0.008892442
family=distribution_switch delta_F/T=-0.008361769
Regressions:
s31_086_tiny_churn: delta_F/T=-0.082027650, delta_T=+400
s31_009_long_heavy: delta_F/T=-0.025423729, delta_T=+40
s31_102_serial_churn: delta_F/T=-0.023444776, delta_T=+100
s31_033_burst_drain: delta_F/T=-0.020441347, delta_T=+20
Gains:
s31_024_fifo: delta_F/T=+0.120579436, delta_T=-280
s31_087_tiny_churn: delta_F/T=+0.044444444, delta_T=-20
s31_021_fifo: delta_F/T=+0.038463134, delta_T=-1320
s31_094_hotset_switching: delta_F/T=+0.030254898, delta_T=-80

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.855381088; mean positive loss on worst 16 cases=0.020356465; max case loss=0.082027650; regressed cases=34; worst family delta F/T=-0.012569120. These are selection diagnostics; primary fitness remains mean F/T.

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
        unsigned sections = 0;
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
        }
        restore(inventory, undo.data(), undoCount);
        return sections;
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

Performance metrics:
Combined score to maximize: 0.86
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 1.13; max_solver_rss_mib: 5.58

Text feedback:
Fitness F/T=0.855540928492; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.737444128
family=short_phase_churn mean_F/T=0.780548782
family=drifting_sizes mean_F/T=0.781193094
family=short_rounding mean_F/T=0.798336172
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.806590790
family=distribution_switch mean_F/T=0.811515896
family=short_heavy mean_F/T=0.815275584
family=additive_cohorts mean_F/T=0.822291875
family=size_biased_deletion mean_F/T=0.826299358
family=uniform_churn mean_F/T=0.829008034
family=tiny_churn mean_F/T=0.836653564
family=long_heavy mean_F/T=0.840357242
family=micro_tail_reuse mean_F/T=0.845833333
family=long_prefill_random mean_F/T=0.848520142
family=size_lifetimes mean_F/T=0.853828113
family=serial_churn mean_F/T=0.865612136
family=hotset_switching mean_F/T=0.876102368
family=bimodal mean_F/T=0.879427340
family=large_live_set mean_F/T=0.880857425
family=recent_window_growth mean_F/T=0.880869772
family=micro_gap_refill mean_F/T=0.881250000
family=section_boundaries mean_F/T=0.883480797
family=burst_drain mean_F/T=0.891978839
family=fifo mean_F/T=0.892865298
family=soft_recency_growth mean_F/T=0.895659861
family=serial_growth mean_F/T=0.914311213
family=long_prefill_recent mean_F/T=0.917776721
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920982365
family=drain_recovery mean_F/T=0.925559380
family=hotset_growth mean_F/T=0.951430918
family=lifo mean_F/T=0.953245266
family=background_ephemeral mean_F/T=0.955199455
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001732 rss_mib=1.328
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001397 rss_mib=1.328
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001402 rss_mib=1.328
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001458 rss_mib=1.344
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001401 rss_mib=1.328
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001493 rss_mib=1.328
case=s31_118_partial_drain family=partial_drain F/T=0.610958339 F/B=0.646045362 B/T=0.945689537 overrun=0.057429 cpu_s=0.089095 rss_mib=1.984
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.612833644 F/B=0.675406191 B/T=0.907355680 overrun=0.102104 cpu_s=0.350453 rss_mib=3.078
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.356087 rss_mib=2.922
case=s31_060_large_live_set family=large_live_set F/T=0.632532089 F/B=0.641932619 B/T=0.985355893 overrun=0.014862 cpu_s=0.467481 rss_mib=3.688
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001360 rss_mib=1.328
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001426 rss_mib=1.328
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.003101 rss_mib=1.391
case=s31_040_distribution_switch family=distribution_switch F/T=0.651809955 F/B=0.692548077 B/T=0.941176471 overrun=0.062500 cpu_s=0.019178 rss_mib=1.422
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.013536 rss_mib=1.438
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.669014085 F/B=0.950000000 B/T=0.704225352 overrun=0.420000 cpu_s=0.372955 rss_mib=2.969
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.669014085 F/B=0.950000000 B/T=0.704225352 overrun=0.420000 cpu_s=0.372955 rss_mib=2.969
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.749293222 F/B=0.950045956 B/T=0.788691555 overrun=0.267923 cpu_s=0.146477 rss_mib=2.016
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.689012739 F/B=0.865400000 B/T=0.796178344 overrun=0.256000 cpu_s=0.081675 rss_mib=1.641
case=s31_009_long_heavy family=long_heavy F/T=0.762500000 F/B=0.953125000 B/T=0.800000000 overrun=0.250000 cpu_s=0.417348 rss_mib=3.000
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.002782 rss_mib=1.375
case=s31_001_uniform_churn family=uniform_churn F/T=0.775609756 F/B=0.963636364 B/T=0.804878049 overrun=0.242424 cpu_s=0.049798 rss_mib=1.500
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.631455399 F/B=0.781976744 B/T=0.807511737 overrun=0.238372 cpu_s=0.356087 rss_mib=2.922
case=s31_039_distribution_switch family=distribution_switch F/T=0.787333333 F/B=0.952419355 B/T=0.826666667 overrun=0.209677 cpu_s=0.683586 rss_mib=4.484
case=s31_031_size_lifetimes family=size_lifetimes F/T=0.829166667 F/B=0.995000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.128022 rss_mib=1.828
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001686 rss_mib=1.359
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.719354839 F/B=0.857692308 B/T=0.838709677 overrun=0.192308 cpu_s=0.002527 rss_mib=1.375
case=s31_017_section_boundaries family=section_boundaries F/T=0.817708333 F/B=0.957317073 B/T=0.854166667 overrun=0.170732 cpu_s=0.034644 rss_mib=1.500
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.576511 rss_mib=3.297
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.819043624 F/B=0.950170316 B/T=0.861996644 overrun=0.160097 cpu_s=0.138393 rss_mib=1.953
case=s31_086_tiny_churn family=tiny_churn F/T=0.830223881 F/B=0.959051724 B/T=0.865671642 overrun=0.155172 cpu_s=0.134515 rss_mib=1.844
case=s31_062_size_biased_deletion family=size_biased_deletion F/T=0.827225131 F/B=0.954682779 B/T=0.866492147 overrun=0.154079 cpu_s=0.041604 rss_mib=1.516

PAIRED SEARCH EVIDENCE
Against parent gen1: delta mean F/T=+0.000159840; improved/regressed/tied=45/46/61.
family=tiny_churn delta_F/T=+0.061045699
family=short_heavy delta_F/T=+0.031651043
family=distribution_switch delta_F/T=-0.025525704
family=fifo delta_F/T=+0.023307799
family=drifting_sizes delta_F/T=-0.021815622
family=short_rounding delta_F/T=-0.020543413
Regressions:
s31_122_short_rounding: delta_F/T=-0.081203008, delta_T=+40
s31_039_distribution_switch: delta_F/T=-0.081049020, delta_T=+140
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_041_drifting_sizes: delta_F/T=-0.061755146, delta_T=+120
Gains:
s31_086_tiny_churn: delta_F/T=+0.194509595, delta_T=-820
s31_006_short_heavy: delta_F/T=+0.114057827, delta_T=-160
s31_087_tiny_churn: delta_F/T=+0.049673203, delta_T=-20
s31_008_short_heavy: delta_F/T=+0.046536797, delta_T=-100

Against leader gen8: delta mean F/T=-0.000186316; improved/regressed/tied=45/44/63.
family=tiny_churn delta_F/T=+0.069384801
family=short_heavy delta_F/T=+0.037748042
family=distribution_switch delta_F/T=-0.025003458
family=fifo delta_F/T=+0.022246802
family=burst_drain delta_F/T=-0.021403685
family=short_rounding delta_F/T=-0.020543413
Regressions:
s31_122_short_rounding: delta_F/T=-0.081203008, delta_T=+40
s31_031_size_lifetimes: delta_F/T=-0.075378788, delta_T=+20
s31_039_distribution_switch: delta_F/T=-0.068463768, delta_T=+120
s31_033_burst_drain: delta_F/T=-0.064468864, delta_T=+60
Gains:
s31_086_tiny_churn: delta_F/T=+0.183421555, delta_T=-760
s31_087_tiny_churn: delta_F/T=+0.094117647, delta_T=-40
s31_006_short_heavy: delta_F/T=+0.088544892, delta_T=-120
s31_008_short_heavy: delta_F/T=+0.055128205, delta_T=-120

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.855540928; mean positive loss on worst 16 cases=0.040253104; max case loss=0.094009950; regressed cases=46; worst family delta F/T=-0.033887473. These are selection diagnostics; primary fitness remains mean F/T.


# Current program

Here is the current program we are trying to improve (you will need to propose a new program with the same inputs and outputs as the original program, but with improved internal implementation):

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
#include <cmath>
namespace {
using Coordinate = std::int64_t;
using GapKey = std::pair<Coordinate, Coordinate>;
using GapAgeKey =
    std::pair<Coordinate, std::pair<std::uint64_t, Coordinate>>;
constexpr bool kOldestGapTieBreak = true;
constexpr bool kCoalescingReleaseGeometry = true;
constexpr bool kAgeConditionalReleaseRisk = true;
constexpr bool kHarmonicFitInventory = true;
constexpr double kFitInventoryWeight = 0.35;
constexpr int kAgeBandCount = 4;
constexpr Coordinate kSectionLength = 20;
constexpr std::size_t kFastWindow = 128;
constexpr std::size_t kSlowWindow = 2048;
constexpr int kPotentialLimit = 160;
constexpr int kDistinctCandidateSizes = 10;
constexpr int kPhaseCount = 8;
// Exposure includes live survivors as well as completed lifetimes.
struct Rate {
    int live = 0;
    double exposure = 0.0;
    double deaths = 0.0;
    std::uint64_t stamp = 0;
    double exposureAt(std::uint64_t now) const {
        return exposure +
            static_cast<double>(now - stamp) * static_cast<double>(live);
    }
    void touch(std::uint64_t now) {
        exposure = exposureAt(now);
        stamp = now;
    }
    void change(std::uint64_t now, int delta, bool removed) {
        touch(now);
        live += delta;
        if (removed) deaths += 1.0;
    }
    void forget(std::uint64_t now) {
        touch(now);
        exposure *= 0.5;
        deaths *= 0.5;
    }
};
struct Pipe {
    Coordinate start = 0;
    std::uint64_t bornTick = 0;
    std::uint64_t ageUnit = 1;
    int length = 0;
    int previous = 0;
    int next = 0;
    unsigned char runPhase = 0;
    unsigned char group = 1;
    unsigned char ageBand = 0;
    bool active = false;
};
struct Gap {
    Coordinate end = 0;
    int left = 0;
    int right = 0;
    std::uint64_t freeSince = 0;
};
struct Choice {
    bool valid = false;
    Coordinate gapStart = 0;
    Coordinate start = 0;
    Coordinate span = 0;
    std::uint64_t freeSince = 0;
    double score = std::numeric_limits<double>::infinity();
};
class Allocator {
public:
    // Preserve the optional diagnostics interface used outside the block.
    std::size_t mcDecisionsUsed = 0;
    std::size_t mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0;
    std::uint64_t expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        beginCommand();
        const bool newlyObservedLength =
            fastFrequency_[static_cast<std::size_t>(length)] == 0;
        if (lastPlacementLength_ != length) {
            lastPlacementLength_ = length;
            runOrdinal_ = 0;
        }
        const int runPhase = static_cast<int>(runOrdinal_ & 7U);
        ++runOrdinal_;
        observeLength(length);
        refreshModel(newlyObservedLength);
        const int pid = static_cast<int>(pipes_.size());
        const int globalPhase = pid & 7;
        const double deletionProbability =
            predictDeletion(length, globalPhase, runPhase);
        const int group = classify(deletionProbability);
        peakLiveVolume_ = std::max(
            peakLiveVolume_, liveVolume_ + static_cast<Coordinate>(length));
        // An existing tail may support two fronts without extra excavation.
        if (!arenaActive_ && canSeparate(deletionProbability)) {
            const auto tail = tailGap();
            if (tail != gaps_.end() &&
                tail->second.end - tail->first >= 2LL * length) {
                arenaActive_ = true;
                arenaStart_ = tail->first;
                arenaEnd_ = trenchLength_;
            }
        }
        Choice choice;
        Coordinate digs = 0;
        const auto firstFit = bySize_.lower_bound({length, 0});
        if (firstFit != bySize_.end()) {
            rebuildFitInventory();
            selectCandidates(length, group, deletionProbability, choice);
        } else {
            // Growth is possible only after the global fitting-gap check.
            digs = growFor(length, deletionProbability, choice);
        }
        const auto selected = gaps_.find(choice.gapStart);
        const Coordinate gapStart = selected->first;
        const Gap gap = selected->second;
        eraseGap(selected);
        Pipe pipe;
        pipe.start = choice.start;
        pipe.length = length;
        pipe.previous = gap.left;
        pipe.next = gap.right;
        pipe.runPhase = static_cast<unsigned char>(runPhase);
        pipe.group = static_cast<unsigned char>(group);
        pipe.bornTick = tick_;
        pipe.ageUnit = std::max<std::uint64_t>(
            1, static_cast<std::uint64_t>(
                std::min(lifetimeHorizon_, static_cast<double>(tick_))));
        pipe.active = true;
        pipes_.push_back(pipe);
        ageRates_[static_cast<std::size_t>(group)][0].change(
            tick_, 1, false);
        ageEvents_.insert({nextAgeCheckpoint(pipe), pid});
        if (gap.left != 0) pipes_[gap.left].next = pid;
        if (gap.right != 0) {
            pipes_[gap.right].previous = pid;
        } else {
            tailPid_ = pid;
        }
        insertGap(
            gapStart, pipe.start, gap.left, pid, gap.freeSince);
        insertGap(
            pipe.start + length, gap.end, pid, gap.right, gap.freeSince);
        changePopulation(length, globalPhase, runPhase, 1, false);
        ++liveGroups_[static_cast<std::size_t>(group)];
        liveVolume_ += length;
        std::cout << digs << ' ' << pipe.start << '\n' << std::flush;
    }
    void remove(Coordinate pidValue) {
        if (pidValue <= 0 ||
            static_cast<std::uint64_t>(pidValue) >= pipes_.size()) {
            printInvalidPid();
            return;
        }
        const int pid = static_cast<int>(pidValue);
        if (!pipes_[static_cast<std::size_t>(pid)].active) {
            printInvalidPid();
            return;
        }
        beginCommand();
        const Pipe pipe = pipes_[static_cast<std::size_t>(pid)];
        ageRates_[static_cast<std::size_t>(pipe.group)]
                 [static_cast<std::size_t>(pipe.ageBand)].change(
            tick_, -1, true);
        if (static_cast<int>(pipe.ageBand) + 1 < kAgeBandCount) {
            ageEvents_.erase({nextAgeCheckpoint(pipe), pid});
        }
        if (pipe.previous != 0) {
            pipes_[pipe.previous].next = pipe.next;
        }
        if (pipe.next != 0) {
            pipes_[pipe.next].previous = pipe.previous;
        } else {
            tailPid_ = pipe.previous;
        }
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
        pipes_[static_cast<std::size_t>(pid)].active = false;
        insertGap(start, end, pipe.previous, pipe.next, tick_);
        changePopulation(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase), -1, true);
        --liveGroups_[static_cast<std::size_t>(pipe.group)];
        liveVolume_ -= pipe.length;
        if (totalRate_.live == 0) arenaActive_ = false;
        std::cout << pipe.start << '\n' << std::flush;
    }
private:
    using GapMap = std::map<Coordinate, Gap>;
    using GapIterator = GapMap::iterator;
    GapMap gaps_;
    std::set<GapKey> bySize_;
    std::set<GapAgeKey> byAge_;
    std::array<std::set<GapKey>, 3> byBoundaryGroup_;
    std::vector<Pipe> pipes_{Pipe{}};
    // Bucket 40 includes every gap whose length is at least 40.
    std::array<std::uint64_t, 41> gapSpanHistogram_{};
    std::array<double, 41> requestProbability_{};
    std::array<double, 41> fitInventoryPrefix_{};
    int tailPid_ = 0;
    Coordinate trenchLength_ = 0;
    Coordinate liveVolume_ = 0;
    Coordinate peakLiveVolume_ = 0;
    std::array<int, 3> liveGroups_{};
    std::uint64_t tick_ = 0;
    std::uint64_t modelTick_ = 0;
    bool haveModel_ = false;
    int lastPlacementLength_ = -1;
    std::uint64_t runOrdinal_ = 0;
    Rate totalRate_;
    std::array<Rate, 41> lengthRates_{};
    std::array<Rate, kPhaseCount> globalPhaseRates_{};
    std::array<Rate, kPhaseCount> runPhaseRates_{};
    std::array<std::array<Rate, kAgeBandCount>, 3> ageRates_{};
    std::array<std::array<double, kAgeBandCount>, 3> ageMultiplier_{};
    std::set<std::pair<std::uint64_t, int>> ageEvents_;
    double lifetimeHorizon_ = 1.0;
    std::array<double, 41> lengthRisk_{};
    std::array<double, kPhaseCount> globalPhaseRisk_{};
    std::array<double, kPhaseCount> runPhaseRisk_{};
    std::deque<int> recentLengths_;
    std::array<int, 41> fastFrequency_{};
    std::array<int, 41> slowFrequency_{};
    std::array<double, kPotentialLimit + 1> potential_{};
    bool arenaActive_ = false;
    Coordinate arenaStart_ = 0;
    Coordinate arenaEnd_ = 0;
    static double difference(double a, double b) {
        return a >= b ? a - b : b - a;
    }
    static int classify(double probability) {
        if (probability < 1.0 / 3.0) return 0;
        if (probability > 2.0 / 3.0) return 2;
        return 1;
    }
    static std::size_t fitBucket(Coordinate length) {
        return static_cast<std::size_t>(
            std::clamp<Coordinate>(length, 0, 40));
    }
    static std::uint64_t nextAgeCheckpoint(const Pipe& pipe) {
        return pipe.bornTick +
            pipe.ageUnit * (std::uint64_t{1} << pipe.ageBand);
    }
    void rebuildFitInventory() {
        std::array<double, 41> marginal{};
        std::uint64_t fitting = 0;
        for (int length = 40; length >= 1; --length) {
            const std::size_t index = static_cast<std::size_t>(length);
            fitting += gapSpanHistogram_[index];
            if (fitting != 0) {
                marginal[index] =
                    static_cast<double>(length) *
                    requestProbability_[index] /
                    static_cast<double>(fitting);
            }
        }
        fitInventoryPrefix_[0] = 0.0;
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index = static_cast<std::size_t>(length);
            fitInventoryPrefix_[index] =
                fitInventoryPrefix_[index - 1] + marginal[index];
        }
    }
    void beginCommand() {
        ++tick_;
        // One event per live pipe and at most three age transitions per pipe.
        while (!ageEvents_.empty() &&
               ageEvents_.begin()->first <= tick_) {
            const auto event = *ageEvents_.begin();
            ageEvents_.erase(ageEvents_.begin());
            Pipe& pipe = pipes_[static_cast<std::size_t>(event.second)];
            auto& rates = ageRates_[static_cast<std::size_t>(pipe.group)];
            rates[static_cast<std::size_t>(pipe.ageBand)].change(
                event.first, -1, false);
            ++pipe.ageBand;
            rates[static_cast<std::size_t>(pipe.ageBand)].change(
                event.first, 1, false);
            if (static_cast<int>(pipe.ageBand) + 1 < kAgeBandCount) {
                ageEvents_.insert({
                    nextAgeCheckpoint(pipe), event.second});
            }
        }
        if ((tick_ & 1023U) == 0) {
            totalRate_.forget(tick_);
            for (Rate& rate : lengthRates_) rate.forget(tick_);
            for (Rate& rate : globalPhaseRates_) rate.forget(tick_);
            for (Rate& rate : runPhaseRates_) rate.forget(tick_);
            for (auto& bands : ageRates_) {
                for (Rate& rate : bands) rate.forget(tick_);
            }
        }
    }
    void changePopulation(
        int length, int globalPhase, int runPhase,
        int delta, bool removed) {
        totalRate_.change(tick_, delta, removed);
        lengthRates_[static_cast<std::size_t>(length)].change(
            tick_, delta, removed);
        globalPhaseRates_[static_cast<std::size_t>(globalPhase)].change(
            tick_, delta, removed);
        runPhaseRates_[static_cast<std::size_t>(runPhase)].change(
            tick_, delta, removed);
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
    void rebuildPhaseRisk(
        const std::array<Rate, kPhaseCount>& observations,
        double globalRate,
        std::array<double, kPhaseCount>& result) {
        for (int residue = 0; residue < kPhaseCount; ++residue) {
            double rate = globalRate;
            for (int period = 2; period <= kPhaseCount; period *= 2) {
                double exposure = 0.0;
                double deaths = 0.0;
                for (int position = residue % period;
                     position < kPhaseCount; position += period) {
                    const Rate& observation =
                        observations[static_cast<std::size_t>(position)];
                    exposure += observation.exposureAt(tick_);
                    deaths += observation.deaths;
                }
                constexpr double priorDeaths = 8.0;
                rate = (deaths + priorDeaths) /
                    (exposure + priorDeaths / rate);
            }
            result[static_cast<std::size_t>(residue)] =
                std::clamp(rate / globalRate, 0.125, 8.0);
        }
    }
    void rebuildAgeRisk(double globalRate) {
        for (std::size_t group = 0; group < ageRates_.size(); ++group) {
            double exposure = 0.0;
            double deaths = 0.0;
            for (const Rate& observation : ageRates_[group]) {
                exposure += observation.exposureAt(tick_);
                deaths += observation.deaths;
            }
            const double pooledRate =
                (deaths + 4.0) / (exposure + 4.0 / globalRate);
            for (int band = 0; band < kAgeBandCount; ++band) {
                const std::size_t index = static_cast<std::size_t>(band);
                const Rate& observation = ageRates_[group][index];
                const double expectedDeaths =
                    observation.exposureAt(tick_) * pooledRate;
                constexpr double priorDeaths = 8.0;
                double multiplier = 1.0;
                if (observation.deaths >= priorDeaths ||
                    expectedDeaths >= priorDeaths) {
                    multiplier =
                        (observation.deaths + priorDeaths) /
                        (expectedDeaths + priorDeaths);
                }
                ageMultiplier_[group][index] = multiplier;
            }
        }
    }
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) return;
        modelTick_ = tick_;
        haveModel_ = true;
        const double globalRate =
            (totalRate_.deaths + 4.0) /
            (totalRate_.exposureAt(tick_) +
             4.0 * static_cast<double>(totalRate_.live + 1));
        lifetimeHorizon_ = 1.0 / globalRate;
        rebuildAgeRisk(globalRate);
        for (int length = 1; length <= 40; ++length) {
            const Rate& observation =
                lengthRates_[static_cast<std::size_t>(length)];
            constexpr double priorDeaths = 4.0;
            const double rate =
                (observation.deaths + priorDeaths) /
                (observation.exposureAt(tick_) +
                 priorDeaths / globalRate);
            lengthRisk_[static_cast<std::size_t>(length)] =
                std::clamp(rate / globalRate, 0.0625, 16.0);
        }
        rebuildPhaseRisk(
            globalPhaseRates_, globalRate, globalPhaseRisk_);
        rebuildPhaseRisk(
            runPhaseRates_, globalRate, runPhaseRisk_);
        std::array<double, 41> probability{};
        std::array<double, 41> prefix{};
        const double fastCount = static_cast<double>(
            std::min(kFastWindow, recentLengths_.size()));
        const double slowCount =
            static_cast<double>(recentLengths_.size());
        for (int length = 1; length <= 40; ++length) {
            const std::size_t index = static_cast<std::size_t>(length);
            probability[index] =
                0.98 * (
                    0.75 * fastFrequency_[index] / fastCount +
                    0.25 * slowFrequency_[index] / slowCount) +
                0.02 / 40.0;
            prefix[index] = prefix[index - 1] + probability[index];
        }
        prefix[40] = 1.0;
        requestProbability_ = probability;
        // Parent renewal potential, with up to four attempts per step.
        potential_[0] = 0.0;
        for (int capacity = 1;
             capacity <= kPotentialLimit; ++capacity) {
            const int maximum = std::min(capacity, 40);
            const double fit = prefix[static_cast<std::size_t>(maximum)];
            const double miss = std::max(0.0, 1.0 - fit);
            const double retryFactor =
                1.0 + miss + miss * miss + miss * miss * miss;
            double reward = 0.0;
            for (int length = 1; length <= maximum; ++length) {
                reward += probability[static_cast<std::size_t>(length)] *
                    (static_cast<double>(length) +
                     potential_[static_cast<std::size_t>(capacity - length)]);
            }
            potential_[static_cast<std::size_t>(capacity)] =
                std::clamp(
                    retryFactor * reward,
                    0.0, static_cast<double>(capacity));
        }
    }
    double predictDeletion(
        int length, int globalPhase, int runPhase) const {
        const double phaseMultiplier = 0.5 * (
            globalPhaseRisk_[static_cast<std::size_t>(globalPhase)] +
            runPhaseRisk_[static_cast<std::size_t>(runPhase)]);
        const double relativeRate = std::clamp(
            lengthRisk_[static_cast<std::size_t>(length)] *
                phaseMultiplier,
            1.0 / 32.0, 32.0);
        return relativeRate / (1.0 + relativeRate);
    }
    double predictDeletion(int pid) const {
        if (pid == 0) return 0.0;
        const Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        const double fallback = predictDeletion(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase));
        if (!kAgeConditionalReleaseRisk) return fallback;
        const auto& multipliers =
            ageMultiplier_[static_cast<std::size_t>(pipe.group)];
        double age = static_cast<double>(tick_ - pipe.bornTick);
        double remaining = lifetimeHorizon_;
        double weightedDuration = 0.0;
        bool adjusted = false;
        for (int band = static_cast<int>(pipe.ageBand);
             band < kAgeBandCount && remaining > 0.0; ++band) {
            double duration = remaining;
            if (band + 1 < kAgeBandCount) {
                const double boundary =
                    static_cast<double>(pipe.ageUnit) *
                    static_cast<double>(std::uint64_t{1} << band);
                duration = std::min(
                    remaining, std::max(0.0, boundary - age));
            }
            const double multiplier =
                multipliers[static_cast<std::size_t>(band)];
            weightedDuration += duration * multiplier;
            if (duration > 0.0 && multiplier != 1.0) adjusted = true;
            age += duration;
            remaining -= duration;
        }
        if (!adjusted) return fallback;
        const double logSurvival =
            std::log1p(-fallback) *
            (weightedDuration / lifetimeHorizon_);
        return std::clamp(-std::expm1(logSurvival), 0.0, 1.0);
    }
    double utility(Coordinate length) const {
        if (length <= 0) return 0.0;
        if (length <= kPotentialLimit) {
            return potential_[static_cast<std::size_t>(length)];
        }
        return potential_[kPotentialLimit] +
            static_cast<double>(length - kPotentialLimit);
    }
    bool canSeparate(double probability) const {
        return totalRate_.deaths >= 16.0 &&
            liveGroups_[0] >= 2 && liveGroups_[2] >= 2 &&
            (probability < 0.25 || probability > 0.75);
    }
    void considerGap(
        Coordinate gapStart, int length,
        double newDeletion, Choice& best) const {
        const auto found = gaps_.find(gapStart);
        if (found == gaps_.end()) return;
        const Gap& gap = found->second;
        const Coordinate span = gap.end - gapStart;
        if (span < length) return;
        if (gap.end == trenchLength_) {
            // Preserve the expandable tail whenever an interior gap fits.
            auto interior = bySize_.lower_bound({length, 0});
            if (interior != bySize_.end() &&
                interior->second == gapStart) {
                ++interior;
            }
            if (interior != bySize_.end()) return;
        }
        const Coordinate remainder = span - length;
        Coordinate leftLength = 0;
        if (gap.left != 0) {
            const Pipe& neighbor =
                pipes_[static_cast<std::size_t>(gap.left)];
            leftLength = neighbor.length;
            const auto next = gaps_.lower_bound(neighbor.start);
            if (next != gaps_.begin()) {
                const auto outside = std::prev(next);
                if (kCoalescingReleaseGeometry &&
                    outside->second.end == neighbor.start) {
                    leftLength += outside->second.end - outside->first;
                }
            }
        }
        Coordinate rightLength = 0;
        if (gap.right != 0) {
            const Pipe& neighbor =
                pipes_[static_cast<std::size_t>(gap.right)];
            rightLength = neighbor.length;
            const auto outside =
                gaps_.find(neighbor.start + neighbor.length);
            if (kCoalescingReleaseGeometry && outside != gaps_.end()) {
                rightLength += outside->second.end - outside->first;
            }
        }
        const double leftDeletion = predictDeletion(gap.left);
        const double rightDeletion = predictDeletion(gap.right);
        const double immediateCost = utility(span) - utility(remainder);
        double futureLow = 0.0;
        double futureHigh = 0.0;
        for (int releaseLeft = 0; releaseLeft < 2; ++releaseLeft) {
            const double leftWeight = releaseLeft
                ? leftDeletion : 1.0 - leftDeletion;
            const Coordinate leftFree =
                releaseLeft ? leftLength : 0;
            for (int releaseRight = 0; releaseRight < 2; ++releaseRight) {
                const double rightWeight = releaseRight
                    ? rightDeletion : 1.0 - rightDeletion;
                const double weight = leftWeight * rightWeight;
                if (weight == 0.0) continue;
                const Coordinate rightFree =
                    releaseRight ? rightLength : 0;
                const double whole =
                    utility(span + leftFree + rightFree);
                futureLow += weight * (
                    whole - utility(leftFree) -
                    utility(remainder + rightFree));
                futureHigh += weight * (
                    whole - utility(remainder + leftFree) -
                    utility(rightFree));
            }
        }
        // Removing this gap and keeping its remainder reduces N_s by one
        // exactly for remainder < s <= span. The harmonic marginal is 1/N_s.
        const double inventoryCost = kHarmonicFitInventory
            ? kFitInventoryWeight * (1.0 - newDeletion) *
                (fitInventoryPrefix_[fitBucket(span)] -
                 fitInventoryPrefix_[fitBucket(remainder)])
            : 0.0;
        const bool insideArena =
            arenaActive_ && gapStart >= arenaStart_ &&
            gap.end <= arenaEnd_;
        const double futureWeight = 0.5 * (1.0 - newDeletion);
        for (int side = 0; side < 2; ++side) {
            const bool high = side != 0;
            if (high && remainder == 0) continue;
            if (high && gap.end == trenchLength_ && !insideArena) {
                continue;
            }
            const double futureCost = high ? futureHigh : futureLow;
            double score =
                (1.0 - futureWeight) * immediateCost +
                futureWeight * futureCost +
                inventoryCost;
            if (remainder > 0) {
                const int neighbor = high ? gap.right : gap.left;
                if (neighbor != 0) {
                    const double neighborDeletion =
                        high ? rightDeletion : leftDeletion;
                    score += 0.10 * length *
                        difference(newDeletion, neighborDeletion);
                }
                if (insideArena) {
                    score += 0.125 * length *
                        (high ? newDeletion : 1.0 - newDeletion);
                }
            } else {
                if (gap.left != 0) {
                    score += 0.05 * length *
                        difference(newDeletion, leftDeletion);
                }
                if (gap.right != 0) {
                    score += 0.05 * length *
                        difference(newDeletion, rightDeletion);
                }
            }
            const Coordinate position =
                high ? gap.end - length : gapStart;
            const bool sameSpanTieBetter =
                (kOldestGapTieBreak && gap.freeSince != best.freeSince)
                    ? gap.freeSince < best.freeSince
                    : position < best.start;
            const bool better =
                !best.valid ||
                score < best.score - 1e-10 ||
                (score <= best.score + 1e-10 &&
                 (span < best.span ||
                  (span == best.span && sameSpanTieBetter)));
            if (better) {
                best.valid = true;
                best.gapStart = gapStart;
                best.start = position;
                best.span = span;
                best.freeSince = gap.freeSince;
                best.score = score;
            }
        }
    }
    void considerOldest(
        Coordinate span, int length,
        double deletionProbability, Choice& choice) const {
        if (span < length) return;
        auto oldest = byAge_.lower_bound({span, {0, 0}});
        if (oldest == byAge_.end() || oldest->first != span) return;
        const auto found = gaps_.find(oldest->second.second);
        if (found->second.end == trenchLength_) {
            const auto next = std::next(oldest);
            if (next != byAge_.end() && next->first == span) {
                oldest = next;
            }
        }
        considerGap(
            oldest->second.second, length, deletionProbability, choice);
    }
    void considerNear(
        const std::set<GapKey>& index, Coordinate minimumSpan,
        int length, double deletionProbability, Choice& choice) const {
        const auto first = index.lower_bound({minimumSpan, 0});
        if (first == index.end()) return;
        considerGap(first->second, length, deletionProbability, choice);
        const auto after = index.upper_bound({
            first->first, std::numeric_limits<Coordinate>::max()});
        const auto last = std::prev(after);
        if (last->second != first->second) {
            considerGap(last->second, length, deletionProbability, choice);
        }
        considerOldest(
            first->first, length, deletionProbability, choice);
    }
    void selectCandidates(
        int length, int group,
        double deletionProbability, Choice& choice) const {
        auto current = bySize_.lower_bound({length, 0});
        for (int count = 0;
             current != bySize_.end() &&
             count < kDistinctCandidateSizes; ++count) {
            const auto after = bySize_.upper_bound({
                current->first,
                std::numeric_limits<Coordinate>::max()});
            considerGap(
                current->second, length, deletionProbability, choice);
            const auto last = std::prev(after);
            if (last->second != current->second) {
                considerGap(
                    last->second, length, deletionProbability, choice);
            }
            considerOldest(
                current->first, length, deletionProbability, choice);
            current = after;
        }
        for (int offset : {40, 80, 160}) {
            considerNear(
                bySize_, static_cast<Coordinate>(length) + offset,
                length, deletionProbability, choice);
        }
        considerNear(
            byBoundaryGroup_[static_cast<std::size_t>(group)],
            length, length, deletionProbability, choice);
        if (!gaps_.empty()) {
            const auto last = std::prev(gaps_.end());
            if (last->second.end == trenchLength_) {
                considerGap(
                    last->first, length, deletionProbability, choice);
                considerOldest(
                    last->second.end - last->first,
                    length, deletionProbability, choice);
            }
        }
    }
    GapIterator tailGap() {
        if (gaps_.empty()) return gaps_.end();
        const auto last = std::prev(gaps_.end());
        return last->second.end == trenchLength_ ? last : gaps_.end();
    }
    Coordinate growFor(
        int length, double deletionProbability, Choice& choice) {
        Coordinate start = trenchLength_;
        int left = tailPid_;
        const auto tail = tailGap();
        if (tail != gaps_.end()) {
            start = tail->first;
            left = tail->second.left;
            eraseGap(tail);
        }
        const Coordinate available = trenchLength_ - start;
        const Coordinate deficit =
            std::max<Coordinate>(0, length - available);
        const Coordinate digs =
            (deficit + kSectionLength - 1) / kSectionLength;
        ++expansionGateOpportunities;
        // Excavate only the sections needed by the current insertion.
        const bool separate = canSeparate(deletionProbability);
        trenchLength_ += digs * kSectionLength;
        arenaActive_ =
            separate && trenchLength_ - start >= 2LL * length;
        if (arenaActive_) {
            arenaStart_ = start;
            arenaEnd_ = trenchLength_;
        }
        insertGap(start, trenchLength_, left, 0, tick_);
        rebuildFitInventory();
        considerGap(start, length, deletionProbability, choice);
        return digs;
    }
    void insertGap(
        Coordinate start, Coordinate end, int left, int right,
        std::uint64_t freeSince) {
        if (start >= end) return;
        gaps_.emplace(start, Gap{end, left, right, freeSince});
        const GapKey key{end - start, start};
        ++gapSpanHistogram_[fitBucket(key.first)];
        bySize_.insert(key);
        byAge_.insert({key.first, {freeSince, start}});
        const int leftGroup = left == 0
            ? -1 : static_cast<int>(pipes_[left].group);
        const int rightGroup = right == 0
            ? -1 : static_cast<int>(pipes_[right].group);
        if (leftGroup >= 0) {
            byBoundaryGroup_[static_cast<std::size_t>(leftGroup)].insert(key);
        }
        if (rightGroup >= 0 && rightGroup != leftGroup) {
            byBoundaryGroup_[static_cast<std::size_t>(rightGroup)].insert(key);
        }
    }
    void eraseGap(GapIterator position) {
        const Coordinate start = position->first;
        const Gap gap = position->second;
        const GapKey key{gap.end - start, start};
        --gapSpanHistogram_[fitBucket(key.first)];
        bySize_.erase(key);
        byAge_.erase({key.first, {gap.freeSince, start}});
        const int leftGroup = gap.left == 0
            ? -1 : static_cast<int>(pipes_[gap.left].group);
        const int rightGroup = gap.right == 0
            ? -1 : static_cast<int>(pipes_[gap.right].group);
        if (leftGroup >= 0) {
            byBoundaryGroup_[static_cast<std::size_t>(leftGroup)].erase(key);
        }
        if (rightGroup >= 0 && rightGroup != leftGroup) {
            byBoundaryGroup_[static_cast<std::size_t>(rightGroup)].erase(key);
        }
        gaps_.erase(position);
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
valid_cases: 152; family_count: 38; mean_raw_kpi: 0.86; worst_family_score: 0.53; mean_overrun: 0.05; mean_bound_to_trench: 0.95; max_solver_cpu_seconds: 1.84; max_solver_rss_mib: 15.02

Here is additional text feedback about the current program:

Fitness F/T=0.855727244402; stress excluded. B/T is diagnostic only.
family=micro_partial_drain mean_F/T=0.533333333
family=micro_short_churn mean_F/T=0.733333333
family=partial_drain mean_F/T=0.738053540
family=tiny_churn mean_F/T=0.767268763
family=short_heavy mean_F/T=0.777527542
family=short_phase_churn mean_F/T=0.778934512
family=drifting_sizes mean_F/T=0.799375640
family=micro_size_shift mean_F/T=0.802083333
family=geometric_cohorts mean_F/T=0.809980025
family=additive_cohorts mean_F/T=0.817814394
family=short_rounding mean_F/T=0.818879585
family=uniform_churn mean_F/T=0.822184278
family=size_biased_deletion mean_F/T=0.830996963
family=distribution_switch mean_F/T=0.836519354
family=micro_tail_reuse mean_F/T=0.845833333
family=long_heavy mean_F/T=0.846182399
family=long_prefill_random mean_F/T=0.847998357
family=fifo mean_F/T=0.870618495
family=size_lifetimes mean_F/T=0.873379271
family=serial_churn mean_F/T=0.875895783
family=large_live_set mean_F/T=0.880339892
family=micro_gap_refill mean_F/T=0.881250000
family=recent_window_growth mean_F/T=0.882120163
family=hotset_switching mean_F/T=0.886871596
family=section_boundaries mean_F/T=0.887578101
family=bimodal mean_F/T=0.888066964
family=soft_recency_growth mean_F/T=0.895649401
family=serial_growth mean_F/T=0.913018630
family=burst_drain mean_F/T=0.913382523
family=long_prefill_recent mean_F/T=0.917918786
family=micro_neighbor_coalescence mean_F/T=0.918750000
family=isolated_recent_churn mean_F/T=0.920458725
family=drain_recovery mean_F/T=0.925545107
family=hotset_growth mean_F/T=0.951937572
family=background_ephemeral mean_F/T=0.952560303
family=lifo mean_F/T=0.953245266
family=striped_recycling mean_F/T=0.960486952
family=tiny_growth mean_F/T=0.962263069
Worst F/T; F/B is an input-only ceiling, not an allocator loss.
case=s31_121_short_rounding family=short_rounding F/T=0.433333333 F/B=0.433333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001606 rss_mib=1.344
case=s31_150_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001914 rss_mib=1.344
case=s31_151_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.002586 rss_mib=1.344
case=s31_152_micro_partial_drain family=micro_partial_drain F/T=0.500000000 F/B=0.500000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001741 rss_mib=1.375
case=s31_139_micro_short_churn family=micro_short_churn F/T=0.550000000 F/B=0.550000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001559 rss_mib=1.344
case=s31_130_micro_gap_refill family=micro_gap_refill F/T=0.575000000 F/B=0.575000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001718 rss_mib=1.344
case=s31_118_partial_drain family=partial_drain F/T=0.610958339 F/B=0.646045362 B/T=0.945689537 overrun=0.057429 cpu_s=0.113182 rss_mib=2.938
case=s31_068_recent_window_growth family=recent_window_growth F/T=0.617529320 F/B=0.675406191 B/T=0.914308053 overrun=0.093723 cpu_s=0.531124 rss_mib=5.719
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.622685185 F/B=0.781976744 B/T=0.796296296 overrun=0.255814 cpu_s=0.547553 rss_mib=5.328
case=s31_060_large_live_set family=large_live_set F/T=0.631721245 F/B=0.641932619 B/T=0.984092763 overrun=0.016164 cpu_s=0.713567 rss_mib=7.562
case=s31_149_micro_partial_drain family=micro_partial_drain F/T=0.633333333 F/B=0.633333333 B/T=1.000000000 overrun=0.000000 cpu_s=0.001892 rss_mib=1.344
case=s31_086_tiny_churn family=tiny_churn F/T=0.646802326 F/B=0.959051724 B/T=0.674418605 overrun=0.482759 cpu_s=0.203040 rss_mib=2.641
case=s31_141_micro_size_shift family=micro_size_shift F/T=0.650000000 F/B=0.650000000 B/T=1.000000000 overrun=0.000000 cpu_s=0.001555 rss_mib=1.328
case=s31_072_soft_recency_growth family=soft_recency_growth F/T=0.650950570 F/B=0.650950570 B/T=1.000000000 overrun=0.000000 cpu_s=0.004218 rss_mib=1.438
case=s31_117_partial_drain family=partial_drain F/T=0.657471264 F/B=0.657471264 B/T=1.000000000 overrun=0.000000 cpu_s=0.015647 rss_mib=1.719
case=s31_008_short_heavy family=short_heavy F/T=0.661538462 F/B=0.758823529 B/T=0.871794872 overrun=0.147059 cpu_s=0.024602 rss_mib=1.641
Largest T/B-1 (diagnostic only); F/B is an input-only ceiling, not an allocator loss.
case=s31_086_tiny_churn family=tiny_churn F/T=0.646802326 F/B=0.959051724 B/T=0.674418605 overrun=0.482759 cpu_s=0.203040 rss_mib=2.641
case=s31_001_uniform_churn family=uniform_churn F/T=0.739534884 F/B=0.963636364 B/T=0.767441860 overrun=0.303030 cpu_s=0.078360 rss_mib=1.828
case=s31_041_drifting_sizes family=drifting_sizes F/T=0.730769231 F/B=0.950000000 B/T=0.769230769 overrun=0.300000 cpu_s=0.487079 rss_mib=5.406
case=s31_044_drifting_sizes family=drifting_sizes F/T=0.678213166 F/B=0.865400000 B/T=0.783699060 overrun=0.276000 cpu_s=0.124470 rss_mib=2.109
case=s31_006_short_heavy family=short_heavy F/T=0.752631579 F/B=0.953333333 B/T=0.789473684 overrun=0.266667 cpu_s=0.560985 rss_mib=5.453
case=s31_052_geometric_cohorts family=geometric_cohorts F/T=0.622685185 F/B=0.781976744 B/T=0.796296296 overrun=0.255814 cpu_s=0.547553 rss_mib=5.328
case=s31_088_tiny_churn family=tiny_churn F/T=0.670000000 F/B=0.837500000 B/T=0.800000000 overrun=0.250000 cpu_s=0.003450 rss_mib=1.422
case=s31_050_geometric_cohorts family=geometric_cohorts F/T=0.769371046 F/B=0.950045956 B/T=0.809825084 overrun=0.234835 cpu_s=0.221798 rss_mib=3.031
case=s31_126_short_phase_churn family=short_phase_churn F/T=0.696875000 F/B=0.857692308 B/T=0.812500000 overrun=0.230769 cpu_s=0.003008 rss_mib=1.406
case=s31_009_long_heavy family=long_heavy F/T=0.788793103 F/B=0.953125000 B/T=0.827586207 overrun=0.208333 cpu_s=0.501458 rss_mib=5.547
case=s31_125_short_phase_churn family=short_phase_churn F/T=0.766666667 F/B=0.920000000 B/T=0.833333333 overrun=0.200000 cpu_s=0.001815 rss_mib=1.406
case=s31_087_tiny_churn family=tiny_churn F/T=0.800000000 F/B=0.950000000 B/T=0.842105263 overrun=0.187500 cpu_s=0.709124 rss_mib=6.141
case=s31_007_short_heavy family=short_heavy F/T=0.826190476 F/B=0.963888889 B/T=0.857142857 overrun=0.166667 cpu_s=0.739087 rss_mib=6.250
case=s31_053_additive_cohorts family=additive_cohorts F/T=0.815963226 F/B=0.950170316 B/T=0.858754701 overrun=0.164477 cpu_s=0.215061 rss_mib=2.828
case=s31_063_size_biased_deletion family=size_biased_deletion F/T=0.841111111 F/B=0.970512821 B/T=0.866666667 overrun=0.153846 cpu_s=0.161577 rss_mib=2.594
case=s31_105_long_prefill_random family=long_prefill_random F/T=0.854591984 F/B=0.982097589 B/T=0.870170127 overrun=0.149201 cpu_s=0.321550 rss_mib=4.641

PAIRED SEARCH EVIDENCE
Against parent gen1: delta mean F/T=+0.000346156; improved/regressed/tied=42/38/72.
family=burst_drain delta_F/T=+0.016241598
family=uniform_churn delta_F/T=-0.013180390
family=serial_churn delta_F/T=+0.010013736
family=section_boundaries delta_F/T=-0.009341718
family=tiny_churn delta_F/T=-0.008339101
family=geometric_cohorts delta_F/T=+0.006943735
Regressions:
s31_001_uniform_churn: delta_F/T=-0.055465116, delta_T=+60
s31_087_tiny_churn: delta_F/T=-0.044444444, delta_T=+20
s31_007_short_heavy: delta_F/T=-0.041309524, delta_T=+20
s31_017_section_boundaries: delta_F/T=-0.037115839, delta_T=+40
Gains:
s31_033_burst_drain: delta_F/T=+0.064468864, delta_T=-60
s31_009_long_heavy: delta_F/T=+0.038793103, delta_T=-60
s31_055_additive_cohorts: delta_F/T=+0.031938250, delta_T=-40
s31_103_serial_churn: delta_F/T=+0.030833333, delta_T=-40

Against leader gen1: delta mean F/T=+0.000346156; improved/regressed/tied=42/38/72.
family=burst_drain delta_F/T=+0.016241598
family=uniform_churn delta_F/T=-0.013180390
family=serial_churn delta_F/T=+0.010013736
family=section_boundaries delta_F/T=-0.009341718
family=tiny_churn delta_F/T=-0.008339101
family=geometric_cohorts delta_F/T=+0.006943735
Regressions:
s31_001_uniform_churn: delta_F/T=-0.055465116, delta_T=+60
s31_087_tiny_churn: delta_F/T=-0.044444444, delta_T=+20
s31_007_short_heavy: delta_F/T=-0.041309524, delta_T=+20
s31_017_section_boundaries: delta_F/T=-0.037115839, delta_T=+40
Gains:
s31_033_burst_drain: delta_F/T=+0.064468864, delta_T=-60
s31_009_long_heavy: delta_F/T=+0.038793103, delta_T=-60
s31_055_additive_cohorts: delta_F/T=+0.031938250, delta_T=-40
s31_103_serial_churn: delta_F/T=+0.030833333, delta_T=-40

REGRESSIONS AGAINST FIXED BASELINE
Fixed gen0 baseline: mean F/T=0.855727244; mean positive loss on worst 16 cases=0.021691462; max case loss=0.070939610; regressed cases=32; worst family delta F/T=-0.017734902. These are selection diagnostics; primary fitness remains mean F/T.


# Task

Rewrite the program to improve its performance on the specified metrics.
Provide the complete new program code.

IMPORTANT: Make sure your rewritten program maintains the same inputs and outputs as the original program, but with improved internal implementation.
