# Case 15: generic online allocation screens

## Result

No tested overlay improved case 15 over the frozen coordinator candidate. I therefore did not run full-open, holdout, or stress suites for these variants.

Input `data/pipes/open/15.in` has 200,000 commands, 130,255 placements, peak live length 418,768 m, and final live length 418,757 m. Its lower bound is `20 * ceil(418768 / 20) = 418,780 m`. The current trench is 438,920 m, 20,140 m above that bound. The final score is `418757/438920 * 10 = 9.54062243689055`.

## Official interactor screens

Each candidate was strict-built with Apple Clang 17 using `-O2 -std=c++20 -Wall -Wextra -Werror -pedantic`, then run only on official case 15 through `tools/pipes_harness.py`. All returned `ok`.

| Candidate | Online rule change | Trench (m) | Δ trench | Weighted case score | Solver CPU (s) | RSS (MiB) |
|---|---|---:|---:|---:|---:|---:|
| Frozen corrected MC + scoped run | baseline | 438,920 | 0 | 9.540622436891 | 0.953230 | 9.046875 |
| `combined_tielow.cpp` | choose lower-address ties in allocator and rollout | 438,920 | 0 | 9.540622436891 | 0.924505 | 8.859375 |
| `broad_median_right.cpp` | with ≥8 recent supported lengths, place lengths at/below recent median on high side | 439,400 | +480 | 9.530200273100 | 0.955362 | 9.468750 |
| `broad_q1_right.cpp` | same signal, use lower quartile instead of median | 439,140 | +220 | 9.535842783623 | 0.961864 | 8.421875 |
| `right14.cpp` | always use high side through length 14 | 439,140 | +220 | 9.535842783623 | 0.980553 | 9.484375 |
| `narrow_dense_small_left.cpp` | when ≥30,000 pipes are active and recent support is narrow, put lengths ≤4 on low side | 438,960 | +40 | 9.539753052670 | 0.956894 | 9.562500 |
| `broad_median_large_right.cpp` | broad-support signal, place lengths at/above recent median on high side | 439,360 | +440 | 9.531067916970 | 0.969749 | 9.609375 |

This is a per-case screen, not evidence that any variant improves the complete benchmark. No candidate qualified for additional controls or full-open testing.

## Hashes and evidence

Baseline source SHA-256: `e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41`.

Input SHA-256: `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`. Interactor SHA-256: `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`.

| Source | SHA-256 | Binary | SHA-256 |
|---|---|---|---|
| `combined_tielow.cpp` | `2299ff12fb441a573b976d9606f52d4e8520d4894164df519eb55945451cfaf1` | `combined_tielow` | `87338bec2337fe2226ed740ac31ebe7c6061d1ad680aa7b6c0022de5948a7e88` |
| `broad_median_right.cpp` | `5936f5b208a3c4f0437e8f8aec64760378f11358a2103d7259a89ce59dafac74` | `broad_median_right` | `ff77c89a1a62cd83b06274865a96c57819ea1cb47c0f9f6efaad3cb14cb67570` |
| `broad_q1_right.cpp` | `b740336a0b9f57a816db7d71e4d45f84a8959d80381fd3ec17cd5072327833cf` | `broad_q1_right` | `33fb5f265ea1ea241f706e09a6f1f04f93dbaae6754e457e7e8fc570f17b8b1a` |
| `right14.cpp` | `acb84917848008a380d012ed0ae39e0af9f2981082cbbcb41f1b2219e1fe7372` | `right14` | `64025a20b382a4a42e868dadb87baa31bc6f8a7a0265237f11303a987e61eec6` |
| `narrow_dense_small_left.cpp` | `d6046d0cd6038379fe864ead182a3c10fe48c31abc275eefd2a9aac5ea9808d3` | `narrow_dense_small_left` | `682c7bb411fe4abcca62d4b80517c7b7688cdb58f762a4619ad053716c7ea12b` |
| `broad_median_large_right.cpp` | `2f1d13d55d04929fd93c31df44a30aab1719d743be77e09534cb12482a548afd` | `broad_median_large_right` | `ca8ad8c0f608ac0dab1fc5852a995ca47c6c78d461ab70169d1825b0e2d7079d` |

Harness outputs and per-case records are under this directory, in `*-case15/summary.json` and `*-case15/cases.csv`.

## Caveat on a prior artifact

The pre-existing binary `results/pipes/improvement/segregated_allocator/adaptive_live_mean` reproduces 438,360 m when re-run on case 15, but recompiling its current source produces 438,920 m. The saved report's 28.951719995/32.1 open score belongs to that binary snapshot; its source and binary do not currently match, and the overall score is below the current candidate regardless. I did not reuse it or infer its policy from its result.

No shared final artifact or `src/pipes.cpp` was changed.

## Offline case-15 window oracle diagnostic

The oracle diagnostic starts from the exact frozen-baseline layout at each selected command boundary, keeps all pre-window pipes fixed, and replays a 64-command suffix. Its beam receives the deletion IDs occurring inside that suffix only. Each state is feasible; the beam uses width 16, up to 12 selected fitting gaps per state (edge and centre starts), all integer starts in a newly extended tail, and always retains the baseline answer as a control action. This is a bounded witness search, not an optimality proof or an online candidate. The small full-stream prefixes at 96, 192, 512, and 1,024 commands also showed zero beam savings.

| Window start (1-based op) | Placements / deletes | Baseline H / growth | Oracle H / growth | Feasible hindsight saving | Baseline end gaps (max, tail) | Oracle end gaps (max, tail) |
|---:|---:|---:|---:|---:|---:|---:|
| 100,000 | 31 / 33 | 241,620 / 240 m | 241,600 / 220 m | 20 m | 12 (157, 157) | 11 (144, 0) |
| 120,000 | 31 / 33 | 281,460 / 180 m | 281,420 / 140 m | 40 m | 1,177 (28, 0) | 1,176 (69, 51) |
| 160,000 | 33 / 31 | 358,320 / 240 m | 358,260 / 180 m | 60 m | 2,908 (28, 12) | 2,907 (30, 30) |

The wider context is more informative than the local wins. At op 100,000, H was 241,380 m against 241,363 m active length, with five gaps and a 15 m maximum gap. From there through the end, the solver added 197,540 m of trench while net active length rose by 177,394 m; the remaining 20,146 m matches the final 20,140 m gap to the rounded peak-live lower bound within 6 m. Of the 5,576 post-transition growth events, 5,574 occurred when total free volume before placement was already at least the incoming pipe length. Since the allocator only digs after finding no fitting gap, this identifies fragmentation as the dominant trigger during the 8–40 m pipe phase. The final 20,163 m of free volume sits in 4,954 gaps: the largest is 34 m and the tail is 10 m.

The three window witnesses reduce only one to three 20 m dig increments and do not reveal a stable survivor-cohort rule. The mid-phase oracle can make a 69 m gap and 51 m tail instead of the baseline's 28 m maximum gap and no tail, but the final trench saving there is 40 m. In the late window, gap and tail metrics change little. This supports the fragmentation diagnosis and shows that exact short-horizon deletion knowledge can recover a small number of sections locally; it does not support a broad online change capable of recovering the existing ~20 km case-15 overhead. The fixed pre-window layout is a deliberate limitation of these suffix experiments: they cannot reclaim earlier high-water growth.

Artifacts and hashes:

- Window diagnostic: [`offline_case15_windows.py`](offline_case15_windows.py), SHA-256 `e8c35af42d3c3b2a7d16b8eee8c4e73c3cc3ba784121860ea98b38fd549570df`.
- Results: [`oracle_windows_final.json`](oracle_windows_final.json), SHA-256 `9fd9b55d75dd305756005b70c666cb1b7c113c6856aa9046d5e4b59343908212`.
- Frozen baseline source: [`../beam_diagnosis/source/cohort_owner_mc_corrected_scoped_run.cpp`](../beam_diagnosis/source/cohort_owner_mc_corrected_scoped_run.cpp), SHA-256 `e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41`.
- Case-15 input: `data/pipes/open/15.in`, SHA-256 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`.
- Frozen-baseline judge transcript: `trace-current-run/runs/15/judge_output.txt`, SHA-256 `0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e`.

The oracle was not copied into any online candidate, and no full-open, holdout, or broader policy search was justified by these bounded local gains.
