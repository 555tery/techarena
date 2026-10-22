# Case 5: reverse-order terminal slab

## Result

The reverse-order slab passed the local interactor but did not improve case 5: trench length remains **62,620 m**, KPI **0.811881188119**, matching the current champion's case-5 result. No Open-15 or holdout run was made.

| Variant | Case 5 trench | KPI | CPU | Peak RSS |
|---|---:|---:|---:|---:|
| Forward lane, gated to lengths 39–40 | 62,620 m | 0.811881188119 | 0.053430 s | 3.188 MiB |
| Reverse lane, gated to lengths 39–40 | 62,620 m | 0.811881188119 | 0.044861 s | 3.141 MiB |

## Trace diagnosis

At the start of the 39 block, trench length is 57,660 m. There are 63 free spans fitting lengths 39 and 40 (largest 67 m); the tail is `[57,618, 57,660)`, 42 m. The lane policy adds 2,420 m and places the predicted deletion cohort from the high-address side; its first 39 m pipe starts at 60,041 m.

After the 39 block's deletions, trench length is 60,080 m and only one free span fits 39/40: `[57,618, 60,080)`, 2,462 m. It can hold 61 pipes of length 40. On transition to 40, the policy adds 60 m to extend its reserved lane to 2,522 m; the first target-cohort pipe starts at 60,100 m. The other cohort then expands the trench while the large span remains reserved. Reversing the slab order therefore changes addresses but not the final trench length.

The trace shows why this branch ties rather than wins: a large coalesced hole already exists before the 40 block, but reserving it for only one predicted cohort prevents the other 40 m pipes from using its capacity. The pair-tail placement/orientation variant is exhausted for case 5.

## Reproduction

Candidate source: `src/bulk_delete_lane_reverse.cpp`, SHA-256 `5a2bf490c49bb49ca6c9191d3600913c5a4f7e774bdbef2bda7cc9b370d1885a`.

Binary SHA-256: `c9cd0339486b0e38140464f5641a31a6c2faac7afc238190d62a250d0fbbd514`.

Build:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
  results/pipes/improvement/case5_bulk_delete_lane_reverse/src/bulk_delete_lane_reverse.cpp \
  -o results/pipes/improvement/case5_bulk_delete_lane_reverse/bin/bulk_delete_lane_reverse
```

Local screen:

```sh
python3 tools/pipes_harness.py \
  --solver results/pipes/improvement/case5_bulk_delete_lane_reverse/bin/bulk_delete_lane_reverse \
  --interactor results/pipes/final/bin/interactor \
  --tests data/pipes/open/5.in \
  --out results/pipes/improvement/case5_bulk_delete_lane_reverse/runs/screen_case5 \
  --name bulk-delete-lane-reverse-screen-case5 \
  --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Test SHA-256: `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b`. Frozen/canonical solver, website, and Docker were not used.
