# Pipes architecture pilot, 2026-10-18

New direct authorization: delegate implementation to GPT-6.1 Sol and test the
discussed hypotheses. This is a bounded local pilot, not a restart of Shinka or
the completed autonomous campaign. No platform interaction or submissions.

## Hypotheses and roles

- H1: a causal regime/scenario model controlling several related placements
  can improve full-trajectory trench length over its own nonplanning kernel.
  Planning must consider a coherent continuation policy and alternative future
  regimes, rather than only reweighting the incumbent's shortlist.
- H2: a learned placement policy optimized on its own complete trajectories
  can outperform its identical untrained/control kernel. One training recipe;
  labels from a forced action followed by fixed best-fit are not H2.
- GPT-6.1 Sol implements these in separate directories. The coordinator owns
  fixtures, independent evaluation, source audit, and conclusions. No recursive
  delegation. A finite-program synthesis search is deferred in this pilot.

## Protected artifacts and controls

Incumbent is trial22, source SHA256
988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4,
saved in the completed 20261018T141843+0700-autonomous campaign's releases.
It is copied as a control; canonical sources, previous campaigns, old validation,
and existing release seeds stay untouched. No reading official input/transcripts
by implementation agents; Open15 is a post-freeze diagnostic only.

## Data and budget

Coordinator creates a fresh procedural generator and fixes its design before
metrics. Training: 24 streams of 2000 commands in six mechanisms. Development:
12 different streams of 4000 commands in the same mechanisms. Training is capped
at 512 full simulator episodes for H2; at most one selected final policy per
hypothesis. Small correctness fixtures and repairs of real implementation errors
are allowed; no parameter/threshold sweeps after diagnostic results.
Before metrics, H2 recipe is fixed as nonlinear24->4tanh->1 CEM full-trajectory
optimization (not policy-gradient RL), 8 generations x8 candidates x6 rotating
train streams +24 control episodes =408. Root selects generation4 or generation8
checkpoint by highest development family-macro F/T, exact tie chooses earlier.
This adds12 official development evaluations; total remains at most300.

Freeze both algorithms and learned parameters before generating final seeds.
Final: 24 streams, six additional mixed/shifted mechanisms, four lengths
(2000, 12000, 50000, 200000), one seed per combination. Also verify shared-prefix
causality and genuine mechanism activation. Final observations and Open15 cannot
be fed back into training or algorithm changes. An implementation defect found
there is reported as such; any repaired version needs a separately identified
evaluation, not reuse as an untouched holdout.

Evaluate five fixed variants: trial22, H1 off/on, H2 control/learned. Every full
evaluation uses the existing official native checker, max two simultaneous
workers, CPU <5 s and RSS <256 MiB per test, unchanged F/T. Open15 retains the
official weighted sum; synthetic family mean and regressions are separate.
Maximum 300 official candidate-stream evaluations, excluding tiny protocol
fixtures; do not extend into an unbounded search. Development may diagnose and
choose one predeclared trained checkpoint; final algorithms freeze together.

## Evidence and stopping

Record source/model/input/binary hashes and command lines, legality, CPU/RSS,
paired F/T and T deltas, per-family results, wins/losses/ties, mechanism counters,
and worst regressions. Recheck export parity if training and inference differ.
Repeated full runs on a small fixed subset test determinism. A stronger claim
requires positive paired final-family mean versus the identical kernel and
uncertainty not consistent with no improvement. Only six final families remain
a limited pilot. A public improvement alone is not generalization. Compare both
to trial22 separately; beating a weak control is not a new contest record.

Preserve at least 65% of every available Codex quota window, checked before
delegation and periodically. If a reliable remaining value is below 65%, stop
model work and active local jobs, preserve artifacts, and report partial results.
No paid API, reset credits, autonomous restart, or scheduled loop.
