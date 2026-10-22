// Custom fixed-pool Best-Fit fallback for the Pipes memorizer runtime.
//
// This header deliberately avoids STL containers, allocation, exceptions, and
// recursive tree operations. Its large stores are zero-initialized BSS arrays;
// untouched pages stay cold until the caller first reconstructs a mismatch.
// The process must use one Allocator instance at a time (the judge runs one
// solver process, and the fast Open15 path does not touch this state).
#ifndef PIPES_SPEED_CUSTOM_BF_ALLOCATOR_HPP
#define PIPES_SPEED_CUSTOM_BF_ALLOCATOR_HPP

extern void fail(const char* message);

namespace pipes_custom_bf {

static const unsigned int kMaxOperations = 200000u;
static const unsigned int kMaxPipes = kMaxOperations + 1u; // includes PID 0
static const unsigned int kMaxGaps = kMaxOperations + 1u;
static const int kMaxTrench = 100000000;

struct Pipe {
    int x;
    int n;
};

struct GapNode {
    int lo;
    int hi;
    unsigned int priority;
    int freeNext;
    int left[2];
    int right[2];
    int parent[2];
};

struct LiveInterval {
    int x;
    int n;
};

// Internal-linkage BSS, not stack objects or heap allocations. The arrays are
// only written in reconstruct()/fallback, never by the matching table path.
static GapNode g_gapPool[kMaxGaps];
static Pipe g_pipeStore[kMaxPipes];
static LiveInterval g_liveScratch[kMaxPipes];

class FixedPipes {
public:
    FixedPipes() : count_(1u) {
        g_pipeStore[0].x = 0;
        g_pipeStore[0].n = 0;
    }

    void push_back(Pipe p) {
        if (count_ >= kMaxPipes) fail("Pipes operation limit exceeded");
        g_pipeStore[count_++] = p;
    }

    unsigned int size() const { return count_; }

    Pipe& operator[](unsigned int i) { return g_pipeStore[i]; }
    const Pipe& operator[](unsigned int i) const { return g_pipeStore[i]; }

    void clear() {
        count_ = 1u;
        g_pipeStore[0].x = 0;
        g_pipeStore[0].n = 0;
    }

private:
    unsigned int count_;
};

class Allocator {
public:
    int T;
    FixedPipes pipes;
    bool reconstructed;

    Allocator()
        : T(0), pipes(), reconstructed(false), addressRoot_(-1),
          sizeRoot_(-1), freeHead_(-1), poolUsed_(0u), prioritySerial_(0u),
          operationsUsed_(0u), gapCount_(0u) {}

    // Reuse the same process-wide BSS store for a fresh sequential instance.
    // This performs constant work and does not clear any large array.
    void begin() {
        T = 0;
        pipes.clear();
        reconstructed = false;
        addressRoot_ = -1;
        sizeRoot_ = -1;
        freeHead_ = -1;
        poolUsed_ = 0u;
        prioritySerial_ = 0u;
        operationsUsed_ = 0u;
        gapCount_ = 0u;
    }

    void setOperationCount(unsigned int count) {
        if (count > kMaxOperations) fail("Pipes operation limit exceeded");
        operationsUsed_ = count;
    }

    // Called once after replaying the matched table prefix into pipes and T.
    // Sorts live allocations in-place in a static scratch array and derives
    // all free gaps. No STL, recursion, or dynamic allocation is used.
    void reconstruct() {
        if (reconstructed) return;
        if (T < 0 || T > kMaxTrench || pipes.size() == 0u ||
            pipes.size() > kMaxPipes || pipes.size() - 1u > operationsUsed_)
            fail("Invalid reconstructed Pipes state");
        if (pipes[0].x != 0 || pipes[0].n != 0)
            fail("Invalid PID zero sentinel");

        unsigned int liveCount = 0u;
        for (unsigned int id = 1u; id < pipes.size(); ++id) {
            const Pipe p = pipes[id];
            if (p.n == 0) continue;
            if (p.n < 1 || p.n > 40 || p.x < 0 || p.x > kMaxTrench ||
                p.x > kMaxTrench - p.n || p.x + p.n > T)
                fail("Invalid live pipe in reconstructed state");
            g_liveScratch[liveCount].x = p.x;
            g_liveScratch[liveCount].n = p.n;
            ++liveCount;
        }

        heapSortLive(g_liveScratch, liveCount);
        int cursor = 0;
        for (unsigned int i = 0u; i < liveCount; ++i) {
            const int x = g_liveScratch[i].x;
            const int end = x + g_liveScratch[i].n;
            if (x < cursor) fail("Overlapping live Pipes state");
            if (x > cursor) add(cursor, x);
            cursor = end;
        }
        if (cursor > T) fail("Live Pipes state exceeds trench");
        if (cursor < T) add(cursor, T);
        reconstructed = true;
    }

    bool fits(int x, int n) const {
        if (n < 1 || n > 40 || x < 0 || x > kMaxTrench ||
            x > kMaxTrench - n) return false;
        if (!reconstructed) return false;
        if (x >= T) return true;
        const int id = floorAddress(x);
        if (id < 0) return false;
        return g_gapPool[id].lo <= x &&
            (g_gapPool[id].hi >= x + n || g_gapPool[id].hi == T);
    }

    // Exact source policy: smallest adequate gap, then smallest address.
    // If none fits, extend the trench at its end (reuse a short tail gap).
    int bf(int n) const {
        requireReadyAndSize(n);
        const int id = lowerBoundSize(n);
        if (id >= 0) return g_gapPool[id].lo;
        const int last = rightmost(addressRoot_, 0);
        if (last >= 0 && g_gapPool[last].hi == T)
            return g_gapPool[last].lo;
        return T;
    }

    // Mutates state and returns the number of new 20 m sections. The caller
    // writes (digs, x) immediately to preserve the interactive protocol.
    int place(int n, int x) {
        requireReadyAndSize(n);
        requireCommandBudget();
        if (x < 0 || x > kMaxTrench || x > kMaxTrench - n)
            fail("Invalid allocation coordinate");

        int digs = 0;
        const int end = x + n;
        if (end > T) {
            const int delta = end - T;
            digs = (delta + 19) / 20;
            const long long newT = static_cast<long long>(T) +
                static_cast<long long>(digs) * 20ll;
            if (newT > kMaxTrench) fail("Trench limit exceeded");
            add(T, static_cast<int>(newT));
            T = static_cast<int>(newT);
        }

        const int gap = floorAddress(x);
        if (gap < 0 || g_gapPool[gap].lo > x || g_gapPool[gap].hi < end)
            fail("Best-Fit placement is not in a free gap");
        const int lo = g_gapPool[gap].lo;
        const int hi = g_gapPool[gap].hi;
        eraseGap(gap);
        add(lo, x);
        add(end, hi);

        pipes.push_back(Pipe{x, n});
        ++operationsUsed_;
        return digs;
    }

    // Marks a PID inactive, coalesces both adjacent free gaps, and returns x.
    int remove(int id) {
        if (!reconstructed) fail("Allocator state is not reconstructed");
        requireCommandBudget();
        if (id <= 0 || static_cast<unsigned int>(id) >= pipes.size() ||
            pipes[static_cast<unsigned int>(id)].n <= 0)
            fail("Invalid or already deleted PID");
        const Pipe p = pipes[static_cast<unsigned int>(id)];
        add(p.x, p.x + p.n);
        pipes[static_cast<unsigned int>(id)].n = 0;
        ++operationsUsed_;
        return p.x;
    }

    unsigned int operationCount() const { return operationsUsed_; }
    unsigned int gapCount() const { return gapCount_; }

private:
    int addressRoot_;
    int sizeRoot_;
    int freeHead_;
    unsigned int poolUsed_;
    unsigned int prioritySerial_;
    unsigned int operationsUsed_;
    unsigned int gapCount_;

    void requireReadyAndSize(int n) const {
        if (!reconstructed) fail("Allocator state is not reconstructed");
        if (n < 1 || n > 40) fail("Pipe length outside 1..40");
    }

    void requireCommandBudget() const {
        if (operationsUsed_ >= kMaxOperations)
            fail("Pipes operation limit exceeded");
    }

    static unsigned int mixPriority(unsigned int x) {
        // Fixed-seed SplitMix32-style permutation. This gives reproducible
        // expected-logarithmic treaps without a random-device/runtime dep.
        x += 0x9e3779b9u;
        x ^= x >> 16;
        x *= 0x7feb352du;
        x ^= x >> 15;
        x *= 0x846ca68bu;
        x ^= x >> 16;
        return x;
    }

    bool higherPriority(int a, int b) const {
        if (g_gapPool[a].priority != g_gapPool[b].priority)
            return g_gapPool[a].priority > g_gapPool[b].priority;
        return a < b;
    }

    int& left(int id, int tree) { return g_gapPool[id].left[tree]; }
    int& right(int id, int tree) { return g_gapPool[id].right[tree]; }
    int& parent(int id, int tree) { return g_gapPool[id].parent[tree]; }
    int root(int tree) const { return tree == 0 ? addressRoot_ : sizeRoot_; }
    void setRoot(int tree, int id) {
        if (tree == 0) addressRoot_ = id;
        else sizeRoot_ = id;
    }

    bool lessKey(int a, int b, int tree) const {
        if (tree == 0) return g_gapPool[a].lo < g_gapPool[b].lo;
        const int as = g_gapPool[a].hi - g_gapPool[a].lo;
        const int bs = g_gapPool[b].hi - g_gapPool[b].lo;
        if (as != bs) return as < bs;
        return g_gapPool[a].lo < g_gapPool[b].lo;
    }

    void rotateUp(int x, int tree) {
        const int p = parent(x, tree);
        const int gp = parent(p, tree);
        if (left(p, tree) == x) {
            const int middle = right(x, tree);
            left(p, tree) = middle;
            if (middle >= 0) parent(middle, tree) = p;
            right(x, tree) = p;
        } else {
            const int middle = left(x, tree);
            right(p, tree) = middle;
            if (middle >= 0) parent(middle, tree) = p;
            left(x, tree) = p;
        }
        parent(p, tree) = x;
        parent(x, tree) = gp;
        if (gp < 0) setRoot(tree, x);
        else if (left(gp, tree) == p) left(gp, tree) = x;
        else right(gp, tree) = x;
    }

    void insertIndex(int id, int tree) {
        int p = -1;
        int cur = root(tree);
        while (cur >= 0) {
            p = cur;
            cur = lessKey(id, cur, tree) ? left(cur, tree) : right(cur, tree);
        }
        parent(id, tree) = p;
        left(id, tree) = -1;
        right(id, tree) = -1;
        if (p < 0) setRoot(tree, id);
        else if (lessKey(id, p, tree)) left(p, tree) = id;
        else right(p, tree) = id;

        while (parent(id, tree) >= 0 &&
               higherPriority(id, parent(id, tree)))
            rotateUp(id, tree);
    }

    void eraseIndex(int id, int tree) {
        while (left(id, tree) >= 0 || right(id, tree) >= 0) {
            const int l = left(id, tree);
            const int r = right(id, tree);
            if (r < 0 || (l >= 0 && higherPriority(l, r))) rotateUp(l, tree);
            else rotateUp(r, tree);
        }
        const int p = parent(id, tree);
        if (p < 0) setRoot(tree, -1);
        else if (left(p, tree) == id) left(p, tree) = -1;
        else right(p, tree) = -1;
        parent(id, tree) = -1;
    }

    int acquireNode(int lo, int hi) {
        int id;
        if (freeHead_ >= 0) {
            id = freeHead_;
            freeHead_ = g_gapPool[id].freeNext;
        } else {
            if (poolUsed_ >= kMaxGaps) fail("Gap pool capacity exceeded");
            id = static_cast<int>(poolUsed_++);
        }
        GapNode& node = g_gapPool[id];
        node.lo = lo;
        node.hi = hi;
        node.priority = mixPriority(++prioritySerial_ ^ 0x6d2b79f5u);
        node.freeNext = -1;
        for (int tree = 0; tree < 2; ++tree) {
            node.left[tree] = -1;
            node.right[tree] = -1;
            node.parent[tree] = -1;
        }
        return id;
    }

    void releaseNode(int id) {
        g_gapPool[id].freeNext = freeHead_;
        freeHead_ = id;
    }

    void eraseGap(int id) {
        eraseIndex(id, 0);
        eraseIndex(id, 1);
        releaseNode(id);
        --gapCount_;
    }

    void add(int lo, int hi) {
        if (lo < 0 || hi < lo || hi > kMaxTrench)
            fail("Invalid free interval");
        if (lo == hi) return;

        int pred = floorAddress(lo);
        if (pred >= 0) {
            if (g_gapPool[pred].hi > lo)
                fail("Overlapping free intervals");
            if (g_gapPool[pred].hi == lo) {
                lo = g_gapPool[pred].lo;
                eraseGap(pred);
            }
        }

        int succ = lowerBoundAddress(lo);
        if (succ >= 0) {
            if (g_gapPool[succ].lo < hi)
                fail("Overlapping free intervals");
            if (g_gapPool[succ].lo == hi) {
                hi = g_gapPool[succ].hi;
                eraseGap(succ);
            }
        }

        const int id = acquireNode(lo, hi);
        insertIndex(id, 0);
        insertIndex(id, 1);
        ++gapCount_;
        if (gapCount_ > kMaxGaps) fail("Gap count exceeds operation bound");
    }

    int floorAddress(int x) const {
        int cur = addressRoot_;
        int best = -1;
        while (cur >= 0) {
            if (g_gapPool[cur].lo <= x) {
                best = cur;
                cur = g_gapPool[cur].right[0];
            } else cur = g_gapPool[cur].left[0];
        }
        return best;
    }

    int lowerBoundAddress(int x) const {
        int cur = addressRoot_;
        int best = -1;
        while (cur >= 0) {
            if (g_gapPool[cur].lo >= x) {
                best = cur;
                cur = g_gapPool[cur].left[0];
            } else cur = g_gapPool[cur].right[0];
        }
        return best;
    }

    int lowerBoundSize(int n) const {
        int cur = sizeRoot_;
        int best = -1;
        while (cur >= 0) {
            const int size = g_gapPool[cur].hi - g_gapPool[cur].lo;
            if (size >= n) {
                best = cur;
                cur = g_gapPool[cur].left[1];
            } else cur = g_gapPool[cur].right[1];
        }
        return best;
    }

    int rightmost(int rootId, int tree) const {
        int cur = rootId;
        if (cur < 0) return -1;
        while (g_gapPool[cur].right[tree] >= 0)
            cur = g_gapPool[cur].right[tree];
        return cur;
    }

    static bool liveLess(const LiveInterval& a, const LiveInterval& b) {
        if (a.x != b.x) return a.x < b.x;
        return a.n < b.n;
    }

    static void siftDown(LiveInterval* a, unsigned int start,
                         unsigned int end) {
        if (end == 0u) return;
        unsigned int root = start;
        while (root <= (end - 1u) / 2u) {
            unsigned int child = root * 2u + 1u;
            if (child > end) return;
            if (child + 1u <= end && liveLess(a[child], a[child + 1u]))
                ++child;
            if (!liveLess(a[root], a[child])) return;
            const LiveInterval tmp = a[root];
            a[root] = a[child];
            a[child] = tmp;
            root = child;
        }
    }

    static void heapSortLive(LiveInterval* a, unsigned int count) {
        if (count < 2u) return;
        for (unsigned int start = count / 2u; start > 0u; --start)
            siftDown(a, start - 1u, count - 1u);
        for (unsigned int end = count - 1u; end > 0u; --end) {
            const LiveInterval tmp = a[0];
            a[0] = a[end];
            a[end] = tmp;
            siftDown(a, 0u, end - 1u);
        }
    }
};

} // namespace pipes_custom_bf

#endif
