# Case 15 ablation: last-64 demand window

**NO-GO.** This predeclared ablation shortened the eligible demand history to the most recent 64 placement lengths, with one observation sufficient. It still finished **340 m above** the frozen baseline: 439,260 m versus 438,920 m. The case KPI was 0.9533237718, weighted score 9.5332377180; weighted delta versus baseline was -0.0073847189. The rule redirected 9,611 placements, so the shorter window did not make the trigger selective enough to transfer the one-trace witness.

| Run | Trench | KPI | Weighted score | CPU | Peak RSS |
|---|---:|---:|---:|---:|---:|
| Frozen baseline | 438,920 m | 0.9540622437 | 9.5406224369 | 1.021344 s | 7.6875 MiB |
| Last-64 candidate | 439,260 m | 0.9533237718 | 9.5332377180 | 1.627848 s | 9.640625 MiB |

Only case 15 was screened. Candidate stayed within 5 s / 256 MiB, but because it did not beat 438,920 m, no synthetic or Open15 runs were made. Frozen final (`c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`), canonical (`526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`), and platform were untouched.

Reproduction details and hashes: [`screen64_manifest.json`](screen64_manifest.json). Harness output: [`screen-case15-w64/summary.json`](screen-case15-w64/summary.json).
