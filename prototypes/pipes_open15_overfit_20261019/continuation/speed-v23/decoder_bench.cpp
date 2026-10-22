#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <ctime>
#include <vector>
#include "decoder_bench_tables.hpp"

#if defined(__GNUC__) || defined(__clang__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

static volatile uint64_t sink = 0;

NOINLINE uint64_t decodePacked(unsigned passes) {
    uint64_t sum = 0;
    for (unsigned pass = 0; pass < passes; ++pass) {
        for (const auto &slice : benchSlices) {
            const unsigned char *p = slice.packed;
            for (unsigned i = 0; i < slice.count; ++i) {
                const unsigned h = *p++;
                const unsigned len = h & 15u;
                sum += (h >> 4) * 17u + len;
                sum += p[0] + (unsigned(p[len - 1]) << 1);
                p += len;
            }
        }
    }
    return sum;
}

NOINLINE uint64_t decodeSplit(unsigned passes) {
    uint64_t sum = 0;
    for (unsigned pass = 0; pass < passes; ++pass) {
        for (const auto &slice : benchSlices) {
            const unsigned char *meta = slice.meta;
            const unsigned char *p = slice.payload;
            for (unsigned i = 0; i < slice.count; ++i) {
                const unsigned h = meta[i];
                const unsigned len = h & 15u;
                sum += (h >> 4) * 17u + len;
                sum += p[0] + (unsigned(p[len - 1]) << 1);
                p += len;
            }
        }
    }
    return sum;
}

static double threadCpuSeconds() {
    timespec t{};
    if (clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t) != 0) return -1.0;
    return double(t.tv_sec) + double(t.tv_nsec) * 1.0e-9;
}

template <class F> static double timed(F fn, unsigned passes, uint64_t &sum) {
    const double begin = threadCpuSeconds();
    sum = fn(passes);
    const double end = threadCpuSeconds();
    sink = sink + sum;
    return end - begin;
}

int main() {
    const unsigned passes = 32;
    const uint64_t checkPacked = decodePacked(1);
    const uint64_t checkSplit = decodeSplit(1);
    if (checkPacked != checkSplit) {
        std::fprintf(stderr, "checksum mismatch %llu %llu\n",
                     (unsigned long long)checkPacked,
                     (unsigned long long)checkSplit);
        return 2;
    }
    // Warm both layouts once before paired measurements.
    (void)decodePacked(2);
    (void)decodeSplit(2);
    std::vector<double> packedTimes, splitTimes, savedTimes;
    for (unsigned round = 0; round < 12; ++round) {
        uint64_t a = 0, b = 0;
        double packed, split;
        if ((round & 1u) == 0) {
            packed = timed(decodePacked, passes, a);
            split = timed(decodeSplit, passes, b);
        } else {
            split = timed(decodeSplit, passes, b);
            packed = timed(decodePacked, passes, a);
        }
        if (a != b) return 3;
        packedTimes.push_back(packed);
        splitTimes.push_back(split);
        savedTimes.push_back(packed - split);
    }
    auto median = [](std::vector<double> v) {
        std::sort(v.begin(), v.end());
        return v[v.size() / 2];
    };
    std::printf("records_per_pass=274639 passes_per_sample=%u paired_rounds=%zu\n", passes, packedTimes.size());
    std::printf("checksum=%llu packed_median_thread_cpu_s=%.9f split_median_thread_cpu_s=%.9f median_saved_s=%.9f relative=%.4f%%\n",
                (unsigned long long)checkPacked,
                median(packedTimes), median(splitTimes), median(savedTimes),
                median(savedTimes) * 100.0 / median(packedTimes));
    std::printf("packed_samples=");
    for (double t : packedTimes) std::printf("%.9f,", t);
    std::printf("\nsplit_samples=");
    for (double t : splitTimes) std::printf("%.9f,", t);
    std::printf("\nsink=%llu\n", (unsigned long long)sink);
}
