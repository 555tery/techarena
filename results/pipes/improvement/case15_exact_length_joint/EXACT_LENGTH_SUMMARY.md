# Case 15: exact-length joint-deletion screen

## Scope and method

This is a diagnostic replay of the saved Open case 15 trace, not a solver or policy run. At 128-command checkpoints, active pipes were paired within exact length, excluding equal-length pipes that physically touch. Future removals label whether each pipe is deleted within the next 128 commands; they are not used as features. A marginal deletion model uses exact length, coarse age band, and newest-rank quartile. PID parity is excluded. The joint model estimates whether paired pipes have additional co-deletion association.

Two deterministic pair constructions were compared to check sensitivity to how pairs are sampled:

1. **PID order:** pair consecutive active PIDs in ascending PID order.
2. **Affine-permuted order:** within each length, use a deterministic affine permutation of current active PIDs, with a coprime multiplier and an offset derived from current step and length; then pair consecutive entries. This uses current state only and does not predict outcomes.

Both runs use the same trace, 1,561 checkpoints, 780 warmup checkpoints, and 781 scored checkpoints. Up to 256 pairs are sampled per checkpoint. Metrics are averaged over scored checkpoints. Improvements are `independent-model loss - joint-model loss`, so positive means the joint model is better.

## Results

| Pair construction | Scored pairs | Both deleted within horizon | Exactly one deleted | Brier improvement | Log-loss improvement |
|---|---:|---:|---:|---:|---:|
| PID order | 199,936 | 24 | 212 | -0.0000665623 | +0.0002753170 |
| Affine-permuted | 199,936 | 3 | 253 | -0.0000060544 | -0.0000297047 |

Under PID-order pairing, log loss improves while Brier worsens. Under affine-permuted pairing, both metrics worsen and only 3 paired co-deletions occur. Thus the apparent joint signal is highly sensitive to the pair construction and is not a robust predictive signal in this screen. This does **not** prove that no useful cohort signal exists; it gives no support for implementing a joint-deletion slab policy. No candidate policy was run.

## Limits

- One Open15 stream only; there is no independent-stream uncertainty estimate.
- The screen measures pairwise association conditional on the stated features, not causal benefit from placing pipes together.
- The exact-length and non-touching restrictions define the sampled population; results do not cover other pipe pairs.
- Hindsight removal labels are used only for evaluation after each prediction horizon.

## Reproducibility manifest

- Candidate trace source SHA-256: `43bfbdadbae18ac180d1e59b6631342cfe1bef99190a449838f0470d6f220200`
- Open15 input SHA-256: `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`
- Saved judge reply SHA-256: `0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e`
- Current diagnostic script SHA-256: `c2547482a7f0b9c7f95e01e0e627c012d3ecda36b4628ea6145058078e6a9c8e`
- PID-order result JSON SHA-256: `ac8b2c55a1276a9b68074eb32715250290225476955b37a1ae64cefb57a67839`
- Affine-permuted result JSON SHA-256: `6885145622162e17146b462ee06fb5e2b866524aeb4fc37ed4ce5813e8381a18`
- Affine-permuted replay resources: 17.37 s wall, 17.25 s user, 0.09 s system; maximum resident set 217,513,984 bytes (about 207.5 MiB).

Artifacts: `diagnose.py`, `pid_order_result.json`, and `hash_order_result.json` in this directory. The diagnostic script writes only the latter result file.
