# Case 5: bulk lane for the predicted deletion cohort

## Result

No Open-15 run was justified. The corrected policy ties the current champion on case 5 and therefore supplies no evidence for improving the Open-15 score.

| Variant | Case 5 trench | KPI | CPU | Peak RSS | Result |
|---|---:|---:|---:|---:|---|
| Current champion reference, reported by coordinator | 62,620 m | 0.811881188119 | — | — | Reference |
| Bulk lane armed at every qualifying size transition | 102,560 m | 0.495709828393 | 0.063881 s | 2.984 MiB | Severe regression |
| Bulk lane gated to next pipe length >= 39 | 62,620 m | 0.811881188119 | 0.053430 s | 3.188 MiB | Exact tie; no gain |

Both runs were valid on the local case-5 interactor, with the 5 s CPU and 256 MiB memory limits. Test SHA-256: `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b`.

## What was tested

The hypothesis was that the observed alternating deletion cohort could be packed into a contiguous tail slab, preserving old holes for the other cohort and creating a large reusable gap after deletion. The policy used only observed history: parity deletion mode, a dominant removed PID parity, and three recent equal-length runs with a linear size step.

The initial implementation armed on every qualifying size transition. Trace aggregation showed it was active repeatedly from small lengths onward: each block pre-reserved a large tail slab, while the other cohort was pushed into trench extensions. This explains the 102,560 m result; it is not evidence against an isolated length-40-only policy.

The corrected screen gated activation to `nextLength >= 39`. It returned exactly the coordinator-reported case-5 trench of 62,620 m. The candidate did not beat the current champion; no Open-15 or holdout run was made.

## Reproduction

Base source: `results/pipes/improvement/archive_mix_screen/gated_causal/pid46_rearm_geometric_gate1.cpp`, SHA-256 `89f7173f61fba3710e752607df4fec83195abe88a14a51b75ff7a710ed6d1982`.

Corrected candidate: `results/pipes/improvement/case5_bulk_delete_lane_gate/src/bulk_delete_lane_gate.cpp`, SHA-256 `3d7fdb6f4d2243ce6783006d1f76f34532a5a3f681c5017132bdf1fae0d61ec2`.

Build:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
  results/pipes/improvement/case5_bulk_delete_lane_gate/src/bulk_delete_lane_gate.cpp \
  -o results/pipes/improvement/case5_bulk_delete_lane_gate/bin/bulk_delete_lane_gate
```

Local screen:

```sh
python3 tools/pipes_harness.py \
  --solver results/pipes/improvement/case5_bulk_delete_lane_gate/bin/bulk_delete_lane_gate \
  --interactor results/pipes/final/bin/interactor \
  --tests data/pipes/open/5.in \
  --out results/pipes/improvement/case5_bulk_delete_lane_gate/runs/screen_case5_corrected \
  --name bulk-delete-lane-gte39-screen-case5 \
  --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

The frozen/canonical solver and website were not modified or used.
