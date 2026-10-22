# Independent learned Pipes prototype v1

Local-only work authorized 2026-10-17. No website, leaderboard, submissions,
Docker, software installations, or modifications of canonical/frozen sources.
The preserved old lab baseline source is `baseline/solution.cpp`, SHA-256
`c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c`.
Its independently repeated Open15 is 30.074287976405728.

## Architecture

A new generic allocation kernel keeps actual physical gaps, active pipes and
causal request/deletion history. It has no case detection, parity routing,
predicted block sizes, fixed PID coordinates or saved official transcripts.
Old specialized code is a separate end-to-end control, not a training oracle.

The generic control is deterministic best-fit, left edge, with minimum 20 m
expansion only if needed. The learned version scores a common list of legal
actions using one shared MLP(128,32 ReLU,1). Features describe current state,
observed history and candidate geometry. No candidate index, stream/seed/test
identifier or future information enters the features. Correctness is enforced
by the allocation kernel independently of neural scores.

Candidate actions include best-fitting gap representatives, low/high-address
gaps, both endpoints, a midpoint, and an expandable tail/append option with
minimum digs for its actual coordinate. Deduplicate by (digs,start), retain
the control action and cap at 32. For physical domains with at most 32 starts,
include every start; otherwise add near-endpoint and quarter-gap offsets.
This expansion was made after the first training-only coverage audit found
omitted gains in five of eight small states, before any neural training or
calibration results. Partial labels from the earlier list are retained and
excluded from the revised training dataset. Every eighth placement with a real choice
may use the network; this fixed cadence bounds runtime and also applies when
collecting learned roll-in states. The model may abstain to the control.

## First measure, then train

Sample up to 64 causal states per synthetic stream at predetermined placement
quantiles, with at least 64 placements of warmup. Total placement count is used
only by the offline sampler, never in the model features. On synthetic training
streams; roll-in is deterministically divided between best-fit-left and
best-fit-right. At each state clone all state, force one legal action, then
replay exactly the same remaining commands to EOF with deterministic
best-fit-left. Full suffix is used only offline for labels.

Report per-state baseline minus best final trench, fraction of states with
at least 20 m gain, action type and family breakdown, and random-action regret.
These are hindsight one-step opportunities conditional on the continuation
policy and action set. They are not additive, not Q*, and not achievable online
score gains. On up to eight early states with <=256 legal positions, audit
the shortlist against all integer starts within current trench plus minimal
tail expansion. Larger states are explicitly outside exhaustive coverage.

If any measured training signal exists, collect the full fixed train dataset
and train one fixed compact network; do not manufacture positive results when
the label signal is weak. No automated architecture search. A single predeclared
DAgger round on train streams is allowed if its cost fits the experiment budget;
if omitted, state that limitation. Calibration may select fixed model epochs
and an abstention margin from [0,0.5,1,2] in 20 m units by actual labeled regret.
Training normalization is fitted on train only. Model and selected threshold
are frozen before final unseen-family generation or Open15 measurements.

## Data separation and evaluation

`data/` fixes all generator parameters and seeds before model metrics.
128 train streams: eight families, 14x6k + 2x20k per family.
24 calibration streams: same eight families, three fresh 8k traces each.
24 final streams: eight NEW family definitions, lengths 12k/30k/200k each.
Final inputs are generated only after model freeze. No row-level random split.
All candidates in a state share one suffix, so rows are not independent.

Final end-to-end controls: old saved lab baseline, generic best-fit, learned
generic allocator. Use the same official local interactor and exact paired
input hashes. Report per-family macro-average KPI delta, separate size results,
trench length, valid commands and maximum solver CPU/RSS. Bootstrap whole family
clusters, not action rows. Eight hand-designed families remain a limited pilot.

Open15 is a single post-freeze diagnostic. No feature, generator, hyperparameter
or threshold adjustment is allowed in response. It is never training data.
Require correctness, <5 s CPU/<256 MiB per test, positive unseen-family mean
with family-bootstrap lower 95% bound >0, and nonnegative Open15 total versus
the saved lab baseline before considering promotion. A trained but weaker model
is delivered as a rejected research prototype; it does not replace the baseline.

## Reproducibility and stopping

Save baseline, data-design, source, model and binary hashes; raw measurements,
training curves, finite-sample uncertainty and exact run commands. Verify kernel
replay and forced baseline equality, feature/export parity, legal action checks,
prefix independence and model-disabled equivalence before interpreting scores.
Bound this run to one data design, one architecture, one final model freeze and
one final comparison. Do not turn a failed result into repeated Open15 tuning.
