# Follow-up: confidence-gated LIFO high-side policy

## Decision

The gate passed the requested screen and full local Open15. It raised the current Open15 total from **29.932085817214315** to **29.936886524552949 / 32.1** (**+0.004800707338634**). Case 11 saved 120 m; cases 13 and 15 returned to the champion's trench lengths. Four newly generated synthetic streams also tied the champion. This is a research candidate for the coordinator to review; it is not a change to frozen final or canonical source.

## Why the gate differs from the failed high-side candidate

Diagnostics show that case 13's only high-side episode began at operation 159 with only 22 active pipes. Its last 90 placements were short in 90% of requests, but the full observed support was already 5–39 m across 10 distinct sizes, while every recent deletion rank rounded to zero. That small, quantized active sample gave a misleadingly strong top-five-percent signal. The gate requires at least 128 active pipes.

Cases 11 and 15 are harder: their input commands and observed states match exactly through the first 4,999 commands. The first high-side activation is the same in both, at operation 1126: 655 active pipes; 890 recent placements, all 1–7 m; 64 deletion ranks with 81.25% in the newest 5%. No causal prefix rule can distinguish those two traces at that point. Case 11 peaks at 3,049 active pipes and naturally exits the short-size condition around the transition near operation 5,400. Case 15 continues growing; the gate permanently disables high-side mode after observed active state exceeds the allocator's existing 4,096-pipe rollout scale, at operation 6,722. No test identity, file name, total command count, or future command is read.

The gate therefore adds two confidence checks to the existing rule: (1) at least 128 active pipes, so rank-permille statistics are not based on a tiny state; and (2) sticky disable after active state exceeds 4,096, where the local cohort inference is no longer treated as reliable. It leaves Best Fit and rollout selection intact, changing only edge orientation for qualifying 5–8 m placements.

## Target and synthetic screen

| Stream | Champion trench | Gated candidate | Δ trench | Result |
|---|---:|---:|---:|---|
| Open case 11 | 22,620 m | 22,500 m | −120 m | Gain |
| Open case 13 | 3,280 m | 3,280 m | 0 m | Tie |
| Open case 15 | 438,920 m | 438,920 m | 0 m | Tie |
| Fresh synthetic: LIFO growth beyond scale | 33,020 m | 33,020 m | 0 m | Tie |
| Fresh synthetic: LIFO then stationary | 11,000 m | 11,000 m | 0 m | Tie |
| Fresh synthetic: small LIFO then wide lengths | 17,620 m | 17,620 m | 0 m | Tie |
| Fresh synthetic: balanced random small lengths | 480 m | 480 m | 0 m | Tie |

Exact CPU/RSS and scores are in [confidence_gate_screen.csv](confidence_gate_screen.csv). The four synthetic flows use new seeds and structures, and are only a small targeted screen, not broad generalization evidence.

## Full Open15

The candidate passed 15/15. Only case 11 changed: its trench fell by 120 m. All other 14 cases, including 13 and 15, retained their champion trench and weighted score. Exact values are in [confidence_gate_open15_comparison.csv](confidence_gate_open15_comparison.csv). Maximum solver CPU was **2.975517 s** and maximum RSS **7.30 MiB**, under the 5 s / 256 MiB limits.

## Reproduction

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic results/pipes/improvement/case11_lifo_stack/src/baseline_champion.cpp -o results/pipes/improvement/case11_lifo_stack/bin/baseline_champion
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic results/pipes/improvement/case11_lifo_stack/src/lifo_confidence_gate.cpp -o results/pipes/improvement/case11_lifo_stack/bin/lifo_confidence_gate
python3 tools/pipes_harness.py --solver results/pipes/improvement/case11_lifo_stack/bin/lifo_confidence_gate --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/case11_lifo_stack/runs/open15_confidence_gate --name lifo-confidence-gate-open15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
```

The fresh synthetic generator and traces are under `generate_followup_synthetic.py`, `synthetic/f0*.in`, and `runs/followup_{baseline,candidate}_*`. SHA-256 values for source, binary, inputs, harness, interactor, summary and comparison tables are in [followup_manifest.json](followup_manifest.json).

Frozen final and canonical source were not modified. Tests were local only; no website or Docker was used.
