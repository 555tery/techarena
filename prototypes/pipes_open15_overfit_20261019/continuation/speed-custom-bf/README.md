# Fixed-pool Best-Fit fallback

`allocator.hpp` is a standalone pure-POD replacement for the `map`/`set`
fallback in `speed-v8/solver_runtime.cpp`. It preserves the same rule:

1. Choose the adequate free gap with minimum length, breaking ties by minimum
   starting address.
2. If no gap is large enough, reuse a short tail gap and extend the trench in
   20 m sections; otherwise start at the current trench end.
3. On deletion, merge an adjacent predecessor, an adjacent successor, or both.

The class keeps two intrusive treap indexes over one fixed node pool: by start
address and by `(gap length, start address)`. All treap walks and rotations are
iterative. With the fixed SplitMix-derived priority sequence, normal operations
have expected `O(log G)` cost, where `G` is the number of free gaps. A treap
still has a theoretical `O(G)` worst case; priorities are deterministic and
must not be described as a worst-case logarithmic guarantee. Iterative code
avoids recursion and stack growth even in that case.

## Integration API

The header expects the runtime to provide `void fail(const char*)`, which must
terminate with exit code 2. It uses no `std::` type, allocation, exception, or
container. Compile as C++14 or later with `-fno-exceptions -fno-rtti` if the
surrounding runtime permits.

After a table mismatch, replay into a fresh local state and reconstruct once:

```cpp
pipes_custom_bf::Allocator state;
state.begin();                         // optional on a fresh object
state.pipes.push_back({x, length});    // each restored allocation ID
state.T = restoredT;
state.setOperationCount(matchedSteps);
state.reconstruct();
```

For a positive fallback command `n`, call `x = state.bf(n)`, then
`digs = state.place(n, x)`, and immediately print `(digs, x)`. For a deletion
`-id`, call `x = state.remove(id)` and immediately print `x`. `pipes` provides
the compatibility surface used during replay: `push_back`, `size`, and
indexing. `T`, `reconstructed`, `bf`, `place`, `remove`, and `reconstruct`
retain familiar names. `place` and `remove` update state only; I/O remains the
caller's responsibility.

`begin()` resets only scalar counters and the pipe count. The fixed arrays are
internal-linkage BSS stores, not stack arrays, and are not cleared up front.
The matching table path must not call `reconstruct`, `bf`, `place`, or `remove`.
The allocator supports one live instance per process; this matches the single
solver process and keeps all backing storage static.

Bounds are enforced: at most 200,000 commands, pipe lengths 1–40 m, trench at
most 100,000,000 m, and at most 200,000 allocated IDs plus sentinel. The pool
has 200,001 gap nodes, sufficient for the maximum `live pipes + 1` gaps. The
header plus POD stores occupies about 11.2 MB of static image data on the
tested 64-bit compiler; pages are written only as reconstruction/fallback
touches them. This is storage size, not measured resident memory.

## Verification

`test_allocator.cpp` compares exact coordinates, section counts, trench state,
pipe IDs, and gap counts against the STL allocator. The test is local and does
not invoke the native evaluator, website, or model. `pod_smoke.cpp` compiles the
header under C++14 with exceptions and RTTI disabled; `nm -u` on its object had
no unresolved symbols, including no C++ runtime symbols.

See `test-result.json` for the completed test record. The host did not run a
Windows compiler; platform build and evaluator stress remain with the parent
integration task.
