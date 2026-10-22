# Combined-source rollout budget 64 check

## Result

An isolated copy of `results/pipes/final/solution.cpp` was made from source SHA-256 `e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41`. The copy changes only `kMcDecisionBudget` from 32 to 64; trials, depth, seed, gates, and thresholds are unchanged. No final or canonical source was edited.

The 15-case official open run passed all cases and scored **29.76927192121269**. This is **+0.037434509541157** over the frozen source's recorded open score **29.731837411671535**, but **0.011855078787310 below** the requested cutoff **29.781127**. It does not qualify for repeat, holdout-v2, or stress validation.

Since budget 64 improves the original combined source, the optional budget-16 experiment was not run. No variant cleared the requested cutoff, so the sweep stops here.

## Per-case deltas

Only three cases changed against the original combined-source open run:

| Case | Baseline weighted score | Budget-64 weighted score | Delta |
|---:|---:|---:|---:|
| 7 | 0.952840909090909 | 0.986470588235294 | +0.033629679144385 |
| 8 | 0.984468085106383 | 0.980296610169492 | −0.004171474936891 |
| 9 | 0.492341356673961 | 0.500317662007624 | +0.007976305333663 |

The other 12 cases are unchanged. The complete table includes all 15 input SHA-256 values in [`open-comparison.csv`](open-comparison.csv).

## Resources and reproduction

The highest measured solver use was on case 15: **0.966684 s CPU** and **9.562500 MiB RSS**, below the harness limits of 5 s and 256 MiB. The run summary, per-run outputs, and input list are in [`open/`](open/).

Frozen variant source: [`solution.cpp`](solution.cpp), SHA-256 `79ea69a005704a5e3417af376776daa056399f874687846a9d693954b95df3f3`. Strict binary: [`solver`](solver), SHA-256 `c476ece29094829724455513bcbfc5479c710eb7e28ab8f146800a03f3cdd0b0`.

Build and harness command:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror \
  results/pipes/improvement/max_open_lookahead/bounded_mc/final_combined_budget64/solution.cpp \
  -o results/pipes/improvement/max_open_lookahead/bounded_mc/final_combined_budget64/solver

python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_lookahead/bounded_mc/final_combined_budget64/solver --name combined_mc_budget64 --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/max_open_lookahead/bounded_mc/final_combined_budget64/open --cpu-limit 5 --memory-limit-mb 256
```

Harness SHA-256: `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d`; interactor SHA-256: `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`. See [`manifest.json`](manifest.json) for the exact run summary and per-input hashes.
