# Case 15: coalescence option value — no-go

## Итог

Проверен один новый causal-механизм на актуальном comparator `lifo_young_offset_scale_gt4096` (Open15 30.044966195). Он защищает конкретную fitting-дыру, если её граничная труба относится к наблюдаемой near-LIFO когорте и её удаление может открыть место под более крупные длины, встречавшиеся в префиксе. При этом solver перенаправляет текущую трубу в следующую по базовой стоимости fitting-дыру, только если дополнительная базовая стоимость не превышает оценённую merge-option value.

**No-go.** На case 15 траншея выросла с **438 640 м до 439 160 м** (**+520 м**, KPI `0.954671257 → 0.953540851`). На восьми заранее сгенерированных синтетических потоках кандидат не выиграл ни разу: семь ties и один проигрыш `+120 м`; сумма KPI снизилась на **0.000661867**. Полный Open15 не запускался, поскольку механизм ухудшил целевой кейс и синтетический gate.

## Причинное правило

Для текущей лучшей fitting-дыры проверяются две граничные трубы. Модель включается только если в последних 48–64 наблюдаемых удалениях не менее 80% пришлись на последние 5% активных PID, а соседняя труба сама находится в этой newest-5% группе. Для удаления такой трубы gap увеличится на её длину. Оценка опциона суммирует частоты ранее наблюдавшихся длин, которые пока не помещаются в gap, но поместились бы после слияния, и умножает сумму на `60`, долю near-LIFO удалений и относительную срочность PID внутри newest-5%.

Если оценка превышает разницу исходных `scoreGap` между текущей дырой и альтернативой, solver пропускает её и выбирает следующую лучшую. Проверяется до двух последовательных кандидатов. Правило использует только текущую геометрию, активные PID и наблюдённый префикс. Оно не читает будущие команды или номер теста.

Механизм отличается от общего сохранения крупных дыр: защищается не всякая большая дыра, а конкретная дыра с молодым соседним PID и наблюдаемой вероятностью скорого локального слияния. Тем не менее результат указывает, что оценка опциона систематически завышала полезность такого ожидания на case 15.

## Результаты

| Поток | Comparator, м | Candidate, м | Δ, м | Изменение KPI | Действия правила |
|---|---:|---:|---:|---:|---:|
| Open case 15 | 438 640 | 439 160 | **+520** | −0.001130406 | 84 684 protected checks; 67 559 diversions |
| fresh_01 uniform/random | 17 520 | 17 520 | 0 | 0 | 0 diversions |
| fresh_02 uniform/LIFO | 14 140 | 14 140 | 0 | 0 | 0 diversions |
| fresh_03 short→wide/LIFO | 3 300 | 3 300 | 0 | 0 | 0 diversions |
| fresh_04 bimodal/FIFO | 11 600 | 11 600 | 0 | 0 | 0 diversions |
| fresh_05 periodic/median-rank | 286 740 | 286 740 | 0 | 0 | 0 diversions |
| fresh_06 four phases/alternating LIFO-FIFO | 14 900 | 14 900 | 0 | 0 | 517 diversions |
| fresh_07 uniform/newest-biased | 180 360 | 180 480 | **+120** | −0.000661867 | 5 846 diversions |
| fresh_08 long-biased/mixed | 178 020 | 178 020 | 0 | 0 | 0 diversions |
| **Сумма KPI synthetic-8** | **7.562443081** | **7.561781214** | — | **−0.000661867** | — |

На case 15 правило проверило coalescence-option value 151 535 раз, сочло 84 684 кандидата ценными для сохранения и перенаправило 67 559 размещений. Следовательно, отсутствие выигрыша не объясняется тем, что условие не активировалось. Синтетическая регрессия возникает именно на потоке с удалением, смещённым к newest 5%, то есть на сценарии, где сигнал удаления наиболее похож на рабочую гипотезу.

Все 9 запусков candidate и baseline прошли официальный локальный interactor. Максимум candidate: **2.632 CPU-с / 12.55 MiB RSS** на case 15 и **0.608 CPU-с / 4.69 MiB** на synthetic-8; лимиты 5 с / 256 MiB соблюдены. Измерения выполнены на macOS arm64, не на Linux/GCC.

## Воспроизведение

Из корня проекта:

```sh
python3 results/pipes/improvement/case15_fresh_policy_20261018/prepare_candidate.py
python3 results/pipes/improvement/case15_fresh_policy_20261018/generate_synthetics.py
clang++ -std=c++20 -O2 -DNDEBUG -Wall -Wextra -Werror -pedantic -DMC_ROLLOUT_DIAGNOSTICS results/pipes/improvement/case15_fresh_policy_20261018/source/coalescence_option_value.cpp -o results/pipes/improvement/case15_fresh_policy_20261018/bin/coalescence_option_value
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_fresh_policy_20261018/bin/coalescence_option_value --name candidate_case15 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_fresh_policy_20261018/tests/case15 --out results/pipes/improvement/case15_fresh_policy_20261018/runs/candidate_case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_fresh_policy_20261018/bin/coalescence_option_value --name candidate_synthetic8 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_fresh_policy_20261018/synthetic --out results/pipes/improvement/case15_fresh_policy_20261018/runs/candidate_synthetic8 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Baseline runs are in `runs/baseline_case15/` and `runs/baseline_synthetic8/`. Candidate runs, raw judge outputs, per-case resources and solver diagnostics are in the matching `runs/candidate_*` directories. Input seeds and generation descriptions are in `synthetic/manifest.json`.

## Хеши и границы вывода

Полные SHA-256 исходников, бинарников, генератора, входов, harness и interactor записаны в [`manifest.json`](manifest.json). Frozen final и canonical source не менялись. Это локальный отрицательный screening; он не меняет lab-лидера и не является результатом платформы. Open15, holdout-v2, сайт и Docker не использовались.
