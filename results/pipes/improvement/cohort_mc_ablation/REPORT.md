# Cohort placement and tail ablations on corrected MC candidate

## Verified starting point

The requested base was confirmed against `results/pipes/improvement/beam_diagnosis/corrected_mc_overlay.json`:

- Source: `source/cohort_owner_mc_corrected_scoped_run.cpp`
- SHA-256: `e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41`, matching the JSON manifest.
- Corrected MC + scoped-run official open score: `29.781127111082185 / 32.1`; case 5 trench: `62,800 m`.
- Canonical `src/pipes.cpp` SHA-256 stayed `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.

I copied the source unchanged to `src/base.cpp`, strict-compiled it with `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror`, and reran the official harness on cases 5, 7, 9, and 12. It reproduced all four rows from the source report. This four-case score sum is `6.26882301053` with official weights (case 12 has weight 4).

## Three causal ablations

Each variant was independently derived from the frozen base, strict-compiled, then screened on exactly official cases 5, 7, 9, and 12. Per-case deltas are against the corrected MC base above.

| Variant | Exact change | Case 5 KPI / trench; Δ | Case 7 Δ | Case 9 Δ | Case 12 Δ | Weighted sum on four cases |
|---|---|---:|---:|---:|---:|---:|
| Base | — | 0.809554140127 / 62,800 m; — | — | — | — | 6.26882301053 |
| `shared_mc_pool` | In cohort mode, let MC compare owner-compatible and shared gaps in one candidate pool. Foreign-owned gaps remain excluded. | 0.809554140127 / 62,800 m; **0** | 0 | 0 | 0 | 6.26882301053 |
| `flip_cohort_edge` | Reverse which parity cohort is placed at the high edge in cohort mode, in both live allocator and MC rollout. | 0.798868636078 / 63,640 m; **−0.010685504049, +840 m** | 0 | 0 | 0 | 6.25813750648 |
| `reuse_foreign_tail` | On expansion fallback, use a foreign-owned free tail; relabel any remainder crossing old/new regions as shared. | 0.718485019785 / 70,760 m; **−0.091069120342, +7,960 m** | 0 | 0 | 0 | 6.17775389018 |

All four cases passed for all candidates. The unchanged cases had exactly the same KPI and trench as base. Maximum per-case CPU/RSS among the four target tests:

| Variant | Max CPU | Max RSS |
|---|---:|---:|
| Base | 0.055094 s | 3.109 MiB |
| `shared_mc_pool` | 0.053035 s | 3.094 MiB |
| `flip_cohort_edge` | 0.056393 s | 3.109 MiB |
| `reuse_foreign_tail` | 0.064662 s | 3.109 MiB |

The `shared_mc_pool` first draft briefly appeared to save 80 m on case 5. Code review caught that its fit-search helper had moved the existing `slack > 40` cutoff before candidate evaluation, changing a non-cohort fallback behavior. That provisional output is retained under `runs/discarded_shared_pool_pre_fix/` and explicitly excluded. After restoring the base cutoff order and rerunning, the candidate ties on all four cases.

## Why no full open or holdout run was made

The only changed code paths are conditional on `parityCohortMode`. A direct causal replay of the gate over all 15 open inputs found it activates only in case 5 (operation 509); the other 14 cases never activate it. Thus these variants can only change open case 5. The one variant with no case-5 change therefore cannot exceed `29.781127111082185`; the other two already regress case 5. None met the requested gate for a full open-15 or holdout-v2 run, so those runs were not spent.

## Decision

No new candidate clears the score threshold. Keep the corrected MC + scoped-run source as the best of this branch. The only plausible policy alternative, sharing MC candidates across owner-compatible/shared gaps, ties case 5 after an exact implementation and cannot change the other open cases. Reversing cohort sides or consuming the foreign wilderness tail makes case 5 worse. No source in this directory was integrated into `src/pipes.cpp`.

## Reproduction and hashes

- `src/base.cpp` — verified copy of the requested corrected candidate.
- `src/shared_mc_pool.cpp`, `src/flip_cohort_edge.cpp`, `src/reuse_foreign_tail.cpp` — independent ablations.
- `make_variants.py` — exact source mutation recipe.
- `tests/` — copies of official cases 5, 7, 9, and 12.
- `runs/base_screen/`, `runs/shared_mc_pool_screen_fixed/`, `runs/flip_cohort_edge_screen/`, `runs/reuse_foreign_tail_screen/` — official harness outputs.
- Compiler: `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror`.
- Harness: `tools/pipes_harness.py`, official interactor, 5 s CPU / 256 MiB RSS per case.

Source SHA-256:

- corrected base: `e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41`
- `shared_mc_pool.cpp`: `71e48adb51a04881ddf77126e2ef67a81d32b1b1f68bdfe50bc7ee6a480cffa5`
- `flip_cohort_edge.cpp`: `dc02d8d0ee8a5e9917e66b41a9b18d24b130251e0d3ad0bfd4b2572ced5b7004`
- `reuse_foreign_tail.cpp`: `f4c6497a18ff4779b03cadc1d82f94f1079c54c94516af28adf11d71e097aaeb`

Binary SHA-256:

- base: `e91fd2b73da63680fdde021e6d64c4feecaa68b31807f21af1518e1af7fe1921`
- `shared_mc_pool`: `1ee00425cf5e02aa1d0dcdfc1c5d914987c020f7a73acb6c0eef9b554442f30f`
- `flip_cohort_edge`: `d0b2edb6d91c85dd255ab330df05640065e8b0ff77755c6bef556679a3fd2d9a`
- `reuse_foreign_tail`: `ec24cd4189e94004375479c5aa40d0cd42b2fb4e24e2907d8d33fa28b03c74b4`
