# Historical allocator behind an online size-shift gate

## Result

**No-go on case 15.** The single gated overlay reached 463,740 m, 24,820 m worse than the current champion's 438,920 m and 25,380 m worse than the historical 438,360 m binary. Since the case-15 screen failed, the planned phase-shift synthetic runs and Open15 run were skipped.

## Gate and policy

The candidate starts as the current champion. It observes placement lengths in a rolling 320-placement window: the oldest 256 form the prior support, and the latest 64 form the recent support. It switches permanently to the historical allocator only when both supports are nonempty, disjoint, and ordered on the size axis (all recent sizes are above all prior sizes, or vice versa). The incoming placement completing the 64-sample window is already known when the switch is applied. No command index, test identity, or future input is read by the solver.

On case 15, the gate first fires at command 100,146 (placement 80,253): prior support 1–7 m, recent support 8–40 m. The candidate and champion have the same cumulative trench length through command 100,245; their first trench-growth difference occurs at command 100,246. By command 200,000, the gated candidate has dug 24,820 m more. This points to a cost of switching allocator regimes midway through a stream whose gaps and pipe locations were created under the champion policy; the old binary benefited from its placement policy from the beginning.

After switching, the candidate uses the historical `12/5` disable and `21/10` enable live-mean hysteresis, PID-parity edge placement while segregated, the historical short-pipe/46-run endpoint while not segregated, historical fit scoring without rollout, and same-length sticky-remainder reuse. Before the gate it uses the current champion unchanged.

## Case-15 comparison

| Solver | Trench | KPI | Weighted case score | CPU | Peak RSS |
|---|---:|---:|---:|---:|---:|
| Current champion | 438,920 m | 0.954062244 | 9.540622437 / 10 | 1.002304 s | 5.95 MiB |
| Gated historical overlay | 463,740 m | 0.902999526 | 9.029995256 / 10 | 0.956064 s | 9.55 MiB |
| Historical binary | 438,360 m | 0.955281048 | 9.552810476 / 10 | 0.923272 s | 6.33 MiB |

The candidate strict-build succeeded and returned `ok` for all 200,000 commands. Build command:

```sh
g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror \
  results/pipes/improvement/case15_adaptive_shift_gate/source/champion_historical_shift_gate.cpp \
  -o results/pipes/improvement/case15_adaptive_shift_gate/bin/champion_historical_shift_gate
```

Source SHA-256: `b08550b7c678887d1f13c60092415049e2e02a7c6c2f09ab8d7a8b1653dccb5c`. Judge-output SHA-256: `c09c41fd2d38b43fcc3361841f4f20886806a672128e6db56536d3c7b752c9b7`.

## Decision

The historical policy's case-15 improvement is not recovered by entering it after a detected phase shift. Do not run Open15 or the synthetic phase-shift matrix for this variant: the required case-15 improvement condition was not met. This is one causal gate, with no threshold sweep. Only local files and the local harness were used; no platform or Docker was used, and frozen/canonical sources were not modified.
