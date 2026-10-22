# Confirmatory synthetic gate

This gate is fixed before running the candidate on `inputs/qualification_confirmatory/`.

## Matrix

- 60 deterministic streams, each evaluated by both the frozen solver and the learned candidate.
- 2 command counts: 16,384 and 200,000.
- 3 pipe-length profiles: `uniform`, `short-heavy`, `long-heavy`.
- 5 deletion policies: `random`, `oldest`, `newest`, `shortest`, `longest`.
- 2 stream regimes: steady (`churn=0.48`, `batch=0`) and periodic drain (`churn=0.42`, `batch=500`).
- Every stream uses a new seed starting at 1,470,000,000. The same input bytes are used for both solvers.
- Inputs use a local order-statistics implementation of `tools/generate_pipes_synthetic.py`; accept them only after exact command-list equality with that generator on the small-seed equivalence checks.
- Every stream has weight 1. The matrix is not used to fit or tune the model.

## Pass criterion

The candidate passes only if both conditions hold:

1. The 2.5th percentile of a 20,000-replicate, whole-stream paired bootstrap CI for the equally weighted mean `candidate KPI - frozen KPI` over all 60 streams is strictly greater than zero. Bootstrap seed: `2026101718`.
2. The equally weighted mean `candidate KPI - frozen KPI` on the 30 long streams (200,000 commands) is nonnegative.

Each bootstrap replicate resamples the 60 stream-level paired differences with replacement. The CI uses linear percentile interpolation. KPI is the interactor's occupied-length/trench-length ratio; all stream weights are 1.

If either condition fails, this candidate is a no-go for further official-data evaluation: do not run holdout-v2 or Open15. Report profile, deletion-policy, horizon, and regime slices as diagnostics only; they do not alter the gate.

## Scope and limits

Passing permits a holdout-v2 check; it does not establish broad generalization. Open15 may be considered only after the holdout check. No website, leaderboard, Docker, test-ID feature, or future runtime input is used.
