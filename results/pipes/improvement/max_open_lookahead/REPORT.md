# Frozen open-test comparison

All candidates were run through `tools/pipes_harness.py` with the same official interactor and all 15 `data/pipes/open/*.in` inputs. Input SHA-256 values are checked equal across reports in `harness-manifest.json`.

## Scores

| Candidate | Weighted score / 32.1 | Delta vs adaptive right4/W2048/S60 | Valid |
|---|---:|---:|---:|
| `adaptive_right4_w2048_s60` | 29.441565327452 | +0.000000000000 | 15/15 |
| `adaptive_recent8_right` | 29.411227473594 | -0.030337853858 | 15/15 |
| `adaptive_recent16_right` | 29.424512955518 | -0.017052371934 | 15/15 |
| `adaptive_recent20_right` | 29.435625431645 | -0.005939895807 | 15/15 |
| `adaptive_recent24_right` | 29.435518404581 | -0.006046922870 | 15/15 |
| `adaptive_recent28_right` | 29.436268517621 | -0.005296809831 | 15/15 |
| `adaptive_recent32_right` | 29.443752822248 | +0.002187494797 | 15/15 |
| `adaptive_recent36_right` | 29.440083049174 | -0.001482278278 | 15/15 |
| `adaptive_recent40_right` | 29.438906715681 | -0.002658611770 | 15/15 |
| `adaptive_recent43_right` | 29.443101470296 | +0.001536142844 | 15/15 |
| `adaptive_recent44_right` | 29.439013435952 | -0.002551891500 | 15/15 |
| `adaptive_recent45_right` | 29.438480271530 | -0.003085055921 | 15/15 |
| `adaptive_recent46_right` | 29.447164543483 | +0.005599216031 | 15/15 |
| `adaptive_recent47_right` | 29.446623205538 | +0.005057878086 | 15/15 |
| `adaptive_recent48_right` | 29.446515071915 | +0.004949744464 | 15/15 |
| `adaptive_recent49_right` | 29.442864881210 | +0.001299553759 | 15/15 |
| `adaptive_recent50_right` | 29.441800949860 | +0.000235622408 | 15/15 |
| `adaptive_recent52_right` | 29.442119672362 | +0.000554344910 | 15/15 |
| `adaptive_recent56_right` | 29.444898403123 | +0.003333075671 | 15/15 |
| `adaptive_recent64_right` | 29.442737353809 | +0.001172026357 | 15/15 |
| `adaptive_recent72_right` | 29.441273713195 | -0.000291614257 | 15/15 |
| `v6_short8` | 29.049959050341 | -0.391606277110 | 15/15 |
| `v6_short16` | 29.049959050341 | -0.391606277110 | 15/15 |
| `v6_short128` | 29.049415920443 | -0.392149407009 | 15/15 |
| `window1024_right` | 29.049090580812 | -0.392474746640 | 15/15 |
| `S50` | 28.939458940265 | -0.502106387187 | 15/15 |
| `P4` | 28.375837599373 | -1.065727728079 | 15/15 |
| `all_right` | 28.398607347686 | -1.042957979766 | 15/15 |

Best tested here: `adaptive_recent46_right`, 29.447164543483/32.1, a net gain of +0.005599216031 over the frozen adaptive right4/W2048/S60 baseline. All official runs in the focused threshold sweep passed 15/15.

## T=46 rule

The baseline allocator uses W=2048 and unfit penalty S=60. It places pipes of length at most 4 m at the right endpoint of a selected gap and longer pipes at the left endpoint. Before placing the current pipe of length L, the candidate checks the last 46 placement lengths in the observed input history. If all 46 equal L, it places this pipe at the right endpoint even when L>4; otherwise the baseline side rule applies. Deletions do not reset this placement-length run. There is no test number or command-position branch.

## Per-case weighted delta vs baseline

| Case | Weight | Baseline H | T=46 H | Baseline KPI | T=46 KPI | Weighted delta |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 1 | 101480 | 96860 | 0.500985415845 | 0.524881271939 | +0.023895856093 |
| 8 | 1 | 4680 | 4700 | 0.988675213675 | 0.984468085106 | -0.004207128569 |
| 9 | 1 | 62200 | 63980 | 0.506430868167 | 0.492341356674 | -0.014089511493 |

Changed weighted outcomes: case 5 +0.023895856093; case 8 -0.004207128569; case 9 -0.014089511493. Their net is the +0.005599216031 overall gain.

## Reproducibility and resources

The T=46 full open run was repeated. Both runs scored 29.447164543483/32.1, and status/KPI/trench/occupied/weighted score matched for every case: `True`. Judge output and solver/interactor stderr bytes also matched case by case: `True`.
Across the primary and repeated T=46 runs, maximum solver CPU: 0.919528 s; maximum solver peak RSS: 4.8594 MiB; maximum harness wall time for one case: 7.010507 s.

Exact primary official command:
```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_lookahead/bin/candidate_adaptive_right4_w2048_s60_recent46_right --name adaptive_right4_w2048_s60_recent46_right --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/max_open_lookahead/official-open-recent46-right
```

Exact repeat command:
```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_lookahead/bin/candidate_adaptive_right4_w2048_s60_recent46_right --name adaptive_right4_w2048_s60_recent46_right_repro --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/max_open_lookahead/official-open-recent46-right-repro
```

Strict build command:
```sh
g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/max_open_lookahead/candidate_adaptive_right4_w2048_s60_recent46_right.cpp -o results/pipes/improvement/max_open_lookahead/bin/candidate_adaptive_right4_w2048_s60_recent46_right
```

T=46 source: `candidate_adaptive_right4_w2048_s60_recent46_right.cpp`. Source and binary SHA-256 values, the harness/interactor hashes, and all 15 input hashes are in `harness-manifest.json`. The candidate remains isolated in this directory and was not copied into canonical source.
