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
#include <cassert>
#include <cmath>
#define private public
#define main archived_solver_entry
#include "src/deletion_seam.cpp"
#undef main
#undef private
int main() {
    Allocator delayed;
    delayed.pipes.push_back(Pipe{0, 10, false, 0});
    delayed.seamBirth.push_back(1);
    delayed.seamDeath.push_back(2);
    delayed.seamPending.push_back(1);
    delayed.seamClock = 255;
    delayed.advanceSeamClock();
    assert(delayed.seamCdf[0][256] == 0);
    delayed.advanceSeamClock();
    assert(delayed.seamCdf[10][0] == 0);
    assert(delayed.seamCdf[10][1] == 1);
    assert(delayed.seamCdf[0][256] == 1);

    Allocator a;
    a.seamClock = 64;
    a.pipes.push_back(Pipe{0, 10, true, 0});
    a.pipes.push_back(Pipe{15, 20, true, 0});
    a.seamBirth = {0, 64, 64};
    a.seamDeath = {0, 0, 0};
    for (int age = 0; age <= 256; ++age) {
        const int count = age < 32 ? 0 : (age < 256 ? 160 : 320);
        a.seamCdf[10][static_cast<std::size_t>(age)] = count;
        a.seamCdf[20][static_cast<std::size_t>(age)] = count;
        a.seamCdf[0][static_cast<std::size_t>(age)] = count * 2;
    }
    assert(std::abs(a.seamReleaseProbability(1) - 0.5) < 1e-12);
    a.seamClock = 104;
    assert(a.seamReleaseProbability(1) == 0.0);
    a.seamClock = 64;
    a.activeByEnd = {{10, 1}, {35, 2}};
    a.freeByStart = {{10, 15}};
    a.freeBySize = {{5, 10}};
    a.trenchLength = 35;
    for (int i = 0; i < 128; ++i) a.recordLength(12);
    auto gap = a.freeByStart.begin();
    assert(std::abs(a.seamBenefit(gap, 2, true) - 6.5) < 1e-12);
    assert(std::abs(a.seamBenefit(gap, 2, false) - 1.5) < 1e-12);
    const auto choice = a.chooseDeletionSeam(2, gap, false);
    assert(choice.first == gap && choice.second);
    assert(a.seamChanges == 1);
    std::cout << "delayed labels, conditional risk and geometric endpoint checks: pass\n";
}
