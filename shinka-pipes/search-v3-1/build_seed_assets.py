"""Prepare simple reference allocators and a code-free independent task contract."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    directory = ROOT / "seeds"
    directory.mkdir(exist_ok=True)
    initial = (ROOT.parent / "search-v2/task/initial.cpp").read_text()
    start, end = "// EVOLVE-BLOCK-START", "// EVOLVE-BLOCK-END"
    prefix, suffix = initial.split(start)[0], initial.split(end)[1]
    body = r'''
namespace {
using Coordinate = std::int64_t;
class Allocator {
    struct Pipe { Coordinate start; int length; };
    std::vector<Pipe> pipes_{{0, 0}};
    std::map<Coordinate, Coordinate> gaps_;
    std::set<std::pair<Coordinate, Coordinate>> sizes_;
    std::array<std::set<Coordinate>, 41> starts_;
    Coordinate trench_ = 0;
    static int bucket(Coordinate n) { return static_cast<int>(std::min<Coordinate>(40, n)); }
    void add(Coordinate a, Coordinate b) {
        if (a >= b) return;
        gaps_[a] = b;
        sizes_.insert({b-a, a});
        starts_[bucket(b-a)].insert(a);
    }
    void erase(Coordinate a) {
        const Coordinate b = gaps_.at(a);
        sizes_.erase({b-a, a});
        starts_[bucket(b-a)].erase(a);
        gaps_.erase(a);
    }
public:
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length) {
        Coordinate at = -1, digs = 0;
        if constexpr (FIRST_FIT) {
            for (int k = length; k <= 40; ++k)
                if (!starts_[k].empty() && (at < 0 || *starts_[k].begin() < at))
                    at = *starts_[k].begin();
        } else {
            auto candidate = sizes_.lower_bound({length, 0});
            if (candidate != sizes_.end()) at = candidate->second;
        }
        if (at < 0) {
            at = trench_;
            if (!gaps_.empty() && gaps_.rbegin()->second == trench_) {
                at = gaps_.rbegin()->first;
                erase(at);
            }
            digs = (length - (trench_ - at) + 19) / 20;
            trench_ += digs * 20;
            add(at, trench_);
        }
        const Coordinate finish = gaps_.at(at);
        erase(at);
        add(at + length, finish);
        pipes_.push_back({at, length});
        std::cout << digs << ' ' << at << '\n' << std::flush;
    }
    void remove(Coordinate pid) {
        const Pipe p = pipes_.at(static_cast<std::size_t>(pid));
        Coordinate a = p.start, b = a + p.length;
        auto right = gaps_.lower_bound(a);
        if (right != gaps_.end() && right->first == b) {
            b = right->second;
            erase(right->first);
        }
        auto left = gaps_.lower_bound(a);
        if (left != gaps_.begin()) {
            --left;
            if (left->second == a) { a = left->first; erase(a); }
        }
        add(a, b);
        std::cout << p.start << '\n' << std::flush;
    }
};
}  // namespace
'''
    for name, first in (("first_fit", "true"), ("best_fit", "false")):
        (directory / f"simple_{name}.cpp").write_text(prefix + start + body.replace("FIRST_FIT", first) + end + suffix)
    scaffold = prefix + start + r'''
namespace {
class Allocator {
public:
    // Required compatibility counters; they may stay zero.
    std::size_t mcDecisionsUsed = 0, mcRolloutsRun = 0;
    std::uint64_t expansionGateOpportunities = 0, expansionGatePasses = 0;
    std::uint64_t unitProfileSuppressedExpansions = 0;
    void place(int length);  // implement placement and print sections + coordinate
    void remove(std::int64_t pid);  // implement deletion and print old coordinate
};
}
''' + end + suffix
    contract = '''Design an independent causal online allocator from this task statement and interface.
No prior allocator implementation, research memory, candidate scores or other lineage is provided.
Do not use tools, read files, browse or run experiments. Return a complete self-contained C++20 source.
Only the EVOLVE-BLOCK region may change; copy the protected prefix and suffix exactly.
The mutable region is yours to implement freely, including extra standard-library includes there.

An interactive stream contains at most 200000 commands. Read only one command at a time.
Positive L (1..40) inserts a pipe of exactly L integer meters. Reply N D: grow the trench by
N sections of 20 meters, then place [D,D+L). N and D are nonnegative integers. Initial trench
length is zero; trench never shrinks and must not exceed 100000000 meters. Live pipes may
never overlap or move. A pipe may cross section boundaries. PID is the insertion ordinal,
starting at 1, and is never reused. Negative -K deletes live PID K; reply its original start
coordinate. Freed space can be reused and adjacent free intervals can be merged. 0 ends
the stream: exit without replying. Every response is exactly one newline-terminated line,
flushed before reading the next command. Deletions are valid. Future commands are unknown.
Solver CPU must be strictly below 5 seconds and RSS below 256 MiB for each stream.

Optimize the arithmetic mean of final live length F divided by final trench length T on
152 diverse synthetic search streams (38 equally weighted families). Hidden streams may
differ. Small cold starts, churn, different sizes and deletion patterns all matter. Never
identify tests or inspect files; decisions may use past commands and current state only.
Choose an algorithmic mechanism with a clear rationale, complexity and possible failure mode.
Novelty is not required; correctness and useful search diversity matter. Randomized algorithms
may use a fixed reproducible seed and may never rely on wall time or input fingerprints.
Explain a possible ablation. Return NAME, DESCRIPTION and a fenced cpp block containing
the entire source. The compatibility counters are interface fields, not hints about an algorithm.

REQUIRED SOURCE INTERFACE (no allocator implementation):
'''
    (directory / "independent-task.txt").write_text(contract + "```cpp\n" + scaffold + "```\n")
    rows = []
    for i, (kind, name, relative) in enumerate([
        ("strong", "SEARCH-v2 generation 17", "seeds/strong_v2_gen17.cpp"),
        ("strong", "SEARCH-v2 generation 27", "seeds/strong_v2_gen27.cpp"),
        ("simple", "First-Fit", "seeds/simple_first_fit.cpp"),
        ("simple", "Best-Fit", "seeds/simple_best_fit.cpp"),
    ]):
        rows.append(dict(lineage_id=i, kind=kind, name=name, source_path=relative,
                         source_sha256=hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()))
    for i in range(4, 8):
        rows.append(dict(lineage_id=i, kind="independent", name=f"Independent {i-3}",
                         prompt_path="seeds/independent-task.txt",
                         prompt_sha256=hashlib.sha256((directory / "independent-task.txt").read_bytes()).hexdigest()))
    (ROOT / "seed-plan.json").write_text(json.dumps(dict(version="mixed-seeds-v1", initial_islands=8,
        max_islands=10, isolation_correct_per_lineage=4, seeds=rows), indent=2) + "\n")
    print("Prepared four fixed seeds and an implementation-free independent task contract.")


if __name__ == "__main__":
    main()
