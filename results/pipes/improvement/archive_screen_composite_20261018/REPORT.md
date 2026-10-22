# Archive screen against the 29.947761 composite

## Result

**No-go:** none of the three archived policies improved the current composite. The current composite was rebuilt and reproduced locally at **29.947761251325 / 32.1, 15/15**. No source was promoted; frozen final and canonical stayed unchanged.

| Archived policy transferred onto current composite | Target screen | Result | Decision |
|---|---|---:|---|
| PID-parity same-size re-arm lane (case 5) | case 5 | 62,620 → **63,220 m** (+600 m; weighted Δ −0.007705294) | Reject before Open15 |
| Live-mean hysteresis with PID-parity placement (case 15) | case 15 | 438,920 → **439,020 m** (+100 m; weighted Δ −0.002173164) | Reject before Open15 |
| Align each selected gap remainder to a 20 m section boundary (case 15) | case 15 | 438,920 → **438,500 m** (−420 m; weighted Δ +0.009138110) | Target gain did not survive Open15 |

Section-phase scored **29.920754046187 / 32.1**, down **0.027007205138** from the composite. It passed all 15 protocol checks, but caused several losses: case 5 +500 m, case 9 +180 m, case 11 +140 m, cases 12–14 +20 m each. Its gains were case 15 −420 m and case 7 −20 m. Maximum measured use was 2.268388 CPU seconds and 7.641 MiB RSS. Holdout-v2 was not run because the candidate failed the full Open15 gate.

## Scope and provenance

The source base is the previously recorded combined candidate `hole_first_survivor_cohorts_plus_lifo_gate`, SHA-256 `5cc564ca88d8ae3be941ca2c3dab252e0836fa8d93e937dec4c32b5168b2aa9a`. A fresh local Open15 run reproduced **29.947761251325**, with all 15 cases `ok`; cases 5 and 15 also matched the target-screen controls.

The three transfer hypotheses came from prior archived reports, not a new parameter sweep:

- PID-parity lanes: [factorial report](../pid_lane_run48_factorial/REPORT.md); archived PID/46 source SHA `1a643a2b8a560de5c7dfd7efe0b288dc93785e96400d2ae6fd4ec7eea5f55f59`. Only the re-arm lane selector was changed in this transfer.
- Live-mean/PID-parity overlay: [transfer report](../case15_adaptive_binary_forensics/REPORT.md); archived overlay source SHA `5e0e4bc9a0fa62a31936b1a01f0ec541f47925dd7edff5295779f3a79eb14b54`.
- Section-phase edge rule: [prior no-go report](../case15_section_phase/REPORT.md); archived source SHA `f40d9a3f6fc07e7c9bce4ce84f7934d92b505f10d1aade285783b95fa7e62e27`.

The composite-based variants and binaries, exact local run directories, and hashes are in [manifest.json](manifest.json). Builds used strict `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wshadow -Wconversion -pedantic -Werror`; the official local interactor and harness hashes are recorded in the manifest. No platform or Docker was used.

**Excluded archive families for this composite:** global PID-parity same-size lanes, live-mean-triggered parity orientation, and section-phase edge selection. The first two lost on their target case; the last improved case 15 but regressed the aggregate. These checks establish no benefit for these specific transfers; they do not prove that every related policy is ineffective.
