# Generational regions: case 15 screen

## Design

The candidate assigned each insertion to `floor((PID-1)/window)` using only the online PID. Free spans received a region owner only while every adjacent span came from the same birth region; mixed spans remained globally shareable. On ordinary placements, a fitting span in the current birth region was preferred, with the existing parity-cohort preference and gap score retained inside that region. If no same-region span fit, the original global selector and tail-growth logic remained in force. Pipes were never moved; exact lengths and immediate coalescing were preserved.

This is not the existing parity cohort or `cohortSlab`: those are triggered by length/deletion patterns and expected same-size runs. This policy uses bounded birth-PID epochs for every ordinary placement and does not forecast future sizes or removals. The short design note includes complexity and risks.

## Result

Baseline case 15 is `T=438,640 m`, score `9.546712566/10`. All three candidates passed the official native checker on Open15 case 15, but all materially regressed trench length:

| Birth-window size | T15 (m) | ΔT vs baseline | Score / 10 | CPU (s) | RSS (MiB) |
|---:|---:|---:|---:|---:|---:|
| 512 | 461,040 | +22,400 | 9.082877841 | 1.028689 | 13.45 |
| 2,048 | 465,200 | +26,560 | 9.001655202 | 0.999915 | 13.44 |
| 8,192 | 465,640 | +27,000 | 8.993149214 | 0.992408 | 13.45 |

The best screen variant is still `0.463835` weighted points worse on this one case. No full Open15 run was warranted. This falsifies the tested direct preference rule and these three PID-window scales for case 15; it does not prove that every possible region-reuse architecture must fail.

## Provenance

- Baseline SHA-256: `c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c`
- Window 512 SHA-256: `ace6413f2f49b46e37c25fa488d6fc7b6b2dac4c70cec22768502ca5f0a4c092`
- Window 2,048 SHA-256: `217b20986c4e6a6ba0871c5af2b552517d272b4663094da53d874f48d35dc2e2`
- Window 8,192 SHA-256: `caaaeaa2d36cced472a876596c11e63c28e4e689cb5100ec8bbd67be956b1ffc`
- Exact evaluator manifests and native harness summaries are in the corresponding `eval-15-window-*` directories.
- Only `/Users/555tery/techarena/data/pipes/open/15.in` was evaluated. No validation, held-out set, or platform was accessed.
