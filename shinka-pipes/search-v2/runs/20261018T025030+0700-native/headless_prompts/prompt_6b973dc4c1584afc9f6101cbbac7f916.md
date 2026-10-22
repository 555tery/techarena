# System Instructions

Improve a causal online dynamic storage allocator in self-contained C++20.
Propose a patch in your response; do not edit files or launch experiments yourself.
Change only EVOLVE-BLOCK regions. Preserve stdin/stdout protocol and immediate flush.
Positive commands insert length 1..40; negative commands delete a PID; 0 exits.
Existing pipes cannot move. Trench grows in sections of 20 and never shrinks.
Use only past observations; no future input, raw test inspection, test fingerprints,
filesystem access, network, subprocesses, or external data in the candidate.
Do not inspect other project results or holdout data. Use supplied code and feedback.
Every case must satisfy 5 seconds solver CPU and 256 MiB RSS.
Fitness uses the frozen SEARCH-v2 corpus (128 streams, 16 families, 8 streams each) only. For each trace calculate
B/T, where B=20*ceil(peak_live_volume/20) and T is actual trench length.
Average over cases within each family, then give every family equal weight.
Fitness lies in [0,1]; B is a lower bound, not necessarily an achievable optimum.
Re-evaluate baseline fitness on this same corpus at the start of each run.
Validation and Open15 are excluded from fitness, selection and your feedback.
Do not inspect their files or results. Generalization is not established by search gains.
State the allocator hypothesis behind the change; avoid case-specific hardcoding.

LITERATURE-INFORMED ALGORITHM SEARCH — prepared 2026-10-18.
PATCH APPLICATION AND REPAIR. Copy SEARCH context exactly from the supplied original parent, including blank lines, indentation and comments. Prefer small unambiguous SEARCH anchors over rewritten surrounding context. If application fails, Shinka supplies the precise error plus the parent and previous response in conversation history. Return the complete corrected patch, retaining the same allocator hypothesis and intended change; do not replace it with an unrelated proposal. Each attempt is applied to the original parent again: include every needed SEARCH/REPLACE block, not just the first failing block. There are at most three attempts total (original plus two feedback corrections), all under one generation ID and one parent. Failed apply attempts are not evaluated or inserted as candidate Programs. After exhaustion the v2 runner stops and saves diagnostics before another generation is proposed; do not attempt to bypass this limit, inspect data or execute tools yourself.
The purpose of these papers is practical allocator improvement, not publication novelty.
Use one substantive mechanism per proposal; identify what is already present in the supplied parent. Parameter-only changes do not satisfy this research objective. State hypothesis H1/H2/H3/H4/H5/H6 (or explain a better causal mechanism), source motivation, expected failure mode, complexity and a minimal one-mechanism ablation. Shinka runs the evaluation; do not run tools/experiments yourself. These are untested engineering transfers, not promised improvements or transplanted theorems.

H1 — AGE-CONDITIONAL RELEASE RISK. LAVA, Ling/Worah/Wang et al., MLSys2025, sections3–4: update remaining-life predictions after survival, rather than retaining an initial point prediction. In Pipes, estimate deletion probability over horizon h conditional on current age a, q=1-S(a+h)/S(a), using past data only; live pipes are censored observations, not observed deaths. Coarse classes and at most three age-checkpoint events per pipe can bound total extra queue work to O(N log N), with O(N) memory and constant-size risk lookup. Do not scan all live pipes per command. Keep the old predictor with insufficient evidence. Change only neighbor-release risk; preserve gap utility, growth and side rules. The reviewed v1 gen2 already has deaths/exposure rates and DP utility: age-conditional risk is the proposed distinction, if missing in the actual parent.
Source: https://proceedings.mlsys.org/paper_files/paper/2025/file/9de62e421d58234dbf773abf43268630-Paper-Conference.pdf

H2 — GLOBAL ADDRESS-FIRST-FIT. Ernst/Stolyar/Wang, arXiv2404.03797v3 (Sep2026), theorem4.1: in a stationary Poisson/iid/exponential large-system model, address-first-fit asymptotically suppresses relative empty space. This is not a guarantee for finite Pipes traces or irrevocable peak trench length. Compare an exact leftmost-fitting free interval query to current gap scoring, preserving all other decisions. An address-ordered tree augmented by subtree maximum gap length gives O(log G) search/update (expected for treap), O(G) memory. A 64-gap prefix scan is an approximation, not exact First-Fit. Handle split/merge invariants carefully; inspect family regressions and CPU.
Source: https://arxiv.org/html/2404.03797v3

H3 — CORRECT WRONG REGION LIFETIME LABELS. Maas/Andersen/Isard/Javanmard/McKinley/Raffel, ASPLOS2020, LLAMA: nonmoving allocation can adjust region lifetime classes when predictions prove wrong. The paper uses call-context models and OS page reclamation, which are unavailable/different in Pipes. Modify labels and future reuse of already excavated regions only; never relocate live pipes or reserve extra trench for prediction. Keep a bounded region count and existing gap-index complexity. Compare the same grouping policy with and without correction; do not merely add an arena, grouping already exists in reviewed variants.
Source: https://www.cs.utexas.edu/~mckinley/papers/llama-asplos-2020.pdf

MODEL BOUNDARIES. LAVA scheduling does not establish a universal rule to group similar lifetimes: its main VM policy may mix shorter and longer VMs to avoid prolonging a host's lifetime. Wilson et al.1995 motivate preserving temporal structure and evaluating separate workload families, not assuming iid random traces. Futureproof Static Memory Planning/idealloc2025 is offline with all lifetimes known; do not copy boxing, future conflicts or future reordering into this online candidate. Buchsbaum et al.2004 OPT Versus LOAD explains a lower bound, not that B=20*ceil(peak_live_volume/20) is achievable by an online allocator. Scientific novelty and gains on hidden/platform tests are not established by this packet or SEARCH gains.

PRODUCTION ALLOCATOR TRANSFERS — prepared 2026-10-18. malloc is an interface: the implementation reviewed here is glibc malloc, not macOS malloc. Reviewed source commits: glibc 04e750e75b73957cf1c791535a3f4319534a52fc; jemalloc 7a34f18502e7b222724097cdcd499b437d189acc; mimalloc d4881d338125e1cb7c47ba4cfb398d6f7c0c8d45. These mechanisms do not require installing/linking any allocator library. Splitting, coalescing, size indices, cohort grouping and a two-front arena are already present in reviewed parent variants; adding their names is not a new mechanism.

H4 — PRESERVE THE EXPANDABLE TAIL. dlmalloc wilderness preservation and glibc _int_malloc/use_top motivate preferring existing interior gaps before the free tail ending at trenchLength. Keep the parent's scoring, side choice, growth and special cohort mode constraints unchanged. If any policy-eligible interior gap fits, score interior candidates only; otherwise use the tail, then ordinary growth. Check interior existence exactly with the size index: the tail is unique, so skip that one element after lower_bound if needed. Do not mistake absence from a bounded candidate sample for absence globally. Reviewed baseline ordinary scoring and gen2 include tail in the common competition; baseline already excludes tail in one narrow counterfactual mode. Skip H4 if equivalent behavior exists in the actual parent. O(log G) extra work, O(1) extra state. Failure: using a 30-unit interior gap for request20 can force later request30 to grow even when request20 could have fitted a 20-unit tail. Ablation changes only this interior-before-tail rule; no tail penalty sweep.
Sources: https://gee.cs.oswego.edu/dl/html/malloc.html ; https://github.com/bminor/glibc/blob/04e750e75b73957cf1c791535a3f4319534a52fc/malloc/malloc.c#L4310

H5 — FREE-GAP AGE AS A TIE-BREAK. dlmalloc/glibc ordinary-bin FIFO motivates leaving newly freed gaps time to coalesce. Among gaps of the same span and equal primary score, prefer the oldest free gap rather than address alone. This is free-gap age, not future lifetime. Track freeSince: current command when a connected gap is formed by deletion/merging; a split remainder inherits the previous value. Maintain a (span, freeSince, address) index, O(log G) updates and O(G) memory. Both ablation arms must see identical candidates, including the oldest gap of each considered size; only the tie-break differs. gen2 samples address endpoints and uses neighbor-sensitive score, so equal span alone is not sufficient to override its score. Do not attribute expanded candidate coverage to FIFO. Failure: an old gap can also be about to merge, or address ordering can be better. Keep coalescing immediate; do not copy tcache/deferred-free paths.
Sources: https://gee.cs.oswego.edu/dl/html/malloc.html ; https://github.com/bminor/glibc/blob/04e750e75b73957cf1c791535a3f4319534a52fc/malloc/malloc.c#L1482

H6 — REUSE A CURRENT EXACT-SIZE REGION, EXPLORATORY. jemalloc uses slabcur then nonfull slabs ordered by serial number/address; it does not select the densest slab. mimalloc checks the queue front, then a next-fit slow search with a candidate budget after the first candidate and a fuller-page preference. For Pipes, test soft region labels and current-region reuse for exact sizes1..40, then previously used regions, then the unchanged global selector. Never round occupied pipe lengths or excavate extra space for a new region. All free spans remain globally available; exact global fitting-gap fallback is mandatory before growth. Labels must not stop coalescing across region boundaries, and live pipes never move. A new label only covers space the ordinary placement already uses; existing growth behavior must be identical in both ablation arms. At most40 current regions plus a fixed bounded catalogue; declare geometry/catalogue/eviction before comparison, no parameter sweep and no per-command live-pipe scans. A catalogue scan bounded by a fixed constant plus O(log G) tree operations is acceptable; copying an unbounded page-queue scan is not. Distinction: existing baseline cohort slabs depend on runs/parity, gen2 arena on deletion groups; neither is this exact-size current-region reuse with shared fallback. The ablation changes only region preference with identical indices and growth. Do not add H1/H3/H4 in the same patch. Failure: equal size does not imply correlated deletions, and survivors can fragment a region. This hypothesis has lower priority than the simpler policies.
Sources: https://github.com/jemalloc/jemalloc/blob/7a34f18502e7b222724097cdcd499b437d189acc/src/bin.c#L289 ; https://github.com/microsoft/mimalloc/blob/d4881d338125e1cb7c47ba4cfb398d6f7c0c8d45/src/page.c#L944

TRANSFER LIMITS AND PRIORITY. Suggested consideration order is H4,H5,H2,H1,H3,H6, not an assigned schedule or budget. CPU speed alone does not improve B/T. Alignment, rounding, mmap/trim/purge, thread caches, remote frees and physical-page reclamation are not Pipes score improvements. Neither publication novelty nor hidden-test improvement is implied. jemalloc's extent ratio cap is conditional on its cache/coalescing policy; do not copy its default64 or tune a cutoff as a substitute for an algorithmic hypothesis. The user explicitly selected SEARCH-v1 generation 2 as this run's initial program; it is generation 0 here and must be re-evaluated on all SEARCH-v2 cases before evolution. Use its supplied code without inspecting the old run. Preserve its existing mechanisms unless your one-mechanism hypothesis explicitly changes one. Keep this selected seed, fixed128 SEARCH cases, family weights, resource limits, model and authorized 30-generation budget unchanged. Validation and Open15 remain excluded. Each candidate and its same-parent ablation must use the same full search suite under the eventual authorized budget; do not launch additional evaluations outside that budget.

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
namespace {
using Coordinate = std::int64_t;
using GapKey = std::pair<Coordinate, Coordinate>;
using GapAgeKey =
    std::pair<Coordinate, std::pair<std::uint64_t, Coordinate>>;
constexpr bool kPreferOldFreeGap = true;
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
    int length = 0;
    int previous = 0;
    int next = 0;
    unsigned char runPhase = 0;
    unsigned char group = 1;
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
        pipe.active = true;
        pipes_.push_back(pipe);
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
    void beginCommand() {
        ++tick_;
        if ((tick_ & 1023U) == 0) {
            totalRate_.forget(tick_);
            for (Rate& rate : lengthRates_) rate.forget(tick_);
            for (Rate& rate : globalPhaseRates_) rate.forget(tick_);
            for (Rate& rate : runPhaseRates_) rate.forget(tick_);
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
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) return;
        modelTick_ = tick_;
        haveModel_ = true;
        const double globalRate =
            (totalRate_.deaths + 4.0) /
            (totalRate_.exposureAt(tick_) +
             4.0 * static_cast<double>(totalRate_.live + 1));
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
        return predictDeletion(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase));
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
            // The tail is unique, so skipping it gives an exact check.
            auto interior = bySize_.lower_bound({length, 0});
            if (interior != bySize_.end() &&
                interior->second == gapStart) {
                ++interior;
            }
            if (interior != bySize_.end()) return;
        }
        const Coordinate remainder = span - length;
        const Coordinate leftLength = gap.left == 0
            ? 0 : pipes_[static_cast<std::size_t>(gap.left)].length;
        const Coordinate rightLength = gap.right == 0
            ? 0 : pipes_[static_cast<std::size_t>(gap.right)].length;
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
            const bool betterTie =
                span < best.span ||
                (span == best.span &&
                 ((kPreferOldFreeGap && gap.freeSince < best.freeSince) ||
                  ((!kPreferOldFreeGap ||
                    gap.freeSince == best.freeSince) &&
                   position < best.start)));
            const bool better =
                !best.valid ||
                score < best.score - 1e-10 ||
                (score <= best.score + 1e-10 && betterTie);
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
        auto oldest = byAge_.lower_bound({span, {0, 0}});
        if (oldest == byAge_.end() || oldest->first != span) return;
        // The unique tail loses eligibility when an interior gap fits.
        // If this size also has an interior gap, include its oldest one.
        if (oldest->second.second + span == trenchLength_) {
            const auto next = std::next(oldest);
            if (next != byAge_.end() && next->first == span) {
                oldest = next;
            }
        }
        // Keep candidate coverage identical in both ablation arms.
        considerGap(
            oldest->second.second, length, deletionProbability, choice);
    }
    void considerNear(
        const std::set<GapKey>& index, Coordinate minimumSpan,
        int length, double deletionProbability, Choice& choice) const {
        const auto first = index.lower_bound({minimumSpan, 0});
        if (first == index.end()) return;
        considerGap(first->second, length, deletionProbability, choice);
        considerOldest(first->first, length, deletionProbability, choice);
        const auto after = index.upper_bound({
            first->first, std::numeric_limits<Coordinate>::max()});
        const auto last = std::prev(after);
        if (last->second != first->second) {
            considerGap(last->second, length, deletionProbability, choice);
        }
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
        byAge_.insert({end - start, {freeSince, start}});
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
        byAge_.erase({gap.end - start, {gap.freeSince, start}});
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
Combined score to maximize: 0.96
valid_cases: 128; family_count: 16; worst_family_score: 0.91; mean_raw_kpi: 0.56; max_solver_cpu_seconds: 2.12; max_solver_rss_mib: 11.22

Text feedback:
case=s2_001_uniform_churn family=uniform_churn normalized=0.860465116 trench=860 bound=740 cpu_s=0.064732 rss_mib=1.625
case=s2_002_uniform_churn family=uniform_churn normalized=0.957820738 trench=11380 bound=10900 cpu_s=0.108584 rss_mib=1.812
case=s2_003_uniform_churn family=uniform_churn normalized=0.977909545 trench=172020 bound=168220 cpu_s=0.244323 rss_mib=2.938
case=s2_004_uniform_churn family=uniform_churn normalized=1.000000000 trench=1320 bound=1320 cpu_s=0.341090 rss_mib=2.578
case=s2_005_uniform_churn family=uniform_churn normalized=0.966252220 trench=33780 bound=32640 cpu_s=0.829041 rss_mib=3.344
case=s2_006_uniform_churn family=uniform_churn normalized=0.985395490 trench=342360 bound=337360 cpu_s=1.153085 rss_mib=4.203
case=s2_007_uniform_churn family=uniform_churn normalized=0.981651376 trench=4360 bound=4280 cpu_s=1.021165 rss_mib=5.031
case=s2_008_uniform_churn family=uniform_churn normalized=0.961684117 trench=89780 bound=86340 cpu_s=1.899433 rss_mib=6.156
case=s2_009_short_heavy family=short_heavy normalized=0.903846154 trench=1040 bound=940 cpu_s=0.131080 rss_mib=1.812
case=s2_010_short_heavy family=short_heavy normalized=0.993911720 trench=13140 bound=13060 cpu_s=0.237962 rss_mib=2.281
case=s2_011_short_heavy family=short_heavy normalized=0.981578529 trench=125940 bound=123620 cpu_s=0.407222 rss_mib=3.953
case=s2_012_short_heavy family=short_heavy normalized=0.777777778 trench=1260 bound=980 cpu_s=0.588414 rss_mib=3.828
case=s2_013_short_heavy family=short_heavy normalized=0.989743590 trench=39000 bound=38600 cpu_s=0.953773 rss_mib=3.188
case=s2_014_short_heavy family=short_heavy normalized=0.782608696 trench=460 bound=360 cpu_s=1.233629 rss_mib=5.109
case=s2_015_short_heavy family=short_heavy normalized=0.987179487 trench=3120 bound=3080 cpu_s=1.279857 rss_mib=6.500
case=s2_016_short_heavy family=short_heavy normalized=0.972431078 trench=7980 bound=7760 cpu_s=0.062484 rss_mib=1.750
case=s2_017_long_heavy family=long_heavy normalized=0.916376307 trench=5740 bound=5260 cpu_s=0.251009 rss_mib=2.188
case=s2_018_long_heavy family=long_heavy normalized=1.000000000 trench=120420 bound=120420 cpu_s=0.340149 rss_mib=2.969
case=s2_019_long_heavy family=long_heavy normalized=0.839285714 trench=1120 bound=940 cpu_s=0.549804 rss_mib=3.859
case=s2_020_long_heavy family=long_heavy normalized=0.959244533 trench=20120 bound=19300 cpu_s=0.817126 rss_mib=3.531
case=s2_021_long_heavy family=long_heavy normalized=1.000000000 trench=227240 bound=227240 cpu_s=0.984930 rss_mib=5.484
case=s2_022_long_heavy family=long_heavy normalized=0.897637795 trench=2540 bound=2280 cpu_s=1.704698 rss_mib=6.062
case=s2_023_long_heavy family=long_heavy normalized=0.982562278 trench=56200 bound=55220 cpu_s=0.074361 rss_mib=1.828
case=s2_024_long_heavy family=long_heavy normalized=0.996965756 trench=138420 bound=138000 cpu_s=0.162896 rss_mib=2.203
case=s2_025_bimodal family=bimodal normalized=0.951612903 trench=14880 bound=14160 cpu_s=0.519463 rss_mib=2.688
case=s2_026_bimodal family=bimodal normalized=0.963987266 trench=201040 bound=193800 cpu_s=0.789620 rss_mib=4.594
case=s2_027_bimodal family=bimodal normalized=0.955882353 trench=1360 bound=1300 cpu_s=0.712600 rss_mib=4.188
case=s2_028_bimodal family=bimodal normalized=0.951937984 trench=25800 bound=24560 cpu_s=1.341241 rss_mib=6.188
case=s2_029_bimodal family=bimodal normalized=1.000000000 trench=153500 bound=153500 cpu_s=1.360090 rss_mib=7.641
case=s2_030_bimodal family=bimodal normalized=0.936974790 trench=4760 bound=4460 cpu_s=0.066638 rss_mib=1.625
case=s2_031_bimodal family=bimodal normalized=0.977248104 trench=73840 bound=72160 cpu_s=0.110636 rss_mib=2.141
case=s2_032_bimodal family=bimodal normalized=1.000000000 trench=660 bound=660 cpu_s=0.213527 rss_mib=2.219
case=s2_033_section_boundaries family=section_boundaries normalized=0.955955335 trench=32240 bound=30820 cpu_s=0.594756 rss_mib=3.859
case=s2_034_section_boundaries family=section_boundaries normalized=0.990785256 trench=399360 bound=395680 cpu_s=0.931600 rss_mib=4.484
case=s2_035_section_boundaries family=section_boundaries normalized=0.985576923 trench=4160 bound=4100 cpu_s=1.028883 rss_mib=6.188
case=s2_036_section_boundaries family=section_boundaries normalized=0.945172506 trench=74780 bound=70680 cpu_s=1.887242 rss_mib=6.984
case=s2_037_section_boundaries family=section_boundaries normalized=0.833333333 trench=960 bound=800 cpu_s=0.055761 rss_mib=1.609
case=s2_038_section_boundaries family=section_boundaries normalized=0.988258317 trench=10220 bound=10100 cpu_s=0.108716 rss_mib=1.812
case=s2_039_section_boundaries family=section_boundaries normalized=0.992158031 trench=201480 bound=199900 cpu_s=0.258551 rss_mib=2.766
case=s2_040_section_boundaries family=section_boundaries normalized=1.000000000 trench=1260 bound=1260 cpu_s=0.343923 rss_mib=2.750
case=s2_041_fifo family=fifo normalized=0.999520384 trench=83400 bound=83360 cpu_s=0.936640 rss_mib=3.531
case=s2_042_fifo family=fifo normalized=0.875000000 trench=960 bound=840 cpu_s=1.239774 rss_mib=5.531
case=s2_043_fifo family=fifo normalized=0.996078431 trench=10200 bound=10160 cpu_s=1.353096 rss_mib=6.125
case=s2_044_fifo family=fifo normalized=0.977040816 trench=7840 bound=7660 cpu_s=0.066118 rss_mib=1.734
case=s2_045_fifo family=fifo normalized=0.904347826 trench=2300 bound=2080 cpu_s=0.133803 rss_mib=1.812
case=s2_046_fifo family=fifo normalized=1.000000000 trench=31320 bound=31320 cpu_s=0.214742 rss_mib=2.172
case=s2_047_fifo family=fifo normalized=0.990685732 trench=397240 bound=393540 cpu_s=0.425322 rss_mib=3.797
case=s2_048_fifo family=fifo normalized=0.939597315 trench=5960 bound=5600 cpu_s=0.717429 rss_mib=3.844
case=s2_049_lifo family=lifo normalized=1.000000000 trench=169280 bound=169280 cpu_s=1.025939 rss_mib=5.281
case=s2_050_lifo family=lifo normalized=1.000000000 trench=1840 bound=1840 cpu_s=1.469803 rss_mib=6.031
case=s2_051_lifo family=lifo normalized=1.000000000 trench=30920 bound=30920 cpu_s=0.051618 rss_mib=1.719
case=s2_052_lifo family=lifo normalized=1.000000000 trench=14540 bound=14540 cpu_s=0.118909 rss_mib=2.016
case=s2_053_lifo family=lifo normalized=1.000000000 trench=5700 bound=5700 cpu_s=0.267524 rss_mib=2.156
case=s2_054_lifo family=lifo normalized=1.000000000 trench=83540 bound=83540 cpu_s=0.427276 rss_mib=2.766
case=s2_055_lifo family=lifo normalized=1.000000000 trench=800 bound=800 cpu_s=0.601885 rss_mib=3.875
case=s2_056_lifo family=lifo normalized=1.000000000 trench=12920 bound=12920 cpu_s=0.883138 rss_mib=3.469
case=s2_057_size_lifetimes family=size_lifetimes normalized=0.976020739 trench=61720 bound=60240 cpu_s=1.892793 rss_mib=6.375
case=s2_058_size_lifetimes family=size_lifetimes normalized=0.909090909 trench=880 bound=800 cpu_s=0.061472 rss_mib=1.625
case=s2_059_size_lifetimes family=size_lifetimes normalized=0.970249520 trench=41680 bound=40440 cpu_s=0.148997 rss_mib=2.125
case=s2_060_size_lifetimes family=size_lifetimes normalized=0.857142857 trench=280 bound=240 cpu_s=0.241298 rss_mib=2.188
case=s2_061_size_lifetimes family=size_lifetimes normalized=0.919354839 trench=3720 bound=3420 cpu_s=0.369854 rss_mib=2.766
case=s2_062_size_lifetimes family=size_lifetimes normalized=0.972534697 trench=136900 bound=133140 cpu_s=0.654276 rss_mib=4.188
case=s2_063_size_lifetimes family=size_lifetimes normalized=0.962616822 trench=4280 bound=4120 cpu_s=1.084501 rss_mib=2.812
case=s2_064_size_lifetimes family=size_lifetimes normalized=0.926470588 trench=4080 bound=3780 cpu_s=1.933211 rss_mib=4.031
case=s2_065_burst_drain family=burst_drain normalized=0.894736842 trench=760 bound=680 cpu_s=0.095637 rss_mib=1.469
case=s2_066_burst_drain family=burst_drain normalized=0.982274742 trench=13540 bound=13300 cpu_s=0.238508 rss_mib=1.438
case=s2_067_burst_drain family=burst_drain normalized=0.998686975 trench=152320 bound=152120 cpu_s=0.539811 rss_mib=2.219
case=s2_068_burst_drain family=burst_drain normalized=1.000000000 trench=440 bound=440 cpu_s=0.515194 rss_mib=1.938
case=s2_069_burst_drain family=burst_drain normalized=0.986484795 trench=159820 bound=157660 cpu_s=1.187693 rss_mib=2.984
case=s2_070_burst_drain family=burst_drain normalized=0.999945394 trench=732520 bound=732480 cpu_s=1.368195 rss_mib=6.266
case=s2_071_burst_drain family=burst_drain normalized=0.995918367 trench=4900 bound=4880 cpu_s=1.272499 rss_mib=4.812
case=s2_072_burst_drain family=burst_drain normalized=1.000000000 trench=168720 bound=168720 cpu_s=1.894407 rss_mib=5.172
case=s2_073_distribution_switch family=distribution_switch normalized=0.992366412 trench=2620 bound=2600 cpu_s=0.130982 rss_mib=1.812
case=s2_074_distribution_switch family=distribution_switch normalized=0.998792271 trench=33120 bound=33080 cpu_s=0.320152 rss_mib=1.891
case=s2_075_distribution_switch family=distribution_switch normalized=1.000000000 trench=255620 bound=255620 cpu_s=0.695230 rss_mib=3.031
case=s2_076_distribution_switch family=distribution_switch normalized=0.990769231 trench=6500 bound=6440 cpu_s=0.735148 rss_mib=3.156
case=s2_077_distribution_switch family=distribution_switch normalized=0.948666475 trench=69740 bound=66160 cpu_s=0.935835 rss_mib=3.453
case=s2_078_distribution_switch family=distribution_switch normalized=0.902777778 trench=1440 bound=1300 cpu_s=1.346298 rss_mib=5.156
case=s2_079_distribution_switch family=distribution_switch normalized=1.000000000 trench=8420 bound=8420 cpu_s=1.589891 rss_mib=5.203
case=s2_080_distribution_switch family=distribution_switch normalized=0.875689592 trench=54380 bound=47620 cpu_s=0.077499 rss_mib=1.875
case=s2_081_drifting_sizes family=drifting_sizes normalized=0.850847458 trench=5900 bound=5020 cpu_s=0.309479 rss_mib=2.156
case=s2_082_drifting_sizes family=drifting_sizes normalized=1.000000000 trench=106700 bound=106700 cpu_s=0.412244 rss_mib=2.672
case=s2_083_drifting_sizes family=drifting_sizes normalized=0.790322581 trench=1240 bound=980 cpu_s=0.741434 rss_mib=3.391
case=s2_084_drifting_sizes family=drifting_sizes normalized=0.905908096 trench=18280 bound=16560 cpu_s=1.348521 rss_mib=3.234
case=s2_085_drifting_sizes family=drifting_sizes normalized=0.996851919 trench=165180 bound=164660 cpu_s=1.532344 rss_mib=4.250
case=s2_086_drifting_sizes family=drifting_sizes normalized=0.810126582 trench=3160 bound=2560 cpu_s=1.923744 rss_mib=4.984
case=s2_087_drifting_sizes family=drifting_sizes normalized=0.928118393 trench=37840 bound=35120 cpu_s=0.083468 rss_mib=1.844
case=s2_088_drifting_sizes family=drifting_sizes normalized=0.968415008 trench=104480 bound=101180 cpu_s=0.200853 rss_mib=2.000
case=s2_089_striped_recycling family=striped_recycling normalized=0.999201278 trench=150240 bound=150120 cpu_s=0.449343 rss_mib=3.359
case=s2_090_striped_recycling family=striped_recycling normalized=1.000000000 trench=775400 bound=775400 cpu_s=0.589348 rss_mib=4.641
case=s2_091_striped_recycling family=striped_recycling normalized=0.998651559 trench=1067900 bound=1066460 cpu_s=0.919011 rss_mib=6.266
case=s2_092_striped_recycling family=striped_recycling normalized=1.000000000 trench=2034140 bound=2034140 cpu_s=1.100593 rss_mib=5.797
case=s2_093_striped_recycling family=striped_recycling normalized=1.000000000 trench=2845400 bound=2845400 cpu_s=1.431199 rss_mib=11.219
case=s2_094_striped_recycling family=striped_recycling normalized=0.999743063 trench=77840 bound=77820 cpu_s=0.056662 rss_mib=1.766
case=s2_095_striped_recycling family=striped_recycling normalized=1.000000000 trench=236280 bound=236280 cpu_s=0.111247 rss_mib=2.234
case=s2_096_striped_recycling family=striped_recycling normalized=0.999958866 trench=486220 bound=486200 cpu_s=0.201530 rss_mib=2.844
case=s2_097_geometric_cohorts family=geometric_cohorts normalized=0.982718894 trench=17360 bound=17060 cpu_s=0.642812 rss_mib=3.875
case=s2_098_geometric_cohorts family=geometric_cohorts normalized=0.990464708 trench=182480 bound=180740 cpu_s=0.917105 rss_mib=3.750
case=s2_099_geometric_cohorts family=geometric_cohorts normalized=0.738805970 trench=2680 bound=1980 cpu_s=0.940196 rss_mib=5.547
case=s2_100_geometric_cohorts family=geometric_cohorts normalized=0.956828885 trench=50960 bound=48760 cpu_s=1.621305 rss_mib=5.156
case=s2_101_geometric_cohorts family=geometric_cohorts normalized=0.909090909 trench=880 bound=800 cpu_s=0.049742 rss_mib=1.625
case=s2_102_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=10780 bound=10780 cpu_s=0.106196 rss_mib=1.828
case=s2_103_geometric_cohorts family=geometric_cohorts normalized=0.913490725 trench=118600 bound=108340 cpu_s=0.248086 rss_mib=3.062
case=s2_104_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=320 bound=320 cpu_s=0.302427 rss_mib=2.750
case=s2_105_additive_cohorts family=additive_cohorts normalized=0.975058275 trench=85800 bound=83660 cpu_s=0.905101 rss_mib=3.625
case=s2_106_additive_cohorts family=additive_cohorts normalized=0.890909091 trench=1100 bound=980 cpu_s=1.303980 rss_mib=5.234
case=s2_107_additive_cohorts family=additive_cohorts normalized=0.994729908 trench=15180 bound=15100 cpu_s=1.454470 rss_mib=5.609
case=s2_108_additive_cohorts family=additive_cohorts normalized=0.988819467 trench=60820 bound=60140 cpu_s=0.080800 rss_mib=1.906
case=s2_109_additive_cohorts family=additive_cohorts normalized=0.849673203 trench=3060 bound=2600 cpu_s=0.126326 rss_mib=1.797
case=s2_110_additive_cohorts family=additive_cohorts normalized=1.000000000 trench=27240 bound=27240 cpu_s=0.235683 rss_mib=2.297
case=s2_111_additive_cohorts family=additive_cohorts normalized=0.899090909 trench=506000 bound=454940 cpu_s=0.484400 rss_mib=5.078
case=s2_112_additive_cohorts family=additive_cohorts normalized=0.939172749 trench=8220 bound=7720 cpu_s=0.615994 rss_mib=3.719
case=s2_113_large_live_set family=large_live_set normalized=0.958147818 trench=44920 bound=43040 cpu_s=0.819328 rss_mib=2.766
case=s2_114_large_live_set family=large_live_set normalized=0.968430615 trench=88060 bound=85280 cpu_s=0.983524 rss_mib=3.406
case=s2_115_large_live_set family=large_live_set normalized=0.981914526 trench=173620 bound=170480 cpu_s=1.228470 rss_mib=3.672
case=s2_116_large_live_set family=large_live_set normalized=0.981298824 trench=253460 bound=248720 cpu_s=1.318741 rss_mib=5.859
case=s2_117_large_live_set family=large_live_set normalized=0.983687737 trench=343300 bound=337700 cpu_s=1.530877 rss_mib=6.547
case=s2_118_large_live_set family=large_live_set normalized=0.986515599 trench=501320 bound=494560 cpu_s=1.896412 rss_mib=5.938
case=s2_119_large_live_set family=large_live_set normalized=0.987764085 trench=681600 bound=673260 cpu_s=2.007139 rss_mib=5.906
case=s2_120_large_live_set family=large_live_set normalized=0.988004875 trench=935380 bound=924160 cpu_s=2.122084 rss_mib=5.188
case=s2_121_size_biased_deletion family=size_biased_deletion normalized=0.999761763 trench=335800 bound=335720 cpu_s=1.541147 rss_mib=5.984
case=s2_122_size_biased_deletion family=size_biased_deletion normalized=0.891598916 trench=7380 bound=6580 cpu_s=0.063257 rss_mib=1.625
case=s2_123_size_biased_deletion family=size_biased_deletion normalized=0.962652784 trench=88360 bound=85060 cpu_s=0.136781 rss_mib=2.266
case=s2_124_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=100 bound=100 cpu_s=0.198624 rss_mib=2.172
case=s2_125_size_biased_deletion family=size_biased_deletion normalized=0.819782062 trench=23860 bound=19560 cpu_s=0.425359 rss_mib=2.812
case=s2_126_size_biased_deletion family=size_biased_deletion normalized=0.893533893 trench=204760 bound=182960 cpu_s=0.791695 rss_mib=4.625
case=s2_127_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=1440 bound=1440 cpu_s=0.699636 rss_mib=4.203
case=s2_128_size_biased_deletion family=size_biased_deletion normalized=0.897952333 trench=59580 bound=53500 cpu_s=1.148821 rss_mib=5.812

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
namespace {
using Coordinate = std::int64_t;
using GapKey = std::pair<Coordinate, Coordinate>;
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
    int length = 0;
    int previous = 0;
    int next = 0;
    unsigned char runPhase = 0;
    unsigned char group = 1;
    bool active = false;
};
struct Gap {
    Coordinate end = 0;
    int left = 0;
    int right = 0;
};
struct Choice {
    bool valid = false;
    Coordinate gapStart = 0;
    Coordinate start = 0;
    Coordinate span = 0;
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
        pipe.active = true;
        pipes_.push_back(pipe);
        if (gap.left != 0) pipes_[gap.left].next = pid;
        if (gap.right != 0) {
            pipes_[gap.right].previous = pid;
        } else {
            tailPid_ = pid;
        }
        insertGap(gapStart, pipe.start, gap.left, pid);
        insertGap(pipe.start + length, gap.end, pid, gap.right);
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
        insertGap(start, end, pipe.previous, pipe.next);
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
    void beginCommand() {
        ++tick_;
        if ((tick_ & 1023U) == 0) {
            totalRate_.forget(tick_);
            for (Rate& rate : lengthRates_) rate.forget(tick_);
            for (Rate& rate : globalPhaseRates_) rate.forget(tick_);
            for (Rate& rate : runPhaseRates_) rate.forget(tick_);
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
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) return;
        modelTick_ = tick_;
        haveModel_ = true;
        const double globalRate =
            (totalRate_.deaths + 4.0) /
            (totalRate_.exposureAt(tick_) +
             4.0 * static_cast<double>(totalRate_.live + 1));
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
        return predictDeletion(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase));
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
            // The tail is unique, so skipping it gives an exact check.
            auto interior = bySize_.lower_bound({length, 0});
            if (interior != bySize_.end() &&
                interior->second == gapStart) {
                ++interior;
            }
            if (interior != bySize_.end()) return;
        }
        const Coordinate remainder = span - length;
        const Coordinate leftLength = gap.left == 0
            ? 0 : pipes_[static_cast<std::size_t>(gap.left)].length;
        const Coordinate rightLength = gap.right == 0
            ? 0 : pipes_[static_cast<std::size_t>(gap.right)].length;
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
            const bool better =
                !best.valid ||
                score < best.score - 1e-10 ||
                (score <= best.score + 1e-10 &&
                 (span < best.span ||
                  (span == best.span && position < best.start)));
            if (better) {
                best.valid = true;
                best.gapStart = gapStart;
                best.start = position;
                best.span = span;
                best.score = score;
            }
        }
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
        insertGap(start, trenchLength_, left, 0);
        considerGap(start, length, deletionProbability, choice);
        return digs;
    }
    void insertGap(
        Coordinate start, Coordinate end, int left, int right) {
        if (start >= end) return;
        gaps_.emplace(start, Gap{end, left, right});
        const GapKey key{end - start, start};
        bySize_.insert(key);
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
Combined score to maximize: 0.96
valid_cases: 128; family_count: 16; worst_family_score: 0.91; mean_raw_kpi: 0.56; max_solver_cpu_seconds: 1.43; max_solver_rss_mib: 11.05

Text feedback:
case=s2_001_uniform_churn family=uniform_churn normalized=0.860465116 trench=860 bound=740 cpu_s=0.044739 rss_mib=1.609
case=s2_002_uniform_churn family=uniform_churn normalized=0.961199295 trench=11340 bound=10900 cpu_s=0.092049 rss_mib=1.781
case=s2_003_uniform_churn family=uniform_churn normalized=0.977454968 trench=172100 bound=168220 cpu_s=0.193096 rss_mib=2.844
case=s2_004_uniform_churn family=uniform_churn normalized=1.000000000 trench=1320 bound=1320 cpu_s=0.250637 rss_mib=2.625
case=s2_005_uniform_churn family=uniform_churn normalized=0.964539007 trench=33840 bound=32640 cpu_s=0.506825 rss_mib=3.938
case=s2_006_uniform_churn family=uniform_churn normalized=0.984532773 trench=342660 bound=337360 cpu_s=0.715088 rss_mib=4.250
case=s2_007_uniform_churn family=uniform_churn normalized=0.981651376 trench=4360 bound=4280 cpu_s=0.737792 rss_mib=5.031
case=s2_008_uniform_churn family=uniform_churn normalized=0.964046449 trench=89560 bound=86340 cpu_s=1.272566 rss_mib=6.250
case=s2_009_short_heavy family=short_heavy normalized=0.870370370 trench=1080 bound=940 cpu_s=0.087234 rss_mib=1.797
case=s2_010_short_heavy family=short_heavy normalized=0.993911720 trench=13140 bound=13060 cpu_s=0.158016 rss_mib=2.234
case=s2_011_short_heavy family=short_heavy normalized=0.981578529 trench=125940 bound=123620 cpu_s=0.296114 rss_mib=3.797
case=s2_012_short_heavy family=short_heavy normalized=0.790322581 trench=1240 bound=980 cpu_s=0.435060 rss_mib=3.750
case=s2_013_short_heavy family=short_heavy normalized=0.989743590 trench=39000 bound=38600 cpu_s=0.686322 rss_mib=2.703
case=s2_014_short_heavy family=short_heavy normalized=0.857142857 trench=420 bound=360 cpu_s=0.803004 rss_mib=4.734
case=s2_015_short_heavy family=short_heavy normalized=0.987179487 trench=3120 bound=3080 cpu_s=1.045240 rss_mib=4.406
case=s2_016_short_heavy family=short_heavy normalized=0.974874372 trench=7960 bound=7760 cpu_s=0.047821 rss_mib=1.734
case=s2_017_long_heavy family=long_heavy normalized=0.919580420 trench=5720 bound=5260 cpu_s=0.183255 rss_mib=2.156
case=s2_018_long_heavy family=long_heavy normalized=1.000000000 trench=120420 bound=120420 cpu_s=0.257672 rss_mib=2.875
case=s2_019_long_heavy family=long_heavy normalized=0.854545455 trench=1100 bound=940 cpu_s=0.410386 rss_mib=3.828
case=s2_020_long_heavy family=long_heavy normalized=0.959244533 trench=20120 bound=19300 cpu_s=0.639723 rss_mib=4.156
case=s2_021_long_heavy family=long_heavy normalized=1.000000000 trench=227240 bound=227240 cpu_s=0.812632 rss_mib=5.281
case=s2_022_long_heavy family=long_heavy normalized=0.890625000 trench=2560 bound=2280 cpu_s=1.153371 rss_mib=5.109
case=s2_023_long_heavy family=long_heavy normalized=0.979078014 trench=56400 bound=55220 cpu_s=0.054455 rss_mib=1.797
case=s2_024_long_heavy family=long_heavy normalized=0.996389892 trench=138500 bound=138000 cpu_s=0.099186 rss_mib=2.125
case=s2_025_bimodal family=bimodal normalized=0.950335570 trench=14900 bound=14160 cpu_s=0.316178 rss_mib=2.188
case=s2_026_bimodal family=bimodal normalized=0.966390745 trench=200540 bound=193800 cpu_s=0.527009 rss_mib=4.359
case=s2_027_bimodal family=bimodal normalized=0.955882353 trench=1360 bound=1300 cpu_s=0.532730 rss_mib=4.172
case=s2_028_bimodal family=bimodal normalized=0.951937984 trench=25800 bound=24560 cpu_s=0.896986 rss_mib=6.016
case=s2_029_bimodal family=bimodal normalized=1.000000000 trench=153500 bound=153500 cpu_s=0.994794 rss_mib=7.344
case=s2_030_bimodal family=bimodal normalized=0.940928270 trench=4740 bound=4460 cpu_s=0.048646 rss_mib=1.609
case=s2_031_bimodal family=bimodal normalized=0.975662520 trench=73960 bound=72160 cpu_s=0.091335 rss_mib=2.078
case=s2_032_bimodal family=bimodal normalized=1.000000000 trench=660 bound=660 cpu_s=0.153190 rss_mib=2.172
case=s2_033_section_boundaries family=section_boundaries normalized=0.955955335 trench=32240 bound=30820 cpu_s=0.443722 rss_mib=3.812
case=s2_034_section_boundaries family=section_boundaries normalized=0.991033412 trench=399260 bound=395680 cpu_s=0.692624 rss_mib=2.719
case=s2_035_section_boundaries family=section_boundaries normalized=0.985576923 trench=4160 bound=4100 cpu_s=0.743033 rss_mib=4.734
case=s2_036_section_boundaries family=section_boundaries normalized=0.956168831 trench=73920 bound=70680 cpu_s=1.358374 rss_mib=4.812
case=s2_037_section_boundaries family=section_boundaries normalized=0.851063830 trench=940 bound=800 cpu_s=0.044198 rss_mib=1.594
case=s2_038_section_boundaries family=section_boundaries normalized=0.988258317 trench=10220 bound=10100 cpu_s=0.084937 rss_mib=1.797
case=s2_039_section_boundaries family=section_boundaries normalized=0.992552135 trench=201400 bound=199900 cpu_s=0.188412 rss_mib=2.703
case=s2_040_section_boundaries family=section_boundaries normalized=1.000000000 trench=1260 bound=1260 cpu_s=0.264198 rss_mib=2.391
case=s2_041_fifo family=fifo normalized=0.999520384 trench=83400 bound=83360 cpu_s=0.603848 rss_mib=3.281
case=s2_042_fifo family=fifo normalized=0.875000000 trench=960 bound=840 cpu_s=0.809005 rss_mib=4.562
case=s2_043_fifo family=fifo normalized=0.996078431 trench=10200 bound=10160 cpu_s=1.012107 rss_mib=5.531
case=s2_044_fifo family=fifo normalized=0.984575835 trench=7780 bound=7660 cpu_s=0.044127 rss_mib=1.719
case=s2_045_fifo family=fifo normalized=0.920353982 trench=2260 bound=2080 cpu_s=0.089212 rss_mib=1.797
case=s2_046_fifo family=fifo normalized=1.000000000 trench=31320 bound=31320 cpu_s=0.160876 rss_mib=2.156
case=s2_047_fifo family=fifo normalized=0.990536119 trench=397300 bound=393540 cpu_s=0.286167 rss_mib=3.672
case=s2_048_fifo family=fifo normalized=0.930232558 trench=6020 bound=5600 cpu_s=0.464383 rss_mib=3.844
case=s2_049_lifo family=lifo normalized=1.000000000 trench=169280 bound=169280 cpu_s=0.781331 rss_mib=4.312
case=s2_050_lifo family=lifo normalized=1.000000000 trench=1840 bound=1840 cpu_s=0.985830 rss_mib=6.125
case=s2_051_lifo family=lifo normalized=1.000000000 trench=30920 bound=30920 cpu_s=0.041346 rss_mib=1.703
case=s2_052_lifo family=lifo normalized=1.000000000 trench=14540 bound=14540 cpu_s=0.076144 rss_mib=2.000
case=s2_053_lifo family=lifo normalized=1.000000000 trench=5700 bound=5700 cpu_s=0.159861 rss_mib=2.172
case=s2_054_lifo family=lifo normalized=1.000000000 trench=83540 bound=83540 cpu_s=0.249493 rss_mib=2.750
case=s2_055_lifo family=lifo normalized=1.000000000 trench=800 bound=800 cpu_s=0.393425 rss_mib=3.156
case=s2_056_lifo family=lifo normalized=1.000000000 trench=12920 bound=12920 cpu_s=0.543382 rss_mib=3.688
case=s2_057_size_lifetimes family=size_lifetimes normalized=0.976020739 trench=61720 bound=60240 cpu_s=1.286164 rss_mib=6.266
case=s2_058_size_lifetimes family=size_lifetimes normalized=0.888888889 trench=900 bound=800 cpu_s=0.044124 rss_mib=1.594
case=s2_059_size_lifetimes family=size_lifetimes normalized=0.973051011 trench=41560 bound=40440 cpu_s=0.093377 rss_mib=2.094
case=s2_060_size_lifetimes family=size_lifetimes normalized=0.857142857 trench=280 bound=240 cpu_s=0.162298 rss_mib=2.156
case=s2_061_size_lifetimes family=size_lifetimes normalized=0.934426230 trench=3660 bound=3420 cpu_s=0.284953 rss_mib=2.734
case=s2_062_size_lifetimes family=size_lifetimes normalized=0.970125328 trench=137240 bound=133140 cpu_s=0.531074 rss_mib=3.859
case=s2_063_size_lifetimes family=size_lifetimes normalized=0.962616822 trench=4280 bound=4120 cpu_s=0.618921 rss_mib=2.969
case=s2_064_size_lifetimes family=size_lifetimes normalized=0.900000000 trench=4200 bound=3780 cpu_s=0.878425 rss_mib=6.094
case=s2_065_burst_drain family=burst_drain normalized=0.918918919 trench=740 bound=680 cpu_s=0.046505 rss_mib=1.594
case=s2_066_burst_drain family=burst_drain normalized=0.982274742 trench=13540 bound=13300 cpu_s=0.092053 rss_mib=1.797
case=s2_067_burst_drain family=burst_drain normalized=0.999211771 trench=152240 bound=152120 cpu_s=0.193362 rss_mib=2.906
case=s2_068_burst_drain family=burst_drain normalized=1.000000000 trench=440 bound=440 cpu_s=0.244726 rss_mib=2.750
case=s2_069_burst_drain family=burst_drain normalized=0.985744654 trench=159940 bound=157660 cpu_s=0.591912 rss_mib=2.984
case=s2_070_burst_drain family=burst_drain normalized=0.999890794 trench=732560 bound=732480 cpu_s=0.801976 rss_mib=5.688
case=s2_071_burst_drain family=burst_drain normalized=0.995918367 trench=4900 bound=4880 cpu_s=0.794964 rss_mib=4.938
case=s2_072_burst_drain family=burst_drain normalized=1.000000000 trench=168720 bound=168720 cpu_s=1.140115 rss_mib=5.047
case=s2_073_distribution_switch family=distribution_switch normalized=0.992366412 trench=2620 bound=2600 cpu_s=0.085179 rss_mib=1.797
case=s2_074_distribution_switch family=distribution_switch normalized=0.998792271 trench=33120 bound=33080 cpu_s=0.161641 rss_mib=2.234
case=s2_075_distribution_switch family=distribution_switch normalized=1.000000000 trench=255620 bound=255620 cpu_s=0.309951 rss_mib=3.125
case=s2_076_distribution_switch family=distribution_switch normalized=0.984709480 trench=6540 bound=6440 cpu_s=0.439728 rss_mib=3.828
case=s2_077_distribution_switch family=distribution_switch normalized=0.947851003 trench=69800 bound=66160 cpu_s=0.564286 rss_mib=4.375
case=s2_078_distribution_switch family=distribution_switch normalized=0.928571429 trench=1400 bound=1300 cpu_s=0.796140 rss_mib=6.016
case=s2_079_distribution_switch family=distribution_switch normalized=1.000000000 trench=8420 bound=8420 cpu_s=1.037556 rss_mib=5.188
case=s2_080_distribution_switch family=distribution_switch normalized=0.877626244 trench=54260 bound=47620 cpu_s=0.051377 rss_mib=1.844
case=s2_081_drifting_sizes family=drifting_sizes normalized=0.850847458 trench=5900 bound=5020 cpu_s=0.186228 rss_mib=2.156
case=s2_082_drifting_sizes family=drifting_sizes normalized=1.000000000 trench=106700 bound=106700 cpu_s=0.245734 rss_mib=2.891
case=s2_083_drifting_sizes family=drifting_sizes normalized=0.790322581 trench=1240 bound=980 cpu_s=0.415495 rss_mib=3.844
case=s2_084_drifting_sizes family=drifting_sizes normalized=0.920000000 trench=18000 bound=16560 cpu_s=0.710417 rss_mib=2.938
case=s2_085_drifting_sizes family=drifting_sizes normalized=0.996851919 trench=165180 bound=164660 cpu_s=0.839945 rss_mib=5.125
case=s2_086_drifting_sizes family=drifting_sizes normalized=0.810126582 trench=3160 bound=2560 cpu_s=1.223843 rss_mib=4.156
case=s2_087_drifting_sizes family=drifting_sizes normalized=0.928118393 trench=37840 bound=35120 cpu_s=0.063387 rss_mib=1.797
case=s2_088_drifting_sizes family=drifting_sizes normalized=0.968415008 trench=104480 bound=101180 cpu_s=0.100521 rss_mib=2.141
case=s2_089_striped_recycling family=striped_recycling normalized=0.999467377 trench=150200 bound=150120 cpu_s=0.313960 rss_mib=3.047
case=s2_090_striped_recycling family=striped_recycling normalized=1.000000000 trench=775400 bound=775400 cpu_s=0.458986 rss_mib=4.000
case=s2_091_striped_recycling family=striped_recycling normalized=0.998614154 trench=1067940 bound=1066460 cpu_s=0.668248 rss_mib=6.266
case=s2_092_striped_recycling family=striped_recycling normalized=1.000000000 trench=2034140 bound=2034140 cpu_s=0.781409 rss_mib=6.141
case=s2_093_striped_recycling family=striped_recycling normalized=1.000000000 trench=2845400 bound=2845400 cpu_s=1.047973 rss_mib=11.047
case=s2_094_striped_recycling family=striped_recycling normalized=0.999743063 trench=77840 bound=77820 cpu_s=0.046502 rss_mib=1.750
case=s2_095_striped_recycling family=striped_recycling normalized=1.000000000 trench=236280 bound=236280 cpu_s=0.084004 rss_mib=2.203
case=s2_096_striped_recycling family=striped_recycling normalized=0.999958866 trench=486220 bound=486200 cpu_s=0.154174 rss_mib=2.828
case=s2_097_geometric_cohorts family=geometric_cohorts normalized=0.984988453 trench=17320 bound=17060 cpu_s=0.433358 rss_mib=3.844
case=s2_098_geometric_cohorts family=geometric_cohorts normalized=0.991986828 trench=182200 bound=180740 cpu_s=0.673552 rss_mib=3.219
case=s2_099_geometric_cohorts family=geometric_cohorts normalized=0.738805970 trench=2680 bound=1980 cpu_s=0.713507 rss_mib=4.609
case=s2_100_geometric_cohorts family=geometric_cohorts normalized=0.959087333 trench=50840 bound=48760 cpu_s=1.221629 rss_mib=4.812
case=s2_101_geometric_cohorts family=geometric_cohorts normalized=0.909090909 trench=880 bound=800 cpu_s=0.044695 rss_mib=1.609
case=s2_102_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=10780 bound=10780 cpu_s=0.086159 rss_mib=1.828
case=s2_103_geometric_cohorts family=geometric_cohorts normalized=0.913490725 trench=118600 bound=108340 cpu_s=0.192860 rss_mib=2.984
case=s2_104_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=320 bound=320 cpu_s=0.250993 rss_mib=2.734
case=s2_105_additive_cohorts family=additive_cohorts normalized=0.975058275 trench=85800 bound=83660 cpu_s=0.612704 rss_mib=4.047
case=s2_106_additive_cohorts family=additive_cohorts normalized=0.890909091 trench=1100 bound=980 cpu_s=0.828283 rss_mib=5.078
case=s2_107_additive_cohorts family=additive_cohorts normalized=0.994729908 trench=15180 bound=15100 cpu_s=1.040430 rss_mib=4.953
case=s2_108_additive_cohorts family=additive_cohorts normalized=0.989470220 trench=60780 bound=60140 cpu_s=0.049884 rss_mib=1.828
case=s2_109_additive_cohorts family=additive_cohorts normalized=0.833333333 trench=3120 bound=2600 cpu_s=0.085371 rss_mib=1.797
case=s2_110_additive_cohorts family=additive_cohorts normalized=1.000000000 trench=27240 bound=27240 cpu_s=0.160830 rss_mib=2.234
case=s2_111_additive_cohorts family=additive_cohorts normalized=0.899090909 trench=506000 bound=454940 cpu_s=0.339214 rss_mib=3.781
case=s2_112_additive_cohorts family=additive_cohorts normalized=0.927884615 trench=8320 bound=7720 cpu_s=0.482580 rss_mib=2.797
case=s2_113_large_live_set family=large_live_set normalized=0.962432916 trench=44720 bound=43040 cpu_s=0.500926 rss_mib=3.547
case=s2_114_large_live_set family=large_live_set normalized=0.968650613 trench=88040 bound=85280 cpu_s=0.684768 rss_mib=2.781
case=s2_115_large_live_set family=large_live_set normalized=0.979995401 trench=173960 bound=170480 cpu_s=0.899960 rss_mib=3.906
case=s2_116_large_live_set family=large_live_set normalized=0.980447808 trench=253680 bound=248720 cpu_s=1.051483 rss_mib=4.766
case=s2_117_large_live_set family=large_live_set normalized=0.984433302 trench=343040 bound=337700 cpu_s=1.067766 rss_mib=5.125
case=s2_118_large_live_set family=large_live_set normalized=0.986712422 trench=501220 bound=494560 cpu_s=1.432573 rss_mib=4.844
case=s2_119_large_live_set family=large_live_set normalized=0.987822055 trench=681560 bound=673260 cpu_s=1.400709 rss_mib=5.516
case=s2_120_large_live_set family=large_live_set normalized=0.988110512 trench=935280 bound=924160 cpu_s=1.370387 rss_mib=5.812
case=s2_121_size_biased_deletion family=size_biased_deletion normalized=0.999761763 trench=335800 bound=335720 cpu_s=1.129656 rss_mib=4.516
case=s2_122_size_biased_deletion family=size_biased_deletion normalized=0.913888889 trench=7200 bound=6580 cpu_s=0.049526 rss_mib=1.609
case=s2_123_size_biased_deletion family=size_biased_deletion normalized=0.961564549 trench=88460 bound=85060 cpu_s=0.098271 rss_mib=2.188
case=s2_124_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=100 bound=100 cpu_s=0.154450 rss_mib=2.172
case=s2_125_size_biased_deletion family=size_biased_deletion normalized=0.807597027 trench=24220 bound=19560 cpu_s=0.329275 rss_mib=2.422
case=s2_126_size_biased_deletion family=size_biased_deletion normalized=0.891096824 trench=205320 bound=182960 cpu_s=0.581841 rss_mib=3.656
case=s2_127_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=1440 bound=1440 cpu_s=0.597973 rss_mib=3.438
case=s2_128_size_biased_deletion family=size_biased_deletion normalized=0.904021629 trench=59180 bound=53500 cpu_s=1.048768 rss_mib=5.469


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
namespace {
using Coordinate = std::int64_t;
using GapKey = std::pair<Coordinate, Coordinate>;
using GapAgeKey =
    std::pair<Coordinate, std::pair<std::uint64_t, Coordinate>>;
// Ablation changes only the tie-break, keeping age indexing and sampling.
constexpr bool kUseGapAgeTieBreak = true;
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
    int length = 0;
    int previous = 0;
    int next = 0;
    unsigned char runPhase = 0;
    unsigned char group = 1;
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
        pipe.active = true;
        pipes_.push_back(pipe);
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
    std::set<GapAgeKey> bySizeAge_;
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
    void beginCommand() {
        ++tick_;
        if ((tick_ & 1023U) == 0) {
            totalRate_.forget(tick_);
            for (Rate& rate : lengthRates_) rate.forget(tick_);
            for (Rate& rate : globalPhaseRates_) rate.forget(tick_);
            for (Rate& rate : runPhaseRates_) rate.forget(tick_);
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
    void refreshModel(bool force) {
        if (haveModel_ && !force && tick_ - modelTick_ < 16) return;
        modelTick_ = tick_;
        haveModel_ = true;
        const double globalRate =
            (totalRate_.deaths + 4.0) /
            (totalRate_.exposureAt(tick_) +
             4.0 * static_cast<double>(totalRate_.live + 1));
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
        return predictDeletion(
            pipe.length, pid & 7, static_cast<int>(pipe.runPhase));
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
            // The tail is unique, so skipping it gives an exact check.
            auto interior = bySize_.lower_bound({length, 0});
            if (interior != bySize_.end() &&
                interior->second == gapStart) {
                ++interior;
            }
            if (interior != bySize_.end()) return;
        }
        const Coordinate remainder = span - length;
        const Coordinate leftLength = gap.left == 0
            ? 0 : pipes_[static_cast<std::size_t>(gap.left)].length;
        const Coordinate rightLength = gap.right == 0
            ? 0 : pipes_[static_cast<std::size_t>(gap.right)].length;
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
            const bool equalSpanBetter =
                (kUseGapAgeTieBreak && gap.freeSince != best.freeSince)
                    ? gap.freeSince < best.freeSince
                    : position < best.start;
            const bool better =
                !best.valid ||
                score < best.score - 1e-10 ||
                (score <= best.score + 1e-10 &&
                 (span < best.span ||
                  (span == best.span && equalSpanBetter)));
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
    void considerOldestGap(
        Coordinate span, int length,
        double deletionProbability, Choice& choice) const {
        if (span < length) return;
        auto oldest = bySizeAge_.lower_bound({span, {0, 0}});
        if (oldest == bySizeAge_.end() || oldest->first != span) return;
        const auto found = gaps_.find(oldest->second.second);
        if (found != gaps_.end() && found->second.end == trenchLength_) {
            // A same-span interior gap makes the unique tail ineligible.
            // Skip at most one entry to find the oldest eligible gap.
            const auto next = std::next(oldest);
            if (next != bySizeAge_.end() && next->first == span) {
                oldest = next;
            }
        }
        // Candidate coverage is identical with the tie-break disabled.
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
        considerOldestGap(
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
            considerOldestGap(
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
                considerOldestGap(
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
        bySizeAge_.insert({end - start, {freeSince, start}});
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
        bySizeAge_.erase({gap.end - start, {gap.freeSince, start}});
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

Combined score to maximize: 0.96
valid_cases: 128; family_count: 16; worst_family_score: 0.91; mean_raw_kpi: 0.56; max_solver_cpu_seconds: 1.98; max_solver_rss_mib: 12.52

Here is additional text feedback about the current program:

case=s2_001_uniform_churn family=uniform_churn normalized=0.860465116 trench=860 bound=740 cpu_s=0.068341 rss_mib=1.641
case=s2_002_uniform_churn family=uniform_churn normalized=0.957820738 trench=11380 bound=10900 cpu_s=0.110283 rss_mib=1.828
case=s2_003_uniform_churn family=uniform_churn normalized=0.975867270 trench=172380 bound=168220 cpu_s=0.223151 rss_mib=2.891
case=s2_004_uniform_churn family=uniform_churn normalized=1.000000000 trench=1320 bound=1320 cpu_s=0.265554 rss_mib=2.766
case=s2_005_uniform_churn family=uniform_churn normalized=0.965109403 trench=33820 bound=32640 cpu_s=0.611099 rss_mib=3.828
case=s2_006_uniform_churn family=uniform_churn normalized=0.985510633 trench=342320 bound=337360 cpu_s=0.837802 rss_mib=4.672
case=s2_007_uniform_churn family=uniform_churn normalized=0.981651376 trench=4360 bound=4280 cpu_s=0.750796 rss_mib=6.172
case=s2_008_uniform_churn family=uniform_churn normalized=0.962327240 trench=89720 bound=86340 cpu_s=1.615759 rss_mib=5.625
case=s2_009_short_heavy family=short_heavy normalized=0.903846154 trench=1040 bound=940 cpu_s=0.102150 rss_mib=1.797
case=s2_010_short_heavy family=short_heavy normalized=0.993911720 trench=13140 bound=13060 cpu_s=0.187389 rss_mib=2.234
case=s2_011_short_heavy family=short_heavy normalized=0.981578529 trench=125940 bound=123620 cpu_s=0.382112 rss_mib=3.172
case=s2_012_short_heavy family=short_heavy normalized=0.790322581 trench=1240 bound=980 cpu_s=0.518120 rss_mib=3.828
case=s2_013_short_heavy family=short_heavy normalized=0.989743590 trench=39000 bound=38600 cpu_s=0.714922 rss_mib=3.094
case=s2_014_short_heavy family=short_heavy normalized=0.782608696 trench=460 bound=360 cpu_s=0.939104 rss_mib=5.422
case=s2_015_short_heavy family=short_heavy normalized=0.987179487 trench=3120 bound=3080 cpu_s=1.182862 rss_mib=5.141
case=s2_016_short_heavy family=short_heavy normalized=0.972431078 trench=7980 bound=7760 cpu_s=0.051996 rss_mib=1.734
case=s2_017_long_heavy family=long_heavy normalized=0.916376307 trench=5740 bound=5260 cpu_s=0.252965 rss_mib=2.172
case=s2_018_long_heavy family=long_heavy normalized=1.000000000 trench=120420 bound=120420 cpu_s=0.333601 rss_mib=2.953
case=s2_019_long_heavy family=long_heavy normalized=0.839285714 trench=1120 bound=940 cpu_s=0.558666 rss_mib=3.547
case=s2_020_long_heavy family=long_heavy normalized=0.959244533 trench=20120 bound=19300 cpu_s=0.794955 rss_mib=4.219
case=s2_021_long_heavy family=long_heavy normalized=1.000000000 trench=227240 bound=227240 cpu_s=0.839841 rss_mib=6.500
case=s2_022_long_heavy family=long_heavy normalized=0.897637795 trench=2540 bound=2280 cpu_s=1.409943 rss_mib=6.469
case=s2_023_long_heavy family=long_heavy normalized=0.982562278 trench=56200 bound=55220 cpu_s=0.055175 rss_mib=1.828
case=s2_024_long_heavy family=long_heavy normalized=0.996965756 trench=138420 bound=138000 cpu_s=0.129745 rss_mib=2.188
case=s2_025_bimodal family=bimodal normalized=0.951612903 trench=14880 bound=14160 cpu_s=0.454956 rss_mib=2.781
case=s2_026_bimodal family=bimodal normalized=0.963987266 trench=201040 bound=193800 cpu_s=0.703058 rss_mib=4.312
case=s2_027_bimodal family=bimodal normalized=0.955882353 trench=1360 bound=1300 cpu_s=0.693835 rss_mib=4.188
case=s2_028_bimodal family=bimodal normalized=0.955642023 trench=25700 bound=24560 cpu_s=1.250750 rss_mib=6.312
case=s2_029_bimodal family=bimodal normalized=1.000000000 trench=153500 bound=153500 cpu_s=1.342132 rss_mib=7.172
case=s2_030_bimodal family=bimodal normalized=0.936974790 trench=4760 bound=4460 cpu_s=0.064226 rss_mib=1.609
case=s2_031_bimodal family=bimodal normalized=0.977248104 trench=73840 bound=72160 cpu_s=0.122970 rss_mib=2.094
case=s2_032_bimodal family=bimodal normalized=1.000000000 trench=660 bound=660 cpu_s=0.222104 rss_mib=2.172
case=s2_033_section_boundaries family=section_boundaries normalized=0.955955335 trench=32240 bound=30820 cpu_s=0.605868 rss_mib=3.156
case=s2_034_section_boundaries family=section_boundaries normalized=0.990785256 trench=399360 bound=395680 cpu_s=0.909301 rss_mib=3.344
case=s2_035_section_boundaries family=section_boundaries normalized=0.985576923 trench=4160 bound=4100 cpu_s=1.024144 rss_mib=4.844
case=s2_036_section_boundaries family=section_boundaries normalized=0.945172506 trench=74780 bound=70680 cpu_s=1.979692 rss_mib=5.891
case=s2_037_section_boundaries family=section_boundaries normalized=0.833333333 trench=960 bound=800 cpu_s=0.067104 rss_mib=1.609
case=s2_038_section_boundaries family=section_boundaries normalized=0.988258317 trench=10220 bound=10100 cpu_s=0.113451 rss_mib=1.797
case=s2_039_section_boundaries family=section_boundaries normalized=0.992158031 trench=201480 bound=199900 cpu_s=0.234709 rss_mib=2.719
case=s2_040_section_boundaries family=section_boundaries normalized=1.000000000 trench=1260 bound=1260 cpu_s=0.318940 rss_mib=2.750
case=s2_041_fifo family=fifo normalized=0.999520384 trench=83400 bound=83360 cpu_s=0.836438 rss_mib=3.828
case=s2_042_fifo family=fifo normalized=0.875000000 trench=960 bound=840 cpu_s=1.091804 rss_mib=5.969
case=s2_043_fifo family=fifo normalized=0.996078431 trench=10200 bound=10160 cpu_s=1.426120 rss_mib=4.188
case=s2_044_fifo family=fifo normalized=0.977040816 trench=7840 bound=7660 cpu_s=0.060530 rss_mib=1.734
case=s2_045_fifo family=fifo normalized=0.904347826 trench=2300 bound=2080 cpu_s=0.155614 rss_mib=1.812
case=s2_046_fifo family=fifo normalized=1.000000000 trench=31320 bound=31320 cpu_s=0.261628 rss_mib=2.016
case=s2_047_fifo family=fifo normalized=0.990685732 trench=397240 bound=393540 cpu_s=0.476047 rss_mib=3.484
case=s2_048_fifo family=fifo normalized=0.939597315 trench=5960 bound=5600 cpu_s=0.756130 rss_mib=3.172
case=s2_049_lifo family=lifo normalized=1.000000000 trench=169280 bound=169280 cpu_s=0.968909 rss_mib=5.562
case=s2_050_lifo family=lifo normalized=1.000000000 trench=1840 bound=1840 cpu_s=1.051528 rss_mib=6.750
case=s2_051_lifo family=lifo normalized=1.000000000 trench=30920 bound=30920 cpu_s=0.044758 rss_mib=1.719
case=s2_052_lifo family=lifo normalized=1.000000000 trench=14540 bound=14540 cpu_s=0.087320 rss_mib=2.016
case=s2_053_lifo family=lifo normalized=1.000000000 trench=5700 bound=5700 cpu_s=0.172346 rss_mib=2.188
case=s2_054_lifo family=lifo normalized=1.000000000 trench=83540 bound=83540 cpu_s=0.262996 rss_mib=2.766
case=s2_055_lifo family=lifo normalized=1.000000000 trench=800 bound=800 cpu_s=0.436128 rss_mib=3.859
case=s2_056_lifo family=lifo normalized=1.000000000 trench=12920 bound=12920 cpu_s=0.584615 rss_mib=4.188
case=s2_057_size_lifetimes family=size_lifetimes normalized=0.975388601 trench=61760 bound=60240 cpu_s=1.551125 rss_mib=6.922
case=s2_058_size_lifetimes family=size_lifetimes normalized=0.909090909 trench=880 bound=800 cpu_s=0.051298 rss_mib=1.625
case=s2_059_size_lifetimes family=size_lifetimes normalized=0.970249520 trench=41680 bound=40440 cpu_s=0.108905 rss_mib=2.125
case=s2_060_size_lifetimes family=size_lifetimes normalized=0.857142857 trench=280 bound=240 cpu_s=0.172092 rss_mib=2.188
case=s2_061_size_lifetimes family=size_lifetimes normalized=0.939560440 trench=3640 bound=3420 cpu_s=0.342955 rss_mib=2.750
case=s2_062_size_lifetimes family=size_lifetimes normalized=0.972534697 trench=136900 bound=133140 cpu_s=0.595164 rss_mib=4.172
case=s2_063_size_lifetimes family=size_lifetimes normalized=0.962616822 trench=4280 bound=4120 cpu_s=0.695285 rss_mib=4.172
case=s2_064_size_lifetimes family=size_lifetimes normalized=0.908653846 trench=4160 bound=3780 cpu_s=1.047323 rss_mib=4.516
case=s2_065_burst_drain family=burst_drain normalized=0.894736842 trench=760 bound=680 cpu_s=0.052992 rss_mib=1.609
case=s2_066_burst_drain family=burst_drain normalized=0.982274742 trench=13540 bound=13300 cpu_s=0.114610 rss_mib=1.828
case=s2_067_burst_drain family=burst_drain normalized=0.998686975 trench=152320 bound=152120 cpu_s=0.231882 rss_mib=3.062
case=s2_068_burst_drain family=burst_drain normalized=1.000000000 trench=440 bound=440 cpu_s=0.291360 rss_mib=2.672
case=s2_069_burst_drain family=burst_drain normalized=0.986484795 trench=159820 bound=157660 cpu_s=0.653926 rss_mib=3.953
case=s2_070_burst_drain family=burst_drain normalized=0.999945394 trench=732520 bound=732480 cpu_s=0.865830 rss_mib=6.422
case=s2_071_burst_drain family=burst_drain normalized=0.995918367 trench=4900 bound=4880 cpu_s=0.944839 rss_mib=5.688
case=s2_072_burst_drain family=burst_drain normalized=1.000000000 trench=168720 bound=168720 cpu_s=1.286764 rss_mib=6.734
case=s2_073_distribution_switch family=distribution_switch normalized=0.992366412 trench=2620 bound=2600 cpu_s=0.120973 rss_mib=1.812
case=s2_074_distribution_switch family=distribution_switch normalized=0.998792271 trench=33120 bound=33080 cpu_s=0.176629 rss_mib=2.266
case=s2_075_distribution_switch family=distribution_switch normalized=1.000000000 trench=255620 bound=255620 cpu_s=0.384785 rss_mib=3.297
case=s2_076_distribution_switch family=distribution_switch normalized=0.990769231 trench=6500 bound=6440 cpu_s=0.696266 rss_mib=3.109
case=s2_077_distribution_switch family=distribution_switch normalized=0.948666475 trench=69740 bound=66160 cpu_s=0.917022 rss_mib=3.391
case=s2_078_distribution_switch family=distribution_switch normalized=0.902777778 trench=1440 bound=1300 cpu_s=1.291786 rss_mib=5.203
case=s2_079_distribution_switch family=distribution_switch normalized=1.000000000 trench=8420 bound=8420 cpu_s=1.371230 rss_mib=5.625
case=s2_080_distribution_switch family=distribution_switch normalized=0.873440939 trench=54520 bound=47620 cpu_s=0.067073 rss_mib=1.906
case=s2_081_drifting_sizes family=drifting_sizes normalized=0.850847458 trench=5900 bound=5020 cpu_s=0.224162 rss_mib=2.188
case=s2_082_drifting_sizes family=drifting_sizes normalized=1.000000000 trench=106700 bound=106700 cpu_s=0.317990 rss_mib=2.938
case=s2_083_drifting_sizes family=drifting_sizes normalized=0.790322581 trench=1240 bound=980 cpu_s=0.532365 rss_mib=2.984
case=s2_084_drifting_sizes family=drifting_sizes normalized=0.905908096 trench=18280 bound=16560 cpu_s=1.029885 rss_mib=2.750
case=s2_085_drifting_sizes family=drifting_sizes normalized=0.996851919 trench=165180 bound=164660 cpu_s=1.251275 rss_mib=4.453
case=s2_086_drifting_sizes family=drifting_sizes normalized=0.815286624 trench=3140 bound=2560 cpu_s=1.679626 rss_mib=5.594
case=s2_087_drifting_sizes family=drifting_sizes normalized=0.928118393 trench=37840 bound=35120 cpu_s=0.074639 rss_mib=1.828
case=s2_088_drifting_sizes family=drifting_sizes normalized=0.968415008 trench=104480 bound=101180 cpu_s=0.179569 rss_mib=1.969
case=s2_089_striped_recycling family=striped_recycling normalized=0.999201278 trench=150240 bound=150120 cpu_s=0.410990 rss_mib=3.750
case=s2_090_striped_recycling family=striped_recycling normalized=1.000000000 trench=775400 bound=775400 cpu_s=0.567764 rss_mib=4.688
case=s2_091_striped_recycling family=striped_recycling normalized=0.998651559 trench=1067900 bound=1066460 cpu_s=0.801743 rss_mib=6.797
case=s2_092_striped_recycling family=striped_recycling normalized=1.000000000 trench=2034140 bound=2034140 cpu_s=0.908467 rss_mib=7.453
case=s2_093_striped_recycling family=striped_recycling normalized=1.000000000 trench=2845400 bound=2845400 cpu_s=1.261886 rss_mib=12.516
case=s2_094_striped_recycling family=striped_recycling normalized=0.999743063 trench=77840 bound=77820 cpu_s=0.056426 rss_mib=1.766
case=s2_095_striped_recycling family=striped_recycling normalized=1.000000000 trench=236280 bound=236280 cpu_s=0.104243 rss_mib=2.266
case=s2_096_striped_recycling family=striped_recycling normalized=0.999958866 trench=486220 bound=486200 cpu_s=0.190806 rss_mib=2.844
case=s2_097_geometric_cohorts family=geometric_cohorts normalized=0.982718894 trench=17360 bound=17060 cpu_s=0.531828 rss_mib=3.859
case=s2_098_geometric_cohorts family=geometric_cohorts normalized=0.990464708 trench=182480 bound=180740 cpu_s=0.725907 rss_mib=4.453
case=s2_099_geometric_cohorts family=geometric_cohorts normalized=0.738805970 trench=2680 bound=1980 cpu_s=0.777467 rss_mib=6.172
case=s2_100_geometric_cohorts family=geometric_cohorts normalized=0.956453511 trench=50980 bound=48760 cpu_s=1.479492 rss_mib=6.469
case=s2_101_geometric_cohorts family=geometric_cohorts normalized=0.909090909 trench=880 bound=800 cpu_s=0.046553 rss_mib=1.609
case=s2_102_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=10780 bound=10780 cpu_s=0.099685 rss_mib=1.859
case=s2_103_geometric_cohorts family=geometric_cohorts normalized=0.913490725 trench=118600 bound=108340 cpu_s=0.232981 rss_mib=3.109
case=s2_104_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=320 bound=320 cpu_s=0.248322 rss_mib=2.750
case=s2_105_additive_cohorts family=additive_cohorts normalized=0.975058275 trench=85800 bound=83660 cpu_s=0.717594 rss_mib=4.469
case=s2_106_additive_cohorts family=additive_cohorts normalized=0.890909091 trench=1100 bound=980 cpu_s=0.914345 rss_mib=6.156
case=s2_107_additive_cohorts family=additive_cohorts normalized=0.994729908 trench=15180 bound=15100 cpu_s=1.065646 rss_mib=6.656
case=s2_108_additive_cohorts family=additive_cohorts normalized=0.988819467 trench=60820 bound=60140 cpu_s=0.057007 rss_mib=1.875
case=s2_109_additive_cohorts family=additive_cohorts normalized=0.849673203 trench=3060 bound=2600 cpu_s=0.101567 rss_mib=1.797
case=s2_110_additive_cohorts family=additive_cohorts normalized=1.000000000 trench=27240 bound=27240 cpu_s=0.190482 rss_mib=2.281
case=s2_111_additive_cohorts family=additive_cohorts normalized=0.899090909 trench=506000 bound=454940 cpu_s=0.389557 rss_mib=5.078
case=s2_112_additive_cohorts family=additive_cohorts normalized=0.939172749 trench=8220 bound=7720 cpu_s=0.484607 rss_mib=3.844
case=s2_113_large_live_set family=large_live_set normalized=0.961143368 trench=44780 bound=43040 cpu_s=0.593202 rss_mib=4.047
case=s2_114_large_live_set family=large_live_set normalized=0.968870711 trench=88020 bound=85280 cpu_s=0.745858 rss_mib=4.344
case=s2_115_large_live_set family=large_live_set normalized=0.981801428 trench=173640 bound=170480 cpu_s=1.030726 rss_mib=4.000
case=s2_116_large_live_set family=large_live_set normalized=0.981298824 trench=253460 bound=248720 cpu_s=1.296515 rss_mib=5.656
case=s2_117_large_live_set family=large_live_set normalized=0.984318526 trench=343080 bound=337700 cpu_s=1.443636 rss_mib=5.969
case=s2_118_large_live_set family=large_live_set normalized=0.986515599 trench=501320 bound=494560 cpu_s=1.659873 rss_mib=5.703
case=s2_119_large_live_set family=large_live_set normalized=0.987648163 trench=681680 bound=673260 cpu_s=1.871550 rss_mib=6.422
case=s2_120_large_live_set family=large_live_set normalized=0.987962626 trench=935420 bound=924160 cpu_s=1.764474 rss_mib=6.562
case=s2_121_size_biased_deletion family=size_biased_deletion normalized=0.999761763 trench=335800 bound=335720 cpu_s=1.235363 rss_mib=6.359
case=s2_122_size_biased_deletion family=size_biased_deletion normalized=0.916434540 trench=7180 bound=6580 cpu_s=0.063966 rss_mib=1.609
case=s2_123_size_biased_deletion family=size_biased_deletion normalized=0.962652784 trench=88360 bound=85060 cpu_s=0.124379 rss_mib=2.234
case=s2_124_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=100 bound=100 cpu_s=0.208537 rss_mib=2.172
case=s2_125_size_biased_deletion family=size_biased_deletion normalized=0.819782062 trench=23860 bound=19560 cpu_s=0.409398 rss_mib=2.797
case=s2_126_size_biased_deletion family=size_biased_deletion normalized=0.895984329 trench=204200 bound=182960 cpu_s=0.780972 rss_mib=4.500
case=s2_127_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=1440 bound=1440 cpu_s=0.674634 rss_mib=4.078
case=s2_128_size_biased_deletion family=size_biased_deletion normalized=0.892261508 trench=59960 bound=53500 cpu_s=1.090875 rss_mib=6.266


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
