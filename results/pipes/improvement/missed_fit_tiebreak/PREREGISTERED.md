# Preregistered experiment: per-gap missed-fit tie-break

Status: locked before any candidate-vs-baseline evaluation.

## Question and single policy change

Test whether a gap-local count of prior positive requests that physically fit
the exact current gap geometry can improve the frozen allocator. For each
eligible distinct gap size, consider all same-size gaps and choose the one with
the greatest exposure count; if exposure ties, use the lower address. Then
compare these one-per-size representatives with the unchanged baseline score
and frozen cross-size tie behavior (`highSide` address direction). No other
decision changes. Cloned Monte Carlo states use the same per-size
representative, followed by the frozen global ordering.

For a gap of length `G`, exposure is the number of prior positive placement
requests with length at most `min(G,40)` since the current exact gap episode was
created. Maintain cumulative observed length counts and a scalar snapshot at
gap creation. Reset the snapshot whenever a new gap is created, or a split or
merge replaces the geometry. A request contributes only after its placement
has been decided and applied; it cannot affect its own tie-break. A remainder
created by the current placement records the post-current cumulative snapshot,
so that request contributes zero exposure to its own remainder. Removal-created
and removal-merged gaps snapshot the unchanged current prefix. Physical fit
does not depend on cohort eligibility.

The candidate reads no test identity, future input, or external state. The
feature and tie-break must agree between the live allocator, rollout copies,
and simulated continuations. The rollout candidate list uses the same
exposure-selected representative per distinct size, then the frozen global
score and `highSide` address ordering; the MC shortlist remains capped at three
distinct sizes. A focused assertion fixture verifies that a request of length
4 creating a remainder of length 6 leaves that remainder at exposure zero,
that a later fitting request increases exposure, and that a removal merge
resets exposure to zero. This fixture must pass before any solver evaluation.
If the behavior cannot be kept consistent, stop without evaluation.

## Protected artifacts

- Frozen baseline: `results/pipes/final/solution.cpp`, SHA-256
  `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Canonical source remains untouched: `src/pipes.cpp`, SHA-256
  `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.
- Candidate is an isolated copy under this experiment directory.

## Fresh synthetic validation matrix

Use 90 streams: operation horizons 16,384 and 200,000, crossed with three
length profiles (`uniform`, `short-heavy`, `long-heavy`), five deletion policies
(`random`, `oldest`, `newest`, `shortest`, `longest`), and three regimes
(`steady`, `periodic-drain`, `phase-shift`). There is exactly one stream per
cell. Assign seeds 2,026,102,300 through 2,026,102,389 in nested order: horizon
(`16,384`, `200,000`), length profile (`uniform`, `short-heavy`, `long-heavy`),
deletion policy (`random`, `oldest`, `newest`, `shortest`, `longest`), then
regime (`steady`, `periodic-drain`, `phase-shift`).

- `steady`: churn 0.42, no batch drain.
- `periodic-drain`: churn 0.38, batch threshold 500, using the repository
  generator's periodic drain behavior.
- `phase-shift`: at the midpoint, change both the length profile and deletion
  policy to the next value in their fixed lists, and change churn from 0.35 to
  0.50. For example, `uniform` becomes `short-heavy` and `random` becomes
  `oldest`; list wraparound is cyclic. The phase shift preserves a valid shared
  PID/live-set history.

Every stream has weight 1.0 and ends with a positive placement. Baseline and
candidate receive byte-identical inputs. Solver labels receive only the input
stream; generator seed and cell metadata are unavailable to them.

## Confirmatory gate

Run each of 90 inputs once with both frozen-final and candidate binaries through
the local official interactor. Require all 180 runs to consume exactly the
declared commands and finish `ok`, with no CPU (5 s) or RSS (256 MiB) violations.
For each stream compute `final_occupied_length / final_trench_length`; paired
delta is candidate KPI minus baseline KPI.

Pass only if all conditions hold:

1. The lower endpoint of the two-sided 95% percentile CI for mean paired
   stream delta is strictly above zero. Use 20,000 whole-stream bootstrap
   resamples with replacement, seed 2,026,102,395, and linear percentile
   interpolation.
2. Mean paired delta on the 45 streams with 200,000 operations is nonnegative.
3. Mean paired delta within each of the three regimes is at least `-0.001` KPI.
4. There are no invalid transcripts, crashes, or resource violations.

After the candidate and inputs are frozen, run exactly one local Open15 pair
regardless of synthetic-gate outcome. Do not tune, repeat, or run holdout-v2.
Record per-case trench/score, changed placement replies and digs where
reconstructable, CPU/RSS, source/binary/input/interactor hashes, and gate
calculation. No Docker or platform interaction.
