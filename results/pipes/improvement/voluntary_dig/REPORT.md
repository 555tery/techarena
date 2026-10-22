# Voluntary trench expansion as option value

## Decision

Candidate rejected. The 32-placement horizon passed the requested first-screen gate by only `+0.000354231338` on open cases 5/9/15 and saved 40 m on case 15. The full 15-case open run then lost `0.199786788394` weighted points. Previously used final-holdout-v2 and development synthetic also regressed. No candidate is recommended for final.

## Policy

For the gap selected by the existing adaptive Best-Fit (after its current rollout decision), compute the future request band that the full gap can fit but the remainder cannot: `(gap_length-current_length, min(gap_length, 40)]`. Use only the existing rolling histogram of up to 2,048 observed placements, requiring at least 64 observations. Discount demand for each size by the number of current gaps that already fit that size. Estimate the chance that one such demand arrives within the next 32 or 64 placements, multiply by its expected avoided 20 m section cost, then compare that expected value to the immediate cost of extending the current tail by `ceil(deficit/20)*20` metres. Voluntary tail placement occurs only when estimated benefit is strictly greater than immediate cost. It does not act when the tail can already fit without digging.

The policy uses current gap state and past demand only. No test ID, operation count, command index, or future command enters the decision. Both variants preserve the original edge selection rule.

## Results

### First screen: official open cases 5, 9, 15

Horizon 32: **+0.000354231338** weighted points summed over weight 12.0; case 15 trench improved by 40 m. Horizon 64: **-0.006692738227**; case 15 trench worsened by 320 m. This gate selected horizon 32 for expanded validation.

### Expanded comparison

| Dataset | Seed score / weight | Horizon 32 score / weight | Delta | Horizon 32 status |
|---|---:|---:|---:|---:|
| Official open 15 | 29.785293754007 / 32.1 | 29.585506965613 / 32.1 | **-0.199786788394** | 15/15 OK |
| final-holdout-v2, previously used | 5.135264324280 / 12.0 | 4.807421004844 / 12.0 | **-0.327843319436** | 12/12 OK |
| development synthetic, previously used | 1.844130426987 / 4.0 | 0.684762410453 / 4.0 | **-1.159368016534** | 4/4 OK |

On open case 15 the trench fell from 438,920 m to 438,880 m (−40 m), giving `+0.000869542694` weighted score. The full-open loss instead came mainly from case 7 (+240 m, −0.122037598545 score) and case 13 (+60 m, −0.069928435811), with smaller regressions on 5, 11, and 14. Changed open trenches are listed in `per-case.csv`.

Horizon 32 accepted 6,068 voluntary placements in open-15 and paid for 121,360 m of extra trench. It used 1.967507 s CPU total / 1.250534 s maximum per case and 9.453125 MiB peak RSS; all measured resource use stayed below 5 s and 256 MiB.

Holdout-v2 and development are secondary checks from datasets already used in earlier experiments; they are not independent hidden-set evidence. The holdout-v2 regression was −0.327843319436 and development regressed by −1.159368016534. No other synthetic set was run.

## Reproduction and hashes

Exact build commands and binary hashes are in [build_manifest.csv](build_manifest.csv); exact harness commands are in [screen_commands.txt](screen_commands.txt) and [extended_commands.txt](extended_commands.txt). The full per-case table includes scores, trench lengths, CPU/RSS, input hashes, and judge/stdio transcript hashes in [per-case.csv](per-case.csv); first-screen rows are in [screen-per-case.csv](screen-per-case.csv). Aggregate results are in [summary.csv](summary.csv), and all source/input/output hashes plus the option-value definition are in [manifest.json](manifest.json).

The target source SHA-256 is `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`; the isolated experiment source SHA-256 is `996b9cf9f174d1d1169700a8dcabccf9075185451d40082490a2f85cc6b636cf`. Files are confined to `results/pipes/improvement/voluntary_dig/`; canonical/final sources were not edited. Apple clang++ 17.0.0 compiled with C++20 and `-Wall -Wextra -Wconversion -Wshadow -Werror -pedantic`. Every harness run used 5 s CPU, 256 MiB RSS, and 120 s wall limits.

## Next useful hypothesis

The option model produces many paid dig actions for almost no improvement on case 15 and damages cases 7/13 and the synthetic workloads. If revisited, the most useful change is to value a preserved gap only when the historical request size is uniquely unsupported by all other gaps and appears in a stable recent size regime; do not increase the horizon or blanket-trigger on a raw gap count.
