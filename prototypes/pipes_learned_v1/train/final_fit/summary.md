# Final learned model fit

The fixed 128→32 ReLU→1 recipe was run once on the completed DAgger-expanded training CSV. The selected checkpoint is epoch 15; training stopped at epoch 30 after 15 stale epochs. No optimizer, architecture, or training hyperparameters were changed.

- Training: 157,203 rows, 10,176 states, 128 streams; CSV SHA256 `1fd786d1c880e2c7783da5f3472318a14f716b3f14d54451fc2300dfbaf93e42`.
- Calibration: 23,296 rows, 1,520 states, 24 streams; stream overlap with training was zero. CSV SHA256 `4273c9c7b6e55cd519d17ca4c7eda6a99dbf6f531c9e61d7621371645f351a2f`.
- Selected abstention margin: `0.5`; calibration mean realized saving: `0.1569 m/state`; pairwise accuracy: `0.5897`; MAE: `27.65 m`.
- The selected policy acts in `6.46%` of calibration states. Hindsight saving is `34.70 m/state`, leaving `34.54 m/state` mean regret.
- Export score parity passed on all 23,296 calibration rows; maximum absolute score difference was `8.34e-7` score units (limit `5e-5`). The staged header replaced the final header atomically after this check.

The calibration gain is small and sparse. Calibration was also used to select the checkpoint and margin, so `0.1569 m/state` is a selection-biased diagnostic, not an independent estimate of generalization. No Open15 or official evaluation was generated or run, and this result does not establish progress to a 30.5 score.

Model JSON SHA256: `e03a88fc00623d759582724deb5875f0db28c551b785132da30134f6b3fcbebd`.

Float32 inference-tensor SHA256: `65454acb06a9d2fb238a6b1e655f6b6f4947632133090ae53eba0c8985246f1f`.

Header SHA256: `b637c15406c1cb138f2b98f53578a4af23d10a3147ac40f39e3628bae48ba4ad`.

See `model.json`, `train.log`, `validation_diagnostic.json`, `export_manifest.json`, and `model.sha256` for the full recipe, epoch history, diagnostics, and artifact hashes.
