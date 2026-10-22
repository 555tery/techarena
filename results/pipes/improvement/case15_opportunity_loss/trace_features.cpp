#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <vector>

struct Pipe { std::int64_t start = -1; int length = 0; bool active = false; };

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    std::ifstream in(argv[1]);
    std::ifstream answer(argv[2]);
    std::ofstream out(argv[3]);
    double weight = 0.0;
    int n = 0;
    in >> weight >> n;
    (void)weight;
    std::map<std::int64_t, std::int64_t> gaps;
    std::multiset<std::int64_t> gapSizes;
    std::array<std::int64_t, 41> fitCount{};
    std::array<std::int64_t, 41> fitVolume{};
    std::vector<Pipe> pipes(1);
    std::int64_t trench = 0;
    std::int64_t freeVolume = 0;
    std::int64_t liveVolume = 0;
    std::int64_t activeCount = 0;

    auto adjustGapStats = [&](std::int64_t len, int sign) {
        for (int q = 1; q <= 40 && q <= len; ++q) {
            fitCount[static_cast<std::size_t>(q)] += sign;
            fitVolume[static_cast<std::size_t>(q)] += sign * len;
        }
    };
    auto eraseGap = [&](std::map<std::int64_t, std::int64_t>::iterator it) {
        const std::int64_t len = it->second - it->first;
        adjustGapStats(len, -1);
        freeVolume -= len;
        auto sizeIt = gapSizes.find(len);
        if (sizeIt == gapSizes.end()) throw 1;
        gapSizes.erase(sizeIt);
        gaps.erase(it);
    };
    auto addGap = [&](std::int64_t start, std::int64_t end) {
        if (start >= end) return;
        auto it = gaps.lower_bound(start);
        if (it != gaps.begin()) {
            auto prev = std::prev(it);
            if (prev->second >= start) {
                start = prev->first;
                end = std::max(end, prev->second);
                eraseGap(prev);
                it = gaps.lower_bound(start);
            }
        }
        while (it != gaps.end() && it->first <= end) {
            end = std::max(end, it->second);
            auto doomed = it++;
            eraseGap(doomed);
        }
        const std::int64_t len = end - start;
        gaps.emplace(start, end);
        gapSizes.insert(len);
        adjustGapStats(len, 1);
        freeVolume += len;
    };
    auto occupy = [&](std::int64_t start, int length) {
        const std::int64_t end = start + length;
        auto it = gaps.upper_bound(start);
        if (it == gaps.begin()) throw 3;
        --it;
        if (it->first > start || it->second < end) throw 4;
        const std::int64_t gs = it->first;
        const std::int64_t ge = it->second;
        eraseGap(it);
        addGap(gs, start);
        addGap(end, ge);
    };

    out << "op,type,length,digs,active_pipes,live_volume,free_volume,gap_count,largest_gap,fit_count,fit_volume,fit_fraction,fit_volume_ratio";
    for (int q = 1; q <= 40; ++q) out << ",fit_count_" << q;
    for (int q = 1; q <= 40; ++q) out << ",fit_volume_" << q;
    out << '\n';
    for (int op = 1; op <= n; ++op) {
        int command = 0;
        in >> command;
        std::string response;
        std::getline(answer, response);
        if (response.empty()) std::getline(answer, response);
        if (command > 0) {
            std::int64_t digs = 0, start = 0;
            if (std::sscanf(response.c_str(), "%lld %lld", &digs, &start) != 2) return 5;
            const std::int64_t largest = gapSizes.empty() ? 0 : *gapSizes.rbegin();
            const auto q = static_cast<std::size_t>(command);
            const std::int64_t count = fitCount[q];
            const std::int64_t volume = fitVolume[q];
            out << op << ",place," << command << ',' << digs << ',' << activeCount << ','
                << liveVolume << ',' << freeVolume << ',' << gaps.size() << ',' << largest << ','
                << count << ',' << volume << ','
                << (freeVolume == 0 ? 0.0 : static_cast<double>(volume) / freeVolume) << ','
                << (command == 0 ? 0.0 : static_cast<double>(largest) / command);
            for (int size = 1; size <= 40; ++size) out << ',' << fitCount[static_cast<std::size_t>(size)];
            for (int size = 1; size <= 40; ++size) out << ',' << fitVolume[static_cast<std::size_t>(size)];
            out << '\n';
            const std::int64_t oldTrench = trench;
            trench += digs * 20;
            if (trench > oldTrench) addGap(oldTrench, trench);
            occupy(start, command);
            if (static_cast<std::size_t>(pipes.size()) > 200001U) return 6;
            pipes.push_back(Pipe{start, command, true});
            ++activeCount;
            liveVolume += command;
        } else if (command < 0) {
            const std::int64_t start = std::stoll(response);
            const std::size_t pid = static_cast<std::size_t>(-command);
            if (pid >= pipes.size() || !pipes[pid].active || pipes[pid].start != start) return 7;
            Pipe& p = pipes[pid];
            addGap(p.start, p.start + p.length);
            p.active = false;
            --activeCount;
            liveVolume -= p.length;
        } else {
            return 8;
        }
    }
    return 0;
}
