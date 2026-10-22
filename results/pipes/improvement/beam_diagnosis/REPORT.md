# Offline beam/oracle diagnosis: case 9

**Date:** 2026-10-16  
**Scope:** offline diagnostics only. Future deletion IDs are available to the beam, but are not an input to any proposed online allocator.

## Setup

The first boundary in `data/pipes/open/9.in` is 1,000 placements of length 1, then deletions of PIDs 1, 3, ..., 999, then 1,000 placements of length 2. The same pattern repeats across increasing lengths. I reduced adjacent length cohorts to 8 and 16 placements and tried five deletion schedules: odd PIDs, even PIDs, first half, second half, and a seeded random half.

The width-256 beam searches every integral start coordinate in each fitting gap. Its ranking uses the future deletion set and future fit capacity, so its result is a feasible hindsight witness, not an online policy or a proof of the optimum. It covers 25 reduced streams (five adjacent length pairs × five deletion schedules). The width-64, count-8 run is retained as a smoke/short-prefix comparison.

## Results

At count 16, the beam found a shorter trench than T46 in 11 of 25 streams. Each table entry is `T46 trench − beam trench` in metres; zero means no beam improvement.

| Length pair | Odd | Even | First half | Second half | Random half |
|---|---:|---:|---:|---:|---:|
| 1 → 2 | 20 | 20 | 20 | 0 | 20 |
| 2 → 4 | 20 | 20 | 20 | 0 | 20 |
| 4 → 8 | 0 | 0 | 0 | 0 | 0 |
| 8 → 16 | 60 | 40 | 0 | 0 | 20 |
| 16 → 32 | 0 | 0 | 0 | 0 | 0 |

The total of 280 m is across separate toy streams, not a score on case 9. The largest single witness saves 60 m in the reduced 8 → 16 / odd-deletion stream. At count 8, the reduced 1 → 2 / odd and even streams both admit a 20 m beam witness. Their placement prefix is identical; the oracle layouts pack the predicted survivors in different regions for the two deletion schedules. That choice depends on future IDs that have not yet appeared online.

I also tested two causal policies that detect a strong deleted-PID parity after eight removals: side selection by the learned parity, and parity-tagged holes. Neither improved any of the 25 count-16 streams. The first regressed on 6; the owner-aware version regressed on 8. On the full case-9 stream, the diagnostic simulator returned:

| Policy | Trench (m) |
|---|---:|
| T46 | 63,980 |
| Side-only learned parity | 74,360 |
| Parity-tagged holes | 65,080 |
| Always-left control | 63,000 |

The stored official T46 result for case 9 is also 63,980 m; the prior left-edge control is a separate known result, not a beam-derived candidate.

## Conclusion

The beam confirms that future-aware placement can improve some small instances, but its wins depend on deletion IDs before that schedule is observable. The first causal parity/owner policies did not transfer the oracle gain and regressed on several synthetics and on full case 9. A separate, narrower causal screen then found a run-scoped policy that improves case 9 without changing case 5 on the official open set; the full open and holdout-v2 results are below. This remains an experimental snapshot only, not a canonical change.

## Causal run-scoped follow-up

The broad latch (“after a run, always use left”) was rejected: on open tests, the T46 variant worsened case 5 by 4,860 m, and the same rule on cohort-owner worsened case 5 by 11,000 m. The surviving experiment only forces left while the current request continues a run: the last 46 placements must all equal the incoming length. A length change immediately resets the override. It latches the override off if the current length and the two most recent distinct placement-run lengths have equal increments. This smooth-trend check uses only past placements and the current request; no IDs or future operations are read.

The operation indices below are 1-based in the input stream. On case 9, the run override starts at op 47 for length 1, resets at op 1,501 for length 2, then starts at 1,547; the analogous start/reset points are op 3,001/3,047 for length 4, op 4,501/4,547 for length 8, op 6,001/6,047 for length 16, and op 7,501/7,547 for length 32. The exponential run lengths do not satisfy the arithmetic-trend gate. On case 5, it starts at op 47 for length 1 and op 235 for length 2; the gate detects the 1→2→3 arithmetic progression at op 377, before the first length-3 placement, and disables later overrides. Case 5’s official trench remains unchanged despite the first two short override intervals.

Official open results:

| Source | Weighted score / 32.1 | Difference from its own baseline | Changed cases | Case 5 trench | Case 9 trench |
|---|---:|---:|---|---:|---:|
| T46 baseline | 29.447164543 | — | — | 96,860 | 63,980 |
| T46 + scoped run gate | 29.455140849 | +0.007976305 | 9 only | 96,860 | 62,960 |
| Cohort-owner baseline | 29.731837412 | — | — | 62,800 | 63,980 |
| Cohort-owner + scoped run gate | 29.739813717 | +0.007976305 | 9 only | 62,800 | 62,960 |

Both candidates passed 15/15. The cohort-owner combination preserves its case-5 gain and improves only case 9 in the open set. However, holdout-v2 did not confirm a safe combination:

| Source | Weighted score / 12 | Difference from its own baseline | Holdout cases with changed trench |
|---|---:|---:|---|
| T46 baseline | 5.135100030 | — | — |
| T46 + scoped run gate | 5.135100030 | 0 | none |
| Cohort-owner baseline | 5.170229506 | — | — |
| Cohort-owner + scoped run gate | 5.135100030 | −0.035129476 | 1, 2, 5, 7, 8, 10, 12 |

The cohort-owner candidate changes holdout trenches by +20, +60, +20, −20, +20, −400, and +20 m respectively; the aggregate happens to equal T46 after gains and losses cancel. The T46 scoped candidate is neutral on this holdout. Maximum measured solver CPU/RSS were 1.080 s / 5.41 MiB on open for T46+gate, 1.138 s / 7.59 MiB on open for cohort-owner+gate, and below 0.27 s / 2.85 MiB per holdout case. All are within the harness limits of 5 s and 256 MiB.

The more permissive parity trigger also improved case 9, but it changed additional open cases and the open total remained below the corresponding baseline. It is not part of the surviving candidate. Applying the scoped gate directly to plain cohort-owner regressed several holdout cases; the separate MC-overlay check below tests whether the same trigger can be isolated on top of that frozen source.

A wider or deeper offline beam remains unjustified: it would refine hindsight layouts but would not solve the observed generalization failure of online edge-selection rules.

`src/pipes.cpp` was not edited. Its observed SHA-256 at completion is `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.

## Corrected frozen MC overlay

This is the qualified combination check against the corrected MC source confirmed by the coordinator. The frozen baseline SHA-256 is `fadbe93b0ae2d1dd1ff2ebce3dbdf384f3969272865f108729092b9d8cb98be3`; the separate overlay is `source/cohort_owner_mc_corrected_scoped_run.cpp`, SHA-256 `e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41`. The baseline file and `src/pipes.cpp` were not edited. The run threshold and trend gate are unchanged from the prior scoped screen.

The exact frozen source reproduced the supplied official scores: `29.77315080574852 / 32.1` on all 15 open cases and `5.135264324280470 / 12` on all 12 holdout-v2 cases. The overlay passed 15/15 and 12/12. Against this corrected baseline, it changes only open case 9: trench `63,980 → 62,960 m`, KPI `0.492341357 → 0.500317662`, for `+0.007976305` open weighted score. Case 5 remains `62,800 m`; all 12 holdout-v2 trenches and the holdout score are identical to corrected MC.

Open trench lengths (m):

| Case | T46 | `results/pipes/final/solution.cpp` | Corrected MC | Corrected MC + scoped gate |
|---:|---:|---:|---:|---:|
| 1 | 20 | 20 | 20 | 20 |
| 2 | 20 | 20 | 20 | 20 |
| 3 | 20 | 20 | 20 | 20 |
| 4 | 60 | 60 | 60 | 60 |
| 5 | 96,860 | 62,800 | 62,800 | 62,800 |
| 6 | 20 | 20 | 20 | 20 |
| 7 | 1,760 | 1,760 | 1,700 | 1,700 |
| 8 | 4,700 | 4,700 | 4,700 | 4,700 |
| 9 | 63,980 | 63,980 | 63,980 | 62,960 |
| 10 | 15,380 | 15,380 | 15,380 | 15,380 |
| 11 | 22,620 | 22,620 | 22,620 | 22,620 |
| 12 | 10,340 | 10,340 | 10,320 | 10,320 |
| 13 | 3,280 | 3,280 | 3,280 | 3,280 |
| 14 | 37,820 | 37,820 | 37,820 | 37,820 |
| 15 | 438,920 | 438,920 | 438,920 | 438,920 |

| Source | Open weighted score / 32.1 | Holdout-v2 score / 12 |
|---|---:|---:|
| T46 | 29.447164543 | 5.135100030 |
| `results/pipes/final/solution.cpp` | 29.731837412 | 5.135100030 |
| Corrected MC | 29.773150806 | 5.135264324 |
| Corrected MC + scoped gate | 29.781127111 | 5.135264324 |

Relative to T46, the complete corrected MC + gate source improves open cases 5, 7, 9, and 12. Compared with `results/pipes/final/solution.cpp`, it improves only cases 7, 9, and 12; case 5 matches cohort-owner. The case-7 and case-12 gains come from corrected MC, while the additional gate effect is only case 9. On holdout-v2, the candidate differs from the freshly rebuilt final source only on cases 1 and 10 (−20 m each); those deltas already exist in corrected MC and are not caused by the gate.

Maximum measured solver CPU/RSS for the candidate were `1.854 s / 7.92 MiB` on open and `0.365 s / 4.16 MiB` on holdout-v2, below the harness limits of `5 s / 256 MiB`. The candidate remains a separate diagnostic source snapshot; no canonical source was changed.

## Preliminary MC overlay — not qualified

This exploratory run predates an independent audit that found a tie-breaking mismatch between rollout simulation and the live allocator in the then-current MC source. The numbers below describe only that earlier snapshot and do not qualify the gate + corrected-MC combination. They are retained for traceability only; the later check against the corrected, frozen MC source is documented above.

For this exploratory run, I copied the then-current `cohort_owner_mc_rollout.cpp` (SHA-256 `b84be191d67515e7a0e2bcc663d9a5268a8545d18f151fa6ea2eed14c9323a37`) into a separate source snapshot (`source/cohort_owner_mc_scoped_run.cpp`, SHA-256 `e584fe5e0f52e1411756e7c8f4caf0aea0fcf5b075144ff26e6d3288b2ffafab`) and overlaid the scoped run gate. The upstream MC source is being corrected separately; I did not edit or test that corrected content. The gate is active only while the incoming placement continues the length of the last 46 placements, and the override resets immediately when the length changes. It forces the left side during that run. A past-only arithmetic-trend check permanently disables this override when the current length and the two preceding distinct placement-run lengths have equal increments. I added the same state and trigger to the MC rollout model so that its forecasts use the same rule as the live allocator. No future command or test identity is read by the candidate.

On case 9, the left override starts at input operations 47 (length 1), 1,547 (length 2), 3,047 (length 4), 4,547 (length 8), 6,047 (length 16), and 7,547 (length 32). It resets at each next run boundary; the exponential length pattern never triggers the arithmetic-trend latch. On case 5, it starts at operations 47 and 235; the observed 1→2→3 pattern disables it at operation 377 before the first length-3 placement. Case 5 remains unchanged.

The pre-audit MC source was rebuilt and rerun to establish a same-harness baseline: its open score reproduced `29.750473320961504 / 32.1`; its holdout-v2 score was `5.135264324280470 / 12`. The exploratory candidate and pre-audit MC source both passed 15/15 open cases and 12/12 holdout-v2 cases.

Open trench lengths (m):

| Case | T46 | `results/pipes/final/solution.cpp` | Pre-audit MC | Pre-audit MC + scoped gate |
|---:|---:|---:|---:|---:|
| 1 | 20 | 20 | 20 | 20 |
| 2 | 20 | 20 | 20 | 20 |
| 3 | 20 | 20 | 20 | 20 |
| 4 | 60 | 60 | 60 | 60 |
| 5 | 96,860 | 62,800 | 62,800 | 62,800 |
| 6 | 20 | 20 | 20 | 20 |
| 7 | 1,760 | 1,760 | 1,740 | 1,740 |
| 8 | 4,700 | 4,700 | 4,700 | 4,700 |
| 9 | 63,980 | 63,980 | 63,980 | 62,960 |
| 10 | 15,380 | 15,380 | 15,380 | 15,380 |
| 11 | 22,620 | 22,620 | 22,620 | 22,620 |
| 12 | 10,340 | 10,340 | 10,320 | 10,320 |
| 13 | 3,280 | 3,280 | 3,280 | 3,280 |
| 14 | 37,820 | 37,820 | 37,820 | 37,820 |
| 15 | 438,920 | 438,920 | 438,920 | 438,920 |

| Source | Open weighted score / 32.1 | Holdout-v2 score / 12 |
|---|---:|---:|
| T46 | 29.447164543 | 5.135100030 |
| `results/pipes/final/solution.cpp` | 29.731837412 | 5.135100030 |
| Pre-audit MC | 29.750473321 | 5.135264324 |
| Pre-audit MC + scoped gate | 29.758449626 | 5.135264324 |

Relative to the pre-audit MC source, the scoped gate changes only open case 9, reducing its trench by 1,020 m and increasing the weighted score by `+0.007976305`; it leaves open case 5 and all holdout cases unchanged. Relative to `results/pipes/final/solution.cpp`, the full MC+gate candidate improves open cases 7, 9, and 12 by 20, 1,020, and 20 m respectively; the case-7 and case-12 changes come from the MC baseline, not from the gate. On holdout-v2, a fresh build of `results/pipes/final/solution.cpp` confirms that the full MC+gate candidate differs only on cases 1 and 10 (−20 m each), for a net score change of `+0.000164294`; those differences are also present in the pre-audit MC baseline, not introduced by the gate.

Maximum measured solver CPU/RSS for MC+gate were 1.862 s / 7.55 MiB on open and 0.364 s / 4.18 MiB on holdout-v2, below the 5 s / 256 MiB harness limits. These are pre-audit exploratory measurements only, not a qualified candidate result. Do not use them to rank the overlay against a corrected MC baseline. `src/pipes.cpp` and `results/pipes/final/solution.cpp` were not changed.

## Artifacts

- `beam_diagnosis.py` — offline simulator and beam search.
- `beam_matrix.json` — count-16, width-256 results for 25 streams.
- `beam_matrix_smoke.json` — count-8, width-64 results for 25 streams.
- `signal_screen.py`, `rolling_left_screen.py`, and `signal_screen.json` / `rolling_left_screen.json` — causal policy screens.
- `source/cohort_owner_mc_corrected_scoped_run.cpp` — scoped gate over the corrected frozen MC source; `corrected_mc_overlay.json` records the exact hashes and harness deltas. The earlier pre-audit snapshot remains explicitly marked unqualified. No canonical source changed.
- `open/` and `holdout-v2/` — official harness outputs for all candidate variants, including both pre-audit diagnostics and corrected-MC baseline/overlay runs, plus a fresh `final/solution.cpp` holdout check.
