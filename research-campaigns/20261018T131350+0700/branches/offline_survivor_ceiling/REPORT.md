# Case 15 clairvoyant survivor-prefix diagnostic

**This is an offline oracle, not a candidate.** It uses the exact future EOF-survivor set and each temporary pipe's deletion operation. Do not copy the policy or the serialized answer into production.

The pinned input is public Open15 case 15, SHA-256 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`. Baseline source SHA-256 is `c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c`. No Validation/holdout data, platform, official evaluator, or model was accessed.

The one heuristic puts all 60,510 EOF survivors in a contiguous prefix in birth order (volume 418,757 m). For each temporary pipe, it uses first-fit in a free interval whose usable start is at least `prefixFinalVolume[known_death_op]`; if no such interval fits, it extends the suffix. Digging occurs in 20 m units.

The independent replay accepted all 200,000 response lines. A separate range min/max tree verified every allocation was inside the dug trench and non-overlapping, every delete named the right active interval, final survivors occupy exactly `[0,418757)`, and no temporary pipe remains at EOF. Replayed peak live volume is 418,768 m, so the volume lower bound rounded to 20 m is `ceil(418768/20)*20 = 418780 m`.

This first-fit schedule ends at **418,840 m**, 60 m above that bound. Two late temporary allocations trigger the excess: one length-16 request has only a 14 m largest eligible free extent and adds 20 m; a later length-40 request has only 8 m eligible and adds 40 m. Their exact operation/PID coordinates are retained only in the diagnostic JSON. This explains where this greedy schema loses space; it does **not** prove the bound is unattainable with a different clairvoyant placement schedule. No parameter tuning or second heuristic was tried.

Artifacts: [answer](clairvoyant-answer.txt), [machine-readable result](clairvoyant-result.json), [reproducer and replay checker](clairvoyant_survivor_prefix.py), [manifest](manifest.json).
