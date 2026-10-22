# H2: complete-trajectory CEM placement policy

This is a bounded nonlinear policy pilot, optimized with parameter-space CEM.
It is **not policy-gradient RL** and does not establish a general conclusion
about end-to-end neural allocation. All105 MLP parameters are optimized; there
is no learned residual over a handcrafted best-fit action score.

## Recipe frozen before training metrics

- Shared actor:24inputs →4tanh hidden units →1scalar score, double precision.
  Physical inputs: request size, extension, left/right residuals, span width,
  relative address, tail/split/exact-fit, capacity loss and historical demand
  fit, actual neighboring sizes/ages/outer gaps/coalescence spans. Causal history:
  occupancy, observed churn, same-size run and observed deletion-size activity.
- At most16actions: best fit; endpoints of four smallest fitting physical
  spans; address-first/address-last fitting spans; tail endpoints; midpoint and
  quarter point of the smallest fitting span. Duplicates removed. Several spans
  of the same width remain distinguishable through position and neighbors.
- Every fourth placement, starting with the first, uses the actor. Other
  placements use generic left best-fit. The same complete policy runs throughout
  each episode. No forced-action labels, target rollouts, or fixed continuation
  labels exist. Deletions update the identical physical state in every mode.
- Control: actor disabled, deterministic left best-fit on that same state.
  An exactly zero actor has the same behavior by first-candidate tie breaking.
- Terminal objective:mean across six mechanisms of
  `terminalF/terminalT - identical_controlF/controlT`. The control subtraction is
  independent of a candidate's actions; it does not change same-generation ranks.
- Eight CEM generations, eight sampled policies each, six full2000-command
  streams per policy, one per mechanism. Replicates rotate0,1,2,3,0,1,2,3.
  Plus24 complete control episodes:408 total training simulator episodes.
- Seed2026101802; custom xorshift64*/Box-Muller sampler. Initial mean0, std0.35.
  Two elites, rank ties prefer lower candidate index. Mean and variance smoothing
  use0.35 new +0.65 old; marginal std floor0.06. No architecture or threshold
  sweep. Population size and dimensionality make this an underpowered pilot.
- Export CEM distribution means after generations4 and8. The coordinator selects
  the greater dev family-macro F/T (equivalently paired delta against control),
  exact tie preferring generation4. No post-dev parameter or algorithm changes.
- Neither final fixtures nor official inputs/transcripts are read for training.
  Training metrics alone do not establish superiority or generalization.

## Build

From this directory:

```sh
c++ -std=c++20 -O3 -DNDEBUG -Isrc src/train.cpp -o bin/train
c++ -std=c++20 -O3 -DNDEBUG -Isrc src/check.cpp -o bin/check
c++ -std=c++20 -O3 -DNDEBUG -Isrc -DLEARNED_ENABLED=0 src/solver.cpp -o bin/control
c++ -std=c++20 -O3 -DNDEBUG -Isrc -DLEARNED_ENABLED=1 src/solver.cpp -o bin/learned
```

`MODEL_HEADER` can select an exported checkpoint header. Both modes share the
same solver source, physical allocator, observation computation, and scorer.
Interactive stdout contains protocol responses only; stderr reports counts for
placements, eligible cadence positions, actor decisions, actual changed actions,
candidate count, selected interior/tail/right-endpoint actions and terminal F/T.

## Provenance and verification

`training/provenance.json` contains source/input/policy hashes and exact process
arguments. `training/episodes.jsonl` preserves every complete simulator episode
including control, correctness, terminal objective and mechanism counters.
`training/generations.csv` preserves CEM selection history. Population files are
retained, as are both predeclared checkpoint means. Tiny correctness/parity checks
are separate from training and are not candidate selection measurements.

The allocator was copied only from the permitted
`prototypes/pipes_learned_v1/src/allocator.hpp`; old models/data/holdouts are unused.
Its old candidate/features methods are retained but never called by this actor.
