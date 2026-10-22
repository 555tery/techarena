# Поиск максимального weighted open score: Pipes

## Лидер и независимая проверка

Фиксированный кандидат `adaptive_right4_w2048_s60` набрал **29.441565327452/32.1** на всех 15 официальных открытых кейсах. Проверка проведена локальным `tools/pipes_harness.py` с официальным интерактором; 15/15 кейсов valid. Это на **+0.502106387187** больше S50 (28.939458940265) и на **+1.065727728079** больше policy4 (28.375837599373).

Правило: история последних 2048 положительных размещений; для каждой подходящей дыры используется recent-unfit scoring `slack * history_size + 60 * count(recent_length > slack)`. Трубы длиной 1–4 м размещаются у правого края выбранной дыры, более длинные — у левого. Правило не использует номер теста, будущие операции или идентификаторы кейсов.

На максимальном официальном кейсе измерено 1.024266 с CPU и 5.828 МиБ RSS. Сборка с `-Werror` прошла.

## Крупнейшие per-case изменения относительно S50

Покейсовые KPI, длины траншей, и взвешенная дельта приведены в [final_per_case_comparison.csv](final_per_case_comparison.csv). Основные вклады:

- кейс 3: **+0.375000** score (траншея 40→20 м);
- кейс 10: **+0.133478** (18 460→15 380 м);
- кейс 13: **+0.046900** (3320→3280 м);
- кейс 7: **−0.045373** (1680→1760 м);
- кейс 12: **−0.007684**;
- кейс 15: **−0.009138**.

В сумме положительные изменения перевешивают регрессии; это open-tuned score, а не claim о закрытых тестах.

## Отбор

Стандартные best-fit/first-fit/worst-fit/age-first варианты не превзошли S50. Полная таблица проверенных official-interactor кандидатов доступна в [all_official_candidates.csv](all_official_candidates.csv); покейсовые дельты ранних стратегий к S50 — в [per_case_scoreboard_vs_s50.csv](per_case_scoreboard_vs_s50.csv). Затем параметры recent-history были проверены на официальных тестах. Для полного right-endpoint при W=1024/S50 результат 29.049090580812; правый конец для всех длин работал лучше левого, а high-address tie-break этот результат немного ухудшил (29.040212877829).

После обнаружения смешанного endpoint проведён быстрый 27-точечный screen: W ∈ {1024, 2048, 4096}, scale ∈ {50, 60, 70}, right-max ∈ {3, 4, 5}. Лучший симуляционный результат — W2048/S60/right-max4; он дополнительно и независимо прошёл официальный harness. Полные данные screen и hash симулятора находятся в [adaptive_grid](adaptive_grid/).

## Воспроизведение

```sh
g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic results/pipes/improvement/max_open_gap_search/src/adaptive_right4_w2048_s60.cpp -o results/pipes/improvement/max_open_gap_search/binaries/adaptive_right4_w2048_s60_fixed
python3 tools/pipes_harness.py --solver results/pipes/improvement/max_open_gap_search/binaries/adaptive_right4_w2048_s60_fixed --name adaptive_right4_w2048_s60_fixed --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/max_open_gap_search/reports/adaptive_right4_w2048_s60_fixed
```

Исходник с фиксированными параметрами: [adaptive_right4_w2048_s60.cpp](../src/adaptive_right4_w2048_s60.cpp). Общая реализация правил и режимов: [gap_search.cpp](../src/gap_search.cpp). Хеши всех сборочных артефактов, тестов и интерактора сохранены в [final_manifest.json](final_manifest.json). `src/pipes.cpp` и канонические файлы не менялись.
