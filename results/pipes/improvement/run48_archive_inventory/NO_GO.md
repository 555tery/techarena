# Run-48 archive inventory — no-go

**Decision:** no archived candidate met all three conditions: one causal change, Open15 score above run-48, and an independent validation gate already recorded for that exact source. No local tests or platform actions were performed in this follow-up.

## Target snapshot

Read-only Safari leaderboard snapshot: `NSUts` page `olympic.nsu.ru/nsuts-new/ranking`, last page update shown as **03:08:15**. `бюро 67` is rank **16** with **29.79021957 / 32.1**, matching the saved run-48 Open15 total **29.790219562101**. The displayed leader `OPZ` has **30.27796507**, a gap of approximately **0.48774550**.

The bureau's displayed per-case scores were: `0.09000000, 1.00000000, 0.75000000, 0.66666667, 0.81188119, 0.90000000, 0.98647059, 0.98446809, 0.50708306, 0.80000000, 0.90013263, 3.97248062, 3.89268293, 3.98773136, 9.54062244`. Case 9 is the largest visible weak spot, consistent with the archived candidate below.

## Strongest archived lead, rejected for lack of an independent gate

`case9_next/preliminary_pid_lane_excluded` is the only exact-input archived Open15 run found above run-48. Its isolated source changes the long same-size-run edge assignment from size-local occurrence parity to PID parity in the live allocator and rollout copy. Its score is **29.791529008364 / 32.1**, or **+0.001309446262** versus run-48. The only score/trench change is case 9: **62,120 m → 61,960 m**, gaining **+0.001309446262** weighted score; the other 14 scores are unchanged.

This is not qualified for continuation here: the archived folder contains the targeted case-9 screen and the same Open15 set, but no holdout or fresh synthetic run for this exact source. The enclosing `case9_next/manifest.json` explicitly records the preprobe as excluded: “PID-parity-trigger preprobe was excluded by task constraint; do not treat as selected candidate.” That exclusion and the missing independent gate are sufficient for no-go; its positive Open15 result alone is not independent evidence.

## Other causal candidate with a gate

The archived size-cohort-lanes candidate does have holdout-v2 and Open15 reruns, but its source is the frozen final (`c4b737…32a991`) and its Open15 result is **29.789717928594**, which is **0.000501633507 below run-48**. Holdout-v2 was neutral. It therefore does not improve the current target.

Run-48 itself has a real but neutral independent gate: holdout-v2 (12/12, unchanged score/output) and eight pre-fixed fresh synthetic streams (all outputs and scores equal). Those runs validate run-48 relative to frozen final, not the PID-parity preprobe.

## Inventory scope and integrity

The scan covered **759** saved `cases.csv` artifacts under `results/pipes/improvement/`, keeping only complete successful rows whose 15 input hashes exactly match the saved Open15 baseline. Among those rows, no other distinct archived result exceeded run-48. This is an inventory of the current workspace artifacts, not a claim about unrecorded variants.

Frozen final and canonical source hashes were rechecked and remain unchanged:

- `results/pipes/final/solution.cpp`: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`
- `src/pipes.cpp`: `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`

No platform submission, platform test, or local solver test was made. Next useful step, if explicitly authorized, would be a narrowly scoped independent local validation of the PID-parity preprobe; it is not recommended as a submission candidate without that gate and resolution of the prior exclusion.
