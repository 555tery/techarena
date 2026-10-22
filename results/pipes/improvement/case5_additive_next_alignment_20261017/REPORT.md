# Case 5: endpoint alignment for the next additive size

## Result

**The rule improves the staircase candidate on Open15 by 0.060158153325 score points.** The full local result is **30.043089199538 / 32.1**, 15/15, compared with **29.982931046212** for the staircase-cohort candidate A. Only case 5 changed: trench length fell from **60,020 m to 56,040 m** (−3,980 m; KPI 0.847051 → 0.907209). Other 14 Open15 trench lengths and weighted scores were unchanged.

On holdout-v2 the candidate tied A exactly: **5.135264324280 / 12**, 12/12; all 12 judge transcripts and trench lengths matched. This is a regression check, not an independent holdout gain. The candidate remains below the user's 30.3 target.

## Causal rule

The live allocator activates the rule only after observing at least **46 placements in each of three consecutive size runs** whose lengths are exactly `L−2, L−1, L`, with `3 ≤ L < 40`. For a fitting free interval, it chooses the endpoint that leaves the remainder beginning nearest a multiple of the predicted next size `L+1`; ties preserve the allocator's existing side choice. The rule changes endpoint choice only. It does not route pipes by deletion cohort, reserve a slab, or read future commands or a case number. Monte Carlo selection is bypassed only while this strict trigger is active because that rollout does not score the new endpoint objective.

The first A→A+B answer divergence on official case 5 is operation 2,866: the 46th placement of a 16 m pipe, exactly when the fixed trigger first affects a fitting-gap choice. This is consistent with the stated mechanism; it is not by itself a general causal proof.

## Paired results

| Comparison | Baseline → candidate | Trench change | Notes |
|---|---:|---:|---|
| Standalone rule B on current composite, case 5 | 62,620 → 61,800 m | −820 m | Initial screen only; no standalone Open15 run |
| A → A+B, case 5 | 60,020 → 56,040 m | −3,980 m | Strong target improvement |
| A → A+B, four first-screen synthetics | 2 wins, 2 regressions | −280, −60, +160, +120 m | FIFO, LIFO, stride-2, and random phase-shift cases |
| A → A+B, 20 predeclared staircase traces | 5 wins, 2 regressions, 13 ties | Regression cases +80 and +100 m | Aggregate KPI sum +0.103102; no policy tuning after results |
| A → A+B, Open15 | 29.982931 → **30.043089** | −3,980 m only in case 5 | 15/15 |
| A → A+B, holdout-v2 | 5.135264 → 5.135264 | 0 m | 12/12; transcripts identical |

The 20 qualification streams vary block count, phase jumps/repeats, block sizes, deletion policy, and stopping point. They were generated from fixed seeds **20261031–20261050** before running the pair; their definitions and hashes are in `synthetic/qualification_v1/manifest.json`. They deliberately test the staircase family and do not establish performance on arbitrary unseen traffic. The four first-screen streams are also defined in `synthetic/manifest.json`.

## Runtime and reproducibility

All local runs passed the interactor. On Open15 the candidate's maximum observed solver use was **3.513 CPU-s** and **5.61 MiB RSS**, below 5 s / 256 MiB. On the 20-stream suite, maximum observed use was 0.035 CPU-s and 2.73 MiB RSS per trace. Builds used Apple clang 17.0.0 with `-O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic`.

- Candidate A source: [`staircase_cohort_capacity.cpp`](../case5_staircase_cohort/src/staircase_cohort_capacity.cpp), SHA-256 `322b5b672c1e64f868a8016c31511d34503f940c450f4a807514aaf8af38ec16`.
- Candidate A+B source: [`staircase_plus_additive_next_alignment.cpp`](src/staircase_plus_additive_next_alignment.cpp), SHA-256 `4c3a3590eb1ad4251640af32f10f7e5b506b8cfac8ee6b9d0edaa6d4e231caae`; binary SHA-256 `ca885fb8869514ab494502e2ee517cfb4d716d9d55c9d291aa9c1b4126544838`.
- Per-test pairs and transcript hashes: [`comparison.csv`](comparison.csv), [`holdout_comparison.csv`](holdout_comparison.csv).
- Commands, all source/input/harness hashes, and run paths: [`manifest.json`](manifest.json).

Frozen final and canonical sources were not changed. Testing was local only; the platform and Docker were not used.
