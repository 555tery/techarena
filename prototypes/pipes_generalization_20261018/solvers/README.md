# Exact BF / SS: shared physical allocator

Standalone C++20 implementations for a local comparison. No claim of score or
generalization improvement is made. Only tiny correctness fixtures were run here;
the coordinator owns official evaluation, resource checks and quality comparisons.

`pipes_exact.cpp` is the complete submission source. Compile **exactly one** policy:

```sh
c++ -std=c++20 -O2 -DNDEBUG -DPOLICY_BF pipes_exact.cpp -o build/pipes_bf
c++ -std=c++20 -O2 -DNDEBUG -DPOLICY_SS pipes_exact.cpp -o build/pipes_ss
```

The compiler used for the checked artifacts is recorded in `manifest.json`.
`correctness_report.json` records exact flags, source/binary hashes and test coverage.
The source SHA-256 in both JSON files is the version evaluated by these fixtures.

## Shared physical rules and protocol

Input consists only of successive signed commands from stdin, terminated by `0` or
EOF. A positive value `L` inserts a pipe, assigning the next arrival PID. A negative
value `-PID` deletes that live pipe. An insert prints `digs start`; a delete prints
the original `start`. Every answer is immediately flushed. No input is read ahead.

Both policies use the same `Allocator`, `GapIndex`, coalescence and extension code.
The candidate domain is **every current maximal physical free interval**, including
the free tail. Both place at the **left edge**. If no current interval fits, the
allocator consumes the current tail and adds the minimum number of 20 m sections
needed for this request. Trench length never decreases. There is no proactive
extension, size-dependent placement side, region, structural specialist or extra
input. The policy macro changes only gap selection and its incremental index.

BF minimizes `(gap length, start)` among fitting gaps.

## Exact SS ranking, including an exact fill

Let `c_h` be the number of current maximal free intervals of positive integer length
`h`, and `Phi = sum_{h >= 1} c_h^2`. For a fitting gap of length `h` and request `L`:

* If `h == L`, the gap disappears and no length-zero gap is counted. Thus
  `Delta Phi = (c_L - 1)^2 - c_L^2 = -2*c_L + 1`.
* If `h > L`, left-edge placement replaces the gap by one gap of length `h-L`.
  These two positive lengths are distinct, so
  `Delta Phi = -2*c_h + 1 + 2*c_(h-L) + 1`
  `= -2*c_h + 2*c_(h-L) + 2`.

All placements share the same pre-insert `Phi`; minimizing this exact delta is
therefore exactly equivalent to minimizing the resulting sum of squares. SS
minimizes `(Delta Phi, h, start)` over **all** fitting current physical gaps. Gaps
with the same length have identical deltas, so each length's smallest address is
sufficient after selecting `(Delta Phi, h)`.

For each `L` from 1 to 40 an indexed binary heap contains every currently present
length `h >= L`, once. Its key is `(Delta Phi, h)`. A count change at length `h`
affects only the candidate `h` for all applicable `L`, and the candidate `h+L` for
each `L`. All affected candidates are removed while old counts remain valid; the
batched counts are then changed and the candidates reinserted. Removed/created
lengths and cancellations are handled in the same batch. This preserves the exact
ranking without restricting the domain to small lengths or sampled gaps.

For `D` current distinct gap lengths, a command changes at most three counts and
requires `O(40 log(D+1))` heap work plus physical map/set updates. At most 200,000
commands imply trench length at most 8,000,000 m; then `D*(D+1)/2 <= 8,000,000`.
Historical length IDs, dense length lookup and pipe records use `O(n + T)` space;
heap entries use `O(40 D)` space. CPU/RSS compliance is **not** inferred from these
bounds and remains for the coordinator to measure on its evaluation suite.

## Correctness fixtures and reproducibility

```sh
python3 test_correctness.py
```

This compiles production and `PIPE_ALLOCATOR_SELF_CHECK` variants for both policies.
The tiny deterministic fixtures contain hand-written cases and 32 seeded legal
streams of 96 commands. No previous result corpus, final/synthetic/Open15 stream,
platform, old Shinka or quality experiment is used.

The Python reference reconstructs all maximal gaps from independent unit cells,
enumerates every fitting physical gap, and recomputes `Phi` literally. It also
checks both closed-form deltas against that recomputation. The C++ self-check
reconstructs physical gaps independently from live pipes after every command and
compares the incremental selector against an exhaustive scan for all 40 possible
next request sizes. Produced answers additionally pass a separate unit-cell
collision/bounds/deletion validator, deterministic repetition, prefix stopping and
an interactive flush test that withholds the next command until an answer arrives.

Covered cases include exact fills, equal-length address ties, SS delta ties between
different lengths, gaps longer than 40, both-neighbor coalescence, existing tail
selection, extension with/without a tail and early termination. These checks
establish correctness on the recorded small fixtures, not a score advantage or a
general resource-limit guarantee.
