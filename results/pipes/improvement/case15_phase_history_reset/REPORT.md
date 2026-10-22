# Case 15: reset of cost-history after a support-disjoint size shift

## Decision

**No-go.** The case15-only candidate increased trench length by 260 m. No synthetic runs, Open15, holdout, or parameter search followed.

## Trace evidence and hypothesis

Case 15 has a sharp size-profile shift near command 100,000. Across the first five 20,000-command blocks, essentially every placement is length 1–7 m and the mean is about 4 m. Across the next five blocks, essentially every placement is length 8–40 m and the mean is about 24 m. The saved champion digs 5,620 m over commands 100,001–102,500 and another 11,600 m by command 110,000.

The tested rule adapts only the history used by the gap cost. It resets that cost history when the latest 32 placement lengths have support disjoint from the preceding history, which must contain at least 128 placements. It then seeds the cost history with those confirmed 32 lengths. The separate history used by existing mode and rollout triggers is left intact. The gate uses observed pipe lengths only; it has no case number or command-position input.

This is a real size-phase transition, but it does not establish that stale cost history caused the extra digging. On this trace, resetting that history made the final allocation worse.

## Case 15 result

| Solver | Case 15 trench | KPI | Weighted contribution (weight 10) |
|---|---:|---:|---:|
| Current champion | 438,920 m | 0.954062244 | 9.540622437 |
| Cost-history reset | 439,180 m | 0.953497427 | 9.534974270 |
| Candidate minus champion | **+260 m** | **−0.000564817** | **−0.005648167** |

The reset triggered once at placement PID 80,222, keeping a 32-placement history window. The candidate run passed the local official interactor: `ok`, 200,000 commands consumed, no protocol or resource-limit failure. Solver CPU was 0.971191 s and peak RSS 9.59375 MiB on macOS arm64.

The trigger is logged to `solver_stderr.txt` under `TRACE_PHASE_RESET`; it does not affect the solver protocol. Since the case15 gate failed, the preregistered continuation gate was not reached and no other input was run.

## Reproduction and hashes

Build:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic \
  -DTRACE_PHASE_RESET \
  results/pipes/improvement/case15_phase_history_reset/source/phase_history_reset.cpp \
  -o results/pipes/improvement/case15_phase_history_reset/bin/phase_history_reset
```

Case15 screen:

```sh
python3 tools/pipes_harness.py \
  --solver results/pipes/improvement/case15_phase_history_reset/bin/phase_history_reset \
  --name phase-history-reset-case15 \
  --interactor results/pipes/final/bin/interactor \
  --tests results/pipes/improvement/case15_phase_history_reset/tests \
  --out results/pipes/improvement/case15_phase_history_reset/runs/case15 \
  --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

- Champion source SHA-256: `43bfbdadbae18ac180d1e59b6631342cfe1bef99190a449838f0470d6f220200`
- Candidate source SHA-256: `139a5cb1c8071a1fcb6d552ae12df677e14d976e06542537e84aa63bb9918365`
- Candidate binary SHA-256: `0ecd7987f83840b4cd6afa4af797815076e7f5ad1749d382877200782cdd1ff5`
- Case15 input SHA-256: `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`
- Candidate judge output SHA-256: `d0e72cb714c7c68d160c2b889c15d84a64f3e7b7d2b4e82c7ee761b0b0943aaf`
- Frozen final SHA-256 (unchanged): `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`
- Canonical source SHA-256 (unchanged): `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`

Candidate code, test input, harness summary, per-case CSV, interactor files, and resource measurements are retained in this directory. The website and Docker were not used.
