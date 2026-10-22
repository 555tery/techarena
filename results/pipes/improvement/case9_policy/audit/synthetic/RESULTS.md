# Synthetic trigger/reset check

This is a narrow causal check of the parity detector requested after the main report was frozen. It uses three constructed streams: stride-2 deletions whose first parity is odd, the same pattern with even parity, and an interrupted stride control. The baseline and candidate binaries were rebuilt with `MC_ROLLOUT_DISABLED`, so the comparison isolates the observed live placement policy from Monte Carlo rollout. No weights or policy parameters were tuned.

The diagnostic build logs the live detector after each deletion. The code activates after seven same-length `+2` PID transitions, which means eight qualifying deletions. A length or PID-stride mismatch resets the count and disables the mode.

| Synthetic stream | Detector observation | Baseline trench | Candidate trench | KPI baseline → candidate |
|---|---|---:|---:|---:|
| `same_len_stride2_odd` | odd parity activation at PID 15; mode resets when deleted length changes at PID 65 | 340 m | 340 m | 0.941176470588 → 0.941176470588 |
| `same_len_stride2_even` | even parity activation at PID 16; mode resets when deleted length changes at PID 66 | 360 m | 340 m | 0.888888888889 → 0.941176470588 |
| `interrupted_stride2_control` | PID 8 breaks the initial stride; the subsequent run ends at 6 transitions and does not reactivate mode | 180 m | 180 m | 0.961111111111 → 0.961111111111 |

Odd-parity detection activates at PID 15 and resets when the deleted length changes at PID 65. The trench is unchanged at 340 m. Even-parity detection activates at PID 16 and resets at PID 66; this constructed sequence reduces trench length from 360 m to 340 m. The interrupted control breaks the first run at PID 8; the later run reaches only six stride-2 transitions, the log contains no `mode=1`, and baseline/candidate both finish at 180 m.

The parity result is asymmetric on these toy streams: only the even-parity sequence improves, while the odd sequence is neutral. These three hand-built checks establish the detector trigger/reset behavior and show one constructed trench reduction; they do not establish a generalizable gain. All three harness runs were valid, below the contest resource limits, and the full input, binary, summary, per-case, diagnostic-log, and judge-output hashes are in [`manifest.json`](manifest.json). The row-wise comparison is in [`per_case_comparison.csv`](per_case_comparison.csv). Superseded initial control trials are archived and excluded.
