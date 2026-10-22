# Case 15 online-policy investigation

## Conclusion

No candidate improved official open case 15. The best screen candidate, recent-PID adjacency, increased its trench from 438,920 m to 458,940 m (+20,020 m), lowering its case KPI from 0.954062243689 to 0.912443892448. The other tested policies were substantially worse. None passed the screen gate, so no candidate was run on all 15 open cases or on holdout data. No final/canonical source or platform submission was changed.

The results argue against using recent deletion rank as a strong allocation mode switch. Case 15 has a near-LIFO component, but enough older-pipe removals remain that restricting placements to a tail/suffix or privileging recent neighbors fragments the rest of the trench.

## Reference and trace diagnosis

The reference is `results/pipes/final/solution.cpp`, SHA256 `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`. Its recorded full open-15 score is 29.785293754. On the three screening cases it obtains:

| Case | Weight | Trench (m) | KPI | Solver CPU | Solver peak RSS |
|---:|---:|---:|---:|---:|---:|
| 5 | 1 | 62,800 | 0.809554140127 | 0.040189 s | 2.828 MiB |
| 9 | 1 | 62,440 | 0.504484304933 | 0.053877 s | 2.969 MiB |
| 15 | 10 | 438,920 | 0.954062243689 | 1.000328 s | 9.266 MiB |

Case 15 contains 200,000 commands: 130,255 placements and 69,745 removals. Peak live pipe length is 418,768 m; the section-rounded lower bound is 418,780 m. The reference trench therefore has 20,140 m overhead over that lower bound. Trace reconstruction found 17,645 trench-growth events; 13,677 occurred when total free length was already at least the incoming pipe length. The first 100,000 commands are placement-heavy and stay close to the lower bound; the second half is approximately balanced churn and produces most of the fragmentation. Removals remain biased toward recent PIDs, but are not strict LIFO: the late stream has a substantial older-PID tail. This explains why stack and suffix restrictions strand reusable old gaps.

Inputs used in the screens were case 5 SHA256 `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b`, case 9 `cfb711efa3a9ccccc17e7170fc7c2ea19c12ed45b789da3a4b2c80750d7ca128`, and case 15 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`.

## Candidate screens

Each candidate was evaluated on official cases 5, 9, and 15 with the official harness. Values are trench / KPI / solver CPU / solver peak RSS. `Δ trench` is candidate minus reference; positive means worse. Scores are for the individual case, not the combined open-15 score.

| Past-only policy | Case 5 | Case 9 | Case 15 | Case 15 Δ trench | Weighted screen sum (5+9+15) |
|---|---|---|---|---:|---:|
| Tail-only stack, left-edge placement | 79,160 / 0.642243557352 / 0.045025 s / 2.906 MiB | 62,440 / 0.504484304933 / 0.054074 s / 2.969 MiB | 1,494,740 / 0.280153739112 / 1.199813 s / 9.828 MiB | +1,055,820 m | 3.948265253403 |
| LIFO suffix arena | 79,060 / 0.643055906906 / 0.049532 s / 2.906 MiB | 62,440 / 0.504484304933 / 0.054939 s / 2.969 MiB | 478,400 / 0.875328177258 / 1.131607 s / 11.172 MiB | +39,480 m | 9.900821984414 |
| Balanced-churn LIFO suffix arena | 62,800 / 0.809554140127 / 0.045817 s / 2.844 MiB | 62,440 / 0.504484304933 / 0.055342 s / 2.984 MiB | 747,520 / 0.560195044949 / 1.123590 s / 10.578 MiB | +308,600 m | 6.915988894546 |
| Recent-PID adjacency bias | 62,920 / 0.808010171647 / 0.046941 s / 2.781 MiB | 62,440 / 0.504484304933 / 0.055478 s / 3.000 MiB | 458,940 / 0.912443892448 / 1.603269 s / 8.375 MiB | +20,020 m | 10.436933401057 |

All runs completed under the 5 s CPU / 256 MiB memory caps. Relative to the reference weighted score on these same three tests (10.854660881951), the best candidate's screen sum is lower by 0.417727480893. No full open-15 result is claimed for any candidate.

## Artifacts and hashes

All candidate artifacts are isolated under this directory. Source and current executable SHA256 values:

| Policy | Source | Source SHA256 | Executable | Executable SHA256 |
|---|---|---|---|---|
| Tail-only stack, left edge | `source/lifo_tail_stack.cpp` | `1c0d604e9c855640a4e7d1b6ef20d01f4e2b82ba9a9d09f080b4b0dcb73fc807` | `bin/lifo_tail_stack` | `515328212bdd2085681450e3c6e2f09a8a3012a1535d046319a0f77f0c1e3f55` |
| LIFO suffix arena | `source/lifo_suffix_arena.cpp` | `c6e21122bd8af5b55cc17c1611636970d810c6974054603ca9eca9b80e7b417a` | `bin/lifo_suffix_arena` | `b2528c89e60d22dd7717f5741cc6baed0f8ad5556beffb6985cad8e91d5123bf` |
| Balanced-churn LIFO suffix arena | `source/lifo_churn_phase.cpp` | `b5fd80231ad7c66794814f8f818d079823309f76fff959fff25cc1765aa8e0e0` | `bin/lifo_churn_phase` | `d17528f3797d11e6405d11dd156834eff4204c1a4467f373f28b8e15662cfc73` |
| Recent-PID adjacency bias | `source/recent_pid_adjacency.cpp` | `439ec6ad402a7ba2b8a030eea1227150f6f7e8b81cbf8ce52667433071bca352` | `bin/recent_pid_adjacency` | `388871c22c49aa21a633352f48c19281170c9a9b9b71cbf1088790b146bc6210` |

Detailed case records and resource measurements are in `screen/lifo-tail-stack-left-edge/cases.csv`, `screen/lifo-suffix-arena/cases.csv`, `screen/lifo-churn-phase/cases.csv`, and `screen/recent-pid-adjacency/cases.csv`; each directory also contains the corresponding summary and raw judge/interactor outputs. The early `screen/lifo-tail-stack/` run predates the left-edge correction and its executable was overwritten; it is not used as source-linked evidence.

Trace artifacts are `analysis/trace_diagnosis.py` and `analysis/trace_diagnosis.json`.
