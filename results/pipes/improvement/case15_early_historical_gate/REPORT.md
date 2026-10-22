# Early prefix gate for the historical allocator

## Result

**No-go.** The one fixed prefix classifier reduced the Open15 score from **29.9320858172** to **29.3240394073** (−0.6080464099). All 15 cases returned `ok`; the worst solver CPU was 0.949339 s and peak RSS was 9.30 MiB. Since the full Open15 screen regressed, no holdout or synthetic follow-up was run.

## Classifier and policy

The first 32 positive placement requests are checked online. If every length is in the low band 1–7 m, the first 32 placements remain under the current champion and the historical regime begins at the next placement. Any out-of-band length rejects the gate permanently. This uses only observed request lengths; there is no test ID, command number, or future input. No thresholds were tuned.

On this Open15 set, the gate qualified cases 5, 9, 10, 11, 14, and 15. The result shows the prefix is not selective enough: cases 5, 9, 11, and 15 regressed, while cases 10 and 14 were unchanged. The largest losses came from cases 9 and 15.

| Case | Gate | Champion trench | Candidate trench | Weighted-score change |
|---:|:---:|---:|---:|---:|
| 5 | yes | 62,620 m | 63,140 m | −0.006686383 |
| 9 | yes | 48,540 m | 62,420 m | −0.144303373 |
| 10 | yes | 15,380 m | 15,380 m | 0 |
| 11 | yes | 22,620 m | 24,480 m | −0.068392430 |
| 14 | yes | 37,820 m | 37,820 m | 0 |
| 15 | yes | 438,920 m | 457,560 m | −0.388664224 |
| Other 9 cases | no | unchanged | unchanged | 0 |

## Reproduction

Candidate source: [champion_early_prefix_gate.cpp](source/champion_early_prefix_gate.cpp), SHA-256 `20da6b34d9dbd08826c8018b88d81d968914794177b4edaae4712ae5d17029cb`. It strict-built with:

```sh
g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror \
  results/pipes/improvement/case15_early_historical_gate/source/champion_early_prefix_gate.cpp \
  -o results/pipes/improvement/case15_early_historical_gate/bin/champion_early_prefix_gate
```

The local Open15 harness summary and per-case records are in [open15/summary.json](open15/summary.json) and [open15/cases.csv](open15/cases.csv). The current champion source and frozen/canonical sources were not modified. No website or Docker was used.
