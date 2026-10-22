# Pipes: causal cohort-gate ablations

## Scope and conclusion

This branch independently tested changes around the frozen `t46_cohort_owner` lifetime/parity policy. It did not modify `src/pipes.cpp`. No tested ablation beats the existing `cohort_owner` on the verified open cases. The strongest finding is diagnostic: parity-based lifetime segregation helps a deliberately smooth size staircase, but broadening the online gate to cover other skewed cohorts harms the official case with geometric size growth. The original exact arithmetic-trend gate avoids that case-9 regression, but its gain still has not transferred to ordinary holdout/alternating streams.

All ablations were strictly compiled with `-Wall -Wextra -Werror`. Each was first run only on official cases 5 and 9. Variants that regressed case 9 were rejected without a full 15-case run. Two more conservative policy changes were checked on the 12-case reused synthetic holdout. Generated staircase inputs are exploratory stress diagnostics, not independent contest evidence.

## Official cases 5 and 9

The frozen reference values are from the fresh T46 and owner 15-case reports. Exact per-case harness outputs for the new variants are in `runs/*_c5_c9/cases.csv`.

| Variant | Change from `cohort_owner` | Case 5 KPI / trench | Δ KPI vs T46 | Case 9 KPI / trench | Δ KPI vs T46 | max CPU / RSS on these two cases |
|---|---|---:|---:|---:|---:|---:|
| T46 | reference | 0.52488127 / 96,860 m | — | 0.49234136 / 63,980 m | — | 0.0454 s / 1.88 MiB in existing open run |
| `cohort_owner` | within-length occurrence parity; exact 3-size arithmetic trend plus skew gate; cohort-owned gaps and owner-side placement | **0.80955414 / 62,800 m** | **+0.28467287** | 0.49234136 / 63,980 m | 0 | 0.1073 s / 2.25 MiB in existing open run |
| `no_trend` | removed the 3-size trend condition; keep >=8 removals and >=85% cohort dominance | 0.80852417 / 62,880 m | +0.28364290 | 0.45918367 / 68,600 m | -0.03315768 | 0.0481 s / 2.11 MiB |
| `cross3` | replace trend gate with >=3 lengths having >=8 removals and >=85% common-cohort dominance | 0.80955414 / 62,800 m | +0.28467287 | 0.43871866 / 71,800 m | -0.05362269 | 0.0484 s / 2.28 MiB |
| `global_parity` | assign cohort by global placement parity instead of per-length occurrence parity; keep original gate | 0.80544994 / 63,120 m | +0.28056866 | 0.49234136 / 63,980 m | 0 | 0.0495 s / 2.27 MiB |
| `flipped_owner` | reverse cohort 0/1 side ownership in the parity mode | 0.79886864 / 63,640 m | +0.27398736 | 0.49234136 / 63,980 m | 0 | 0.0492 s / 2.27 MiB |

The loosening failures have a causal explanation in the input: `no_trend` activates at operation 133 in case 5, but also at operation 1008 in case 9. `cross3` activates at operation 509 in case 5 and operation 4008 in case 9. In case 9, parity segregation starts before later size blocks arrive; its trench rises by 4,620 m (`no_trend`) or 7,820 m (`cross3`). The original trend gate activates at operation 509 in case 5, with the last distinct requested lengths `[3, 2, 1]`, and never activates in case 9.

Global placement parity preserves case 9 but costs 320 m on case 5 versus owner. Reversing the owners costs 840 m on case 5. Neither is a better policy.

## Holdout checks

`global_parity` scored **5.10263434231 / 12** on `final-holdout-v2`, versus the previously verified T46/owner **5.13510003034 / 12**. The entire -0.03246568803 difference is case-01: KPI 0.96723137 instead of 0.99969706. Other 11 cases tie. This independently rejects global placement parity.

`flipped_owner` scored **5.13510003034 / 12**, tying T46/owner on all 12 cases. That is not a transfer gain; together with its case-5 regression, reject it.

No full 15-case run was spent on `no_trend` or `cross3`: both already fail materially on official case 9. Their selected-case results are sufficient to reject them as candidate improvements.

## Constructed staircase diagnostics

To test whether the original gate captures a broader causal pattern, four small synthetic streams were generated after source freezing. Each batches 128 placements of a size profile and then removes every other placement in that size batch. The profiles are unit-step `1..40`, step-2 odd sizes `1,3,...,39`, step-4 sizes `4,8,...,40`, and geometric sizes `1,2,4,8,16,32`.

| Profile | T46 KPI / trench | `cohort_owner` KPI / trench | Δ KPI | Δ trench |
|---|---:|---:|---:|---:|
| Unit staircase | 0.52042840 / 100,840 m | **0.80540209 / 65,160 m** | +0.28497369 | -35,680 m |
| Step-2 staircase | 0.51364366 / 49,840 m | **0.76099881 / 33,640 m** | +0.24735515 | -16,200 m |
| Step-4 staircase | 0.51499634 / 27,340 m | **0.66793169 / 21,080 m** | +0.15293535 | -6,260 m |
| Geometric | 0.49655172 / 8,120 m | 0.49655172 / 8,120 m | 0 | 0 |
| **Sum across these four exploratory streams** | **2.04562013 / 4** | **2.73088431 / 4** | **+0.68526418** | — |

These tests show a reproducible response to the *constructed* staircase family, not generalization to unknown contest streams: they share the same removal-generation structure and were created to isolate that structure. Runtime stayed below 0.041 s CPU and 1.93 MiB RSS per run. The official case 5 can be understood as one real member of this family; case 9 is a useful counterexample to broadly treating skewed cohort removals as a sufficient signal.

## Decision

Keep the frozen `t46_cohort_owner` as the best cohort-based candidate from this branch; do not replace it with these ablations. Its score is still 29.731837411672 / 32.1, with the complete +0.284672868189 gain concentrated in official case 5 and no demonstrated gain on holdout-v2 or the prior alternating-policy diagnostics. The evidence supports a narrow online cue—same-length cohort skew observed during a smooth additive size trend—but not a generally validated lifetime predictor.

## Reproduction and artifacts

- Source variants: `src/no_trend.cpp`, `src/cross3.cpp`, `src/global_parity.cpp`, `src/flipped_owner.cpp`.
- Generated-input recipe and inputs: `generate_cohort_streams.py`, `synthetic/*.in`.
- Selected-case runs: `runs/*_c5_c9/`; holdout runs: `runs/*_holdout/`; staircase runs: `runs/{baseline_staircase,owner_staircase}/`.
- Compiler: `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror`.
- Harness: `tools/pipes_harness.py`, official interactor, 5 s CPU / 256 MiB RSS per case.
- Frozen cohort-owner source SHA-256: `2cce753dfaa9aa6f625cefee9550edff6d8c4ce8c915e9cb77cbfbb0c3dc3583`.
- Ablation source SHA-256:
  - `no_trend.cpp`: `8ad828d16ff1779cf9c29483ba2e7cb7a70275c48229fbcadfd322f6049aa21f`
  - `cross3.cpp`: `0b839c276886a7eae0259766ad8e4aabb0ab6bc77c0d8c5eb2625903f47e97a4`
  - `global_parity.cpp`: `cdaa20f1e8c30c251e1901f6276e6c83840f959ff1648348ea275bc4ab7df74e`
  - `flipped_owner.cpp`: `c2a141987d894493a6600de6b676a35b6d957f950af46d463d68f35bcf3dc3f9`
