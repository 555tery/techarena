# Bayesian latent-regime MPC — synthetic validation

Gate: **NO-GO**. 28 paired streams; all sizes/profiles were preregistered.
Mean Δ KPI: **+0.000028849**; stratified paired 95% CI: **[-0.000535065, +0.000592482]**.
Per-stream: 7 improved, 6 regressed, 15 tied.
Maximum candidate CPU **1.190035 s**; maximum RSS **8.828 MiB**; protocol/resource checks: **pass**.

## По размерам

| Команд | Mean paired Δ KPI |
|---:|---:|
| 16384 | +0.000559925 |
| 200000 | -0.000502226 |

## По профилям

| Профиль | Mean paired Δ KPI |
|---|---:|
| bimodal_shortest | -0.002482654 |
| long_newest | +0.000000000 |
| long_to_short | +0.000000000 |
| short_fifo | +0.001965580 |
| short_to_long | -0.000113743 |
| uniform_fifo_to_newest | +0.000000000 |
| uniform_random | +0.000832763 |

Holdout-v2/Open15 разрешены только при PASS; параметры после freeze не меняются.
Точные входные hashes и fitted params — `input_manifest.json` / `model_params.json`; per-stream outcomes — `stream_results.csv`.
