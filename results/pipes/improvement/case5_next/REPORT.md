# Case 5: online deletion-neighborhood experiment

## Result

**No candidate win.** The tested online feature records the coalescence history of each free interval. When a deletion joins existing free intervals, it adds one merge event per joined interval and carries the resulting count through later splits. For equal allocator fit scores, the chooser prefers the interval with more observed coalescences. The feature uses only prior placements/deletions and current free-span state; it does not read future commands, test IDs, or command indices.

Interactive checks against a freshly built snapshot of the current final source show:

| Open case | Baseline trench / KPI | Candidate trench / KPI | Candidate delta | Candidate CPU / peak RSS |
|---:|---:|---:|---:|---:|
| 5 | 62,800 m / 0.8095541401273886 | 62,800 m / 0.8095541401273886 | 0 m | 0.081934 s / 2.921875 MiB |
| 9 | 62,440 m / 0.5044843049327354 | 62,440 m / 0.5044843049327354 | 0 m | 0.100660 s / 3.109375 MiB |
| 15 | 438,920 m / 0.9540622436890549 | 439,280 m / 0.9532803678747040 | +360 m, KPI −0.0007818758143509 (weighted score −0.007818758143509) | 1.199870 s / 9.921875 MiB |

All six runs were protocol-OK; neither candidate nor baseline exceeded the harness limits (5 s solver CPU, 256 MiB RSS). On case 5 and case 9, baseline and candidate judge-output transcripts are byte-identical. Case 15 differs and the candidate is worse. Thus the feature does not improve its target case and the measured effect does not generalize favorably. I did not run the full open-15 suite or holdout: this screen failed the requested improvement gate, so there is no promising candidate to validate further.

The earlier cohort evidence for case 5 remains censored: cohort 1 was not observed to be removed before EOF. That is not evidence that cohort 1 pipes have intrinsically long lifetimes. In the corrected replay, operation 509 removes a length-3 pipe after 8 cohort-0 and 0 cohort-1 removals of that length; the 502/63 interpretation was an erroneous intermediate replay and is not used here. The present candidate does not use that cohort gate.

The exact per-case rows and transcript-identity flags are in [comparison.csv](comparison.csv); raw harness outputs are in `runs/baseline{5,9,15}` and `runs/consistent{5,9,15}`.

## Reproduction

Baseline snapshot: [current_final.cpp](src/current_final.cpp), SHA-256 `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`.

Candidate: [coalescence_lineage_consistent.cpp](src/coalescence_lineage_consistent.cpp), SHA-256 `8685b4acf41a21fa2b6329d52e3ea626cd7e7d25bb1735020ce894f5f3f3dc99`; binary SHA-256 `684e1b35bacf6c5898d9ec9079f67a81d30cb63dc749e7e733bf3be14b9bc053`.

The baseline binary SHA-256 is `3e29292287d65f2a1a640cf249f91daa1d4e4be1b3feaff6c03b7c01b4058194`. Both binaries were compiled with Apple clang 17.0.0 using:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
  results/pipes/improvement/case5_next/src/current_final.cpp \
  -o results/pipes/improvement/case5_next/bin/current_final
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
  results/pipes/improvement/case5_next/src/coalescence_lineage_consistent.cpp \
  -o results/pipes/improvement/case5_next/bin/coalescence_lineage_consistent
```

Both strict builds succeeded. The harness and interactor SHA-256 values were `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d` and `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`, respectively. Inputs were case 5 `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b`, case 9 `cfb711efa3a9ccccc17e7170fc7c2ea19c12ed45b789da3a4b2c80750d7ca128`, and case 15 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`.

The exact interactive harness commands were:

```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_next/bin/current_final --interactor tools/interactor --tests data/pipes/open/5.in --out results/pipes/improvement/case5_next/runs/baseline5 --name current-final-snapshot-case5 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_next/bin/current_final --interactor tools/interactor --tests data/pipes/open/9.in --out results/pipes/improvement/case5_next/runs/baseline9 --name current-final-snapshot-case9 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_next/bin/current_final --interactor tools/interactor --tests data/pipes/open/15.in --out results/pipes/improvement/case5_next/runs/baseline15 --name current-final-snapshot-case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_next/bin/coalescence_lineage_consistent --interactor tools/interactor --tests data/pipes/open/5.in --out results/pipes/improvement/case5_next/runs/consistent5 --name lineage-consistent-case5 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_next/bin/coalescence_lineage_consistent --interactor tools/interactor --tests data/pipes/open/9.in --out results/pipes/improvement/case5_next/runs/consistent9 --name lineage-consistent-case9 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_next/bin/coalescence_lineage_consistent --interactor tools/interactor --tests data/pipes/open/15.in --out results/pipes/improvement/case5_next/runs/consistent15 --name lineage-consistent-case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Run directory/name mapping: baseline cases 5/9/15 → `baseline5`, `baseline9`, `baseline15` with names `current-final-snapshot-case5`, `current-final-snapshot-case9`, `current-final-snapshot-case15`; candidate cases 5/9/15 → `consistent5`, `consistent9`, `consistent15` with names `lineage-consistent-case5`, `lineage-consistent-case9`, `lineage-consistent-case15`.

An earlier exploratory source, `coalescence_lineage.cpp` (SHA-256 `d75e4006e27faa6c6e5525d95187e2e87959319ced52d474d3e7d5759651e301`), let the rollout simulator compare every equal-length gap while the live index compared only its selected representative. It was not used for the conclusion; the corrected source above makes the simulator follow the live index.

No canonical source, final binary, or platform submission was changed.
