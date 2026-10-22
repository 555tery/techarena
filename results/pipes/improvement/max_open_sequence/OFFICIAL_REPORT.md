# Candidate: 1024-window history score with right-edge placement

## Official open result

The candidate passed **15/15** official open cases and scored **29.049090580812/32.1**. The unchanged canonical S50 source passed the same suite at **28.939458940265/32.1**. Difference: **+0.109631640546**.

The candidate is a generic online rule: it uses a 1024-placement length history, the same scale-50 penalty for currently unfit residuals, and places each selected pipe at the right edge of its chosen free interval. It contains no test identifier or sequence detection.

## Per-case comparison

| Case | Weight | Baseline KPI / H | Candidate KPI / H | Weighted delta |
|---:|---:|---:|---:|---:|
| 1 | 0.1 | 0.900000000 / 20 | 0.900000000 / 20 | +0.000000000 |
| 2 | 1 | 1.000000000 / 20 | 1.000000000 / 20 | +0.000000000 |
| 3 | 1 | 0.375000000 / 40 | 0.750000000 / 20 | +0.375000000 |
| 4 | 1 | 0.666666667 / 60 | 0.500000000 / 80 | -0.166666667 |
| 5 | 1 | 0.499803382 / 101720 | 0.524881272 / 96860 | +0.025077890 |
| 6 | 1 | 0.900000000 / 20 | 0.900000000 / 20 | +0.000000000 |
| 7 | 1 | 0.998214286 / 1680 | 0.975000000 / 1720 | -0.023214286 |
| 8 | 1 | 0.988675214 / 4680 | 0.959958506 / 4820 | -0.028716707 |
| 9 | 1 | 0.500000000 / 63000 | 0.492341357 / 63980 | -0.007658643 |
| 10 | 1 | 0.666522210 / 18460 | 0.666522210 / 18460 | +0.000000000 |
| 11 | 1 | 0.900929204 / 22600 | 0.908162355 / 22420 | +0.007233152 |
| 12 | 4 | 0.993120155 / 10320 | 0.974239544 / 10520 | -0.075522445 |
| 13 | 4 | 0.961445783 / 3320 | 0.967272727 / 3300 | +0.023307777 |
| 14 | 4 | 0.996405920 / 37840 | 0.993779652 / 37940 | -0.010505070 |
| 15 | 10 | 0.954976055 / 438500 | 0.954105719 / 438900 | -0.008703359 |

The clearest gains are case 3 (H 40→20) and case 5 (H 101,720→96,860). Case 4 falls from H=60 to H=80; cases 7, 8, 9, 12, 14, and 15 also lose weighted score. The net gain is therefore a measurable open-set improvement, not per-case dominance.

## Reproduction and artifact hashes

Official harness command:

```sh
clang++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/max_open_sequence/candidate_window1024_right.cpp -o results/pipes/improvement/max_open_sequence/candidate_window1024_right
python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_sequence/candidate_window1024_right --name window1024-right --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/max_open_sequence/official-open-window1024-right --response-timeout 5 --wall-timeout 120
```

SHA256 values and exact input hashes are in [`official_open_evidence.json`](official_open_evidence.json). Full per-case harness output is in [`official-open-window1024-right/summary.json`](official-open-window1024-right/summary.json) and [`official-open-window1024-right/cases.csv`](official-open-window1024-right/cases.csv).

## Limits

This variant was selected by a parameter sweep on the 15 open inputs. Its 1024 window and right-edge choice are therefore open-set tuned. There is no evidence here that it improves hidden tests. The parameter search did not use test-ID branches, but the open cases themselves strongly shaped parameter selection.
