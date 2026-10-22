# Shadow expert portfolio — synthetic screen

Gate: **NO-GO**

36 streams; mean paired KPI delta (portfolio − frozen): **+0.000603680**.
Stratified paired 95% bootstrap CI: **[-0.000865148, +0.002393385]**.
Shadow fidelity mismatches: **0**. Protocol/resource failures: **0**.
Portfolio maximum CPU: **1.426922 s**; maximum RSS: **19.172 MiB**.

## По размерам

| Команд | Средняя paired Δ KPI |
|---:|---:|
| 5000 | +0.000313615 |
| 50000 | +0.000268685 |
| 200000 | +0.001228740 |

## По семействам

| Семейство | Средняя paired Δ KPI |
|---|---:|
| bimodal_sticky_oldest | +0.000000000 |
| long_newest | +0.000274759 |
| long_to_short_delete_shift | +0.000000000 |
| short_fifo | -0.000961065 |
| short_to_long_delete_shift | +0.004668246 |
| uniform_random | -0.000359861 |

Все seed, параметры и входные hashes находятся в `input_manifest.json`; 
покейсовые ресурсы, shadow fidelity и switch counts — в `stream_results.csv`.
Gate parameters and split were frozen in `PREREGISTERED.md` before runs.
