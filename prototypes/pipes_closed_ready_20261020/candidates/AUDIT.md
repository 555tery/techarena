# Candidate construction audit

`../build_candidates.py` produces exactly three policies: `online`, `full`,
`hybrid`. Compilation uses `clang++ -std=c++17 -O2`; MSVC compilation has not
been performed. There are no platform interactions in the builder or solvers.

## Core provenance and parity

The pinned original is SHA256
`988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4`.
Its unchanged copy and binary are in `build/reference/`.

Embedding changes are limited to naming the namespace, adding an `emit` flag,
making import helpers accessible, and guarding the original three output
sites. Output functions become instance functions to access `emit`. Reversing
these changes must recover the original core byte for byte; the builder asserts
this before compiling. Allocation decisions and original internal Monte Carlo
logic are unchanged. No cache32 `Planner`, episode restrictions, scale gate,
per-command core clone, or fallback proposal wrapper is included.

`online/parity-open15.json` records direct noninteractive stdout equality against
the unchanged reference on all fifteen existing Open inputs, 280156 commands.
This verifies output parity, not interactive timing or score. Full/hybrid
evaluation is deliberately left to the coordinator.

## Replay and handoff

The public command/position tables come from cache32. Multiple matching prefixes
must agree on an address. A command mismatch, conflicting address, invalid
physical replay placement, or hybrid guard rejection causes one permanent
handoff, before answering that command. No future command is read ahead.

Handoff rebuilds births/deaths and age exposure, observed ranks/history, run and
cohort counters including relative deletion parity, trend/scale latches, active
end index and Fenwick counts using already answered commands and their immutable
physical positions. `recordPrimalEvent` registers lifetime-model births. PID,
physical positions/activity and total Fenwick count are checked after import.

This is a foreign physical layout, not the original online trajectory. All
physical free gaps are imported as shared; their age is the final observed
deletion epoch. Policy-specific reservations are discarded, the full physical
free space is exposed, and decision/model caches and original MC budget start
fresh. These are explicit import semantics, not claims of recovering nonexistent
original gap ownership or policy decisions. Later commands use the same trial22
methods without restrictions.

Shadow memory is freed before creating the imported core. After import, the
physical snapshot, observed-command vector, decoded tables and prefix matches
are released. Import occurs once, O(N log N); there is no O(N) snapshot on every
command. Peak CPU/RSS still require evaluator measurement.

## Hybrid guarantee

`hybrid` advances an exact trial22 shadow from the first command, with output
disabled. It permits a replay placement only when the physical resulting trench
is no longer than the shadow trench after this command, and the placement touches
a boundary of its complete physical free interval after any necessary digging.
Interior splits are rejected. No fixed public IDs, waiting threshold, or seed
condition is used. This bounds trench length only on the accepted replay prefix;
it does not guarantee any bound on performance after handoff or on hidden tests.

Every command response flushes before the next command is read. stderr reports
`replay_placements`, `fallback_commands`, `abort_reason`, 1-based `abort_step`
(zero if no handoff), and final `T`.

## Portability and hashes

The old table contained concatenated string literals larger than MSVC's literal
limit. This representation stores the original short literals separately and
joins one table at startup; encoded payloads are unchanged. Aggregate `build.json`
records original/core/table/payload/source/binary hashes and import semantics;
each candidate also has a small `build.json`.
