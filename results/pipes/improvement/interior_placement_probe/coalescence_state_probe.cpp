#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#define private public
#define main pipes_original_main
#include "solution_interior.cpp"
#undef main
#undef private

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    std::ifstream input(argv[1]);
    std::string id;
    int trench, leftFill, leftExt, leftAnchor, targetGap;
    int rightAnchor, rightExt, rightFill, probeLength, futureLength;
    while (input >> id >> trench >> leftFill >> leftExt >> leftAnchor >> targetGap
                 >> rightAnchor >> rightExt >> rightFill >> probeLength >> futureLength) {
        Allocator allocator;
        allocator.trenchLength = trench;
        allocator.pipes.resize(5);
        const int leftAnchorStart = leftFill + leftExt;
        const int targetStart = leftAnchorStart + leftAnchor;
        const int rightAnchorStart = targetStart + targetGap;
        const int rightFillStart = rightAnchorStart + rightAnchor + rightExt;
        if (rightFillStart + rightFill != trench) return 3;
        allocator.pipes[1] = Pipe{0, leftFill, true, 0};
        allocator.pipes[2] = Pipe{leftAnchorStart, leftAnchor, true, 0};
        allocator.pipes[3] = Pipe{rightAnchorStart, rightAnchor, true, 0};
        allocator.pipes[4] = Pipe{rightFillStart, rightFill, true, 0};
        allocator.activePipeCount = 4;
        for (int pid = 1; pid <= 4; ++pid) {
            for (int i = pid; i < static_cast<int>(allocator.activeFenwick.size()); i += i & -i) {
                ++allocator.activeFenwick[static_cast<std::size_t>(i)];
            }
        }
        if (leftExt > 0) allocator.addFreeGap(leftFill, leftAnchorStart, -1);
        allocator.addFreeGap(targetStart, rightAnchorStart, -1);
        if (rightExt > 0) allocator.addFreeGap(rightAnchorStart + rightAnchor,
                                               rightFillStart, -1);
        allocator.lengthOccurrenceCount[futureLength] = 16;
        for (int i = 0; i < 16; ++i) allocator.recordLength(futureLength);
        for (int i = 0; i < 8; ++i) {
            allocator.recordObservation(Observation{-1, 750});
            allocator.recordObservation(Observation{1, futureLength});
            allocator.recordObservation(Observation{-1, 750});
            allocator.recordObservation(Observation{1, futureLength});
        }
        allocator.place(probeLength);
        std::cout << "CASE " << id << ' ' << trench << ' '
                  << allocator.pipes.back().start << '\n';
    }
}
