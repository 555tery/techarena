# Seam-preservation screen

Date: 2026-10-18. All writes and candidate sources are in this branch. The frozen comparison source was copied byte-for-byte from campaign baseline (`c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c`, Open15 score `30.074287976405728`). Every solver run used the campaign `evaluate.py`, the pinned official native checker, and its fresh quota gate (`65%` minimum). No site, validation set, old holdout, or stress set was accessed.

## Hypothesis

At an unavoidable tail expansion, placing the new pipe high-side can keep an existing tail gap beside a young pipe. If that pipe is deleted, the old gap can merge with its span. The online rule may use only past request lengths and observed deletion ranks; no future command or case fingerprint is available to it.

## Variants and results

| Variant | Screen | Baseline | Candidate | Activations | CPU / peak RSS |
|---|---|---:|---:|---:|---:|
| Broad observed demand, source SHA `966afcb0943e642611f4c494e04f687d43b3290a9770ea075f4face0e71cec1b` | Open13 | 3.892682927 / 3280 m | 3.869090909 / 3300 m | 17; first op 2981 | 0.059149 s / 2.86 MiB |
| Repeated bridge-only demand, source SHA `234c2657b1985cdcf2e961d98199d5f2e675e0f4c040b9bbcc3578a72e8fcac4` | Open11 | 0.904933333 / 22500 m | 0.899337456 / 22640 m | 25 | 0.072017 s / 3.27 MiB |
| Same | Open12 | 3.972480620 / 10320 m | 3.957142857 / 10360 m | 32 | 0.027986 s / 2.81 MiB |
| Same | Open13 | 3.892682927 / 3280 m | 3.892682927 / 3280 m | 7 | 0.059163 s / 2.86 MiB |
| Same | Open14 | 3.985623679 / 37840 m | 3.985623679 / 37840 m | 0 | 0.134365 s / 5.23 MiB |
| Same | `counterexamples/paired-v1` (32 light/pressure pairs, 64 traces) | 32.058333333 | 32.058333333 | 0 / 64 cases | 0.002373 s / 2.22 MiB |

The repeated-demand rule requires one request size in the capacity range that high-side preservation adds beyond the low-side remainder, with historical count at least `sqrt(window size)`, plus the existing strong-rank LIFO evidence. Across Open11–14, the weighted-score change is `−0.0209336405`; this is a four-case delta, not a full-Open15 score. All evaluated cases passed protocol and resource limits. The paired-v1 result is not evidence for or against the action itself: its 18-command traces never met the gate and had zero activations.

## Diagnosis and decision

The broad rule changed 1,531 command responses on Open13 and worsened trench length by 20 m. It activated early, before the hypothesized late seam, so the trajectory no longer represented the baseline opportunity. The repeated-demand rule likewise began intervening at op 6775. At op 8786 it saw a different state and selected request size 10 (tail 8 m, low-side remainder 8 m, neighbor 10 m), rather than the baseline state (tail 13 m, request 15 m, neighbor 10 m). It tied Open13, lost on Open11 and Open12, and did not trigger on Open14.

Both variants are no-go and should not be promoted. No full Open15 evaluation was run because the targeted screens showed regressions and no positive case-level gain. There is no evidence here of leaderboard improvement or generalization. The useful result is narrower: the action is plausible in a baseline counterfactual, but the current online selector cannot enter that state without earlier, harmful changes.

## Provenance

- Candidate evaluation manifests and exact per-case records are under `evaluations/`; each stores source/input hashes, protocol status, CPU, RSS, and result.
- V1 Open13 summary SHA-256: `96a0ade937ef70441fec50a75c8a735da8b8a0b4acee453293fef6aa0116d1bd`.
- V2 summaries: Open11 `4f471137bae95a3f21abb8cf2fd0695bbf4e9b88a5687986dab354c74077b9fc`; Open12 `6138dabd3f43fda6ea7d598f732c3b3bff7fcf464a23c98687f2a80a15b7be4b`; Open13 `ff4c7e7099d79292df98983b8c57ae6401335668a3c1f1edc19b091b69cfb65a`; Open14 `91f8aa5680c7f2e64d96a4428210a0caa3dbc4632b006d25318e157462d6e95f`.
- Paired-v1 manifest SHA-256: `80f1ee12989131d35bc4b3f5e4281c91fd4a545694920a2dd1bf2493e8fb0f3e`; traces SHA-256: `3b774726ea6d92254c064f69ccdc7212a12170fa91b35d35a7e3f67a4984ec80`. Baseline paired summary SHA-256: `e0b8d51f179f05172254a1f485f2b906e2e828499142b91481d1afa9de18cbfa`; candidate paired summary SHA-256: `50dc5598e95f98bddd6b26aeb5edfe9a23507ef58a20102f5d7147a2f57f5f9c`.
