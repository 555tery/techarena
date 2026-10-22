# Case 15: unique recent-demand gap redirect screen

## Result

**NO-GO.** The isolated candidate increased trench length by **460 m**, from **438,920 m** to **439,380 m**. Its case KPI fell from **0.9540622437** to **0.9530634075**; weighted case score fell by **0.0099883616** (from 9.5406224369 to 9.5306340753). No further policy tuning or wider dataset runs were performed.

The policy redirected **9,770** placements. At candidate PID 80265 (operation 100170), it protected recently observed length 20 and redirected from a 29 m gap to a 19 m gap. This is already a counterfactual state: earlier redirects had altered the trace. In the frozen baseline, that operation selected a 25 m interval, left 9 m after a 16 m placement, and the next input pipe had length 24 m and caused a 20 m expansion. Thus the original baseline episode is a plausible causal witness, but the broad history-based trigger did not preserve that exact state and compounded across the stream.

## Tested rule

After the existing gap selection (including the current rollout choice), if cohort mode is off, inspect the selected gap. If placing the current pipe there would leave less room than a request size `q` that occurs in the existing recent placement history (`recentFrequency`, at most the last 2,048 positive commands), and the selected gap is the only current physical gap large enough for `q`, redirect to the best-scoring other physical gap already fitting the current pipe. The redirect itself never digs. No test identity, command index, future command, or tuned threshold is used.

## Measurement

- Input: `data/pipes/open/15.in`, SHA-256 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`, 200,000 operations, 130,255 placements.
- Frozen baseline: source SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`; trench 438,920 m; CPU 1.021344 s; peak RSS 7.6875 MiB.
- Candidate: source SHA-256 `d3dfe5d17074b6c2bd0021020696c44fddbe6cdbf96539c7c09fcf2ee3d05fb0`; binary SHA-256 `a882cf26238c2052c1308dcaad92399490fa5d78be0a284002b4a2cd5686acee`; trench 439,380 m; CPU 1.577089 s; peak RSS 9.609375 MiB.
- Limits: 5 s CPU / 256 MiB; candidate stayed within both.
- Local official interactor and harness were used. The frozen source and canonical source were not changed; no site was accessed.

All input, source, binary, interactor, harness, and output hashes are in [`screen_manifest.json`](screen_manifest.json). Detailed harness record: [`screen-case15/summary.json`](screen-case15/summary.json).
