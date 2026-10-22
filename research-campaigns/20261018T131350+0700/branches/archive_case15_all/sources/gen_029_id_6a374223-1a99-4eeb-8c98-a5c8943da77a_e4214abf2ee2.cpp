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
/*
NAME: interior_pair_growth_regret
DESCRIPTION:
Базовая политика tail_growth_regret сохранена в chooseBaseFit().
Её выбор хвоста и точное заполнение выбранного интервала сохраняются.
Для неполного заполнения внутреннего интервала дополнительно проверяется
первый внутренний интервал строго большей длины.
Выбирается вариант с меньшей оптимистичной оценкой роста для двух
независимых вставок из requestMass_ с равномерным prior.
Модель использует два наибольших внутренних интервала после размещения
и свободный хвост. Равенства сохраняют базовый выбор.
Возможный недостаток: прогноз игнорирует удаления, зависимости запросов
и ограничения последовательного выбора мест для гипотетической пары.
Сложность команды: O(40 + log(H + 1)), память: O(Q).
Прогноз выполняет не более 320 итераций по длинам на вставку,
дополнительная временная память — O(40).
Ablation: chooseFit() сразу возвращает chooseBaseFit(length).
*/
class Allocator {
    struct Node {
        int start;
        int length;
        int previous;
        int next;
        int pid;
    };
    struct FreeKey {
        int length;
        int start;
        int node;
    };
    struct FreeOrder {
        bool operator()(const FreeKey& a, const FreeKey& b) const {
            if (a.length != b.length) return a.length < b.length;
            if (a.start != b.start) return a.start < b.start;
            return a.node < b.node;
        }
    };
    // Node 0 is the sentinel of the physical interval list.
    std::vector<Node> nodes_;
    std::vector<int> pidNode_;
    std::set<FreeKey, FreeOrder> freeBySize_;
    std::array<int, 41> liveByLength_{};
    std::array<double, 41> requestMass_{};
    std::array<double, 41> exposure_{};
    std::array<double, 41> deaths_{};
    int liveCount_ = 0;
    int trenchLength_ = 0;
    double totalExposure_ = 0.0;
    double totalDeaths_ = 0.0;
    void advanceHistory() {
        // Effective history length is approximately 4000 commands.
        constexpr double decay = 0.99975;
        for (int length = 1; length <= 40; ++length) {
            requestMass_[length] *= decay;
            exposure_[length] =
                decay * exposure_[length] + liveByLength_[length];
            deaths_[length] *= decay;
        }
        totalExposure_ = decay * totalExposure_ + liveCount_;
        totalDeaths_ *= decay;
    }
    int linkBetween(int previous, int next, int start, int length, int pid) {
        const int id = static_cast<int>(nodes_.size());
        nodes_.push_back(Node{start, length, previous, next, pid});
        nodes_[previous].next = id;
        nodes_[next].previous = id;
        return id;
    }
    void indexFree(int id) {
        freeBySize_.insert(
            FreeKey{nodes_[id].length, nodes_[id].start, id});
    }
    void unindexFree(int id) {
        freeBySize_.erase(
            FreeKey{nodes_[id].length, nodes_[id].start, id});
    }
    auto chooseBaseFit(int length) const {
        const auto fit =
            freeBySize_.lower_bound(FreeKey{length, -1, -1});
        if (fit == freeBySize_.end() ||
            fit->node != nodes_[0].previous) {
            return fit;
        }
        // There is only one physical tail, so the next fit is internal.
        const auto interior = std::next(fit);
        if (interior == freeBySize_.end()) return fit;
        int otherMaximum = 0;
        for (auto it = freeBySize_.rbegin();
             it != freeBySize_.rend(); ++it) {
            if (it->node != fit->node && it->node != interior->node) {
                otherMaximum = it->length;
                break;
            }
        }
        const int tailLength = fit->length;
        const int tailAfter = tailLength - length;
        const int bestMaximum =
            std::max(otherMaximum, interior->length);
        // Best fit already accommodates every possible next length.
        if (bestMaximum >= 40) return fit;
        const int interiorMaximum = std::max(
            std::max(otherMaximum, tailLength),
            interior->length - length);
        double advantage = 0.0;
        for (int request = 1; request <= 40; ++request) {
            const int bestGrowth = request <= bestMaximum
                ? 0 : (request - tailAfter + 19) / 20;
            const int interiorGrowth = request <= interiorMaximum
                ? 0 : (request - tailLength + 19) / 20;
            advantage += (1.0 + requestMass_[request]) *
                         (bestGrowth - interiorGrowth);
        }
        return advantage > 0.0 ? interior : fit;
    }
    auto chooseFit(int length) const {
        const auto base = chooseBaseFit(length);
        const int tail = nodes_[0].previous;
        if (base == freeBySize_.end() || base->node == tail ||
            base->length == length) {
            return base;
        }
        constexpr int maximumKey = std::numeric_limits<int>::max();
        auto alternative = freeBySize_.upper_bound(
            FreeKey{base->length, maximumKey, maximumKey});
        if (alternative != freeBySize_.end() &&
            alternative->node == tail) {
            ++alternative;
        }
        if (alternative == freeBySize_.end()) return base;
        std::array<double, 41> probability{};
        std::array<double, 41> prefix{};
        double mass = 0.0;
        for (int request = 1; request <= 40; ++request) {
            mass += 1.0 + requestMass_[request];
        }
        for (int request = 1; request <= 40; ++request) {
            probability[request] =
                (1.0 + requestMass_[request]) / mass;
            prefix[request] =
                prefix[request - 1] + probability[request];
        }
        const int tailLength =
            tail != 0 && nodes_[tail].pid == 0 ? nodes_[tail].length : 0;
        const auto expectedGrowth = [&](int hole) {
            int first = 0;
            int second = 0;
            const auto addGap = [&](int gap) {
                if (gap >= first) {
                    second = first;
                    first = gap;
                } else {
                    second = std::max(second, gap);
                }
            };
            // Removing the candidate and tail skips at most two entries.
            int kept = 0;
            for (auto it = freeBySize_.rbegin();
                 it != freeBySize_.rend() && kept < 2; ++it) {
                if (it->node == hole || it->node == tail) continue;
                addGap(it->length);
                ++kept;
            }
            addGap(nodes_[hole].length - length);
            double growth = 0.0;
            for (int sections = 0; sections < 4; ++sections) {
                const int expandedTail = tailLength + 20 * sections;
                const int largest = std::max(first, expandedTail);
                const int runnerUp =
                    std::max(second, std::min(first, expandedTail));
                if (largest >= 80 ||
                    (largest >= 40 && runnerUp >= 40)) {
                    break;
                }
                double fits = 0.0;
                for (int request = 1;
                     request <= std::min(40, largest); ++request) {
                    // Both requests share one gap, or use separate gaps.
                    const int sharedLimit = largest - request;
                    const int separateLimit =
                        request <= runnerUp ? largest : runnerUp;
                    const int limit = std::min(
                        40, std::max(sharedLimit, separateLimit));
                    fits += probability[request] * prefix[limit];
                }
                // E[K] = sum over k=0..3 of P(K > k), since K <= 4.
                growth += std::max(0.0, 1.0 - fits);
            }
            return growth;
        };
        constexpr double tolerance = 1e-12;
        const double baseGrowth = expectedGrowth(base->node);
        if (baseGrowth <= tolerance) return base;
        const double alternativeGrowth = expectedGrowth(alternative->node);
        return alternativeGrowth + tolerance < baseGrowth
            ? alternative : base;
    }
    bool preferRight(int hole) const {
        const int left = nodes_[hole].previous;
        const int right = nodes_[hole].next;
        // Boundary holes are filled from their left edge.
        if (left == 0 || right == 0 || totalDeaths_ < 12.0) {
            return false;
        }
        if (nodes_[left].pid <= 0 || nodes_[right].pid <= 0) {
            return false;
        }
        const int leftLength = nodes_[left].length;
        const int rightLength = nodes_[right].length;
        if (leftLength == rightLength) return false;
        // Three pseudo-events shrink each estimate toward the global rate.
        constexpr double priorEvents = 3.0;
        const double priorExposure =
            priorEvents * (totalExposure_ + 1.0) / (totalDeaths_ + 1.0);
        const double leftNumerator = deaths_[leftLength] + priorEvents;
        const double rightNumerator = deaths_[rightLength] + priorEvents;
        const double leftDenominator = exposure_[leftLength] + priorExposure;
        const double rightDenominator = exposure_[rightLength] + priorExposure;
        // Place against the right neighbor when the left neighbor has a
        // sufficiently higher estimated deletion rate.
        return leftNumerator * rightDenominator >
               1.25 * rightNumerator * leftDenominator;
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        nodes_.reserve(400001);
        pidNode_.reserve(200001);
        nodes_.push_back(Node{0, 0, 0, 0, -1});
        pidNode_.push_back(0);
    }
    void place(int length) {
        advanceHistory();
        requestMass_[length] += 1.0;
        int sections = 0;
        int hole = 0;
        const auto fit = chooseFit(length);
        if (fit != freeBySize_.end()) {
            hole = fit->node;
            freeBySize_.erase(fit);
        } else {
            const int tail = nodes_[0].previous;
            const bool freeTail = tail != 0 && nodes_[tail].pid == 0;
            const int available = freeTail ? nodes_[tail].length : 0;
            sections = (length - available + 19) / 20;
            const int added = sections * 20;
            if (freeTail) {
                unindexFree(tail);
                nodes_[tail].length += added;
                hole = tail;
            } else {
                hole = linkBetween(tail, 0, trenchLength_, added, 0);
            }
            trenchLength_ += added;
        }
        const int pid = static_cast<int>(pidNode_.size());
        const int originalStart = nodes_[hole].start;
        const int remainder = nodes_[hole].length - length;
        const int previous = nodes_[hole].previous;
        const int next = nodes_[hole].next;
        const bool fromRight = remainder > 0 && preferRight(hole);
        nodes_[hole].pid = pid;
        nodes_[hole].length = length;
        if (fromRight) {
            nodes_[hole].start = originalStart + remainder;
            const int freeNode =
                linkBetween(previous, hole, originalStart, remainder, 0);
            indexFree(freeNode);
        } else if (remainder > 0) {
            const int freeNode =
                linkBetween(hole, next, originalStart + length, remainder, 0);
            indexFree(freeNode);
        }
        pidNode_.push_back(hole);
        ++liveByLength_[length];
        ++liveCount_;
        std::cout << sections << ' ' << nodes_[hole].start
                  << '\n' << std::flush;
    }
    void remove(std::int64_t pid) {
        advanceHistory();
        const std::size_t ordinal = static_cast<std::size_t>(pid);
        const int id = pidNode_[ordinal];
        const int originalStart = nodes_[id].start;
        const int length = nodes_[id].length;
        deaths_[length] += 1.0;
        totalDeaths_ += 1.0;
        --liveByLength_[length];
        --liveCount_;
        pidNode_[ordinal] = 0;
        nodes_[id].pid = 0;
        const int left = nodes_[id].previous;
        if (left != 0 && nodes_[left].pid == 0) {
            unindexFree(left);
            const int previous = nodes_[left].previous;
            nodes_[id].start = nodes_[left].start;
            nodes_[id].length += nodes_[left].length;
            nodes_[id].previous = previous;
            nodes_[previous].next = id;
        }
        const int right = nodes_[id].next;
        if (right != 0 && nodes_[right].pid == 0) {
            unindexFree(right);
            const int next = nodes_[right].next;
            nodes_[id].length += nodes_[right].length;
            nodes_[id].next = next;
            nodes_[next].previous = id;
        }
        indexFree(id);
        std::cout << originalStart << '\n' << std::flush;
    }
};
}
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