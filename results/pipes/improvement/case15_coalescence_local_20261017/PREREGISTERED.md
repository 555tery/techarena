# Local deletion-seam experiment, 2026-10-17

User authorized local work on case 15, with no platform access or submissions.
Canonical and frozen-final sources remain unchanged.

## Fixed baseline

`../case9_push_20261018/residual_slack/source/latest_leader_plus_c2.cpp`
SHA-256 `c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c`.
Saved Open15 30.074287976405728; case 15 trench 438640 m.
Earlier wiki status is stale relative to this archived full run.

## Hypothesis and distinction from earlier failures

Earlier policies matched neighboring lifetime classes or maximized hypothetical
merged length/lineage. This experiment estimates the expected *unusable meters*
removed by merging a remainder with a neighbor and its existing outer gap.
The relevant distinction is the geometry of the resulting hole relative to the
observed size demand, rather than closeness of two lifetime probabilities.
This remains a new test within an already weakly supported research family.

Forecast training is delayed: a placement enters the lifetime histogram only
after 256 actual commands have elapsed. Its label is the observed death age,
clipped at 256. Thus persistent live pipes enter the training denominator and
early completed lifetimes do not constitute the entire sample. Horizon is 64
commands, used only for neighbors younger than 192 commands. All thresholds,
profiles and candidate variants below are fixed before observing scores.

Let `W(g)=g*Pr(recent request > g)`, with W(0)=W(g>=40)=0.
For remainder r, adjacent pipe B and outer free gap z, the merge benefit is
`p(B removed within H | B alive now) * [W(r)+W(B+z)-W(r+B+z)]`.
Only past events and current geometry are used. This is a surrogate, not a
proved expected trench saving. In particular it ignores simultaneous releases,
changes in demand and future allocations. It may fail empirically.

## Exactly two policy variants

1. E: choose the endpoint of the baseline-selected gap by the merge benefit.
2. G: additionally inspect at most four low-address and four high-address gaps
   of the *same length* as the baseline-selected gap, retaining baseline fit cost.

Both require at least 128 past lengths, 128 mature global observations, at
least 16 observations at risk for a neighbor's length and 1 m of estimated
benefit above the baseline action. Use 32 global pseudo-observations for
shrinkage. Skip cohort ownership, active same-length runs and existing explicit
next-size alignment actions. Never reserve space, copy a pipe or add a dig to
accommodate this overlay. The incumbent algorithm may still dig normally.
No parameter tuning using official case 15, test IDs, absolute command indexes,
fixed PIDs, input hashes or saved future commands is allowed.

## Evaluation and stopping rule

Independent agent fixes 12 development and 12 sealed-validation streams in
`validation/` without reading official case 15. Two sealed streams have 200k
commands. Sealed streams are evaluated only after source and finalist freeze.
Use exact current sources and binaries with strict C++20 warnings.

Run baseline and both variants on development, one pass each. Select by mean
paired KPI delta, requiring positive mean and no individual trench regression
above 2%. If neither qualifies, both are rejected; any case-15 run is explicitly
a diagnostic of rejected variants and cannot be used to retune them.

If a candidate qualifies, freeze it and compare on the sealed suite and Open15.
Require all protocol/resource checks, nonnegative Open15 total, actual case-15
saving, positive sealed mean, and paired bootstrap 95% CI lower endpoint above
zero before promotion. A reused holdout is only a regression check. If this
gate fails, retain the baseline and report the negative evidence. No broad
parameter sweep or automatic agentic search is authorized by this protocol.

Record source/input hashes, all per-case deltas, correction counts, CPU/RSS and
finite-sample uncertainty. A higher Open15 score alone is not generalization.
