# Case 5: capacity-aware cohort slabs on a unit staircase

## Result

The candidate improves the current composite from **29.947761251325** to **29.982931046212 / 32.1** on local Open15 (**+0.035169794887**). The only changed Open15 case is case 5: trench length **62,620 → 60,020 m** (−2,600 m). Cases 1–4 and 6–15 have identical trench lengths and scores. All 15 runs returned `ok`.

The candidate is the current **local lab champion** for this experiment set, not the canonical or frozen solver. Holdout-v2 is neutral: both versions score **5.135264324280**, 12/12, with all trench lengths identical. On four new synthetic streams, one unit-staircase/stride-2 stream improves by 140 m and the other three are ties. That is a narrow positive transfer signal, not evidence of broad generalization.

## Causal rule

At a new size run, the solver uses only its prefix to check: the two completed runs and the new run form an increasing unit-step staircase; the previous run's deletion length matches; stride-2 deletion has been observed; the two completed run counts are stable within 10% (or 10 items); and the estimated run size is at least 64. For the new branch, the predicted deleted cohort's capacity for the next size must be below 64 and exceed compatible existing-gap capacity. The solver then places survivor pipes into fitting owned/shared old gaps and groups the predicted deleted PID-parity cohort in a contiguous tail slab.

The trigger is causal: it does not read the test number, future commands, or full input. On case 5 the trace shows new-branch activations at lengths 3–16 and 21–26; it does not activate at length 40. The source includes the prior geometric slab path, whose existing ≥64 capacity guard remains unchanged. No thresholds were adjusted after Open15.

## Paired Open15 results

| Case | Weight | Baseline trench → candidate, m | Baseline score → candidate score |
|---:|---:|---:|---:|
| 1 | 0.1 | 20 → 20 | 0.090000000 → 0.090000000 |
| 2 | 1 | 20 → 20 | 1.000000000 → 1.000000000 |
| 3 | 1 | 20 → 20 | 0.750000000 → 0.750000000 |
| 4 | 1 | 60 → 60 | 0.666666667 → 0.666666667 |
| 5 | 1 | 62,620 → 60,020 | 0.811881188 → 0.847050983 |
| 6 | 1 | 20 → 20 | 0.900000000 → 0.900000000 |
| 7 | 1 | 1,700 → 1,700 | 0.986470588 → 0.986470588 |
| 8 | 1 | 4,700 → 4,700 | 0.984468085 → 0.984468085 |
| 9 | 1 | 47,740 → 47,740 | 0.659824047 → 0.659824047 |
| 10 | 1 | 15,380 → 15,380 | 0.800000000 → 0.800000000 |
| 11 | 1 | 22,500 → 22,500 | 0.904933333 → 0.904933333 |
| 12 | 4 | 10,320 → 10,320 | 0.993120155 → 0.993120155 |
| 13 | 4 | 3,280 → 3,280 | 0.973170732 → 0.973170732 |
| 14 | 4 | 37,820 → 37,820 | 0.996932840 → 0.996932840 |
| 15 | 10 | 438,920 → 438,920 | 9.540622437 → 9.540622437 |
| **Total** | **32.1** | — | **29.947761251 → 29.982931046** |

## New synthetic screen

| Stream | Deletion/size regime | Baseline → candidate trench, m | Δ trench |
|---|---|---:|---:|
| `unit_stride2` | unit staircase, stable block counts, alternating within-block deletions | 11,800 → 11,660 | −140 m |
| `unit_random` | unit staircase, random half-deletions | 11,780 → 11,780 | 0 m |
| `unit_fifo` | unit staircase, FIFO removals | 13,980 → 13,980 | 0 m |
| `step2_stride2` | step-2 staircase, alternating within-block deletions | 23,460 → 23,460 | 0 m |

## Resources and artifacts

Open15 candidate maximum: **3.563 CPU-s**, **5.219 MiB RSS**. Holdout-v2 candidate maximum: **0.682 CPU-s**, **3.281 MiB RSS**. Both are below the configured 5 CPU-s / 256 MiB limits. Tests were local; no website or Docker was used.

- Candidate source: [`src/staircase_cohort_capacity.cpp`](src/staircase_cohort_capacity.cpp), SHA-256 `322b5b672c1e64f868a8016c31511d34503f940c450f4a807514aaf8af38ec16`.
- Candidate binary SHA-256: `8cb47aa8770940348c44f45303dd3a69b5a27b34f905b1d50a25c7765cdaeee5`.
- Baseline source: `results/pipes/improvement/case9_hole_first_cohorts/source/hole_first_survivor_cohorts_plus_lifo_gate.cpp`, SHA-256 `5cc564ca88d8ae3be941ca2c3dab252e0836fa8d93e937dec4c32b5168b2aa9a`.
- Exact per-case rows, resource measurements, test hashes, and commands are in [`manifest.json`](manifest.json) and the paired CSVs under [`runs/`](runs/).
- Frozen final and canonical source remain unchanged; their recorded hashes are `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` and `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.
