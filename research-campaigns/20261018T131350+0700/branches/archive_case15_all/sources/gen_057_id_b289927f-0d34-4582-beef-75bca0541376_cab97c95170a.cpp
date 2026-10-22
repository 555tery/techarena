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
// NAME: shift_triggered_demand_blend
// DESCRIPTION: Demand-Weighted Residual Fit с детектором смены спроса.
//
// Каждые 16 вставок сравниваются распределения последних 64 вставок
// и накопленных наблюдений. При TV > 1/4 используется их равная смесь
// с прежней эффективной массой наблюдений и равномерным prior +1.
// Дробные веса представлены целыми числителями с общим знаменателем.
//
// Для интервала s и запроса L оценивается дополнительная потеря вместимости:
// R(s,L) = sum_k w[k]*k*(floor(s/k)-floor((s-L)/k)-floor(L/k)).
// Минимизируется 8*R(s,L) + sum(w)*min(s-L,40);
// при равенстве выбирается меньший интервал, затем меньшая координата.
// Для размеров <80 рассматриваются все непустые bins. Для больших дыр
// оценивается левейшая дыра каждого из первых восьми различных размеров.
// Свободный хвост используется после внутренних дыр.
//
// Вставка: амортизированно O(80 + 8*40 + 9*log H + 40*80/16).
// Удаление: O(log H). Память: O(P + H + 64 + 40).
// Возможный недостаток: ложный сигнал смены спроса и задержка окна
// на коротких фазах; корреляция удалений по-прежнему не моделируется.
// Ablation: kEnableShiftBlend = false восстанавливает решения родителя.
namespace {
class Allocator {
    static constexpr int kMaxLength = 40;
    static constexpr int kSmallLimit = 80;
    static constexpr std::int64_t kRegretScale = 8;
    struct Pipe {
        int start;
        int length;
    };
    using HoleMap = std::map<int, int>;
    std::vector<Pipe> pipes_;
    HoleMap holes_;
    std::array<std::set<int>, kSmallLimit> bins_;
    std::set<std::pair<int, int>> large_;
    std::uint64_t lowMask_ = 0;
    std::uint64_t highMask_ = 0;
    int trench_ = 0;
    int frontier_ = 0;
    std::size_t insertions_ = 0;
    static constexpr bool kEnableShiftBlend = true;
    std::array<std::uint8_t, 64> recentLengths_{};
    std::array<std::uint32_t, kMaxLength + 1> recentObservations_{};
    bool shiftedProfile_ = false;
    std::array<std::uint32_t, kMaxLength + 1> observations_{};
    std::array<std::uint32_t, kMaxLength + 1> weights_{};
    std::array<std::int64_t, kSmallLimit> waste_{};
    std::int64_t totalWeight_ = 0;
    void rebuildProfile() {
        const std::uint32_t recentCount = static_cast<std::uint32_t>(
            std::min(insertions_, recentLengths_.size()));
        std::uint32_t observationCount = 0;
        if (shiftedProfile_) {
            for (int k = 1; k <= kMaxLength; ++k) {
                observationCount += observations_[k];
            }
        }
        waste_.fill(0);
        totalWeight_ = 0;
        for (int k = 1; k <= kMaxLength; ++k) {
            if (shiftedProfile_) {
                // 2*recentCount times the effective weight:
                // 1 + (observations[k] + N*recent[k]/recentCount)/2.
                weights_[k] =
                    recentCount * (observations_[k] + 2u)
                    + observationCount * recentObservations_[k];
            } else {
                weights_[k] = observations_[k] + 1;
            }
            const std::int64_t weight = weights_[k];
            totalWeight_ += weight;
            int remainder = 0;
            for (int s = 0; s < kSmallLimit; ++s) {
                waste_[s] += weight * remainder;
                if (++remainder == k) {
                    remainder = 0;
                }
            }
        }
    }
    void observe(int length) {
        const std::size_t slot = insertions_ & 63u;
        if (insertions_ >= recentLengths_.size()) {
            --recentObservations_[recentLengths_[slot]];
        }
        recentLengths_[slot] = static_cast<std::uint8_t>(length);
        ++recentObservations_[length];
        ++insertions_;
        ++observations_[length];
        if ((insertions_ & 511u) == 0) {
            for (int k = 1; k <= kMaxLength; ++k) {
                observations_[k] >>= 1;
            }
        }
        bool refreshProfile =
            insertions_ <= 32 || (insertions_ & 63u) == 0;
        if (kEnableShiftBlend && (insertions_ & 15u) == 0) {
            const std::uint64_t recentCount =
                std::min(insertions_, recentLengths_.size());
            std::uint64_t observationCount = 0;
            for (int k = 1; k <= kMaxLength; ++k) {
                observationCount += observations_[k];
            }
            std::uint64_t difference = 0;
            for (int k = 1; k <= kMaxLength; ++k) {
                const std::uint64_t recent =
                    recentObservations_[k] * observationCount;
                const std::uint64_t accumulated =
                    observations_[k] * recentCount;
                difference += recent >= accumulated
                    ? recent - accumulated : accumulated - recent;
            }
            // TV = difference / (2*recentCount*observationCount).
            const bool shifted =
                2 * difference > recentCount * observationCount;
            refreshProfile = refreshProfile || shifted
                || shifted != shiftedProfile_;
            shiftedProfile_ = shifted;
        }
        if (refreshProfile) {
            rebuildProfile();
        }
    }
    void addHole(int start, int length) {
        if (length == 0) {
            return;
        }
        holes_.emplace(start, length);
        if (length < kSmallLimit) {
            bins_[length].insert(start);
            if (length < 64) {
                lowMask_ |= std::uint64_t{1} << length;
            } else {
                highMask_ |= std::uint64_t{1} << (length - 64);
            }
        } else {
            large_.emplace(length, start);
        }
    }
    void eraseHole(HoleMap::iterator it) {
        const int start = it->first;
        const int length = it->second;
        if (length < kSmallLimit) {
            auto& bin = bins_[length];
            bin.erase(start);
            if (bin.empty()) {
                if (length < 64) {
                    lowMask_ &= ~(std::uint64_t{1} << length);
                } else {
                    highMask_ &= ~(std::uint64_t{1} << (length - 64));
                }
            }
        } else {
            large_.erase(std::make_pair(length, start));
        }
        holes_.erase(it);
    }
    std::pair<int, int> chooseHole(int length) const {
        if (!bins_[length].empty()) {
            return {*bins_[length].begin(), length};
        }
        int bestStart = -1;
        int bestSize = 0;
        std::int64_t bestScore =
            std::numeric_limits<std::int64_t>::max();
        const auto consider = [&](int size) {
            const int residual = size - length;
            const std::int64_t regret =
                waste_[residual] + waste_[length] - waste_[size];
            const std::int64_t score =
                kRegretScale * regret
                + totalWeight_ * std::min(residual, kMaxLength);
            if (score < bestScore ||
                (score == bestScore && size < bestSize)) {
                bestScore = score;
                bestSize = size;
                bestStart = *bins_[size].begin();
            }
        };
        std::uint64_t mask =
            lowMask_ & (~std::uint64_t{0} << length);
        while (mask != 0) {
            const int size = std::countr_zero(mask);
            mask &= mask - 1;
            consider(size);
        }
        mask = highMask_;
        while (mask != 0) {
            const int size = 64 + std::countr_zero(mask);
            mask &= mask - 1;
            consider(size);
        }
        if (!large_.empty()) {
            constexpr int kLargeProbes = 8;
            // Здесь residual >= 40, а regret неотрицателен.
            const std::int64_t baseScore = totalWeight_ * kMaxLength;
            auto candidate = large_.begin();
            for (int probe = 0;
                 probe < kLargeProbes && candidate != large_.end()
                     && baseScore < bestScore;
                 ++probe) {
                const int size = candidate->first;
                const int start = candidate->second;
                std::int64_t score = baseScore;
                for (int k = 2; k <= kMaxLength; ++k) {
                    const int remainder = length % k;
                    if (remainder != 0 && size % k < remainder) {
                        score += kRegretScale
                               * static_cast<std::int64_t>(weights_[k]) * k;
                        if (score >= bestScore) {
                            break;
                        }
                    }
                }
                if (score < bestScore) {
                    bestStart = start;
                    bestSize = size;
                    bestScore = score;
                }
                if (bestScore == baseScore) {
                    break;
                }
                candidate = large_.upper_bound(
                    std::make_pair(size, std::numeric_limits<int>::max()));
            }
        }
        return {bestStart, bestSize};
    }
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    Allocator() {
        pipes_.reserve(200001);
        pipes_.push_back({0, 0});
        rebuildProfile();
    }
    void place(int length) {
        observe(length);
        const auto chosen = chooseHole(length);
        int start;
        int sections = 0;
        if (chosen.first >= 0) {
            start = chosen.first;
            const int size = chosen.second;
            eraseHole(holes_.find(start));
            addHole(start + length, size - length);
        } else {
            start = frontier_;
            const int missing = length - (trench_ - frontier_);
            if (missing > 0) {
                sections = (missing + 19) / 20;
                trench_ += sections * 20;
            }
            frontier_ += length;
        }
        pipes_.push_back({start, length});
        std::cout << sections << ' ' << start << '\n';
        std::cout.flush();
    }
    void remove(std::int64_t pid) {
        Pipe& pipe = pipes_[static_cast<std::size_t>(pid)];
        const int originalStart = pipe.start;
        int start = pipe.start;
        int end = start + pipe.length;
        pipe.length = 0;
        auto next = holes_.lower_bound(start);
        if (next != holes_.begin()) {
            auto previous = std::prev(next);
            if (previous->first + previous->second == start) {
                start = previous->first;
                eraseHole(previous);
            }
        }
        if (next != holes_.end() && next->first == end) {
            end += next->second;
            eraseHole(next);
        }
        if (end == frontier_) {
            frontier_ = start;
        } else {
            addHole(start, end - start);
        }
        std::cout << originalStart << '\n';
        std::cout.flush();
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