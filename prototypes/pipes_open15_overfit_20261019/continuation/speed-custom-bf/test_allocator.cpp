#include "allocator.hpp"

#include <cstdio>
#include <cstdlib>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>

void fail(const char* message) {
    std::fprintf(stderr, "custom BF failure: %s\n", message);
    std::exit(2);
}

struct RefPipe { int x, n; };

struct Reference {
    int T = 0;
    std::map<int, int> gaps;
    std::set<std::pair<int, int> > sizes;
    std::vector<RefPipe> pipes{RefPipe{0, 0}};
    unsigned int ops = 0;

    void erase(std::map<int, int>::iterator it) {
        sizes.erase(std::make_pair(it->second - it->first, it->first));
        gaps.erase(it);
    }

    void add(int lo, int hi) {
        if (lo >= hi) return;
        std::map<int, int>::iterator it = gaps.lower_bound(lo);
        if (it != gaps.begin()) {
            std::map<int, int>::iterator p = it;
            --p;
            if (p->second == lo) { lo = p->first; erase(p); }
        }
        it = gaps.lower_bound(lo);
        if (it != gaps.end() && it->first == hi) { hi = it->second; erase(it); }
        gaps[lo] = hi;
        sizes.insert(std::make_pair(hi - lo, lo));
    }

    int bf(int n) const {
        std::set<std::pair<int, int> >::const_iterator it =
            sizes.lower_bound(std::make_pair(n, -1));
        if (it != sizes.end()) return it->second;
        if (!gaps.empty() && gaps.rbegin()->second == T) return gaps.rbegin()->first;
        return T;
    }

    int place(int n, int x) {
        int digs = (x + n - T + 19) / 20;
        if (digs < 0) digs = 0;
        if (digs) { add(T, T + 20 * digs); T += 20 * digs; }
        std::map<int, int>::iterator it = gaps.upper_bound(x);
        if (it == gaps.begin()) fail("reference placement has no predecessor gap");
        --it;
        const int lo = it->first, hi = it->second;
        if (x < lo || x + n > hi) fail("reference placement does not fit");
        erase(it);
        add(lo, x);
        add(x + n, hi);
        pipes.push_back(RefPipe{x, n});
        ++ops;
        return digs;
    }

    int remove(int id) {
        if (id <= 0 || static_cast<unsigned int>(id) >= pipes.size() || pipes[id].n <= 0)
            fail("bad reference PID");
        const RefPipe p = pipes[id];
        add(p.x, p.x + p.n);
        pipes[id].n = 0;
        ++ops;
        return p.x;
    }
};

struct Command {
    int command;
    int first;
    int second;
    int expectedT;
};

static unsigned int rngState = 1u;
static unsigned int rnd() {
    rngState = rngState * 1664525u + 1013904223u;
    return rngState;
}

static void checkState(const pipes_custom_bf::Allocator& fast,
                       const Reference& ref, const char* where) {
    if (fast.T != ref.T || fast.pipes.size() != ref.pipes.size() ||
        fast.gapCount() != ref.gaps.size()) {
        std::fprintf(stderr, "state mismatch at %s: T %d/%d pipes %u/%u gaps %u/%zu\n",
                     where, fast.T, ref.T, fast.pipes.size(),
                     static_cast<unsigned int>(ref.pipes.size()), fast.gapCount(),
                     ref.gaps.size());
        std::exit(2);
    }
}

static void checkPipes(const pipes_custom_bf::Allocator& fast,
                       const Reference& ref, const char* where) {
    for (unsigned int id = 0; id < fast.pipes.size(); ++id) {
        if (fast.pipes[id].x != ref.pipes[id].x || fast.pipes[id].n != ref.pipes[id].n) {
            std::fprintf(stderr, "pipe mismatch id=%u at %s\n", id, where);
            std::exit(2);
        }
    }
}

static void applyAndCheck(pipes_custom_bf::Allocator& fast,
                          unsigned int expectedOps, const Command& cmd,
                          const char* label) {
    if (cmd.command > 0) {
        const int x = fast.bf(cmd.command);
        const int digs = fast.place(cmd.command, x);
        if (digs != cmd.first || x != cmd.second) {
            std::fprintf(stderr, "allocation mismatch at %s command=%d got=(%d,%d) expected=(%d,%d)\n",
                         label, cmd.command, digs, x, cmd.first, cmd.second);
            std::exit(2);
        }
    } else {
        const int x = fast.remove(-cmd.command);
        if (x != cmd.first) {
            std::fprintf(stderr, "deletion mismatch at %s PID=%d got=%d expected=%d\n",
                         label, -cmd.command, x, cmd.first);
            std::exit(2);
        }
    }
    if (fast.T != cmd.expectedT || fast.operationCount() != expectedOps)
        fail("operation counter or trench mismatch");
}

static std::vector<Command> generateRandom(unsigned int seed,
                                           unsigned int count,
                                           Reference& ref,
                                           unsigned int split,
                                           Reference& splitState) {
    rngState = seed;
    std::vector<Command> commands;
    commands.reserve(count);
    std::vector<int> active;
    for (unsigned int step = 0; step < count; ++step) {
        const bool allocate = active.empty() || (rnd() % 100u < 63u);
        if (allocate) {
            const int n = 1 + static_cast<int>(rnd() % 40u);
            const int x = ref.bf(n);
            const int digs = ref.place(n, x);
            active.push_back(static_cast<int>(ref.pipes.size() - 1u));
            commands.push_back(Command{n, digs, x, ref.T});
        } else {
            const unsigned int slot = rnd() % static_cast<unsigned int>(active.size());
            const int id = active[slot];
            const int x = ref.remove(id);
            active[slot] = active.back();
            active.pop_back();
            commands.push_back(Command{-id, x, 0, ref.T});
        }
        if (step + 1u == split) {
            splitState = ref;
        }
    }
    return commands;
}

static void restoreAtSplit(pipes_custom_bf::Allocator& fast,
                           const Reference& snapshot) {
    fast.begin();
    for (unsigned int i = 1; i < snapshot.pipes.size(); ++i)
        fast.pipes.push_back(pipes_custom_bf::Pipe{snapshot.pipes[i].x,
                                                   snapshot.pipes[i].n});
    fast.T = snapshot.T;
    fast.setOperationCount(snapshot.ops);
    fast.reconstruct();
}

static unsigned long long differential(const char* label,
                                       unsigned int seed,
                                       unsigned int count,
                                       unsigned int split) {
    Reference ref;
    Reference splitState;
    std::vector<Command> commands = generateRandom(seed, count, ref, split,
                                                  splitState);
    const Reference finalRef = ref;

    pipes_custom_bf::Allocator fast;
    fast.begin();
    fast.reconstruct();
    for (unsigned int i = 0; i < split; ++i)
        applyAndCheck(fast, i + 1u, commands[i], label);

    // Force lazy state reconstruction at the exact prefix boundary, as the
    // memorizer does on the first command mismatch.
    restoreAtSplit(fast, splitState);
    Reference prefixRef = splitState;
    for (std::vector<Command>::const_iterator it = commands.begin() + split;
         it != commands.end(); ++it) {
        applyAndCheck(fast, prefixRef.ops + 1u, *it, label);
        if (it->command > 0) {
            const int digs = prefixRef.place(it->command, it->second);
            if (digs != it->first) fail("reference suffix placement mismatch");
        } else {
            if (prefixRef.remove(-it->command) != it->first)
                fail("reference suffix deletion mismatch");
        }
        if (prefixRef.T != it->expectedT) fail("reference suffix T mismatch");
        checkState(fast, prefixRef, label);
    }
    checkState(fast, finalRef, label);
    checkPipes(fast, finalRef, label);
    return count;
}

static unsigned long long exactPoolBoundary() {
    pipes_custom_bf::Allocator fast;
    fast.begin();
    const unsigned int live = 200000u;
    for (unsigned int i = 0; i < live; ++i)
        fast.pipes.push_back(pipes_custom_bf::Pipe{static_cast<int>(2u * i + 1u), 1});
    fast.T = static_cast<int>(2u * live + 1u);
    fast.setOperationCount(200000u);
    fast.reconstruct();
    if (fast.gapCount() != 200001u) fail("exact fixed-pool boundary mismatch");
    for (int n = 1; n <= 40; ++n) {
        const int x = fast.bf(n);
        const int expected = n == 1 ? 0 : 400000;
        if (x != expected) fail("Best-Fit address tie break mismatch");
    }
    return live;
}

int main() {
    unsigned long long checked = 0;
    std::fprintf(stderr, "stage=random\n");
    for (unsigned int seed = 1; seed <= 40; ++seed) {
        const unsigned int n = 2500u;
        checked += differential("random", seed * 0x9e3779b9u, n, n / 2u);
        if ((seed % 10u) == 0u) std::fprintf(stderr, "random_seeds=%u\n", seed);
    }

    // 200k valid operations: alternating 1/40 allocations, reverse deletion,
    // then FIFO deletion. This includes both ends of the active-ID order.
    {
        std::fprintf(stderr, "stage=mixed_200k\n");
        Reference ref;
        std::vector<Command> commands;
        commands.reserve(200000u);
        std::vector<int> ids;
        for (unsigned int i = 0; i < 100000u; ++i) {
            const int n = (i & 1u) ? 40 : 1;
            const int x = ref.bf(n);
            const int digs = ref.place(n, x);
            ids.push_back(static_cast<int>(ref.pipes.size() - 1u));
            commands.push_back(Command{n, digs, x, ref.T});
        }
        for (unsigned int i = 0; i < 50000u; ++i) {
            const int id = ids[ids.size() - 1u - i];
            const int x = ref.remove(id);
            commands.push_back(Command{-id, x, 0, ref.T});
        }
        for (unsigned int i = 0; i < 50000u; ++i) {
            const int id = ids[i];
            const int x = ref.remove(id);
            commands.push_back(Command{-id, x, 0, ref.T});
        }
        const Reference finalRef = ref;
        pipes_custom_bf::Allocator fast;
        fast.begin();
        fast.reconstruct();
        for (unsigned int i = 0; i < commands.size(); ++i) {
            const Command& cmd = commands[i];
            if (cmd.command > 0) {
                const int x = fast.bf(cmd.command);
                const int digs = fast.place(cmd.command, x);
                if (digs != cmd.first || x != cmd.second) fail("200k mixed allocation mismatch");
            } else if (fast.remove(-cmd.command) != cmd.first) {
                fail("200k reverse/FIFO deletion mismatch");
            }
            if (fast.T != cmd.expectedT) fail("200k mixed trench mismatch");
        }
        checkState(fast, finalRef, "200k mixed");
        checkPipes(fast, finalRef, "200k mixed");
        checked += commands.size();
    }

    // 200k valid operations producing 50k separated unit gaps, then merging
    // the remaining live pipes in the opposite parity order.
    {
        std::fprintf(stderr, "stage=fragmented_200k\n");
        Reference ref;
        std::vector<int> ids;
        ids.reserve(100000u);
        pipes_custom_bf::Allocator fast;
        fast.begin();
        fast.reconstruct();
        for (unsigned int i = 0; i < 100000u; ++i) {
            const int x = ref.bf(1);
            const int digs = ref.place(1, x);
            const int cx = fast.bf(1);
            const int cd = fast.place(1, cx);
            if (x != cx || digs != cd) fail("fragmented setup allocation mismatch");
            ids.push_back(static_cast<int>(ref.pipes.size() - 1u));
        }
        for (unsigned int i = 1; i < 100000u; i += 2u) {
            const int id = ids[i];
            if (ref.remove(id) != fast.remove(id)) fail("alternate deletion mismatch");
        }
        if (fast.gapCount() < 49999u) fail("fragmented gap count unexpectedly small");
        for (unsigned int i = 0; i < 100000u; i += 2u) {
            const int id = ids[i];
            if (ref.remove(id) != fast.remove(id)) fail("mass coalescing mismatch");
        }
        if (fast.gapCount() != ref.gaps.size()) fail("final coalescing gap mismatch");
        checked += 200000u;
    }

    std::fprintf(stderr, "stage=pool_boundary\n");
    const unsigned long long boundaryLive = exactPoolBoundary();
    std::printf("{\"status\":\"passed\",\"differential_operations\":%llu,\"pool_capacity\":200001,\"pool_boundary_live_pipes\":%llu,\"pool_boundary_gaps\":200001,\"checks\":[\"40 seeded random streams with prefix reconstruction\",\"200k mixed sizes with reverse and FIFO deletions\",\"200k unit allocations/deletions with 50k-gap mass coalescing\",\"exact 200001-gap pool boundary\"]}\n",
                checked, boundaryLive);
    return 0;
}
