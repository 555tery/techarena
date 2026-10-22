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
valid_cases: 128; family_count: 16; worst_family_score: 0.91; mean_raw_kpi: 0.56; max_solver_cpu_seconds: 1.52; max_solver_rss_mib: 8.36

Text feedback:
case=s2_001_uniform_churn family=uniform_churn normalized=0.860465116 trench=860 bound=740 cpu_s=0.048372 rss_mib=1.641
case=s2_002_uniform_churn family=uniform_churn normalized=0.961199295 trench=11340 bound=10900 cpu_s=0.084120 rss_mib=1.781
case=s2_003_uniform_churn family=uniform_churn normalized=0.977454968 trench=172100 bound=168220 cpu_s=0.188635 rss_mib=2.812
case=s2_004_uniform_churn family=uniform_churn normalized=1.000000000 trench=1320 bound=1320 cpu_s=0.242478 rss_mib=2.734
case=s2_005_uniform_churn family=uniform_churn normalized=0.964539007 trench=33840 bound=32640 cpu_s=0.498627 rss_mib=3.938
case=s2_006_uniform_churn family=uniform_churn normalized=0.984532773 trench=342660 bound=337360 cpu_s=0.836542 rss_mib=3.750
case=s2_007_uniform_churn family=uniform_churn normalized=0.981651376 trench=4360 bound=4280 cpu_s=0.902511 rss_mib=4.625
case=s2_008_uniform_churn family=uniform_churn normalized=0.964046449 trench=89560 bound=86340 cpu_s=1.391694 rss_mib=5.906
case=s2_009_short_heavy family=short_heavy normalized=0.870370370 trench=1080 bound=940 cpu_s=0.100739 rss_mib=1.797
case=s2_010_short_heavy family=short_heavy normalized=0.993911720 trench=13140 bound=13060 cpu_s=0.174711 rss_mib=2.219
case=s2_011_short_heavy family=short_heavy normalized=0.981578529 trench=125940 bound=123620 cpu_s=0.353389 rss_mib=2.781
case=s2_012_short_heavy family=short_heavy normalized=0.790322581 trench=1240 bound=980 cpu_s=0.482988 rss_mib=3.844
case=s2_013_short_heavy family=short_heavy normalized=0.989743590 trench=39000 bound=38600 cpu_s=0.684003 rss_mib=4.125
case=s2_014_short_heavy family=short_heavy normalized=0.857142857 trench=420 bound=360 cpu_s=0.908135 rss_mib=5.312
case=s2_015_short_heavy family=short_heavy normalized=0.987179487 trench=3120 bound=3080 cpu_s=1.225682 rss_mib=5.875
case=s2_016_short_heavy family=short_heavy normalized=0.974874372 trench=7960 bound=7760 cpu_s=0.048733 rss_mib=1.734
case=s2_017_long_heavy family=long_heavy normalized=0.919580420 trench=5720 bound=5260 cpu_s=0.200212 rss_mib=2.172
case=s2_018_long_heavy family=long_heavy normalized=1.000000000 trench=120420 bound=120420 cpu_s=0.277441 rss_mib=2.875
case=s2_019_long_heavy family=long_heavy normalized=0.854545455 trench=1100 bound=940 cpu_s=0.466365 rss_mib=3.828
case=s2_020_long_heavy family=long_heavy normalized=0.959244533 trench=20120 bound=19300 cpu_s=0.723915 rss_mib=3.922
case=s2_021_long_heavy family=long_heavy normalized=1.000000000 trench=227240 bound=227240 cpu_s=0.963682 rss_mib=4.875
case=s2_022_long_heavy family=long_heavy normalized=0.890625000 trench=2560 bound=2280 cpu_s=1.521565 rss_mib=4.625
case=s2_023_long_heavy family=long_heavy normalized=0.979078014 trench=56400 bound=55220 cpu_s=0.054751 rss_mib=1.766
case=s2_024_long_heavy family=long_heavy normalized=0.996389892 trench=138500 bound=138000 cpu_s=0.111258 rss_mib=2.141
case=s2_025_bimodal family=bimodal normalized=0.950335570 trench=14900 bound=14160 cpu_s=0.352598 rss_mib=2.766
case=s2_026_bimodal family=bimodal normalized=0.966390745 trench=200540 bound=193800 cpu_s=0.715435 rss_mib=3.297
case=s2_027_bimodal family=bimodal normalized=0.955882353 trench=1360 bound=1300 cpu_s=0.626530 rss_mib=4.188
case=s2_028_bimodal family=bimodal normalized=0.951937984 trench=25800 bound=24560 cpu_s=1.078486 rss_mib=4.953
case=s2_029_bimodal family=bimodal normalized=1.000000000 trench=153500 bound=153500 cpu_s=1.382085 rss_mib=4.188
case=s2_030_bimodal family=bimodal normalized=0.940928270 trench=4740 bound=4460 cpu_s=0.059032 rss_mib=1.609
case=s2_031_bimodal family=bimodal normalized=0.975662520 trench=73960 bound=72160 cpu_s=0.098284 rss_mib=2.078
case=s2_032_bimodal family=bimodal normalized=1.000000000 trench=660 bound=660 cpu_s=0.189218 rss_mib=2.094
case=s2_033_section_boundaries family=section_boundaries normalized=0.955955335 trench=32240 bound=30820 cpu_s=0.449432 rss_mib=3.500
case=s2_034_section_boundaries family=section_boundaries normalized=0.991033412 trench=399260 bound=395680 cpu_s=0.640381 rss_mib=3.672
case=s2_035_section_boundaries family=section_boundaries normalized=0.985576923 trench=4160 bound=4100 cpu_s=0.723676 rss_mib=5.859
case=s2_036_section_boundaries family=section_boundaries normalized=0.956168831 trench=73920 bound=70680 cpu_s=1.332858 rss_mib=5.453
case=s2_037_section_boundaries family=section_boundaries normalized=0.851063830 trench=940 bound=800 cpu_s=0.047137 rss_mib=1.609
case=s2_038_section_boundaries family=section_boundaries normalized=0.988258317 trench=10220 bound=10100 cpu_s=0.082132 rss_mib=1.781
case=s2_039_section_boundaries family=section_boundaries normalized=0.992552135 trench=201400 bound=199900 cpu_s=0.184794 rss_mib=2.234
case=s2_040_section_boundaries family=section_boundaries normalized=1.000000000 trench=1260 bound=1260 cpu_s=0.239635 rss_mib=2.688
case=s2_041_fifo family=fifo normalized=0.999520384 trench=83400 bound=83360 cpu_s=0.584478 rss_mib=3.859
case=s2_042_fifo family=fifo normalized=0.875000000 trench=960 bound=840 cpu_s=0.827010 rss_mib=4.219
case=s2_043_fifo family=fifo normalized=0.996078431 trench=10200 bound=10160 cpu_s=0.978363 rss_mib=5.750
case=s2_044_fifo family=fifo normalized=0.984575835 trench=7780 bound=7660 cpu_s=0.043491 rss_mib=1.719
case=s2_045_fifo family=fifo normalized=0.920353982 trench=2260 bound=2080 cpu_s=0.092452 rss_mib=1.812
case=s2_046_fifo family=fifo normalized=1.000000000 trench=31320 bound=31320 cpu_s=0.193127 rss_mib=1.766
case=s2_047_fifo family=fifo normalized=0.990536119 trench=397300 bound=393540 cpu_s=0.319711 rss_mib=3.516
case=s2_048_fifo family=fifo normalized=0.930232558 trench=6020 bound=5600 cpu_s=0.467846 rss_mib=3.844
case=s2_049_lifo family=lifo normalized=1.000000000 trench=169280 bound=169280 cpu_s=0.731798 rss_mib=5.328
case=s2_050_lifo family=lifo normalized=1.000000000 trench=1840 bound=1840 cpu_s=1.054567 rss_mib=4.188
case=s2_051_lifo family=lifo normalized=1.000000000 trench=30920 bound=30920 cpu_s=0.042904 rss_mib=1.719
case=s2_052_lifo family=lifo normalized=1.000000000 trench=14540 bound=14540 cpu_s=0.084388 rss_mib=1.766
case=s2_053_lifo family=lifo normalized=1.000000000 trench=5700 bound=5700 cpu_s=0.167616 rss_mib=2.031
case=s2_054_lifo family=lifo normalized=1.000000000 trench=83540 bound=83540 cpu_s=0.246980 rss_mib=2.734
case=s2_055_lifo family=lifo normalized=1.000000000 trench=800 bound=800 cpu_s=0.396146 rss_mib=3.469
case=s2_056_lifo family=lifo normalized=1.000000000 trench=12920 bound=12920 cpu_s=0.537376 rss_mib=4.188
case=s2_057_size_lifetimes family=size_lifetimes normalized=0.976020739 trench=61720 bound=60240 cpu_s=1.310848 rss_mib=5.109
case=s2_058_size_lifetimes family=size_lifetimes normalized=0.888888889 trench=900 bound=800 cpu_s=0.048717 rss_mib=1.594
case=s2_059_size_lifetimes family=size_lifetimes normalized=0.973051011 trench=41560 bound=40440 cpu_s=0.097585 rss_mib=2.094
case=s2_060_size_lifetimes family=size_lifetimes normalized=0.857142857 trench=280 bound=240 cpu_s=0.169882 rss_mib=2.141
case=s2_061_size_lifetimes family=size_lifetimes normalized=0.934426230 trench=3660 bound=3420 cpu_s=0.326310 rss_mib=2.219
case=s2_062_size_lifetimes family=size_lifetimes normalized=0.970125328 trench=137240 bound=133140 cpu_s=0.533831 rss_mib=4.125
case=s2_063_size_lifetimes family=size_lifetimes normalized=0.962616822 trench=4280 bound=4120 cpu_s=0.656668 rss_mib=2.922
case=s2_064_size_lifetimes family=size_lifetimes normalized=0.900000000 trench=4200 bound=3780 cpu_s=0.876247 rss_mib=5.594
case=s2_065_burst_drain family=burst_drain normalized=0.918918919 trench=740 bound=680 cpu_s=0.045140 rss_mib=1.609
case=s2_066_burst_drain family=burst_drain normalized=0.982274742 trench=13540 bound=13300 cpu_s=0.097917 rss_mib=1.797
case=s2_067_burst_drain family=burst_drain normalized=0.999211771 trench=152240 bound=152120 cpu_s=0.189902 rss_mib=2.906
case=s2_068_burst_drain family=burst_drain normalized=1.000000000 trench=440 bound=440 cpu_s=0.255247 rss_mib=2.672
case=s2_069_burst_drain family=burst_drain normalized=0.985744654 trench=159940 bound=157660 cpu_s=0.542102 rss_mib=3.125
case=s2_070_burst_drain family=burst_drain normalized=0.999890794 trench=732560 bound=732480 cpu_s=0.802001 rss_mib=6.109
case=s2_071_burst_drain family=burst_drain normalized=0.995918367 trench=4900 bound=4880 cpu_s=0.827812 rss_mib=4.625
case=s2_072_burst_drain family=burst_drain normalized=1.000000000 trench=168720 bound=168720 cpu_s=1.104480 rss_mib=5.828
case=s2_073_distribution_switch family=distribution_switch normalized=0.992366412 trench=2620 bound=2600 cpu_s=0.094081 rss_mib=1.797
case=s2_074_distribution_switch family=distribution_switch normalized=0.998792271 trench=33120 bound=33080 cpu_s=0.165558 rss_mib=2.266
case=s2_075_distribution_switch family=distribution_switch normalized=1.000000000 trench=255620 bound=255620 cpu_s=0.368148 rss_mib=2.422
case=s2_076_distribution_switch family=distribution_switch normalized=0.984709480 trench=6540 bound=6440 cpu_s=0.446490 rss_mib=3.844
case=s2_077_distribution_switch family=distribution_switch normalized=0.947851003 trench=69800 bound=66160 cpu_s=0.596527 rss_mib=3.797
case=s2_078_distribution_switch family=distribution_switch normalized=0.928571429 trench=1400 bound=1300 cpu_s=0.801464 rss_mib=5.719
case=s2_079_distribution_switch family=distribution_switch normalized=1.000000000 trench=8420 bound=8420 cpu_s=0.992293 rss_mib=5.891
case=s2_080_distribution_switch family=distribution_switch normalized=0.877626244 trench=54260 bound=47620 cpu_s=0.055584 rss_mib=1.750
case=s2_081_drifting_sizes family=drifting_sizes normalized=0.850847458 trench=5900 bound=5020 cpu_s=0.205847 rss_mib=2.031
case=s2_082_drifting_sizes family=drifting_sizes normalized=1.000000000 trench=106700 bound=106700 cpu_s=0.267555 rss_mib=2.344
case=s2_083_drifting_sizes family=drifting_sizes normalized=0.790322581 trench=1240 bound=980 cpu_s=0.470791 rss_mib=2.859
case=s2_084_drifting_sizes family=drifting_sizes normalized=0.920000000 trench=18000 bound=16560 cpu_s=0.717854 rss_mib=3.094
case=s2_085_drifting_sizes family=drifting_sizes normalized=0.996851919 trench=165180 bound=164660 cpu_s=0.852238 rss_mib=4.422
case=s2_086_drifting_sizes family=drifting_sizes normalized=0.810126582 trench=3160 bound=2560 cpu_s=1.118515 rss_mib=5.141
case=s2_087_drifting_sizes family=drifting_sizes normalized=0.928118393 trench=37840 bound=35120 cpu_s=0.050356 rss_mib=1.781
case=s2_088_drifting_sizes family=drifting_sizes normalized=0.968415008 trench=104480 bound=101180 cpu_s=0.105066 rss_mib=2.156
case=s2_089_striped_recycling family=striped_recycling normalized=0.999467377 trench=150200 bound=150120 cpu_s=0.295327 rss_mib=3.703
case=s2_090_striped_recycling family=striped_recycling normalized=1.000000000 trench=775400 bound=775400 cpu_s=0.504610 rss_mib=2.938
case=s2_091_striped_recycling family=striped_recycling normalized=0.998614154 trench=1067940 bound=1066460 cpu_s=0.693374 rss_mib=5.875
case=s2_092_striped_recycling family=striped_recycling normalized=1.000000000 trench=2034140 bound=2034140 cpu_s=0.776128 rss_mib=7.016
case=s2_093_striped_recycling family=striped_recycling normalized=1.000000000 trench=2845400 bound=2845400 cpu_s=1.165584 rss_mib=8.359
case=s2_094_striped_recycling family=striped_recycling normalized=0.999743063 trench=77840 bound=77820 cpu_s=0.045264 rss_mib=1.766
case=s2_095_striped_recycling family=striped_recycling normalized=1.000000000 trench=236280 bound=236280 cpu_s=0.096006 rss_mib=2.188
case=s2_096_striped_recycling family=striped_recycling normalized=0.999958866 trench=486220 bound=486200 cpu_s=0.169889 rss_mib=2.453
case=s2_097_geometric_cohorts family=geometric_cohorts normalized=0.984988453 trench=17320 bound=17060 cpu_s=0.440503 rss_mib=3.859
case=s2_098_geometric_cohorts family=geometric_cohorts normalized=0.991986828 trench=182200 bound=180740 cpu_s=0.634298 rss_mib=3.953
case=s2_099_geometric_cohorts family=geometric_cohorts normalized=0.738805970 trench=2680 bound=1980 cpu_s=0.703052 rss_mib=6.156
case=s2_100_geometric_cohorts family=geometric_cohorts normalized=0.959087333 trench=50840 bound=48760 cpu_s=1.172262 rss_mib=6.062
case=s2_101_geometric_cohorts family=geometric_cohorts normalized=0.909090909 trench=880 bound=800 cpu_s=0.040438 rss_mib=1.609
case=s2_102_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=10780 bound=10780 cpu_s=0.080642 rss_mib=1.828
case=s2_103_geometric_cohorts family=geometric_cohorts normalized=0.913490725 trench=118600 bound=108340 cpu_s=0.199926 rss_mib=3.000
case=s2_104_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=320 bound=320 cpu_s=0.235388 rss_mib=2.750
case=s2_105_additive_cohorts family=additive_cohorts normalized=0.975058275 trench=85800 bound=83660 cpu_s=0.613764 rss_mib=3.578
case=s2_106_additive_cohorts family=additive_cohorts normalized=0.890909091 trench=1100 bound=980 cpu_s=0.821565 rss_mib=4.938
case=s2_107_additive_cohorts family=additive_cohorts normalized=0.994729908 trench=15180 bound=15100 cpu_s=0.961169 rss_mib=6.531
case=s2_108_additive_cohorts family=additive_cohorts normalized=0.989470220 trench=60780 bound=60140 cpu_s=0.049166 rss_mib=1.828
case=s2_109_additive_cohorts family=additive_cohorts normalized=0.833333333 trench=3120 bound=2600 cpu_s=0.085276 rss_mib=1.797
case=s2_110_additive_cohorts family=additive_cohorts normalized=1.000000000 trench=27240 bound=27240 cpu_s=0.161115 rss_mib=2.141
case=s2_111_additive_cohorts family=additive_cohorts normalized=0.899090909 trench=506000 bound=454940 cpu_s=0.403908 rss_mib=3.922
case=s2_112_additive_cohorts family=additive_cohorts normalized=0.927884615 trench=8320 bound=7720 cpu_s=0.468459 rss_mib=3.156
case=s2_113_large_live_set family=large_live_set normalized=0.962432916 trench=44720 bound=43040 cpu_s=0.552262 rss_mib=3.422
case=s2_114_large_live_set family=large_live_set normalized=0.968650613 trench=88040 bound=85280 cpu_s=0.675463 rss_mib=3.938
case=s2_115_large_live_set family=large_live_set normalized=0.979995401 trench=173960 bound=170480 cpu_s=0.884523 rss_mib=3.312
case=s2_116_large_live_set family=large_live_set normalized=0.980447808 trench=253680 bound=248720 cpu_s=0.908881 rss_mib=6.562
case=s2_117_large_live_set family=large_live_set normalized=0.984433302 trench=343040 bound=337700 cpu_s=1.062753 rss_mib=6.750
case=s2_118_large_live_set family=large_live_set normalized=0.986712422 trench=501220 bound=494560 cpu_s=1.304014 rss_mib=5.203
case=s2_119_large_live_set family=large_live_set normalized=0.987822055 trench=681560 bound=673260 cpu_s=1.380799 rss_mib=6.109
case=s2_120_large_live_set family=large_live_set normalized=0.988110512 trench=935280 bound=924160 cpu_s=1.275821 rss_mib=6.547
case=s2_121_size_biased_deletion family=size_biased_deletion normalized=0.999761763 trench=335800 bound=335720 cpu_s=1.018099 rss_mib=5.984
case=s2_122_size_biased_deletion family=size_biased_deletion normalized=0.913888889 trench=7200 bound=6580 cpu_s=0.049320 rss_mib=1.609
case=s2_123_size_biased_deletion family=size_biased_deletion normalized=0.961564549 trench=88460 bound=85060 cpu_s=0.095439 rss_mib=2.172
case=s2_124_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=100 bound=100 cpu_s=0.155787 rss_mib=2.188
case=s2_125_size_biased_deletion family=size_biased_deletion normalized=0.807597027 trench=24220 bound=19560 cpu_s=0.371346 rss_mib=2.016
case=s2_126_size_biased_deletion family=size_biased_deletion normalized=0.891096824 trench=205320 bound=182960 cpu_s=0.555051 rss_mib=3.953
case=s2_127_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=1440 bound=1440 cpu_s=0.557011 rss_mib=4.062
case=s2_128_size_biased_deletion family=size_biased_deletion normalized=0.904021629 trench=59180 bound=53500 cpu_s=0.998017 rss_mib=6.312

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
constexpr bool kOldestGapTieBreak = true;
constexpr bool kCoalescingReleaseGeometry = true;
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
Combined score to maximize: 0.96
valid_cases: 128; family_count: 16; worst_family_score: 0.90; mean_raw_kpi: 0.56; max_solver_cpu_seconds: 1.85; max_solver_rss_mib: 11.69

Text feedback:
case=s2_001_uniform_churn family=uniform_churn normalized=0.860465116 trench=860 bound=740 cpu_s=0.073429 rss_mib=1.656
case=s2_002_uniform_churn family=uniform_churn normalized=0.957820738 trench=11380 bound=10900 cpu_s=0.119136 rss_mib=1.812
case=s2_003_uniform_churn family=uniform_churn normalized=0.974849328 trench=172560 bound=168220 cpu_s=0.262312 rss_mib=2.906
case=s2_004_uniform_churn family=uniform_churn normalized=1.000000000 trench=1320 bound=1320 cpu_s=0.277982 rss_mib=2.750
case=s2_005_uniform_churn family=uniform_churn normalized=0.965109403 trench=33820 bound=32640 cpu_s=0.643273 rss_mib=3.984
case=s2_006_uniform_churn family=uniform_churn normalized=0.985222826 trench=342420 bound=337360 cpu_s=0.905296 rss_mib=4.891
case=s2_007_uniform_churn family=uniform_churn normalized=0.981651376 trench=4360 bound=4280 cpu_s=0.749135 rss_mib=6.172
case=s2_008_uniform_churn family=uniform_churn normalized=0.965987917 trench=89380 bound=86340 cpu_s=1.691434 rss_mib=7.016
case=s2_009_short_heavy family=short_heavy normalized=0.886792453 trench=1060 bound=940 cpu_s=0.104075 rss_mib=1.797
case=s2_010_short_heavy family=short_heavy normalized=0.993911720 trench=13140 bound=13060 cpu_s=0.174761 rss_mib=2.266
case=s2_011_short_heavy family=short_heavy normalized=0.981890389 trench=125900 bound=123620 cpu_s=0.342582 rss_mib=3.922
case=s2_012_short_heavy family=short_heavy normalized=0.790322581 trench=1240 bound=980 cpu_s=0.526219 rss_mib=3.844
case=s2_013_short_heavy family=short_heavy normalized=0.989743590 trench=39000 bound=38600 cpu_s=0.689193 rss_mib=4.312
case=s2_014_short_heavy family=short_heavy normalized=0.857142857 trench=420 bound=360 cpu_s=0.896994 rss_mib=6.172
case=s2_015_short_heavy family=short_heavy normalized=0.987179487 trench=3120 bound=3080 cpu_s=1.034628 rss_mib=6.766
case=s2_016_short_heavy family=short_heavy normalized=0.977329975 trench=7940 bound=7760 cpu_s=0.054093 rss_mib=1.734
case=s2_017_long_heavy family=long_heavy normalized=0.922807018 trench=5700 bound=5260 cpu_s=0.232232 rss_mib=2.172
case=s2_018_long_heavy family=long_heavy normalized=1.000000000 trench=120420 bound=120420 cpu_s=0.288887 rss_mib=2.984
case=s2_019_long_heavy family=long_heavy normalized=0.870370370 trench=1080 bound=940 cpu_s=0.461441 rss_mib=3.828
case=s2_020_long_heavy family=long_heavy normalized=0.963073852 trench=20040 bound=19300 cpu_s=0.748305 rss_mib=4.219
case=s2_021_long_heavy family=long_heavy normalized=1.000000000 trench=227240 bound=227240 cpu_s=0.845359 rss_mib=6.500
case=s2_022_long_heavy family=long_heavy normalized=0.883720930 trench=2580 bound=2280 cpu_s=1.377728 rss_mib=6.188
case=s2_023_long_heavy family=long_heavy normalized=0.981165601 trench=56280 bound=55220 cpu_s=0.054297 rss_mib=1.828
case=s2_024_long_heavy family=long_heavy normalized=0.996965756 trench=138420 bound=138000 cpu_s=0.116604 rss_mib=2.141
case=s2_025_bimodal family=bimodal normalized=0.949061662 trench=14920 bound=14160 cpu_s=0.414746 rss_mib=2.781
case=s2_026_bimodal family=bimodal normalized=0.964947222 trench=200840 bound=193800 cpu_s=0.805900 rss_mib=3.469
case=s2_027_bimodal family=bimodal normalized=0.955882353 trench=1360 bound=1300 cpu_s=0.693490 rss_mib=3.328
case=s2_028_bimodal family=bimodal normalized=0.951200620 trench=25820 bound=24560 cpu_s=1.239101 rss_mib=5.391
case=s2_029_bimodal family=bimodal normalized=1.000000000 trench=153500 bound=153500 cpu_s=1.215059 rss_mib=4.891
case=s2_030_bimodal family=bimodal normalized=0.944915254 trench=4720 bound=4460 cpu_s=0.079154 rss_mib=1.609
case=s2_031_bimodal family=bimodal normalized=0.978308026 trench=73760 bound=72160 cpu_s=0.141096 rss_mib=2.094
case=s2_032_bimodal family=bimodal normalized=1.000000000 trench=660 bound=660 cpu_s=0.205283 rss_mib=2.031
case=s2_033_section_boundaries family=section_boundaries normalized=0.961322520 trench=32060 bound=30820 cpu_s=0.575034 rss_mib=3.828
case=s2_034_section_boundaries family=section_boundaries normalized=0.991182365 trench=399200 bound=395680 cpu_s=0.820210 rss_mib=4.406
case=s2_035_section_boundaries family=section_boundaries normalized=0.985576923 trench=4160 bound=4100 cpu_s=0.809070 rss_mib=5.188
case=s2_036_section_boundaries family=section_boundaries normalized=0.963730570 trench=73340 bound=70680 cpu_s=1.707707 rss_mib=5.859
case=s2_037_section_boundaries family=section_boundaries normalized=0.800000000 trench=1000 bound=800 cpu_s=0.047629 rss_mib=1.609
case=s2_038_section_boundaries family=section_boundaries normalized=0.988258317 trench=10220 bound=10100 cpu_s=0.098053 rss_mib=1.797
case=s2_039_section_boundaries family=section_boundaries normalized=0.992749305 trench=201360 bound=199900 cpu_s=0.201249 rss_mib=2.766
case=s2_040_section_boundaries family=section_boundaries normalized=1.000000000 trench=1260 bound=1260 cpu_s=0.258742 rss_mib=2.766
case=s2_041_fifo family=fifo normalized=0.999520384 trench=83400 bound=83360 cpu_s=0.645416 rss_mib=4.359
case=s2_042_fifo family=fifo normalized=0.893617021 trench=940 bound=840 cpu_s=0.911535 rss_mib=6.172
case=s2_043_fifo family=fifo normalized=0.996078431 trench=10200 bound=10160 cpu_s=1.028006 rss_mib=6.750
case=s2_044_fifo family=fifo normalized=0.987113402 trench=7760 bound=7660 cpu_s=0.049582 rss_mib=1.734
case=s2_045_fifo family=fifo normalized=0.859504132 trench=2420 bound=2080 cpu_s=0.106900 rss_mib=1.797
case=s2_046_fifo family=fifo normalized=1.000000000 trench=31320 bound=31320 cpu_s=0.174544 rss_mib=2.172
case=s2_047_fifo family=fifo normalized=0.991334576 trench=396980 bound=393540 cpu_s=0.319764 rss_mib=4.141
case=s2_048_fifo family=fifo normalized=0.930232558 trench=6020 bound=5600 cpu_s=0.571401 rss_mib=3.844
case=s2_049_lifo family=lifo normalized=1.000000000 trench=169280 bound=169280 cpu_s=0.777275 rss_mib=6.188
case=s2_050_lifo family=lifo normalized=1.000000000 trench=1840 bound=1840 cpu_s=1.029630 rss_mib=6.750
case=s2_051_lifo family=lifo normalized=1.000000000 trench=30920 bound=30920 cpu_s=0.042296 rss_mib=1.719
case=s2_052_lifo family=lifo normalized=1.000000000 trench=14540 bound=14540 cpu_s=0.084491 rss_mib=2.016
case=s2_053_lifo family=lifo normalized=1.000000000 trench=5700 bound=5700 cpu_s=0.173612 rss_mib=2.172
case=s2_054_lifo family=lifo normalized=1.000000000 trench=83540 bound=83540 cpu_s=0.267073 rss_mib=2.766
case=s2_055_lifo family=lifo normalized=1.000000000 trench=800 bound=800 cpu_s=0.424760 rss_mib=3.844
case=s2_056_lifo family=lifo normalized=1.000000000 trench=12920 bound=12920 cpu_s=0.575780 rss_mib=4.188
case=s2_057_size_lifetimes family=size_lifetimes normalized=0.975388601 trench=61760 bound=60240 cpu_s=1.635414 rss_mib=6.938
case=s2_058_size_lifetimes family=size_lifetimes normalized=0.888888889 trench=900 bound=800 cpu_s=0.049737 rss_mib=1.625
case=s2_059_size_lifetimes family=size_lifetimes normalized=0.970715314 trench=41660 bound=40440 cpu_s=0.107660 rss_mib=2.141
case=s2_060_size_lifetimes family=size_lifetimes normalized=0.857142857 trench=280 bound=240 cpu_s=0.171688 rss_mib=2.172
case=s2_061_size_lifetimes family=size_lifetimes normalized=0.944751381 trench=3620 bound=3420 cpu_s=0.338082 rss_mib=2.750
case=s2_062_size_lifetimes family=size_lifetimes normalized=0.972108645 trench=136960 bound=133140 cpu_s=0.637162 rss_mib=4.188
case=s2_063_size_lifetimes family=size_lifetimes normalized=0.967136150 trench=4260 bound=4120 cpu_s=0.728746 rss_mib=4.188
case=s2_064_size_lifetimes family=size_lifetimes normalized=0.913043478 trench=4140 bound=3780 cpu_s=1.099864 rss_mib=5.984
case=s2_065_burst_drain family=burst_drain normalized=0.894736842 trench=760 bound=680 cpu_s=0.049431 rss_mib=1.625
case=s2_066_burst_drain family=burst_drain normalized=0.989583333 trench=13440 bound=13300 cpu_s=0.115651 rss_mib=1.812
case=s2_067_burst_drain family=burst_drain normalized=0.999211771 trench=152240 bound=152120 cpu_s=0.273223 rss_mib=3.062
case=s2_068_burst_drain family=burst_drain normalized=1.000000000 trench=440 bound=440 cpu_s=0.289440 rss_mib=2.750
case=s2_069_burst_drain family=burst_drain normalized=0.986608260 trench=159800 bound=157660 cpu_s=0.726386 rss_mib=4.250
case=s2_070_burst_drain family=burst_drain normalized=0.999945394 trench=732520 bound=732480 cpu_s=0.994182 rss_mib=6.641
case=s2_071_burst_drain family=burst_drain normalized=0.995918367 trench=4900 bound=4880 cpu_s=1.026146 rss_mib=6.109
case=s2_072_burst_drain family=burst_drain normalized=1.000000000 trench=168720 bound=168720 cpu_s=1.488710 rss_mib=4.984
case=s2_073_distribution_switch family=distribution_switch normalized=0.984848485 trench=2640 bound=2600 cpu_s=0.135389 rss_mib=1.812
case=s2_074_distribution_switch family=distribution_switch normalized=0.998792271 trench=33120 bound=33080 cpu_s=0.241993 rss_mib=2.312
case=s2_075_distribution_switch family=distribution_switch normalized=1.000000000 trench=255620 bound=255620 cpu_s=0.480094 rss_mib=3.312
case=s2_076_distribution_switch family=distribution_switch normalized=0.990769231 trench=6500 bound=6440 cpu_s=0.703965 rss_mib=2.953
case=s2_077_distribution_switch family=distribution_switch normalized=0.947579490 trench=69820 bound=66160 cpu_s=0.855306 rss_mib=3.047
case=s2_078_distribution_switch family=distribution_switch normalized=0.942028986 trench=1380 bound=1300 cpu_s=1.106378 rss_mib=4.375
case=s2_079_distribution_switch family=distribution_switch normalized=1.000000000 trench=8420 bound=8420 cpu_s=1.301193 rss_mib=4.812
case=s2_080_distribution_switch family=distribution_switch normalized=0.881525361 trench=54020 bound=47620 cpu_s=0.062184 rss_mib=1.938
case=s2_081_drifting_sizes family=drifting_sizes normalized=0.847972973 trench=5920 bound=5020 cpu_s=0.311047 rss_mib=1.766
case=s2_082_drifting_sizes family=drifting_sizes normalized=1.000000000 trench=106700 bound=106700 cpu_s=0.333972 rss_mib=2.328
case=s2_083_drifting_sizes family=drifting_sizes normalized=0.790322581 trench=1240 bound=980 cpu_s=0.538320 rss_mib=3.859
case=s2_084_drifting_sizes family=drifting_sizes normalized=0.911894273 trench=18160 bound=16560 cpu_s=1.053983 rss_mib=3.406
case=s2_085_drifting_sizes family=drifting_sizes normalized=0.996851919 trench=165180 bound=164660 cpu_s=1.277121 rss_mib=4.297
case=s2_086_drifting_sizes family=drifting_sizes normalized=0.790123457 trench=3240 bound=2560 cpu_s=1.852901 rss_mib=5.594
case=s2_087_drifting_sizes family=drifting_sizes normalized=0.929592377 trench=37780 bound=35120 cpu_s=0.100365 rss_mib=1.875
case=s2_088_drifting_sizes family=drifting_sizes normalized=0.968415008 trench=104480 bound=101180 cpu_s=0.148218 rss_mib=2.219
case=s2_089_striped_recycling family=striped_recycling normalized=0.999467377 trench=150200 bound=150120 cpu_s=0.459660 rss_mib=3.203
case=s2_090_striped_recycling family=striped_recycling normalized=1.000000000 trench=775400 bound=775400 cpu_s=0.664539 rss_mib=4.688
case=s2_091_striped_recycling family=striped_recycling normalized=0.998614154 trench=1067940 bound=1066460 cpu_s=0.931264 rss_mib=6.797
case=s2_092_striped_recycling family=striped_recycling normalized=1.000000000 trench=2034140 bound=2034140 cpu_s=1.040799 rss_mib=6.594
case=s2_093_striped_recycling family=striped_recycling normalized=1.000000000 trench=2845400 bound=2845400 cpu_s=1.479805 rss_mib=11.688
case=s2_094_striped_recycling family=striped_recycling normalized=1.000000000 trench=77820 bound=77820 cpu_s=0.062739 rss_mib=1.750
case=s2_095_striped_recycling family=striped_recycling normalized=1.000000000 trench=236280 bound=236280 cpu_s=0.125038 rss_mib=2.297
case=s2_096_striped_recycling family=striped_recycling normalized=0.999958866 trench=486220 bound=486200 cpu_s=0.262574 rss_mib=2.344
case=s2_097_geometric_cohorts family=geometric_cohorts normalized=0.984988453 trench=17320 bound=17060 cpu_s=0.606790 rss_mib=3.375
case=s2_098_geometric_cohorts family=geometric_cohorts normalized=0.991225184 trench=182340 bound=180740 cpu_s=0.759137 rss_mib=4.406
case=s2_099_geometric_cohorts family=geometric_cohorts normalized=0.738805970 trench=2680 bound=1980 cpu_s=0.738435 rss_mib=6.188
case=s2_100_geometric_cohorts family=geometric_cohorts normalized=0.956078431 trench=51000 bound=48760 cpu_s=1.461663 rss_mib=6.875
case=s2_101_geometric_cohorts family=geometric_cohorts normalized=0.909090909 trench=880 bound=800 cpu_s=0.044784 rss_mib=1.609
case=s2_102_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=10780 bound=10780 cpu_s=0.088830 rss_mib=1.828
case=s2_103_geometric_cohorts family=geometric_cohorts normalized=0.912874958 trench=118680 bound=108340 cpu_s=0.226773 rss_mib=3.078
case=s2_104_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=320 bound=320 cpu_s=0.250213 rss_mib=2.766
case=s2_105_additive_cohorts family=additive_cohorts normalized=0.975285614 trench=85780 bound=83660 cpu_s=0.675082 rss_mib=4.406
case=s2_106_additive_cohorts family=additive_cohorts normalized=0.907407407 trench=1080 bound=980 cpu_s=0.920783 rss_mib=6.172
case=s2_107_additive_cohorts family=additive_cohorts normalized=0.994729908 trench=15180 bound=15100 cpu_s=1.004982 rss_mib=6.750
case=s2_108_additive_cohorts family=additive_cohorts normalized=0.989470220 trench=60780 bound=60140 cpu_s=0.058976 rss_mib=1.859
case=s2_109_additive_cohorts family=additive_cohorts normalized=0.860927152 trench=3020 bound=2600 cpu_s=0.098082 rss_mib=1.797
case=s2_110_additive_cohorts family=additive_cohorts normalized=1.000000000 trench=27240 bound=27240 cpu_s=0.168520 rss_mib=2.266
case=s2_111_additive_cohorts family=additive_cohorts normalized=0.899090909 trench=506000 bound=454940 cpu_s=0.410849 rss_mib=5.094
case=s2_112_additive_cohorts family=additive_cohorts normalized=0.946078431 trench=8160 bound=7720 cpu_s=0.480621 rss_mib=3.859
case=s2_113_large_live_set family=large_live_set normalized=0.959001783 trench=44880 bound=43040 cpu_s=0.622320 rss_mib=4.000
case=s2_114_large_live_set family=large_live_set normalized=0.969311207 trench=87980 bound=85280 cpu_s=0.793173 rss_mib=4.328
case=s2_115_large_live_set family=large_live_set normalized=0.979207352 trench=174100 bound=170480 cpu_s=0.991200 rss_mib=4.781
case=s2_116_large_live_set family=large_live_set normalized=0.980989193 trench=253540 bound=248720 cpu_s=1.135179 rss_mib=6.688
case=s2_117_large_live_set family=large_live_set normalized=0.983859690 trench=343240 bound=337700 cpu_s=1.329266 rss_mib=7.078
case=s2_118_large_live_set family=large_live_set normalized=0.986830553 trench=501160 bound=494560 cpu_s=1.494605 rss_mib=7.516
case=s2_119_large_live_set family=large_live_set normalized=0.987445367 trench=681820 bound=673260 cpu_s=1.600849 rss_mib=7.875
case=s2_120_large_live_set family=large_live_set normalized=0.988004875 trench=935380 bound=924160 cpu_s=1.590754 rss_mib=8.266
case=s2_121_size_biased_deletion family=size_biased_deletion normalized=0.999761763 trench=335800 bound=335720 cpu_s=1.043739 rss_mib=7.672
case=s2_122_size_biased_deletion family=size_biased_deletion normalized=0.924157303 trench=7120 bound=6580 cpu_s=0.059932 rss_mib=1.609
case=s2_123_size_biased_deletion family=size_biased_deletion normalized=0.965712988 trench=88080 bound=85060 cpu_s=0.115591 rss_mib=2.250
case=s2_124_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=100 bound=100 cpu_s=0.162380 rss_mib=2.188
case=s2_125_size_biased_deletion family=size_biased_deletion normalized=0.808264463 trench=24200 bound=19560 cpu_s=0.394368 rss_mib=2.781
case=s2_126_size_biased_deletion family=size_biased_deletion normalized=0.891704845 trench=205180 bound=182960 cpu_s=0.744664 rss_mib=4.625
case=s2_127_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=1440 bound=1440 cpu_s=0.611100 rss_mib=4.141
case=s2_128_size_biased_deletion family=size_biased_deletion normalized=0.907087148 trench=58980 bound=53500 cpu_s=1.219364 rss_mib=5.719


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

Here are the performance metrics of the program:

Combined score to maximize: 0.96
valid_cases: 128; family_count: 16; worst_family_score: 0.91; mean_raw_kpi: 0.56; max_solver_cpu_seconds: 1.54; max_solver_rss_mib: 9.94

Here is additional text feedback about the current program:

case=s2_001_uniform_churn family=uniform_churn normalized=0.860465116 trench=860 bound=740 cpu_s=0.051422 rss_mib=1.609
case=s2_002_uniform_churn family=uniform_churn normalized=0.959507042 trench=11360 bound=10900 cpu_s=0.095260 rss_mib=1.781
case=s2_003_uniform_churn family=uniform_churn normalized=0.977227838 trench=172140 bound=168220 cpu_s=0.188606 rss_mib=2.781
case=s2_004_uniform_churn family=uniform_churn normalized=1.000000000 trench=1320 bound=1320 cpu_s=0.239467 rss_mib=2.734
case=s2_005_uniform_churn family=uniform_churn normalized=0.969121140 trench=33680 bound=32640 cpu_s=0.492942 rss_mib=3.922
case=s2_006_uniform_churn family=uniform_churn normalized=0.985165284 trench=342440 bound=337360 cpu_s=0.700384 rss_mib=4.734
case=s2_007_uniform_churn family=uniform_churn normalized=0.972727273 trench=4400 bound=4280 cpu_s=0.759544 rss_mib=4.094
case=s2_008_uniform_churn family=uniform_churn normalized=0.958481350 trench=90080 bound=86340 cpu_s=1.366320 rss_mib=4.453
case=s2_009_short_heavy family=short_heavy normalized=0.870370370 trench=1080 bound=940 cpu_s=0.088588 rss_mib=1.781
case=s2_010_short_heavy family=short_heavy normalized=0.993911720 trench=13140 bound=13060 cpu_s=0.160653 rss_mib=2.219
case=s2_011_short_heavy family=short_heavy normalized=0.980644138 trench=126060 bound=123620 cpu_s=0.291713 rss_mib=3.828
case=s2_012_short_heavy family=short_heavy normalized=0.753846154 trench=1300 bound=980 cpu_s=0.439307 rss_mib=3.828
case=s2_013_short_heavy family=short_heavy normalized=0.988223246 trench=39060 bound=38600 cpu_s=0.606074 rss_mib=3.906
case=s2_014_short_heavy family=short_heavy normalized=0.818181818 trench=440 bound=360 cpu_s=0.801476 rss_mib=4.938
case=s2_015_short_heavy family=short_heavy normalized=0.987179487 trench=3120 bound=3080 cpu_s=1.028334 rss_mib=5.188
case=s2_016_short_heavy family=short_heavy normalized=0.972431078 trench=7980 bound=7760 cpu_s=0.048009 rss_mib=1.719
case=s2_017_long_heavy family=long_heavy normalized=0.906896552 trench=5800 bound=5260 cpu_s=0.190591 rss_mib=2.141
case=s2_018_long_heavy family=long_heavy normalized=1.000000000 trench=120420 bound=120420 cpu_s=0.303059 rss_mib=2.094
case=s2_019_long_heavy family=long_heavy normalized=0.854545455 trench=1100 bound=940 cpu_s=0.499591 rss_mib=2.906
case=s2_020_long_heavy family=long_heavy normalized=0.958291956 trench=20140 bound=19300 cpu_s=0.696758 rss_mib=3.078
case=s2_021_long_heavy family=long_heavy normalized=1.000000000 trench=227240 bound=227240 cpu_s=0.821009 rss_mib=4.484
case=s2_022_long_heavy family=long_heavy normalized=0.890625000 trench=2560 bound=2280 cpu_s=1.315416 rss_mib=4.062
case=s2_023_long_heavy family=long_heavy normalized=0.978384125 trench=56440 bound=55220 cpu_s=0.053371 rss_mib=1.797
case=s2_024_long_heavy family=long_heavy normalized=0.996389892 trench=138500 bound=138000 cpu_s=0.101383 rss_mib=2.109
case=s2_025_bimodal family=bimodal normalized=0.954177898 trench=14840 bound=14160 cpu_s=0.312531 rss_mib=2.422
case=s2_026_bimodal family=bimodal normalized=0.963412209 trench=201160 bound=193800 cpu_s=0.553365 rss_mib=3.438
case=s2_027_bimodal family=bimodal normalized=0.955882353 trench=1360 bound=1300 cpu_s=0.564415 rss_mib=3.250
case=s2_028_bimodal family=bimodal normalized=0.948995363 trench=25880 bound=24560 cpu_s=0.912650 rss_mib=4.609
case=s2_029_bimodal family=bimodal normalized=1.000000000 trench=153500 bound=153500 cpu_s=1.090731 rss_mib=4.984
case=s2_030_bimodal family=bimodal normalized=0.940928270 trench=4740 bound=4460 cpu_s=0.047591 rss_mib=1.594
case=s2_031_bimodal family=bimodal normalized=0.977777778 trench=73800 bound=72160 cpu_s=0.090039 rss_mib=2.078
case=s2_032_bimodal family=bimodal normalized=1.000000000 trench=660 bound=660 cpu_s=0.165184 rss_mib=2.062
case=s2_033_section_boundaries family=section_boundaries normalized=0.949476278 trench=32460 bound=30820 cpu_s=0.455690 rss_mib=3.641
case=s2_034_section_boundaries family=section_boundaries normalized=0.990884504 trench=399320 bound=395680 cpu_s=0.661109 rss_mib=3.938
case=s2_035_section_boundaries family=section_boundaries normalized=0.985576923 trench=4160 bound=4100 cpu_s=0.743201 rss_mib=5.219
case=s2_036_section_boundaries family=section_boundaries normalized=0.939393939 trench=75240 bound=70680 cpu_s=1.366782 rss_mib=4.547
case=s2_037_section_boundaries family=section_boundaries normalized=0.851063830 trench=940 bound=800 cpu_s=0.043418 rss_mib=1.578
case=s2_038_section_boundaries family=section_boundaries normalized=0.992141454 trench=10180 bound=10100 cpu_s=0.083103 rss_mib=1.781
case=s2_039_section_boundaries family=section_boundaries normalized=0.992256527 trench=201460 bound=199900 cpu_s=0.179134 rss_mib=2.703
case=s2_040_section_boundaries family=section_boundaries normalized=1.000000000 trench=1260 bound=1260 cpu_s=0.244797 rss_mib=2.656
case=s2_041_fifo family=fifo normalized=0.999520384 trench=83400 bound=83360 cpu_s=0.624756 rss_mib=2.984
case=s2_042_fifo family=fifo normalized=0.893617021 trench=940 bound=840 cpu_s=0.814123 rss_mib=5.391
case=s2_043_fifo family=fifo normalized=0.996078431 trench=10200 bound=10160 cpu_s=0.977361 rss_mib=5.203
case=s2_044_fifo family=fifo normalized=0.984575835 trench=7780 bound=7660 cpu_s=0.045464 rss_mib=1.719
case=s2_045_fifo family=fifo normalized=0.912280702 trench=2280 bound=2080 cpu_s=0.091121 rss_mib=1.781
case=s2_046_fifo family=fifo normalized=1.000000000 trench=31320 bound=31320 cpu_s=0.174083 rss_mib=2.047
case=s2_047_fifo family=fifo normalized=0.988595257 trench=398080 bound=393540 cpu_s=0.292936 rss_mib=3.172
case=s2_048_fifo family=fifo normalized=0.933333333 trench=6000 bound=5600 cpu_s=0.483443 rss_mib=2.781
case=s2_049_lifo family=lifo normalized=1.000000000 trench=169280 bound=169280 cpu_s=0.742001 rss_mib=4.688
case=s2_050_lifo family=lifo normalized=1.000000000 trench=1840 bound=1840 cpu_s=1.010536 rss_mib=4.312
case=s2_051_lifo family=lifo normalized=1.000000000 trench=30920 bound=30920 cpu_s=0.044380 rss_mib=1.703
case=s2_052_lifo family=lifo normalized=1.000000000 trench=14540 bound=14540 cpu_s=0.080612 rss_mib=2.000
case=s2_053_lifo family=lifo normalized=1.000000000 trench=5700 bound=5700 cpu_s=0.167154 rss_mib=2.047
case=s2_054_lifo family=lifo normalized=1.000000000 trench=83540 bound=83540 cpu_s=0.250115 rss_mib=2.312
case=s2_055_lifo family=lifo normalized=1.000000000 trench=800 bound=800 cpu_s=0.386214 rss_mib=3.297
case=s2_056_lifo family=lifo normalized=1.000000000 trench=12920 bound=12920 cpu_s=0.589130 rss_mib=2.859
case=s2_057_size_lifetimes family=size_lifetimes normalized=0.976653696 trench=61680 bound=60240 cpu_s=1.527522 rss_mib=4.391
case=s2_058_size_lifetimes family=size_lifetimes normalized=0.888888889 trench=900 bound=800 cpu_s=0.046063 rss_mib=1.594
case=s2_059_size_lifetimes family=size_lifetimes normalized=0.971181556 trench=41640 bound=40440 cpu_s=0.123426 rss_mib=1.875
case=s2_060_size_lifetimes family=size_lifetimes normalized=0.923076923 trench=260 bound=240 cpu_s=0.177929 rss_mib=1.844
case=s2_061_size_lifetimes family=size_lifetimes normalized=0.929347826 trench=3680 bound=3420 cpu_s=0.292570 rss_mib=2.734
case=s2_062_size_lifetimes family=size_lifetimes normalized=0.970691164 trench=137160 bound=133140 cpu_s=0.516726 rss_mib=3.438
case=s2_063_size_lifetimes family=size_lifetimes normalized=0.958139535 trench=4300 bound=4120 cpu_s=0.650282 rss_mib=2.812
case=s2_064_size_lifetimes family=size_lifetimes normalized=0.908653846 trench=4160 bound=3780 cpu_s=0.884945 rss_mib=4.859
case=s2_065_burst_drain family=burst_drain normalized=0.918918919 trench=740 bound=680 cpu_s=0.042817 rss_mib=1.578
case=s2_066_burst_drain family=burst_drain normalized=0.977941176 trench=13600 bound=13300 cpu_s=0.091517 rss_mib=1.766
case=s2_067_burst_drain family=burst_drain normalized=0.997900813 trench=152440 bound=152120 cpu_s=0.188140 rss_mib=2.891
case=s2_068_burst_drain family=burst_drain normalized=1.000000000 trench=440 bound=440 cpu_s=0.295638 rss_mib=2.016
case=s2_069_burst_drain family=burst_drain normalized=0.986484795 trench=159820 bound=157660 cpu_s=0.567817 rss_mib=3.500
case=s2_070_burst_drain family=burst_drain normalized=0.999863496 trench=732580 bound=732480 cpu_s=0.745079 rss_mib=6.188
case=s2_071_burst_drain family=burst_drain normalized=0.995918367 trench=4900 bound=4880 cpu_s=0.860830 rss_mib=4.359
case=s2_072_burst_drain family=burst_drain normalized=1.000000000 trench=168720 bound=168720 cpu_s=1.163624 rss_mib=4.391
case=s2_073_distribution_switch family=distribution_switch normalized=0.992366412 trench=2620 bound=2600 cpu_s=0.089946 rss_mib=1.781
case=s2_074_distribution_switch family=distribution_switch normalized=1.000000000 trench=33080 bound=33080 cpu_s=0.170075 rss_mib=2.062
case=s2_075_distribution_switch family=distribution_switch normalized=1.000000000 trench=255620 bound=255620 cpu_s=0.347693 rss_mib=2.719
case=s2_076_distribution_switch family=distribution_switch normalized=0.993827160 trench=6480 bound=6440 cpu_s=0.470291 rss_mib=3.141
case=s2_077_distribution_switch family=distribution_switch normalized=0.945683248 trench=69960 bound=66160 cpu_s=0.646739 rss_mib=2.828
case=s2_078_distribution_switch family=distribution_switch normalized=0.928571429 trench=1400 bound=1300 cpu_s=0.938626 rss_mib=4.094
case=s2_079_distribution_switch family=distribution_switch normalized=1.000000000 trench=8420 bound=8420 cpu_s=1.014687 rss_mib=5.078
case=s2_080_distribution_switch family=distribution_switch normalized=0.874403232 trench=54460 bound=47620 cpu_s=0.047317 rss_mib=1.812
case=s2_081_drifting_sizes family=drifting_sizes normalized=0.847972973 trench=5920 bound=5020 cpu_s=0.182410 rss_mib=2.156
case=s2_082_drifting_sizes family=drifting_sizes normalized=1.000000000 trench=106700 bound=106700 cpu_s=0.251441 rss_mib=2.828
case=s2_083_drifting_sizes family=drifting_sizes normalized=0.803278689 trench=1220 bound=980 cpu_s=0.440926 rss_mib=3.031
case=s2_084_drifting_sizes family=drifting_sizes normalized=0.922048998 trench=17960 bound=16560 cpu_s=0.703936 rss_mib=3.719
case=s2_085_drifting_sizes family=drifting_sizes normalized=0.996851919 trench=165180 bound=164660 cpu_s=0.770776 rss_mib=5.531
case=s2_086_drifting_sizes family=drifting_sizes normalized=0.771084337 trench=3320 bound=2560 cpu_s=1.196893 rss_mib=4.203
case=s2_087_drifting_sizes family=drifting_sizes normalized=0.930577636 trench=37740 bound=35120 cpu_s=0.056697 rss_mib=1.812
case=s2_088_drifting_sizes family=drifting_sizes normalized=0.968415008 trench=104480 bound=101180 cpu_s=0.105499 rss_mib=2.109
case=s2_089_striped_recycling family=striped_recycling normalized=0.996283515 trench=150680 bound=150120 cpu_s=0.333773 rss_mib=2.719
case=s2_090_striped_recycling family=striped_recycling normalized=1.000000000 trench=775400 bound=775400 cpu_s=0.477765 rss_mib=3.844
case=s2_091_striped_recycling family=striped_recycling normalized=0.997400022 trench=1069240 bound=1066460 cpu_s=0.731795 rss_mib=5.391
case=s2_092_striped_recycling family=striped_recycling normalized=1.000000000 trench=2034140 bound=2034140 cpu_s=0.785209 rss_mib=6.812
case=s2_093_striped_recycling family=striped_recycling normalized=1.000000000 trench=2845400 bound=2845400 cpu_s=1.075514 rss_mib=9.938
case=s2_094_striped_recycling family=striped_recycling normalized=0.991590214 trench=78480 bound=77820 cpu_s=0.053258 rss_mib=1.781
case=s2_095_striped_recycling family=striped_recycling normalized=1.000000000 trench=236280 bound=236280 cpu_s=0.088442 rss_mib=2.188
case=s2_096_striped_recycling family=striped_recycling normalized=1.000000000 trench=486200 bound=486200 cpu_s=0.175674 rss_mib=2.172
case=s2_097_geometric_cohorts family=geometric_cohorts normalized=0.983852364 trench=17340 bound=17060 cpu_s=0.508222 rss_mib=2.641
case=s2_098_geometric_cohorts family=geometric_cohorts normalized=0.991116473 trench=182360 bound=180740 cpu_s=0.717003 rss_mib=2.859
case=s2_099_geometric_cohorts family=geometric_cohorts normalized=0.738805970 trench=2680 bound=1980 cpu_s=0.734030 rss_mib=5.047
case=s2_100_geometric_cohorts family=geometric_cohorts normalized=0.956828885 trench=50960 bound=48760 cpu_s=1.260523 rss_mib=4.500
case=s2_101_geometric_cohorts family=geometric_cohorts normalized=0.909090909 trench=880 bound=800 cpu_s=0.042287 rss_mib=1.594
case=s2_102_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=10780 bound=10780 cpu_s=0.082079 rss_mib=1.812
case=s2_103_geometric_cohorts family=geometric_cohorts normalized=0.908130763 trench=119300 bound=108340 cpu_s=0.202019 rss_mib=2.859
case=s2_104_geometric_cohorts family=geometric_cohorts normalized=1.000000000 trench=320 bound=320 cpu_s=0.233882 rss_mib=2.734
case=s2_105_additive_cohorts family=additive_cohorts normalized=0.974831042 trench=85820 bound=83660 cpu_s=0.614991 rss_mib=3.812
case=s2_106_additive_cohorts family=additive_cohorts normalized=0.907407407 trench=1080 bound=980 cpu_s=0.804584 rss_mib=4.594
case=s2_107_additive_cohorts family=additive_cohorts normalized=0.994729908 trench=15180 bound=15100 cpu_s=1.001216 rss_mib=5.312
case=s2_108_additive_cohorts family=additive_cohorts normalized=0.989470220 trench=60780 bound=60140 cpu_s=0.051219 rss_mib=1.812
case=s2_109_additive_cohorts family=additive_cohorts normalized=0.860927152 trench=3020 bound=2600 cpu_s=0.085492 rss_mib=1.781
case=s2_110_additive_cohorts family=additive_cohorts normalized=1.000000000 trench=27240 bound=27240 cpu_s=0.160617 rss_mib=2.234
case=s2_111_additive_cohorts family=additive_cohorts normalized=0.899090909 trench=506000 bound=454940 cpu_s=0.326802 rss_mib=4.266
case=s2_112_additive_cohorts family=additive_cohorts normalized=0.932367150 trench=8280 bound=7720 cpu_s=0.429973 rss_mib=3.547
case=s2_113_large_live_set family=large_live_set normalized=0.962863535 trench=44700 bound=43040 cpu_s=0.496877 rss_mib=3.688
case=s2_114_large_live_set family=large_live_set normalized=0.969972702 trench=87920 bound=85280 cpu_s=0.659654 rss_mib=3.609
case=s2_115_large_live_set family=large_live_set normalized=0.980784720 trench=173820 bound=170480 cpu_s=0.803539 rss_mib=3.984
case=s2_116_large_live_set family=large_live_set normalized=0.981066583 trench=253520 bound=248720 cpu_s=0.914191 rss_mib=4.875
case=s2_117_large_live_set family=large_live_set normalized=0.983687737 trench=343300 bound=337700 cpu_s=1.089844 rss_mib=5.156
case=s2_118_large_live_set family=large_live_set normalized=0.986122189 trench=501520 bound=494560 cpu_s=1.362886 rss_mib=6.016
case=s2_119_large_live_set family=large_live_set normalized=0.987619187 trench=681700 bound=673260 cpu_s=1.537073 rss_mib=5.656
case=s2_120_large_live_set family=large_live_set normalized=0.988173906 trench=935220 bound=924160 cpu_s=1.351550 rss_mib=4.703
case=s2_121_size_biased_deletion family=size_biased_deletion normalized=0.999761763 trench=335800 bound=335720 cpu_s=1.005921 rss_mib=6.297
case=s2_122_size_biased_deletion family=size_biased_deletion normalized=0.924157303 trench=7120 bound=6580 cpu_s=0.047623 rss_mib=1.594
case=s2_123_size_biased_deletion family=size_biased_deletion normalized=0.960478771 trench=88560 bound=85060 cpu_s=0.094448 rss_mib=2.188
case=s2_124_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=100 bound=100 cpu_s=0.152705 rss_mib=2.156
case=s2_125_size_biased_deletion family=size_biased_deletion normalized=0.815000000 trench=24000 bound=19560 cpu_s=0.348602 rss_mib=2.391
case=s2_126_size_biased_deletion family=size_biased_deletion normalized=0.896247673 trench=204140 bound=182960 cpu_s=0.588271 rss_mib=4.391
case=s2_127_size_biased_deletion family=size_biased_deletion normalized=1.000000000 trench=1440 bound=1440 cpu_s=0.536863 rss_mib=4.172
case=s2_128_size_biased_deletion family=size_biased_deletion normalized=0.901888065 trench=59320 bound=53500 cpu_s=1.014224 rss_mib=5.703


# Instructions

Make sure that the changes you propose are consistent with each other. For example, if you refer to a new config variable somewhere, you should also propose a change to add that variable.

Note that the changes you propose will be applied sequentially, so you should assume that the previous changes have already been applied when writing the SEARCH block.

# Task

Suggest a new idea to improve the performance of the code that is inspired by your expert knowledge of the considered subject.
Your goal is to maximize the `combined_score` of the program.
Describe each change with a SEARCH/REPLACE block.

IMPORTANT: Do not rewrite the entire program - focus on targeted improvements.
