# Post-hoc Pipes evaluation — native macOS

This is a local descriptive evaluation of the existing frozen candidate on 27 cases (Open15 and holdout-v2). It is not a qualification gate. The synthetic validation matrix remains a separate mixed-platform set (16 Linux/GCC 14.2 results plus two macOS results); CPU measurements from macOS are not comparable to the Linux safe/official CPU limits.

Environment: `macOS-26.6.2-arm64-arm-64bit-Mach-O`; `Apple clang version 17.0.0 (clang-1700.0.13.5)`; Python `3.14.5`.
Candidate source: `/Users/555tery/techarena/results/pipes/improvement/policy_conditioned_unique8/src/policy_conditioned.cpp` SHA-256 `365e0967b2687ec71619f0cd38df95480a34b8f03e165a5e5ab75c6a0c0edfe7`.
Frozen baseline SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`. Interactor source SHA-256 `85672e4c3ad9fdcb97d8b601758de1f1d1b5e86d6dd20252e0f72acdb9cb122a`.

KPI and trench values are compared within each exact input against the frozen baseline. Both solvers use the same local official interactor and exact input hash; algorithm decisions use the source's explicit deterministic integer RNG. Native macOS CPU values are reported for diagnosis only and do not establish Linux-limit compliance.

## Per-case outcomes

| Set | Case | Baseline KPI | Candidate KPI | ΔKPI | Baseline trench (m) | Candidate trench (m) | Δtrench (m) | Answers identical | Accepted B/C |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| open15 | 1 | 0.900000000 | 0.900000000 | +0.000000000 | 20 | 20 | +0 | yes | yes |
| open15 | 2 | 1.000000000 | 1.000000000 | +0.000000000 | 20 | 20 | +0 | yes | yes |
| open15 | 3 | 0.750000000 | 0.750000000 | +0.000000000 | 20 | 20 | +0 | yes | yes |
| open15 | 4 | 0.666666667 | 0.666666667 | +0.000000000 | 60 | 60 | +0 | yes | yes |
| open15 | 5 | 0.810070108 | 0.810070108 | +0.000000000 | 62760 | 62760 | +0 | yes | yes |
| open15 | 6 | 0.900000000 | 0.900000000 | +0.000000000 | 20 | 20 | +0 | yes | yes |
| open15 | 7 | 0.986470588 | 0.986470588 | +0.000000000 | 1700 | 1700 | +0 | yes | yes |
| open15 | 8 | 0.984468085 | 0.984468085 | +0.000000000 | 4700 | 4700 | +0 | yes | yes |
| open15 | 9 | 0.508392511 | 0.508392511 | +0.000000000 | 61960 | 61960 | +0 | yes | yes |
| open15 | 10 | 0.800000000 | 0.800000000 | +0.000000000 | 15380 | 15380 | +0 | yes | yes |
| open15 | 11 | 0.900132626 | 0.900132626 | +0.000000000 | 22620 | 22620 | +0 | yes | yes |
| open15 | 12 | 0.993120155 | 0.993120155 | +0.000000000 | 10320 | 10320 | +0 | yes | yes |
| open15 | 13 | 0.973170732 | 0.973170732 | +0.000000000 | 3280 | 3280 | +0 | yes | yes |
| open15 | 14 | 0.996932840 | 0.996932840 | +0.000000000 | 37820 | 37820 | +0 | yes | yes |
| open15 | 15 | 0.954062244 | 0.954062244 | +0.000000000 | 438920 | 438920 | +0 | yes | yes |
| holdout_v2 | case-01 | 0.999757635 | 0.999636496 | -0.000121139 | 330080 | 330120 | +40 | no | yes |
| holdout_v2 | case-02 | 0.014583333 | 0.014583333 | +0.000000000 | 480 | 480 | +0 | yes | yes |
| holdout_v2 | case-03 | 0.144444444 | 0.144444444 | +0.000000000 | 360 | 360 | +0 | yes | yes |
| holdout_v2 | case-04 | 0.999942904 | 0.999942904 | +0.000000000 | 315260 | 315260 | +0 | yes | yes |
| holdout_v2 | case-05 | 0.320000000 | 0.320000000 | +0.000000000 | 300 | 300 | +0 | yes | yes |
| holdout_v2 | case-06 | 0.103333333 | 0.103333333 | +0.000000000 | 300 | 300 | +0 | yes | yes |
| holdout_v2 | case-07 | 0.994946149 | 0.994946149 | +0.000000000 | 467960 | 467960 | +0 | yes | yes |
| holdout_v2 | case-08 | 0.264634146 | 0.264634146 | +0.000000000 | 820 | 820 | +0 | yes | yes |
| holdout_v2 | case-09 | 0.093333333 | 0.093333333 | +0.000000000 | 300 | 300 | +0 | yes | yes |
| holdout_v2 | case-10 | 0.999247379 | 0.999247379 | +0.000000000 | 192660 | 192660 | +0 | yes | yes |
| holdout_v2 | case-11 | 0.116666667 | 0.116666667 | +0.000000000 | 180 | 180 | +0 | yes | yes |
| holdout_v2 | case-12 | 0.084375000 | 0.084375000 | +0.000000000 | 320 | 320 | +0 | yes | yes |

## Descriptive summaries

| Set | Cases | Frozen weighted score sum | Candidate weighted score sum | Mean ΔKPI | Mean Δtrench (m) | Matching answer transcripts |
|---|---:|---:|---:|---:|---:|---:|
| open15 | 15 | 29.789717929 | 29.789717929 | +0.000000000 | +0.00 | 15/15 |
| holdout_v2 | 12 | 5.135264324 | 5.135143186 | -0.000010095 | +3.33 | 11/12 |

No Open15/holdout qualification gate or bootstrap claim is made here. Existing synthetic protocol-stop status is unchanged.

Detailed per-case CPU/RSS, transcript hashes, input hashes, harness exit codes, commands, and binary hashes are in `comparison.csv` and `run_manifest.json`. The Open15 frozen-baseline summary was recovered without rerunning; its command array is reconstructed from the runner and adjacent candidate invocation, and marked as such in the manifest.
