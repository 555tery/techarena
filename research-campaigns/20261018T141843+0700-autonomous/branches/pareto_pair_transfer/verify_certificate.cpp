// Independent finite oracle for every positive certificate in the legal range.
#define main candidate_main
#include "solution.cpp"
#undef main

static bool fitsTwo(std::int64_t a, std::int64_t b, int x, int y) {
    return x + y <= a || x + y <= b ||
        (x <= a && y <= b) || (y <= a && x <= b);
}

int main() {
    const auto masks = makeParetoCarryMasks();
    std::uint64_t pairCertificates = 0, jointCertificates = 0;
    for (int length = 1; length <= 40; ++length) {
        for (int g = length; g < 80; ++g) {
            for (int h = g + 1; h < 80; ++h) {
                if (!strictlyDominatesParetoPairs(g, h, length)) continue;
                ++pairCertificates;
                bool strict = false;
                for (int x = 1; x <= 40; ++x) {
                    for (int y = x; y <= 40; ++y) {
                        const bool before = fitsTwo(g - length, h, x, y);
                        const bool after = fitsTwo(g, h - length, x, y);
                        if (before && !after) return 1;
                        strict |= !before && after;
                    }
                }
                if (!strict) return 2;
                if ((masks[h][length] & ~masks[g][length]) != 0) continue;
                ++jointCertificates;
                for (int s = 1; s <= 40; ++s) {
                    if (g / s + (h - length) / s < (g - length) / s + h / s) return 3;
                }
            }
        }
    }
    std::cout << "{\"positive_pair_certificates\":" << pairCertificates
              << ",\"joint_pair_and_homogeneous_certificates\":" << jointCertificates
              << ",\"range\":\"1<=L<=40,L<=g<h<80,all1<=x<=y<=40\",\"passed\":true}\n";
}
