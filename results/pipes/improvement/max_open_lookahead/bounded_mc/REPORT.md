# Bounded Monte Carlo rollout candidate

## Status

**Corrected candidate frozen; canonical solver unchanged.** The rollout model now matches the allocator's tie behavior for equally sized free spans. The corrected candidate passed all 15 official open cases twice, with byte-identical solver/judge outputs on the repeated run. It improves the official weighted sum over the frozen `cohort_owner` baseline by `0.041313394076987` and has no regressions on the reused `holdout-v2` comparison.

The earlier rollout build had a simulation mismatch and is retained under [`v1-model-mismatch/`](v1-model-mismatch/). Its score is historical evidence only; the corrected source below is the copyable artifact.

## Candidate and model correction

- Source: [`cohort_owner_mc_rollout.cpp`](cohort_owner_mc_rollout.cpp)
- Source SHA-256: `fadbe93b0ae2d1dd1ff2ebce3dbdf384f3969272865f108729092b9d8cb98be3`
- Strict optimized binary: [`solver_mc_corrected`](solver_mc_corrected), SHA-256 `d48784bc2a26e72755fd52fa1222607f17c88cda5e1fd222adc2cdfc51211a2f`
- Diagnostic binary: [`solver_mc_corrected_diag`](solver_mc_corrected_diag), SHA-256 `738dc2fd693aceda5810ddce8c896628f828a1648e3d68f350446df25b3cfe22`
- Disabled-control binary: [`solver_mc_corrected_disabled`](solver_mc_corrected_disabled), SHA-256 `6e727d0628e208de1889fed21e2c409ca81acd1dc2ba247cbcc5821354d10aed`

The audit found that the previous `RolloutState::bestGap` compared every address in an equal-length group. The real allocator indexes spans by `(length, start)` and evaluates only the lowest-address span for each distinct length. The corrected simulation suppresses later equal-length spans after the first eligible address. Only the simulator changed; the real allocation policy was not changed. The main source was frozen after the correction and all reported corrected runs use this same hash.

## Official open results

Harness: `tools/pipes_harness.py` (`65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d`), using the official `tools/interactor` (`47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`). Every input hash is recorded in [`open-comparison.csv`](open-comparison.csv).

| Case | Weight | Corrected weighted score | `cohort_owner` weighted score | Delta |
|---:|---:|---:|---:|---:|
| 1 | 0.1 | 0.090000000000000 | 0.090000000000000 | 0 |
| 2 | 1 | 1.000000000000000 | 1.000000000000000 | 0 |
| 3 | 1 | 0.750000000000000 | 0.750000000000000 | 0 |
| 4 | 1 | 0.666666666666667 | 0.666666666666667 | 0 |
| 5 | 1 | 0.809554140127389 | 0.809554140127389 | 0 |
| 6 | 1 | 0.900000000000000 | 0.900000000000000 | 0 |
| 7 | 1 | 0.986470588235294 | 0.952840909090909 | +0.033629679144385 |
| 8 | 1 | 0.984468085106383 | 0.984468085106383 | 0 |
| 9 | 1 | 0.492341356673961 | 0.492341356673961 | 0 |
| 10 | 1 | 0.800000000000000 | 0.800000000000000 | 0 |
| 11 | 1 | 0.900132625994695 | 0.900132625994695 | 0 |
| 12 | 4 | 3.972480620155039 | 3.964796905222437 | +0.007683714932602 |
| 13 | 4 | 3.892682926829268 | 3.892682926829268 | 0 |
| 14 | 4 | 3.987731359069275 | 3.987731359069275 | 0 |
| 15 | 10 | 9.540622436890550 | 9.540622436890550 | 0 |
| **Total** | **32.1** | **29.773150805748520** | **29.731837411671535** | **+0.041313394076987** |

All 15 cases passed. The corrected candidate also exceeds the frozen T46 result `29.447164543483026` by `0.325986262265495`. Only cases 7 and 12 changed against `cohort_owner`; neither regressed. Relative to the earlier mismatched model, the corrected open score is higher by `0.022677484787017`, entirely from case 7; case 12 and the other cases are unchanged.

Diagnostic-only reruns show the rollout was active on both improved cases: case 7 used 32 decisions / 1,128 rollouts; case 12 used 32 decisions / 888 rollouts. These diagnostics were built from the same frozen source with stderr counters enabled; scoring runs use the non-diagnostic binary.

The corrected official run is in [`official-open-mc-model-corrected/`](official-open-mc-model-corrected/), and the frozen repeat is in [`official-open-mc-model-corrected-repro/`](official-open-mc-model-corrected-repro/). The `judge_output.txt`, `solver_stderr.txt`, and `interactor_stderr.txt` files match byte-for-byte for every case. Both runs scored exactly `29.77315080574852`.

## Reused holdout-v2 comparison

The corrected candidate was run on the existing 12-case `data/pipes/synthetic/final-holdout-v2/` set and compared with the already frozen original `cohort_owner` run. No tuning was done on this set between runs. Results and every input hash are in [`holdout-v2-comparison.csv`](holdout-v2-comparison.csv).

- Corrected candidate: `5.135264324280470`
- Original `cohort_owner`: `5.135100030340453`
- Delta: `+0.000164293940017`
- No case regressed. Cases `case-01` and `case-10` improved by `+0.000060573016329` and `+0.000103720923688`; the other 10 cases were unchanged.

This is a reused local synthetic holdout, not evidence about unseen official tests.
The corrected and earlier model-mismatch candidates produced identical holdout scores and per-case outcomes.

## Forecast inputs and bounded work

At a real placement, the candidate first obtains the baseline gap. Rollout is eligible only when all of these online conditions hold: fewer than 32 rollout decisions have been used, at least 32 observed events are available, there are at most 64 current free gaps and at most 4,096 active pipes, and at least two fitting gap candidates with slack no greater than 40 are available. The top candidate must equal the baseline allocator's selected gap; otherwise the baseline action is kept.

For an eligible decision, the solver tests at most three gap candidates. For each, it runs 12 deterministic continuations, each exactly four events deep. The continuation is sampled from contiguous blocks in the most recent 128 observed events, first looking for a suffix-context match of up to three events and otherwise sampling from the recent window. The observation buffer itself retains at most 256 events. It contains observed positive pipe lengths and removal ranks-from-newest, quantized to permille and calculated online from the active-PID Fenwick tree. The rollout clones the current gaps, active pipes, and policy statistics; it applies the candidate placement and then replays the sampled historical events using the existing `cohort_owner` placement rule. It accepts a different gap only when the mean predicted trench length improves by at least 1 m.

No future input commands, test number, or test-specific branch is read by the solver. Scenario selection is deterministic from current state and observed history. Hard ceilings are 32 decisions × 3 candidates × 12 trials = **1,152 rollouts**, each with four forecast events (at most **4,608 forecast events**, plus the counterfactual candidate placement per trial). The solver itself does not search or inspect unobserved future commands.

## Resource check

The 200,000-command synthetic stress test [`stress_200k_mc_cap_v2.in`](stress_200k_mc_cap_v2.in), SHA-256 `41028468e6ae0ea94779c45cd770bcd9dab468035266d13420938b8e57e097ab`, deliberately alternates lengths 39 and 40 after constructing three reusable gaps. This avoids the base policy's 46-identical-length side switch and reaches the rollout ceiling. Diagnostic stderr confirms `mc_decisions=32 mc_rollouts=1152`.

| Run | Commands | Rollout count | Solver CPU | Peak solver RSS | Harness limits |
|---|---:|---:|---:|---:|---|
| Official open, run 1 (max over 15) | 200,000 in case 15 | Not instrumented in scoring binary | 0.945238 s | 9.468750 MiB | 5 s / 256 MiB |
| Official open, repeat (max over 15) | 200,000 in case 15 | Not instrumented in scoring binary | 0.948193 s | 9.546875 MiB | 5 s / 256 MiB |
| Synthetic stress at the full rollout ceiling | 200,000 | 1,152 | 0.850672 s | 7.703125 MiB | 5 s / 256 MiB |

The CPU/RSS values are solver-child measurements from the harness on Apple Silicon. The 200k stress is a bounded-load check, not a benchmark of allocation quality. All measured runs stayed below the harness limits.

## Reproduction

Build the frozen source with Apple Clang 17 using:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror \
  results/pipes/improvement/max_open_lookahead/bounded_mc/cohort_owner_mc_rollout.cpp \
  -o results/pipes/improvement/max_open_lookahead/bounded_mc/solver_mc_corrected
```

The exact recorded harness runs were:

```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_lookahead/bounded_mc/solver_mc_corrected --name cohort_owner_mc_rollout_model_corrected --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/max_open_lookahead/bounded_mc/official-open-mc-model-corrected --cpu-limit 5 --memory-limit-mb 256

python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_lookahead/bounded_mc/solver_mc_corrected --name cohort_owner_mc_rollout_model_corrected_repro --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/max_open_lookahead/bounded_mc/official-open-mc-model-corrected-repro --cpu-limit 5 --memory-limit-mb 256

python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_lookahead/bounded_mc/solver_mc_corrected --name cohort_owner_mc_rollout_model_corrected_holdoutv2 --interactor tools/interactor --tests data/pipes/synthetic/final-holdout-v2 --out results/pipes/improvement/max_open_lookahead/bounded_mc/holdout-v2-mc-model-corrected --cpu-limit 5 --memory-limit-mb 256

python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_lookahead/bounded_mc/solver_mc_corrected_diag --name mc_model_corrected_stress_200k_cap_v2 --interactor tools/interactor --tests results/pipes/improvement/max_open_lookahead/bounded_mc/stress_200k_mc_cap_v2.in --out results/pipes/improvement/max_open_lookahead/bounded_mc/stress-cap-v2-model-corrected --cpu-limit 5 --memory-limit-mb 256
```

The original comparison builds are frozen in `results/pipes/improvement/cohort_owner_audit/`: owner binary SHA-256 `26e2b1285825406ed0c4390cfdef2e1c9717d1aed30769430f78f9a613a0bf1d`, T46 binary SHA-256 `bce18761000c395c9aacc6f7b1883fe48a279df3cb86d20a3c8fd95882c1b4a0`. The source and all run manifests are enumerated in [`manifest.json`](manifest.json).

## Interpretation

This is a small empirical gain on the public open set and a tiny positive result on a reused synthetic holdout. The rollout is a short, history-resampled heuristic, not a calibrated forecast; it may not generalize to future command sequences. Keep it as a separate candidate until independently reviewed; it has not been copied into `src/pipes.cpp`.
