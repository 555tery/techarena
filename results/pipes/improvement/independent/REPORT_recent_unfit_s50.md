# Независимое сравнение с `recent_unfit_s50`

Официальный harness повторно прогнал бинарник strategy-агента по всем 15 открытым тестам. Сверены SHA-256 файлов входных тестов с baseline и demand-aware запуском; совпали все 15. Frozen holdout-v2 не читался и не запускался.

| Solver | Weighted score / 32.1 | OK | max CPU (s) | max RSS (MiB) |
|---|---:|---:|---:|---:|
| `recent_unfit_s50` | 28.9394589403 | 15/15 | 0.861180 | 5.5938 |
| `demand W32/B10` | 28.4235657495 | 15/15 | 1.055179 | 6.0156 |
| `policy4 baseline` | 28.3758375994 | 15/15 | 0.964313 | 4.6094 |
| `age hybrid L<=5` | 28.4072450762 | 15/15 | 1.302101 | 4.6406 |

Разница W32/B10 минус `recent_unfit_s50`: **-0.5158931908** балла. По суммарному score открытых тестов W32/B10 ниже.

По отдельным тестам W32/B10 выигрывает 2 раз, проигрывает 6 раз и совпадает 7 раз по взвешенному score с `recent_unfit_s50`. Разницы по кейсам приведены в [`per_case_vs_recent_unfit_s50.csv`](./per_case_vs_recent_unfit_s50.csv).

| Case | Weight | recent KPI / trench (m) | demand KPI / trench (m) | demand weighted delta |
|---:|---:|---:|---:|---:|
| 1 | 0.1 | 0.900000000 / 20 | 0.900000000 / 20 | +0.000000000 |
| 2 | 1 | 1.000000000 / 20 | 0.500000000 / 40 | -0.500000000 |
| 3 | 1 | 0.375000000 / 40 | 0.375000000 / 40 | +0.000000000 |
| 4 | 1 | 0.666666667 / 60 | 0.666666667 / 60 | +0.000000000 |
| 5 | 1 | 0.499803382 / 101720 | 0.499803382 / 101720 | +0.000000000 |
| 6 | 1 | 0.900000000 / 20 | 0.900000000 / 20 | +0.000000000 |
| 7 | 1 | 0.998214286 / 1680 | 0.931666667 / 1800 | -0.066547619 |
| 8 | 1 | 0.988675214 / 4680 | 0.980296610 / 4720 | -0.008378604 |
| 9 | 1 | 0.500000000 / 63000 | 0.500000000 / 63000 | +0.000000000 |
| 10 | 1 | 0.666522210 / 18460 | 0.800000000 / 15380 | +0.133477790 |
| 11 | 1 | 0.900929204 / 22600 | 0.900132626 / 22620 | -0.000796578 |
| 12 | 4 | 0.993120155 / 10320 | 0.989285714 / 10360 | -0.015337763 |
| 13 | 4 | 0.961445783 / 3320 | 0.967272727 / 3300 | +0.023307777 |
| 14 | 4 | 0.996405920 / 37840 | 0.996405920 / 37840 | +0.000000000 |
| 15 | 10 | 0.954976055 / 438500 | 0.946814235 / 442280 | -0.081618194 |

## Идентификация артефактов

- Demand source: `results/pipes/improvement/independent/source/demand_aware.cpp`, SHA-256 `13298d85ec3e4703fc000690a6ce2778cb0efdce6a23065325b72173cc057a9a`.
- Demand binary: `results/pipes/improvement/independent/bin/demand_w32_b10`, SHA-256 `af7a92b61c12ae3b9c96b010e7f3a3f1c489ded50dd3305441b723fe9310b805`.
- Reference source: `/Users/555tery/techarena/results/pipes/improvement/strategies/adaptive_allocator.cpp`, SHA-256 `002f5bb77c131f829fc5ccfb0a310204113b6d8164d09d8dc7ed001e96833095`.
- Reference binary: `/Users/555tery/techarena/results/pipes/improvement/strategies/binaries/recent_unfit_s50`, SHA-256 `5c9efebc85b11d7b176ffe77a9ac002d58a78debfd045d535249a65ff2bd2e93`.
- Reference build: `g++ -O2 -std=c++17 -Wall -Wextra -pedantic -DPIPES_STRATEGY=2 -DPIPES_HISTORY_WINDOW=128 -DPIPES_PENALTY_SCALE=50 /Users/555tery/techarena/results/pipes/improvement/strategies/adaptive_allocator.cpp -o /Users/555tery/techarena/results/pipes/improvement/strategies/binaries/recent_unfit_s50`.
- Exact official run report: `results/pipes/improvement/independent/runs/recent-unfit-s50-reference/summary.json`.

Результаты показывают только эмпирическое сравнение на публичном наборе, а не ожидаемый балл на невидимых входах. W32/B10 выбран после sweep по шести конфигурациям на этом же наборе, поэтому лучший результат подвержен selection bias. `recent_unfit_s50` повторно прогнан по тем же 15 входам для парного сравнения.
