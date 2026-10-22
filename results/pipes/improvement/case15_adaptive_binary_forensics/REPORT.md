# Case 15: adaptive binary provenance and transfer check

## Finding

The 438,360 m result is reproducible from a reconstructed historical source. Its judge-output transcript is byte-identical to the saved run (`3b60d6aa…77e87`), confirming that the discrepancy came from a later source rewrite rather than a stale score file. The useful historical behavior did not transfer as a complete policy to the current champion: the parity-only overlay saved 40 m on case 15, while adding sticky-gap reuse regressed by 180 m. Neither beats 438,360 m, so this branch is a no-go and Open15 was not run.

## Provenance

The pre-existing binary is `segregated_allocator/adaptive_live_mean` (SHA-256 `ff1015a0…0213043`). Its current wrapper/base source hashes are `32ee2907…e86da6a` and `277eda6f…cddcc0`. A historical source reconstruction was made from the saved agent-session patch/build record and compiled locally with strict warnings. It reproduces the old case-15 placement transcript exactly:

| Run | Trench | KPI | Solver CPU | Peak RSS | Judge-output SHA-256 |
|---|---:|---:|---:|---:|---|
| Saved old binary | 438,360 m | 0.955281048 | 0.923272 s | 6.33 MiB | `3b60d6aa12c9e007f40de2bd29fd32380a9f3d5708d24144bd0ac2be91777e87` |
| Reconstructed source | 438,360 m | 0.955281048 | 0.944192 s | 6.31 MiB | same, byte-for-byte |

Historical source: [adaptive_base_historical.cpp](source/adaptive_base_historical.cpp), SHA-256 `7208e668…c2527c`; wrapper: [adaptive_live_mean_historical.cpp](source/adaptive_live_mean_historical.cpp), SHA-256 `d6b49fe7…47d60`. Build command:

```sh
g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror \
  results/pipes/improvement/case15_adaptive_binary_forensics/source/adaptive_live_mean_historical.cpp \
  -o results/pipes/improvement/case15_adaptive_binary_forensics/bin/historic_adaptive_live_mean
```

The historical source differs from the currently saved adaptive source in three relevant ways: it starts in segregated mode; its live-mean hysteresis can switch modes immediately without the later 32-placement same-size gate; and while segregated it uses PID-parity placement plus same-length sticky-remainder reuse. When the mode is off, it uses the existing short-pipe/46-run endpoint rule for fitting gaps and grows from the low end.

The historical binary's Open15 score was **28.9517199951/32.1**, versus **29.9320858172/32.1** for the current champion. It gains case 15 but has broad regressions, especially case 9 (62,240 m vs 48,540 m); therefore its binary was not substituted. See the per-case lengths below.

| Case | Historical m | Champion m | Case | Historical m | Champion m | Case | Historical m | Champion m |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 20 | 20 | 6 | 20 | 20 | 11 | 22,620 | 22,620 |
| 2 | 40 | 20 | 7 | 1,760 | 1,700 | 12 | 10,540 | 10,320 |
| 3 | 20 | 20 | 8 | 4,860 | 4,700 | 13 | 3,300 | 3,280 |
| 4 | 80 | 60 | 9 | 62,240 | 48,540 | 14 | 37,820 | 37,820 |
| 5 | 63,440 | 62,620 | 10 | 15,380 | 15,380 | 15 | 438,360 | 438,920 |

## Transfer probes on the current champion

Both sources are separate copies; the champion and frozen/canonical sources were untouched. Each was strict-built and screened only on local Open case 15.

| Variant | Causal change | Case-15 trench | Δ vs champion | KPI | CPU / RSS | Source SHA-256 |
|---|---|---:|---:|---:|---:|---|
| Champion baseline | none | 438,920 m | — | 0.954062244 | 1.002304 s / 5.95 MiB | `43bfbdad…220200` |
| Live-mean parity overlay | Track active pipe count/length; apply historical 12/5 disable and 21/10 enable thresholds; while active use PID-parity edge, including tail growth | 438,880 m | −40 m | 0.954149198 | 0.949580 s / 9.53 MiB | `5e0e4bc9…14b54` |
| Parity + sticky remainder | Above, plus same-length reuse of the prior remainder while the mode stays active | 439,100 m | +180 m | 0.953671146 | 0.963215 s / 9.59 MiB | `0c9aaee2…fe381` |

Sources: [parity overlay](source/champion_live_mean_parity_overlay.cpp) and [parity plus sticky overlay](source/champion_live_mean_parity_sticky_overlay.cpp). Both strict builds succeeded with the command above, substituting the relevant source and binary names. Neither candidate reaches the historical 438,360 m mark, so there is no Open15 result to report.

## Conclusion

The historical result is a genuine source-revision effect, not a binary anomaly. On the current architecture, the observable live-mean/PID-parity signal recovers only 40 m, and copying the sticky-remainder behavior makes case 15 worse. The 560 m gap to the old binary is therefore interaction-dependent and was not recovered by these two causal variants. Stop this branch rather than tuning its thresholds on case 15.

All runs used the local harness only; no platform or Docker was used.
