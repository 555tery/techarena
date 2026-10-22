# Baseline route scorer — fixed pre-measurement trainer

This directory contains a copy of the already-reviewed v1 trainer and exporter,
adapted to the fixed router architecture `128 -> 16 ReLU -> 1`. No fitting is
authorized until root reports measured headroom and supplies the final train
and calibration CSVs. Do not run the trainer from this preparation state.

The C++ fork calls `learned_model::score(array<float,128>)` and reads
`learned_model::kMargin`. The safe stub in `src/trained_router.hpp` returns a
constant score and sets a very large margin, so the baseline route remains
selected. The trained score predicts `(target_trench - base_trench) / 20`;
lower is better and candidate 0 is the forced baseline action.

The CSV contract is `stream,state,action,is_base,target_trench,base_trench,f0`
through `f127`, with optional metadata such as `kind`. The loader groups and
weights by stream/state, reads only `f0..f127` as model input, validates one
baseline row per state, and requires numeric action IDs. The explicit semantic
route one-hot features at `f112..f115` are permitted by the protocol. Stream and
state identifiers are metadata only and are never model inputs.

The copied fixed recipe retains seed 20261017, Adam at 0.001, equal Huber and
pairwise losses, train-only normalization/clipping, 64-state batches, 120 epoch
cap and 15-epoch patience. Calibration selects the checkpoint and one margin
from `[0, 0.5, 1, 2]`; threshold arithmetic is
`float32(base_score - candidate_score) > float32(margin)`, matching the C++
runtime. Epoch 0 is logged only as a random initialization control; selection
starts after a trained epoch. Ties use numeric action index.

The specified `128 -> 16 -> 1` dense MLP has 2,081 trainable parameters
(`128*16 + 16 + 16 + 1`), matching the corrected protocol.

When root authorizes fitting, pass only its supplied paths to `train_mlp.py`
and use a fresh output directory. Re-export a saved model with
`export_model.py`; parity can be checked against the supplied calibration CSV.
The exporter stages a header and atomically replaces the destination only
after score parity passes. Once the final header is compiled into the binary,
do not regenerate or edit it.
