# Causal survival-hazard allocation: screening report

## Conclusion

**Reject this policy.** The best screen configuration reduced case 15 trench by 120 m, but its full official-open score was lower than the current baseline by **0.015181219284 / 32.1**. Case 13 regressed by 20 m and its weight 4 more than erased gains from cases 8, 11, and 15. The candidate passed 15/15 protocol checks and resource limits, but its memory footprint is about 108 MiB in the full run (up to 114.3 MiB in screening), versus 9.5 MiB for baseline. No synthetic-development or holdout-v2 run was made after the full-open regression.

## Causal method tested

- Infer a coarse removal regime from the mean of the last 64 observed removal ranks from newest: mean ≤250‰ → LIFO-like; mean ≥750‰ → FIFO-like; otherwise mixed. Require 16 observed removals before using a non-mixed regime.
- At placement, record the current inferred regime and placement count on the pipe. On removal, record its observed lifetime in placement events into an age histogram indexed by exact length and birth regime (16-placement age bins). Estimate probability of removal within the next horizon from completed lifetimes at risk plus currently active same-length/same-birth-regime pipes treated as right-censored.
- For an already selected gap, estimate the incoming pipe risk at age 0 and adjacent pipes’ risk at their current age, under the current inferred regime. When the two boundaries have sufficiently different risk, place at the edge next to the boundary with the closer predicted hazard, grouping pipes expected to have similar removal timing. The existing baseline gap selection and rollout remain in place.

This policy uses only observed past/current commands, known pipe PIDs/lengths, placement times, and removal ranks. It does not read the test ID, the input file, future commands, environment variables, or score files. The hazard itself remains a forecast, not a guarantee; mode can change after placement, and histogram buckets are coarse.

## Screening variants

All tests used the same current candidate baseline source SHA-256 `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`. Initial screen used cases 5, 9, and 15.

| Configuration | Horizon | Match tolerance | Neighbor separation | Weighted score / 12 | Delta vs baseline | Case 15 trench | Max CPU | Max RSS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | - | - | - | 10.854660882 | +0.000000000 | 438,920 m | 1.167 s | 9.53 MiB |
| Hazard default | 64 | 120 | 60 | 10.850315545 | -0.004345337 | 439,120 m | 1.167 s | 116.13 MiB |
| H32 | 32 | 80 | 80 | 10.857269986 | +0.002609104 | 438,800 m | 1.658 s | 114.27 MiB |
| H128 | 128 | 200 | 80 | 10.850315545 | -0.004345337 | 439,120 m | 1.758 s | 103.08 MiB |
| Wide match | 64 | 250 | 60 | 10.848578518 | -0.006082364 | 439,200 m | 1.479 s | 116.19 MiB |

H32 was the only positive three-case screen, by 0.002609104 score points, entirely from case 15. Cases 5 and 9 were unchanged in every tested variant.

## Full official open set: baseline vs H32

Baseline: **29.785293754007 / 32.1**. H32: **29.770112534723 / 32.1**. Delta: **-0.015181219284**. Both were valid on 15/15 tests.

| Case | Weight | Baseline trench | H32 trench | Δ trench | Δ weighted score |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.1 | 20 m | 20 m | +0 m | +0.000000000 |
| 2 | 1 | 20 m | 20 m | +0 m | +0.000000000 |
| 3 | 1 | 20 m | 20 m | +0 m | +0.000000000 |
| 4 | 1 | 60 m | 60 m | +0 m | +0.000000000 |
| 5 | 1 | 62,800 m | 62,800 m | +0 m | +0.000000000 |
| 6 | 1 | 20 m | 20 m | +0 m | +0.000000000 |
| 7 | 1 | 1,700 m | 1,700 m | +0 m | +0.000000000 |
| 8 | 1 | 4,700 m | 4,680 m | -20 m | +0.004207129 |
| 9 | 1 | 62,440 m | 62,440 m | +0 m | +0.000000000 |
| 10 | 1 | 15,380 m | 15,380 m | +0 m | +0.000000000 |
| 11 | 1 | 22,620 m | 22,580 m | -40 m | +0.001594566 |
| 12 | 4 | 10,320 m | 10,320 m | +0 m | +0.000000000 |
| 13 | 4 | 3,280 m | 3,300 m | +20 m | -0.023592018 |
| 14 | 4 | 37,820 m | 37,820 m | +0 m | +0.000000000 |
| 15 | 10 | 438,920 m | 438,800 m | -120 m | +0.002609104 |

Full-open resources: baseline CPU sum/max **1.712041 / 1.292794 s**, max RSS **9.500 MiB**; H32 **2.599558 / 1.820347 s**, max RSS **107.750 MiB**. Worst H32 case was case 15 at **1.820347 s CPU** and **107.750 MiB RSS**, below 5 s / 256 MiB but materially heavier than baseline.

## Reproducibility

- Candidate implementation: [`candidate.cpp`](candidate.cpp), source SHA-256 `2fe202bb534bcb5808e310b508e48ca74dca0525ce74d41e3f381019560378d0`.
- H32 binary: [`short-horizon.bin`](short-horizon.bin), SHA-256 `a94b0375629982856683f7155a833df421b444ee0028e773fa3147104086d90e`.
- Baseline binary: [`baseline.bin`](baseline.bin), built from the fixed baseline source above, SHA-256 `ef9e5b5b1cd63d001559ced40151a781d872a3efd85e57ed88f4cb24f1f54c7d`.
- Strict compiler flags: `-O2 -std=c++20 -pipe -Wall -Wextra -Werror`; H32 parameters were set with compile-time definitions shown in [`manifest.json`](manifest.json).
- Detailed per-case CSV: [`open15_per_case.csv`](open15_per_case.csv). Raw harness summaries and per-run outputs are in [`open15/`](open15/) and [`screen-variants/`](screen-variants/).

## Limitations

The risk model has a high memory cost because it keeps dense Fenwick trees by (birth mode, length, placement age). The measured gain on case 15 is too narrow: the same policy hurts case 13, and the full open score falls. Hazard estimates also assume enough repeat behavior in a coarse LIFO/FIFO/mixed class; changes of regime during a pipe’s lifetime weaken calibration. Since the candidate failed the complete open set, no claim about holdout transfer is made.
