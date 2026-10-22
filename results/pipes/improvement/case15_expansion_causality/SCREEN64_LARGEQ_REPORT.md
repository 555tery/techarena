# Case 15 refinement: protect only q > current pipe length

**NO-GO.** The refined last-64 policy still produced a **439,260 m** trench, **340 m above** the frozen 438,920 m baseline. It made the same **9,611 redirects** and produced a byte-identical judge output to the prior last-64 candidate. Requiring `q > current_pipe_length` therefore did not make the intervention set smaller on case 15.

| Run | Trench | KPI | Weighted score | CPU | Peak RSS |
|---|---:|---:|---:|---:|---:|
| Frozen baseline | 438,920 m | 0.9540622437 | 9.5406224369 | 1.021344 s | 7.6875 MiB |
| Last-64 plus `q > current length` | 439,260 m | 0.9533237718 | 9.5332377180 | 1.739960 s | 9.625000 MiB |

The candidate stayed within the 5 s / 256 MiB limits. It did not beat baseline, so no synthetic or Open15 runs were made. Frozen final (`c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`), canonical (`526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`), and platform were untouched.

Exact hashes and reproduction record: [`screen64_largeq_manifest.json`](screen64_largeq_manifest.json). Harness output: [`screen-case15-w64-largeq/summary.json`](screen-case15-w64-largeq/summary.json).
