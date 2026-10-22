# Size arenas with a bimodal-demand/churn gate

**No-go.** A causal histogram/churn gate reduced the original arena regression, but did not eliminate it: case 15 still used 120 m more trench than the current champion. No full Open15 or holdout-v2 run was made, as required by the gate condition.

## Rule tested

On each placement, before incorporating that placement, inspect the last 512 placed lengths and the last 512 operations. Enable size arenas only if both outer arena classes (`1–10`, `21–40`) account for at least 1/8 of the length sample, the middle class (`11–20`) is less than half the smaller outer class, and removals are at least 1/4 of the operation window. Counters are updated from observed commands only. This is one fixed rule, not a threshold sweep.

The gate did not cleanly separate case 15 from bimodal synthetic streams. Its histogram/churn predicate held at 81 placement decisions between commands 100,280 and 100,735 in case 15. At the first such decision the last-512 length classes were `397 / 38 / 77`, with 204 removals among the last 512 operations. The relatively small second outer mode and shallow center valley passed the rule; some arena actions changed the result. This is direct evidence that this shape test is too permissive for the target trace.

## Results

Trench lengths in metres; all six synthetic cases have weight 1. Candidate deltas below are against champion.

| Stream | Demand / removal style | Champion | Ungated arenas | Gated candidate | Δ gated vs champion |
|---|---|---:|---:|---:|---:|
| Open 15 | official | 438,920 | 444,600 (prior run) | 439,040 | +120 |
| fresh_01 | balanced separated bimodal, random | 9,820 | 9,820 | 10,000 | +180 |
| fresh_02 | 35/65 separated bimodal, FIFO | 9,140 | 9,020 | 9,000 | −140 |
| fresh_03 | uniform 8–40, LIFO | 10,080 | 10,080 | 10,080 | 0 |
| fresh_04 | uniform 8–40, 20% deletion churn | 597,540 | 598,520 | 597,540 | 0 |
| fresh_05 | uniform → bimodal → uniform, FIFO/LIFO | 297,760 | 297,760 | 297,760 | 0 |
| fresh_06 | bimodal → uniform → shifted bimodal, median/random | 11,360 | 11,360 | 11,240 | −120 |

Case 15 score changed `9.540622436891 → 9.538014759475` (−0.002607677415); solver CPU/RSS were `1.153 s / 7.609 MiB`, within limits. Across the six fresh inputs, score sum changed `5.179807369651 → 5.186127083490` (+0.006319713839): two wins, one loss, three ties. The gated candidate was also 0.003719624861 below the ungated arena variant on this synthetic suite. The balanced bimodal stream `fresh_01` regressed by 180 m, so the evidence does not establish that arenas help whenever demand is bimodal.

All 7 gated-candidate runs and all baseline/ungated runs completed `ok`; no CPU (5 s) or memory (256 MiB) violation. The case-15 regression fails the promotion condition, despite the small positive synthetic sum. Open15 and holdout-v2 were not run.

## Reproduction

Commands from the repository root:

```sh
python3 results/pipes/improvement/case15_arena_bimodal_gate/generate_candidate.py
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/case15_arena_bimodal_gate/source/bimodal_churn_gate.cpp -o results/pipes/improvement/case15_arena_bimodal_gate/bin/bimodal_churn_gate
python3 results/pipes/improvement/case15_arena_bimodal_gate/make_synthetic.py
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name champion_case15 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_arena_bimodal_gate/tests --out results/pipes/improvement/case15_arena_bimodal_gate/runs/champion_case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_arena_bimodal_gate/bin/bimodal_churn_gate --name bimodal_churn_gate_case15 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_arena_bimodal_gate/tests --out results/pipes/improvement/case15_arena_bimodal_gate/runs/candidate_case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name champion_six_new_synthetics --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_arena_bimodal_gate/synthetic --out results/pipes/improvement/case15_arena_bimodal_gate/runs/champion_synthetic --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_size_arenas/bin/coarse_size_class_arenas --name ungated_size_arenas_six_new_synthetics --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_arena_bimodal_gate/synthetic --out results/pipes/improvement/case15_arena_bimodal_gate/runs/ungated_synthetic --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_arena_bimodal_gate/bin/bimodal_churn_gate --name bimodal_churn_gate_six_new_synthetics --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_arena_bimodal_gate/synthetic --out results/pipes/improvement/case15_arena_bimodal_gate/runs/candidate_synthetic --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

## Provenance (SHA-256)

| Artifact | SHA-256 |
|---|---|
| Gated candidate source | `53f8877b26f4f9baf333e9a507cde7e6707c9e4351251c73762629844b4914f1` |
| Gated candidate binary | `1be3fd19a7bb42e360f0e04fb416062275139afc794fc3cbd550e8e197e8df0d` |
| Candidate generator | `b999a41f446269d455c953e9d7ce87fbdc8e34ac359bd6f86c2f9e88f8d10305` |
| Six-stream generator | `d79198e5d58ff30998d05ff2621d5228e8579a558cbe62be2f56d3b5a29b336f` |
| Ungated arena source | `568b24b5e7f0915cd48993c247e7c4d60dd2be3d91e07207dc332ef8ec6196cf` |
| Champion source / binary | `43bfbdadbae18ac180d1e59b6631342cfe1bef99190a449838f0470d6f220200` / `e4b79d8eb55a1fdc03a8c62505142ee615304401e821895bf6ab7f3712e54049` |
| Official case 15 input | `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353` |
| Official interactor | `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a` |
| Frozen final / canonical source, unchanged | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` / `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8` |

Synthetic input SHA-256: `fresh_01` `2d185e6a98bf1797058267a0644839f729c34ea286e23875962d912726c5cbe2`; `fresh_02` `7f4533c83915180c1e1f37255404961fdff39e6ab6c5917248a2d494bec57539`; `fresh_03` `ff940c4ee1025ed63542f3c816699141f51d5dad264a18f46017bb8c8336d58a`; `fresh_04` `cfde340a9e83ff7f7cd1a47a18d5085af76e534d54fbf51a42b087d8e90b2179`; `fresh_05` `e6bd3e81ef2fa527f7081b06f4583e03a87c9e3b2f2e240920008ce340dde10a`; `fresh_06` `68904eff94ed3f137c117aec37fe970c1120872e9d48e1f4b7e1564b45ce3755`.

Six generated inputs and per-run harness outputs are retained in `synthetic/` and `runs/`. The user-facing platform and Docker were not used.
