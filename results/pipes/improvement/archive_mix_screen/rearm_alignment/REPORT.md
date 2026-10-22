# Composition check: re-arm reverse cohort + geometric alignment

## Result

The merged causal rules compile and pass the official local interactor on Open15 (15/15), but score **29.779763130622 / 32.1**. This is below frozen final (29.789717928594) by **0.009954797972**, and below the requested holdout gate 29.79136. I did not run holdout-v2.

Only cases 5 and 9 changed trench length or score. The merged rule regresses case 5 from 62,760 m to 63,580 m (**+820 m**, weighted score **−0.010447585543**) while improving case 9 from 61,960 m to 61,900 m (**−60 m**, **+0.000492787572**). The other 13 cases have identical trench and score. Raw judge transcripts also differ in cases 8, 13, and 14, without a score change.

This is a real policy interaction. The re-arm rule removes the smooth-trend veto and reverses the cohort edge. The geometric rule then overrides that edge when its observed three-run predictor fires. These branches both act on the same `runLeftActive` placement decision. I did not add trigger telemetry, so I cannot attribute the case-5 loss to an exact activation count; the combined Open15 result is sufficient to reject this merge.

For comparison, the component runs scored **29.790642260839** (case 5 candidate) and **29.791364277400** (case 9 candidate), each tested separately from frozen final. Their improvements do not compose: the combined candidate loses more on case 5 than it gains on case 9.

## Per-case delta from frozen final

| Case | Frozen trench | Merged trench | Δ trench | Δ weighted score | Transcript differs |
|---:|---:|---:|---:|---:|:---:|
| 1 | 20 | 20 | 0 | +0.000000000000 | no |
| 2 | 20 | 20 | 0 | +0.000000000000 | no |
| 3 | 20 | 20 | 0 | +0.000000000000 | no |
| 4 | 60 | 60 | 0 | +0.000000000000 | no |
| 5 | 62,760 | 63,580 | +820 | −0.010447585543 | yes |
| 6 | 20 | 20 | 0 | +0.000000000000 | no |
| 7 | 1,700 | 1,700 | 0 | +0.000000000000 | no |
| 8 | 4,700 | 4,700 | 0 | +0.000000000000 | yes |
| 9 | 61,960 | 61,900 | −60 | +0.000492787572 | yes |
| 10 | 15,380 | 15,380 | 0 | +0.000000000000 | no |
| 11 | 22,620 | 22,620 | 0 | +0.000000000000 | no |
| 12 | 10,320 | 10,320 | 0 | +0.000000000000 | no |
| 13 | 3,280 | 3,280 | 0 | +0.000000000000 | yes |
| 14 | 37,820 | 37,820 | 0 | +0.000000000000 | yes |
| 15 | 438,920 | 438,920 | 0 | +0.000000000000 | no |

Maximum measured candidate resources: **0.942137 s CPU**, **9.4375 MiB RSS**. Limits were 5 s CPU / 256 MiB.

## Merge and reproduction

The source starts from the case-9 candidate, which itself is derived from frozen final. I applied only the two case-5 edits at both mirrored locations: `runLeftActive` no longer checks `runLeftDisabledBySmoothTrend`, and the cohort side test changes from `sizeCohort != 0` to `sizeCohort == 0`. The case-9 geometric predictor and its override in both the rollout clone and live allocator remain unchanged.

Build command:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wshadow -Werror -pedantic \
  results/pipes/improvement/archive_mix_screen/rearm_alignment/solution.cpp \
  -o results/pipes/improvement/archive_mix_screen/rearm_alignment/solver
```

Open15 command:

```sh
python3 tools/pipes_harness.py \
  --solver results/pipes/improvement/archive_mix_screen/rearm_alignment/solver \
  --interactor tools/interactor --tests data/pipes/open \
  --out results/pipes/improvement/archive_mix_screen/rearm_alignment/open15 \
  --name rearm-reverse-plus-geometric-alignment-open15 \
  --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

No site, Docker, frozen-final source, or canonical source was changed.

## Hashes

| Artifact | SHA-256 |
|---|---|
| Frozen source | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` |
| Case-5 source | `88cdde2fe63a3681292ff1f06c201a087707379fa7d4060b462beb558ffa0ba4` |
| Case-9 source | `4d0eada1669b9a757b2d09bc82f46b3b7ef60f95f73f5f4e6d0c77ca00d95a8d` |
| Merged source | `0bb499d76233f12f056c9313319dec5ad22143c285396f70360535c1fd75b4fa` |
| Merged binary | `9f4477bb04bdcb57d5f41d562869c61747532f2e67e9b50e41e7bb75c11c76b3` |
| Open15 summary | `0e635ca33ce5799db702c01fdf1e3e490becd4ecd90e1ee6183bc3382a4fb030` |
| Open15 per-case CSV | `8beaa4937d70e0077a1dec301b08817d50500547ec89575f215ca2246a21ec95` |
| Harness | `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d` |
| Interactor | `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a` |
