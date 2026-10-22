# Baseline router v1: protocol before measurement

User authorized a local-only router over the existing lab baseline on 2026-10-17.
Never access the platform, leaderboard or submission API. Preserve all old files.
Baseline source: SHA256 c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c.

## Preserve the allocator

Use a mechanically generated instrumentation fork of the exact baseline.
Keep its physical gap indices, history, ownership, reserved cohort slabs,
Monte Carlo budgets, prediction gates, placement/deletion and expansion rules.
Do not substitute a new allocator or train with a best-fit continuation.
Router disabled must produce identical command responses and state evolution.

Router acts only on an existing fitting gap after baseline has selected its
normal gap/side and updated the same prediction/rollout counters. All slab,
additive-next alignment, geometric/rearmed lanes, counterfactual-capacity,
parity ownership, alternating-delete and LIFO branches remain protected.
Expansion choices remain baseline. Short-pipe and same-size-run endpoints are protected.
Every 16th placement is eligible; deterministic placement count is not a feature.

At an eligible unprotected fallback, deduplicate up to four routes by physical
start coordinate: (0) baseline; (1) opposite endpoint of baseline gap, only L>4
outside an observed long same-size run;
(2) tightest fitting gap, same baseline endpoint side; (3) second distinct
fitting gap size, same side. Alternatives keep the baseline gap's owner.
Address tie follows the baseline endpoint side.
No voluntary excavation, arbitrary coordinate search or route-specific rules
derived from an official input are allowed.

## Measure before learning

Pilot: up to 24 sampled eligible states on one train input per family (8 inputs).
Full labels if measurable headroom exists: up to 32 states per train/calibration
input, >=64 placements warmup. Sampling quantiles are offline-only, not features.
Clone the complete allocator before each sampled command, force exactly one
route, then run the SAME exact remaining commands with the original BASELINE
policy and its copied internal state. Record final trench for all legal routes.
Verify forced-baseline final trench equals a direct full baseline replay.

Report conditional one-action hindsight gain, nonzero fraction, route/family
coverage, and uniform-random regret. No additive or achievable online claim.
At most one predeclared aggregate-data round from learned roll-in states is
allowed; continuation remains original baseline. Do not disguise previous-input
states as new independent streams or include them in independent validation.

## Small model and selection

One action scorer MLP(128,16 ReLU,1), 2,081 parameters; shared causal state and
candidate geometry, with semantic route identity allowed for this explicit
router. No input/test/seed/PID identifier, future command, suffix summary or
precomputed placements as a feature. Fixed Adam recipe from learned-v1:
seed 20261017, lr .001, Huber/pairwise mix 50/50, max120/patience15, train-only
normalization and clipping. No architecture search. Baseline is always legal
and is retained unless a calibrated predicted margin is exceeded.

Calibration selects epoch and margin from [0,0.5,1,2] in 20m units using labeled
actual costs. Then assess ONE model on full calibration rollouts. If its actual
mean KPI delta vs baseline is negative, deploy an abstaining router and record
the learned candidate as rejected. Do not tune another model to the rollout.
Allow positive labeled signal to justify training, never label it a rollout win.

## Evaluation and freeze

Separate fresh synthetic train/calibration/final inputs, seeds and SHA.
64 train: 8 families x (6x4k +2x16k); 16 calibration: 8x2x8k.
24 final: 8 new families x 12k/30k/200k. Final design fixed before measurements;
inputs generated only after source/model/threshold/binary freeze.

Final comparisons: exact old baseline, instrumentation with router disabled,
and frozen learned candidate. If a calibration safety gate rejects the candidate,
report both its frozen diagnostic result and the abstaining deployable policy;
never call the baseline tie a learned improvement. Use official LOCAL interactor,
paired input hashes, per-family macro KPI and whole-family bootstrap, per-length
results, and 5s CPU/256MiB limits. Eight designed families remain a limited pilot.

Open15 is optional ONE post-freeze diagnostic, after independent final evaluation.
No decisions, data, features, gates, hyperparameters or thresholds may change in
response. No official input is used for training/labeling/selection. Require
positive unseen-family delta with bootstrap lower95%>0, no resource/correctness
failure, and nonnegative total Open15 vs old baseline before promotion.

## Verification and stopping

Check exact disabled equivalence, cloning, physical legality, reserved slabs,
Python/C++ scores and chosen-action parity, prefix independence, protected
branch bypass, baseline replay equality, and hashes. Save raw data and command
manifests. One design, one architecture, at most two fits, one final candidate;
no repeated Open15 optimization. Rejected results are preserved, not deleted.
