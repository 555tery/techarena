# Learned action scorer v1

This directory contains a fixed training recipe for the 128 → 32 ReLU → 1
action scorer. The script reads only the supplied training and calibration CSVs.

For each state, exactly one row has is_base=1. Its target_trench must equal
that state's base_trench, the final trench after forcing deterministic generic
greedy action 0 and continuing with the same greedy suffix. The supervised
target is (target_trench - base_trench) / 20. Lower scores are better.

At use time, compare a candidate action's score with the baseline action's
score. The fixed abstention margins are [0, 0.5, 1, 2] score units. Select the
lowest-scored nonbaseline action only when the float32 baseline-minus-candidate
score difference is strictly greater than the selected margin, matching C++
runtime threshold arithmetic. If no margin gives positive stream-balanced realized meter
savings, the checkpoint is marked non-deployable and runtime should retain the
baseline. The exported header then sets learned_model::kMargin to 1e30 so the
engine abstains; a positive calibration gain exports the chosen grid margin.
If model scores tie exactly, diagnostics select the lowest numeric action index,
matching the engine's first-candidate tie-break.

## Fixed recipe

- Architecture: one hidden layer, 128 inputs, 32 ReLU units, one linear output.
- Seed: 20261017; initialization and epoch shuffling use NumPy default_rng.
- Feature normalization: equal stream, state, and row weighting; means and
  standard deviations use training rows only; standardized values are clipped
  to [-8, 8].
- Optimizer: Adam (lr=0.001, beta1=0.9, beta2=0.999, epsilon=1e-8),
  weight decay 1e-5.
- Loss: equal mixture of state/stream-balanced Huber regression (delta 1 in
  20 m units) and logistic pairwise ranking over unequal-label action pairs.
- Batch: 64 states; at most 120 epochs; stop after 15 epochs without improving
  the fixed calibration selection criterion.
- Epoch 0 is logged only as an untrained random-initialization control. A
  checkpoint can be selected only after at least one optimizer epoch.
- Checkpoint criterion: maximize calibration mean realized savings in meters,
  averaging states equally within each stream and streams equally, over the
  fixed abstention grid. Ties prefer larger margin, then better pairwise
  accuracy, lower MAE in meters, and earlier epoch. Zero or negative best
  savings yields deployable=false.
- `export_model.py` re-exports a saved `model.json` without training, stages
  the header and atomically replaces the destination only after an optional
  C++ score-parity check against deterministic samples from a supplied CSV.
  The header embeds SHA256 hashes for the full model JSON and ordered float32
  inference tensors; an adjacent manifest records the header hash and parity
  result.

The fixed architecture and optimizer are not tuned on official inputs.
train_mlp.py writes model.json, train.log, validation_diagnostic.json, and
../src/trained_model.hpp only when run with both CSV paths.

Train and calibration stream IDs must be disjoint. The source collections used
file-local stream names, so the current training invocation uses metadata-only
copies with train_ and calibration_ prefixes. The original CSVs remain
unchanged, and the loader keeps its overlap guard enabled.
