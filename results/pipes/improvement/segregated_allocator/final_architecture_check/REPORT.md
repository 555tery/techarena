# Strict source rebuild: adaptive segregated allocator screen

## Scope and decision

This bounded check compares three source implementations under fresh strict builds against the current best source, `alternating_delete_parity_edges.cpp` (SHA-256 `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`). Only official cases 5, 9, and 15 were screened. The older prebuilt binaries were not used because their recorded behavior does not match the current sources.

All four builds passed Apple Clang 17 with:

```text
clang++ -O2 -std=c++20 -Wall -Wextra -Werror -pedantic
```

Every run passed the official interactor. The three rebuilt allocator sources produce byte-identical judge transcripts on all three screened cases.

## Results

| Source | Case 5 trench / KPI | Case 9 trench / KPI | Case 15 trench / KPI | Weighted sum, cases 5+9+15 | Δ vs current best |
|---|---:|---:|---:|---:|---:|
| Current best `57338ca2…` | 62,800 / 0.809554140127 | 62,440 / 0.504484304933 | 438,920 / 0.954062243689 | 10.854660881951 | — |
| `adaptive_live_mean.cpp` | 63,460 / 0.801134572959 | 62,400 / 0.504807692308 | 438,920 / 0.954062243689 | 10.846564702158 | −0.008096179793 |
| `adaptive_live_mean_minrun32.cpp` | same | same | same | 10.846564702158 | −0.008096179793 |
| `cohort_sticky_live_mean32.cpp` | same | same | same | 10.846564702158 | −0.008096179793 |

The allocator variants lose 660 m on case 5, gain 40 m on case 9, and make no change on case 15. The case-5 loss (−0.008419567168 KPI) outweighs the case-9 gain (+0.000323387375). Case 15 remains at 438,920 m, so the required case-15 improvement and net screen gain both fail. No code was integrated, and no full-open or holdout run was launched.

Resource use remained below the 5 s / 256 MiB limits. Across the candidate runs, the largest solver CPU time was 1.342775 s and the largest solver RSS was 6.3125 MiB (case 15). The baseline maxima were 1.017268 s and 9.140625 MiB.

## Source inspection

The three names do not represent three distinct algorithms in these source snapshots:

- `adaptive_live_mean.cpp` defines policy 7, a 2,048-request window, scale 60, PID-parity right placement, and sticky-mode enable/disable ratios; it includes `adaptive_base.cpp`.
- `adaptive_live_mean_minrun32.cpp` sets the same macros and explicitly sets `PIPES_STICKY_MIN_RUN` to 32. The base already defaults this value to 32.
- `cohort_sticky_live_mean32.cpp` defines the same settings and embeds the same base implementation. Its body after the wrapper is identical to `adaptive_base.cpp`.

Thus all three select the same policy parameters and their transcripts are identical. In the base, a 32-or-longer same-size request run can enable segregated mode when the incoming size is at most 2.1 times the mean live pipe length (or when no pipes are live); the mode is disabled at 2.4 times the mean. The allocator then favors a sticky remainder gap and alternates the placement edge by PID parity. This did not affect case 15's final trench in the screen, and the case-5 regression rejects the architecture overlay for the current best.

The common candidate transcript hashes are case 5 `6c3477a3edea8fa4e342bdbc5ccc638db56d84b2741c177c8e2e3cddb268635f`, case 9 `049f4c15f53861dd757608d64049e6b438df596c64dca7c22acacc68184eb1b6`, and case 15 `fc30e6f9145581e53f4ddfb0a16e51253c44da5cc689852f272c01206528ec45`. The current-best transcript hashes are case 5 `21b1dcc7ccdff134b604feebb814758b9034bac0080a09da5aa01cfdd382c17a`, case 9 `40fc3c3bdcfcdd69fea86bdb8a221db7c5d4dc2693c9c3d2b6631bc3fb41831b`, and case 15 `0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e`.

## Reproducibility hashes

| Artifact | SHA-256 |
|---|---|
| `adaptive_live_mean.cpp` | `32ee2907511918b0b5cf174fd67786557855a04f70814d2365b673c05e86da6a` |
| `adaptive_live_mean_minrun32.cpp` | `ab1fa9b772b316448a18d255fe0944af8b13e85cd1c19d9437f0df9f2511801c` |
| `cohort_sticky_live_mean32.cpp` | `b08d01c9cfb5dfc66a3f69359caceb0cf4276d3f1fe0b70e31c0fb891e667a55` |
| shared `adaptive_base.cpp` | `277eda6f269127c62ff27edd0f5fe5377438030c747b2ea8180ee126cfcddcc0` |
| freshly built `adaptive_live_mean` | `24a07c8e46ffe9fb450944404a994aa6af38b99c9e613223ebfe72c3265e0c20` |
| freshly built `adaptive_live_mean_minrun32` | `fcdfc1543d431056545f0e79c2cb3db57c889fcb16af2520cf7581c7fcc2c6a2` |
| freshly built `cohort_sticky_live_mean32` | `4d67283551f4a90e5be61a7669ee9c21f898efbbc60b00a0f7119a294100baf1` |
| freshly built current-best binary | `3c6abe73af8db998cb514e113f4915fe9e0072a6a83c9d7986dc7db363729332` |
| case 5 input | `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b` |
| case 9 input | `cfb711efa3a9ccccc17e7170fc7c2ea19c12ed45b789da3a4b2c80750d7ca128` |
| case 15 input | `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353` |

Per-case CPU, RSS, scores, and transcript hashes are in each variant's `cases.csv` and `runs/{5,9,15}/` directory under this check folder.
