# Policy-conditioned rollout candidate — local qualification

## Decision

**No-go; do not promote or run Open15/holdout.** On the frozen 18-stream independent synthetic matrix, the paired estimate does not establish lower trench length: mean candidate-minus-baseline trench is **+8.89 m**, with whole-stream bootstrap 95% CI **[−51.11, +71.11] m**. Mean ΔKPI is **+0.000144**, CI **[−0.000787, +0.001108]**. Both intervals include zero. The 200k subset is directionally worse on average: mean ΔKPI **−0.000744** and **4 regressions / 2 improvements / 3 ties**. The selector made real decisions, so this is not a zero-effect cadence artifact; they did not produce a reproducible overall gain.

## Candidate and evaluation

- Candidate source: [`src/policy_conditioned.cpp`](src/policy_conditioned.cpp), frozen SHA-256 `7d6c6ddaa482b4ab2f92bd0c7a9f94c78481deff5aa44214d57430302aa13086`.
- Exact frozen baseline: `results/pipes/final/solution.cpp`, SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`. Protected canonical `src/pipes.cpp` remained `526ba58e…a1dfec8`.
- Runtime selector compares the current baseline action with P4, then runs 16 paired history-only scenarios of depth 16 under each policy. It chooses P4 iff its paired mean terminal trench is strictly smaller. No future command, PID, test ID, or known scenario is used. It runs only after the frozen solver has exhausted its 32-decision MC budget; selector cadence is 60 commands and the decision budget is 8.
- The sampler and rollout were matched against `depth16_probe.py`: 128-event history window; suffix contexts 3→2→1 then all starts; matching deletion kind and positive request length; common scenarios for both actions; same baseline/P4 continuation policies; terminal trench without a tail proxy. C++ `random.choice` matched Python in 400/400 checks. The probe’s states came from frozen-noMC trajectories, whereas this candidate activates after MC decisions on the frozen-final trajectory; transfer was therefore tested rather than assumed.
- Independent validation: 18 fresh streams, 16,384 and 200,000 commands × `uniform`/`short-heavy`/`long-heavy` × `random`/`oldest`/`newest` deletion, churn 0.48, batch disabled. Each was paired against the same exact frozen binary. All **18/18** interactor transcripts were accepted, with all expected replies present. Full input hashes are in [`inputs/validation_manifest.json`](inputs/validation_manifest.json); per-case scores and resources are in [`validation/per_case.csv`](validation/per_case.csv).
- Analysis uses 50,000 paired bootstrap replicates over whole streams, equal stream weight, seed `20261017`; details are in [`validation/paired_bootstrap.json`](validation/paired_bootstrap.json).

## Results by stream profile

| Profile | Streams | Mean ΔKPI | 95% paired CI | Mean Δ trench | Better / worse / tied |
|---|---:|---:|---:|---:|---:|
| Uniform | 6 | +0.000632 | [−0.000499, +0.002199] | +10.0 m | 2 / 1 / 3 |
| Short-heavy | 6 | −0.001228 | [−0.002695, 0] | +86.7 m | 0 / 2 / 4 |
| Long-heavy | 6 | +0.001027 | [−0.000034, +0.002670] | −70.0 m | 2 / 1 / 3 |

For 16,384-command streams, mean ΔKPI was +0.001031 (9 streams; 2 better, 0 worse, 7 tied). For 200,000-command streams, mean ΔKPI was −0.000744 (9 streams; 2 better, 4 worse, 3 tied); its 95% CI was [−0.001957, +0.000280]. Slices and intervals are exploratory at these small sample counts, but the combined gate fails and the short-heavy/200k regressions are a concern.

## Selector telemetry and resources

Across the 18 diagnostic replays: 970,125 selector calls, 144 post-gate checks, 57 rollout evaluations, and **19 P4 choices**. Fallback/skip counts: no pair 0; non-improving mean 38; same action 87; MC budget 5,624; cadence 948,406; decision budget 15,951; insufficient history 0; gap cap 0; active-pipe cap 0. MC continuation made 576 decisions and 16,512 rollouts. Ten streams had changed reply sequences (1,226,019 reply lines differed in total); eight streams changed final trench, split four improvements/four regressions. The telemetry is in [`validation/telemetry.json`](validation/telemetry.json).

Linux/GCC build: Linux 6.10.14 aarch64, GCC 14.2.0, strict warning flags passed. On 200k cases the maximum candidate solver usage was **4.407242 CPU s** and **35.20 MiB RSS**; the official limits are 5 s / 256 MiB and no harness violation occurred. A provisional engineering margin gate was set at 4.50 s / 230 MiB (10% below each official limit); the candidate is within it, but CPU headroom is narrow. The matrix harness ran up to three independent case pairs concurrently, so CPU figures are child process CPU time, while host scheduling could affect reproducibility. No resource rerun was made after the quality gate failed.

## Reproduction and scope

Build with [`build_linux.sh`](build_linux.sh); generate fresh validation inputs with [`generate_validation.py`](generate_validation.py); run paired harnesses and telemetry with [`run_validation.py`](run_validation.py); recompute bootstrap summaries with [`analyze_validation.py`](analyze_validation.py). Frozen source/binary identities and build environment are recorded in [`manifest.json`](manifest.json).

Open15, holdout-v2, the website, and the leaderboard were not accessed. The candidate is an isolated research artifact; the frozen final and canonical source were not changed.
