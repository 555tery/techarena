# H1: causal scenarios and conditional group plans

Bounded local prototype, fixed before coordinator development/final evaluation.
No official input, platform, old campaign, final generator or training fixture
was read by this implementation. No trained parameters or external libraries.

## Paired controls and build

Run from repository root (C++20, no install):

```sh
clang++ -std=c++20 -O2 -DNDEBUG -DPLANNER_ENABLED=0 prototypes/pipes_architecture_v2_20261018/planner/solver.cpp -o prototypes/pipes_architecture_v2_20261018/planner/h1-off
clang++ -std=c++20 -O2 -DNDEBUG -DPLANNER_ENABLED=1 prototypes/pipes_architecture_v2_20261018/planner/solver.cpp -o prototypes/pipes_architecture_v2_20261018/planner/h1-on
```

`off` is best-fit, left endpoint, then left tail extension. Both modes use the
same copied physical allocator and collect identical causal prefix statistics.
The only policy switch is `PLANNER_ENABLED`. No incumbent branches are copied.
`allocator.hpp` is byte-identical to the permitted `pipes_learned_v1` allocator;
its feature extractor/candidate classifier is unused. Source hashes and exact
compiler commands are in `manifest.json`. The solver reads one command, replies
and flushes immediately; telemetry goes only to stderr after termination.

## Mechanism

The online model observes the most recent 512 commands, pooled arrival counts,
length transitions between four size groups, event transitions, same-size runs,
deletion ages and insertion-order deletion quantiles. An online Fenwick index
maps simulated deletion quantiles to real live PIDs without copying all pipes.

Each planning decision creates three deterministic, prefix-seeded scenarios of
14 future commands: (1) local event/size transitions and persistence, (2) a
pooled-size phase switch, (3) a build/retire cohort cycle. Cycle lengths are the
observed mean arrival/deletion runs clipped to 2--5. The cohort weight is
`0.05 + 0.35*evidence`; evidence counts nearby-birth deletions close in observed
command time. Other weights are `0.65-w/2` and `0.35-w/2`. Young-cohort retirement
of new simulated pipes is enabled only by mean deletion rank >=0.65 and mean
age <=64; otherwise this expert retires adjacent initial insertion ranks.
These are heuristic regime hypotheses, not a calibrated probabilistic model.

Root candidates (at most 10) include best-fit and opposite endpoints, distinct
equal-size gaps at different addresses, first/last fitting gaps and tail ends.
An interior size-preserving split is included when capacity remains. Future
placements branch on up to six exact coordinates. Width-three beam search
optimizes several placements with immutable pipe positions and coherent PID
deletions, including virtual births. It preserves geometrically different plans
and lifetime labels. It does not use a fixed best-fit continuation for scoring.

Per-scenario terminal objective is `8*T + 2*additional_probe_trench`, where the
five-placement probe uses that scenario's causal arrival model. Beam pruning
uses current three-placement probe growth and a second exact probe after
projecting known scenario retirements. Root choice minimizes 90% weighted mean
plus 10% worst scenario. These finite probes approximate future fragmentation;
they are not the contest KPI or a bound on the attainable full-run result.

For the selected common root, all three best contingent plans are retained.
Every actual command filters paths by exact arrival size or actual deletion PID;
virtual births map to the actual insertion PID. A matching arrival executes the
highest-weight compatible plan's coordinate after a full physical legality
check. Paths prescribing different coordinates are dropped. Mismatch or failed
legality invalidates paths immediately; exhausted paths terminate. With no
compatible path the solver uses best-fit or starts a new budgeted plan. Thus
several planned actions can actually execute between replans; stale forecasts
are never consumed across a mismatch.

Scenario-wise beam recourse can exploit knowledge of its own sampled future.
The retained-plan filter implements only compatible forecast prefixes, so the
scoring value is optimistic relative to a fully causal future policy. Prefix
matching can be rare, especially for high-entropy sizes/deletions. Record actual
plan execution before interpreting this pilot as evidence about group control.

## Scale and finite budget

There is no total-live-count gate. A snapshot contains all candidate root gaps,
free neighbors of every predicted real deletion, the tail and optional future
best-fit gaps, at most 74 initial spans. Other free regions are frozen/unavailable
inside the forecast. Selected PID deletions and coalescence within captured
regions are exact; omitted remote capacity makes the approximation pessimistic
and potentially changes rankings. If mandatory spans exceed the cap, abstain.
At most 96 spans are held after simulated splits/deletions/probes.

Total search is capped at 420000 expanded nodes and 128 scored roots. Command
epochs `<2048`, `<16384`, `<65536`, and later have root quotas 24/32/32/40 and
minimum replan strides 64/384/1536/4096. Search first requires 16 observed events.
These deterministic limits spread work over long streams, but influence remains
sparse. A negative result with low execution/coverage does not refute a general
scenario-planning hypothesis. CPU<5s/RSS<256MiB at 200k remains the coordinator's
independent verification obligation; tiny checks establish no resource claim.

Telemetry reports all insertions, candidate-eligible insertions, fully scored
roots and changed outputs in live buckets `<64`, `64..511`, `512..4095`, `>=4096`.
`changed` includes root and executed continuation changes against current full
best-fit. Other counters expose region compression/abstention, work exhaustion,
regime votes, cohort influence on root choice, selected non-greedy recourse,
actual planned placements/kernel changes, matched deletions and path aborts.
`cohort_decisive` is removal-of-expert disagreement, not proof of causation.

## Tiny verification

```sh
clang++ -std=c++20 -O2 -DPLANNER_ENABLED=1 prototypes/pipes_architecture_v2_20261018/planner/selftest.cpp -o prototypes/pipes_architecture_v2_20261018/planner/selftest
prototypes/pipes_architecture_v2_20261018/planner/selftest
python3 prototypes/pipes_architecture_v2_20261018/planner/test_protocol.py --on prototypes/pipes_architecture_v2_20261018/planner/h1-on --off prototypes/pipes_architecture_v2_20261018/planner/h1-off
```

`selftest.cpp` checks live rank, repeated deterministic scenarios, exact local
geometry against the physical allocator, and a deliberately scenario-matching
fixture for retained-plan execution/PID mapping. `test_protocol.py` independently
checks overlap/digs/deletion coordinates, zero termination, repeat determinism,
shared-prefix causality and command-by-command flush on a 184-command handwritten
fixture. It is not an official harness or representative quality evaluation.
The handwritten mixed fixture had zero continued planned actions; the targeted
matching fixture executed twelve, including two deviations from current BF.
