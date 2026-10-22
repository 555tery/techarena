# Case 15 — candidate choice and interval lineage

## Result

The frozen-final replay is exact: its judge output SHA-256 is `0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e`, matching the saved baseline. The frozen source is `results/pipes/final/solution.cpp`, SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`; the input is `data/pipes/open/15.in`, SHA-256 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`.

The exact expansion replay found **17,645** extensions, at ops 1–199,978. Before each expansion it scanned every current interval: all 17,645 had **zero physically fitting intervals**. In 13,677 cases, free volume in aggregate was enough for the request, so no single contiguous hole was large enough. The trench ended at 438,920 m. This establishes fragmentation or aggregate-volume shortage at the expansion decision; it does not identify a better alternative placement.

## Bounded preceding-placement audit

The original empty expansion-candidate file could only establish “no fit at expansion”; it did not explain earlier placement choices. This replay now follows each interval episode to its **first strictly later expansion** and audits preceding positive placement operations while that exact gap remained alive and physically fit the request.

- 65,707 gap episodes had a later expansion before that episode closed; 25,859 had at least one preceding fitting placement.
- The audit covers **131,576 gap × placement pairs** on **34,021 unique placement ops**. Those target ops are all non-expansion placements. They lead into 7,729 distinct first-successor expansion ops.
- Across all 17,645 expansions there were **13,814,470 pre-expansion gap × expansion states**. The detailed candidate replay is intentionally bounded to each interval's first subsequent expansion instead of repeating the same long-lived gaps at every later expansion.
- At those placements, the full physical universe contained 1,275,602 gap instances in total across the repeated states. Of these, 961,080 were omitted by same-length representative selection; 365 representatives fell after the scorer's first `slack > 40` cutoff; 314,157 representatives were actually scored.
- Of the target gap × placement pairs, **64,242** reached the score loop and **67,334** were hidden behind a lower-address interval of the same length. None was excluded by cohort or the slack cutoff. `parityCohortMode` was off for all 34,021 audited ops; the selected pool was `all`.
- For target intervals in the physical universe, the diagnostic records their hypothetical full-universe cost rank: median 19, P90 71, maximum 211. For the 64,242 intervals actually scored, rank was 2–27 (median 6, P90 14). The selected baseline winner and score reconcile with the independent placement trace on all 34,021 ops.
- An independent reconstruction from gap lifetimes checked all **131,576** target ranks and matched the replay's physical-fit universe totals. Among same-length-shadowed target pairs, **1,847** ranked first in the full physical universe; **2,219** would outrank the baseline winner by score and address tie-break if they were directly compared. These are counterfactual rankings on the frozen state, not measured trench savings.
- Monte Carlo ran on four audited ops and kept the baseline choice each time. No target interval that survived to a later expansion was selected in these audited decisions.

Candidate ranks use the frozen solver's score formula and address tie-break. `physical_rank` ranks a target among every physically fitting gap; `scored_rank` ranks it only among intervals the live scorer actually evaluates. A lower-address representative is not necessarily tie-break superior when the allocator chooses the high side, so “shadowed” alone does not mean harmless. The saved rows contain the target's full-universe rank, representative, score, baseline winner, and selected winner.

## Scope and limits

This is an exact explanation of candidate decisions on the frozen baseline trajectory, selected by the fact that the gap later survived until an expansion. That selection uses future survival, so it is diagnostic hindsight and has survivor-selection bias. It does **not** show that changing any placement would reduce trench length, and these hindsight labels cannot be used as online features.

The audit links each gap episode only until its first later expansion. Repeating the full candidate dump at every later expansion would duplicate many long-lived intervals across 13.8 million interval-state pairs; that repeated-state candidate audit was not generated. Gap episodes close on the first consume/merge/tail-extension event. When deletion merges create a new gap, the trace records a new episode and a lineage bitmask, but no parent IDs or complete ancestry graph. Therefore this is not a full causal reconstruction through successive deletion merges.

## Artifacts

- [`candidate_audit.json`](candidate_audit.json) — compact metrics, evidence checks, source/artifact hashes, and the SHA-256 of this report.
- [`runs/candidate_ops.csv`](runs/candidate_ops.csv) — full physical-universe counts, filter counts, scored candidate counts, baseline/selected winner, and Monte Carlo result at each target op.
- [`runs/candidate_targets.csv.gz`](runs/candidate_targets.csv.gz) — one row per audited gap × placement pair, including its first successor expansion, physical rank, eligibility, representative, score rank, and winner.
- [`runs/candidate_scores.csv.gz`](runs/candidate_scores.csv.gz) — scored representatives plus the top-three rollout candidate pool, with costs and ranks.
- [`runs/extensions.csv`](runs/extensions.csv) and [`runs/extension_candidates.csv`](runs/extension_candidates.csv) — one row per expansion and physical candidates there; the latter is header-only because no expansion had a fit.
- [`interval_fates.csv`](interval_fates.csv) and [`geometry/`](geometry/) — first-close gap episodes, placements, and EOF intervals.

## Reproduction

From the project root, run:

```sh
python3 results/pipes/improvement/case15_exact_candidate_telemetry/reproduce.py
```

The script reconstructs target pairs from the saved frozen answer, builds diagnostic copies in this directory, replays the frozen final, checks the output hash, then summarizes interval and candidate telemetry. It does not edit the frozen source or submit anything to the platform. The instrumented replay took 21.0 seconds wall on this Mac; this is a diagnostic runtime, not a Linux/GCC contest-limit measurement.
