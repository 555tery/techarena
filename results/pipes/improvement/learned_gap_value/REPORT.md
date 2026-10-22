# Learned gap-value candidate — exploratory result

**Decision: no-go.** The supervised state/action value model did not beat the frozen solver on the preregistered synthetic confirmation. I did not run holdout-v2 or Open15.

## What was tested

The candidate is a causal allocator variant of the frozen solution. A 24-tree, depth-5 regression forest scores up to three existing gap choices using 180 features, including the complete post-placement free-gap histogram. Training targets were the trench growth over the next 512 commands when continuing with the frozen policy. Future commands were used only offline to form labels; the compiled policy reads current state/history and has no test-ID or future-input access.

Training used only 18 synthetic streams (887 candidate rows, 534 sampled states). The earlier action-level diagnostic on a separate synthetic validation set was weak (paired stream CI crossed zero) and was not reused as confirmation or for tuning. The approach differs from the previously tested hand-written per-gap potential: it learns nonlinear action values over the whole gap state.

The confirmatory gate was committed in [`qualification-gate.md`](qualification-gate.md) before running either solver. It specified 60 paired streams: 16,384 and 200,000 commands × 3 length profiles × 5 deletion policies × steady and periodic-drain regimes. Seeds were 1,470,000,000–1,470,000,059; both solvers received byte-identical inputs. A local optimized generator matched the repository generator's command lists exactly in 30 small-seed checks.

## Results

| Measure | Result |
|---|---:|
| Frozen weighted KPI sum on this 60-stream matrix | 40.3790975043 |
| Learned weighted KPI sum | 40.2792952713 |
| Mean paired ΔKPI (learned − frozen) | −0.00166337 |
| 20,000-replicate whole-stream bootstrap 95% CI | [−0.00399472, +0.00034916] |
| 200,000-command subset mean ΔKPI | +0.00064382 |
| Wins / losses / ties | 16 / 26 / 18 |
| Accepted solver transcripts | 120 / 120 |

The long-stream condition passed, but the primary gate failed: the confidence interval's lower endpoint was not above zero. The matrix also shows negative mean ΔKPI at 16,384 commands (−0.00397056), on all three length profiles, and in both regimes. Results by deletion policy ranged from +0.001377 (oldest) to −0.007093 (longest); these are descriptive slices, not new tuning targets.

## Runtime and integrity

Both binaries were built with Apple clang 17.0.0 on macOS 26.6.2 arm64. The maximum measured solver CPU was 1.973 s for frozen and 2.099 s for learned; maximum RSS was 7.375 MiB and 7.063 MiB respectively. There were no 5 s CPU or 256 MiB memory exceedances. All 60 runs per solver returned `ok` and consumed the declared commands plus the final terminator.

Protected hashes are unchanged:

- Frozen final source: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`
- Canonical source: `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`

Learned candidate source SHA-256: `517f25b260163587b057a4149e12ad6a6aca1941e93b5de135e2f6d1c15dd2aa`. The generated model header SHA-256 is `dae9cb16e8a7ba530eb5a8cd5d9b030399feb3829b6e950e9eb5a431e948ae99`.

## Reproduction artifacts

- Per-stream paired CSV: [`runs/qualification-analysis/per-case.csv`](runs/qualification-analysis/per-case.csv)
- Gate result: [`runs/qualification-analysis/summary.json`](runs/qualification-analysis/summary.json)
- Full seed, input, source, model, toolchain, and command manifest: [`runs/qualification-analysis/manifest.json`](runs/qualification-analysis/manifest.json)
- Input hashes and generator-equivalence record: [`inputs/qualification_confirmatory/manifest.json`](inputs/qualification_confirmatory/manifest.json)
- Baseline and candidate raw harness outputs: [`runs/qualification-frozen/`](runs/qualification-frozen/) and [`runs/qualification-learned/`](runs/qualification-learned/)
- Candidate implementation: [`src/learned_gap_value.cpp`](src/learned_gap_value.cpp); generated forest: [`src/learned_model.hpp`](src/learned_model.hpp)

The manifest records the exact Apple Clang build and local harness commands. No Docker, website, leaderboard, holdout-v2, or Open15 was used. An earlier Python-generator attempt left 38 unbenchmarked partial inputs in `inputs/qualification/`; those files are not part of the confirmatory matrix.
