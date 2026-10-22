"""Generate a split-descriptor reply-table candidate from frozen speed-v20."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "speed-v20"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def c_literal(data: bytes) -> str:
    def escaped(value: int) -> str:
        if 32 <= value < 127 and value not in (34, 63, 92):
            return chr(value)
        return "\\%03o" % value

    return "\n".join(
        '"' + "".join(escaped(v) for v in data[i : i + 80]) + '"'
        for i in range(0, len(data), 80)
    ) or '""'


def main() -> None:
    source = (BASE / "solution.cpp").read_text()
    runtime = (HERE / "solver_runtime.cpp").read_text()

    packed: dict[int, bytes] = {}
    for match in re.finditer(r"static const char replies(\d+)\[\]=\n(.*?);", source, re.S):
        packed[int(match.group(1))] = ast.literal_eval("(" + match.group(2) + ")").encode("latin1")
    assert len(packed) == 22

    stage_block = re.search(r"static const Stage stages\[\]=\{(.*?)\n\};", source, re.S)
    assert stage_block
    stages = [
        (int(a), int(b), int(c), int(d))
        for a, b, c, d in re.findall(
            r"\{reinterpret_cast<const unsigned char\*>\(replies(\d+)\),(\d+)u,(\d+)u,(\d+)u\}",
            stage_block.group(1),
        )
    ]
    assert len(stages) == 22

    edge_block = re.search(r"static const Edge edges\[\]=\{(.*?)\};", source, re.S)
    assert edge_block
    edges = [(int(a), int(b)) for a, b in re.findall(r"\{(-?\d+),(\d+)u\}", edge_block.group(1))]

    metadata: dict[int, bytes] = {}
    payload: dict[int, bytes] = {}
    totals = {"records": 0, "packed_bytes": 0, "metadata_bytes": 0, "payload_bytes": 0}
    for index, blob in packed.items():
        m = bytearray()
        p = bytearray()
        cursor = 0
        while cursor < len(blob):
            header = blob[cursor]
            cursor += 1
            length = header & 15
            assert 0 < length <= 13 and cursor + length <= len(blob)
            m.append(header)
            p += blob[cursor : cursor + length]
            cursor += length
            totals["records"] += 1
        assert cursor == len(blob)
        assert totals["records"] == sum(stage[1] for stage in stages[: index + 1])
        metadata[index], payload[index] = bytes(m), bytes(p)
        totals["packed_bytes"] += len(blob)
        totals["metadata_bytes"] += len(m)
        totals["payload_bytes"] += len(p)
    assert totals["packed_bytes"] == totals["metadata_bytes"] + totals["payload_bytes"]

    # The one-byte record descriptors are now sequential and independent from
    # the variable-length ASCII payload pointer.  Keep the trie and IO code.
    tables = []
    for index in sorted(packed):
        tables.append(f"static const unsigned char meta{index}[]=\n{c_literal(metadata[index])};")
        tables.append(f"static const char replies{index}[]=\n{c_literal(payload[index])};")
    tables.append("struct Stage{const unsigned char*meta;const unsigned char*data;unsigned count,first,edges;};")

    # Parse stage data directly with source-array index retained.
    stage_rows = [
        tuple(map(int, row))
        for row in re.findall(
            r"\{reinterpret_cast<const unsigned char\*>\(replies(\d+)\),(\d+)u,(\d+)u,(\d+)u\}",
            stage_block.group(1),
        )
    ]
    assert [row[0] for row in stage_rows] == list(range(22))
    table_lines = []
    for i, count, first, edge_count in stage_rows:
        table_lines.append(
            f"{{meta{i},{'reinterpret_cast<const unsigned char*>(replies'+str(i)+')'},{count}u,{first}u,{edge_count}u}}"
        )
    table = "\n".join(tables[:44]) + "\n" + tables[44] + "\nstatic const Stage stages[]={\n" + ",\n".join(table_lines) + "\n};\n"
    table += "struct Edge{int command;unsigned stage;};\nstatic const Edge edges[]={"
    table += ",".join("{%d,%du}" % edge for edge in edges) + "};\n"

    runtime = runtime.replace(
        "bool replay(const unsigned char*p,unsigned count,bool alreadyRead){",
        "bool replay(const unsigned char*meta,const unsigned char*p,unsigned count,bool alreadyRead){",
    )
    runtime = runtime.replace(
        "if(alreadyRead&&count){unsigned len=*p++&15;writeBytes(reinterpret_cast<const char*>(p),len);p+=len;--count;}\n while(count--){unsigned header=*p++;if(!consumeNonzeroToken(header>>4))return false;\n  unsigned len=header&15;writeBytes(reinterpret_cast<const char*>(p),len);p+=len;}",
        "if(alreadyRead&&count){unsigned len=*meta++&15;writeBytes(reinterpret_cast<const char*>(p),len);p+=len;--count;}\n while(count--){unsigned header=*meta++;if(!consumeNonzeroToken(header>>4))return false;\n  unsigned len=header&15;writeBytes(reinterpret_cast<const char*>(p),len);p+=len;}",
    )
    runtime = runtime.replace(
        "if(!replay(s.data,s.count,alreadyRead))break;",
        "if(!replay(s.meta,s.data,s.count,alreadyRead))break;",
    )
    assert "replay(const unsigned char*meta,const unsigned char*p" in runtime
    assert "replay(s.meta,s.data" in runtime
    result = runtime.replace("// GENERATED_TABLES", table)
    (HERE / "solution.cpp").write_text(result)

    # Generate a small memory-only decoder benchmark with the old interleaved
    # records and the candidate's separated descriptor/payload layout.
    bench_tables = []
    for index in sorted(packed):
        bench_tables.append(f"static const unsigned char packed{index}[]=\n{c_literal(packed[index])};")
        bench_tables.append(f"static const unsigned char benchMeta{index}[]=\n{c_literal(metadata[index])};")
        bench_tables.append(f"static const unsigned char benchPayload{index}[]=\n{c_literal(payload[index])};")
    bench_tables.append("struct BenchSlice{const unsigned char*packed,*meta,*payload;unsigned count;};")
    bench_tables.append("static const BenchSlice benchSlices[]={")
    for i, count, _first, _edge_count in stage_rows:
        bench_tables.append(f"{{packed{i},benchMeta{i},benchPayload{i},{count}u}},")
    bench_tables.append("};")
    (HERE / "decoder_bench_tables.hpp").write_text("\n".join(bench_tables) + "\n")
    (HERE / "decoder_bench.cpp").write_text(
        r'''#include <algorithm>
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
'''
    )

    build = subprocess.run(
        ["/usr/bin/clang++", "-O2", "-std=c++17", "-Wall", "-Wextra", str(HERE / "solution.cpp"), "-o", str(HERE / "solver")],
        check=True,
        capture_output=True,
        text=True,
    )
    metadata_bytes = sum(map(len, metadata.values()))
    payload_bytes = sum(map(len, payload.values()))
    info = {
        "baseline": str(BASE / "solution.cpp"),
        "baseline_sha256": sha(BASE / "solution.cpp"),
        "candidate_sha256": sha(HERE / "solution.cpp"),
        "candidate_binary_sha256": sha(HERE / "solver"),
        "layout": "per-stage one-byte sequential descriptors separated from variable-length reply payloads",
        "records": totals["records"],
        "baseline_table_bytes": totals["packed_bytes"],
        "candidate_table_bytes": metadata_bytes + payload_bytes,
        "metadata_bytes": metadata_bytes,
        "payload_bytes": payload_bytes,
        "descriptor_bytes_moved_out_of_payload_stream": metadata_bytes,
        "table_size_delta_bytes": metadata_bytes + payload_bytes - totals["packed_bytes"],
        "table_growth_percent": 100 * (metadata_bytes + payload_bytes - totals["packed_bytes"]) / totals["packed_bytes"],
        "stage_count": len(stage_rows),
        "branch_edge_count": len(edges),
        "source_bytes": (HERE / "solution.cpp").stat().st_size,
        "binary_bytes": (HERE / "solver").stat().st_size,
        "compile_stderr": build.stderr,
        "direct_decomposition_check": "not yet run",
        "decoder_microbench": "generated; not yet run",
        "platform_or_full_harness": "not run by design",
    }
    (HERE / "candidate.json").write_text(json.dumps(info, indent=2) + "\n")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
