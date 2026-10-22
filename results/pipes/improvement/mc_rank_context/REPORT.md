# Pipes: MC suffix matching by removal-rank quartile

**Статус:** узкий screen cases 5/9/15 завершён; кандидат не улучшил score. Полный Open15, holdout-v2 и robustness suite не запускались по условию продвижения только при положительном screen.

## Результат

В четырёхбинном варианте KPI полностью совпали с baseline на всех трёх кейсах. Взвешенная сумма по screen осталась **10.8590850565** против **10.8590850565** (`Δ=0`). Trench length и occupied length также совпали по каждому кейсу. Оснований продолжать проверку на Open15 нет.

## Новизна относительно прежних MC-опытов

В текущем final Monte Carlo rollout уже хранит удаление как `rank-from-newest` в permille и затем применяет этот rank к counterfactual active-list. Но `observationKeyEqual` для removal проверяет только совпадение `kind`, игнорируя сохранённое значение ранга: [`solution.cpp:552-555`](/Users/555tery/techarena/results/pipes/final/solution.cpp:552).

Это ограничение прямо указано в прежних MC-аудитах: [`bounded_mc/REPORT.md:64`](/Users/555tery/techarena/results/pipes/improvement/max_open_lookahead/bounded_mc/REPORT.md:64) описывает suffix-context matching, а [`cohort_owner_mc_corrected_audit/REPORT.md:51`](/Users/555tery/techarena/results/pipes/improvement/cohort_owner_mc_corrected_audit/REPORT.md:51) уточняет, что deletion-контекст совпадает независимо от ранга. В просмотренных отчётах, manifest-файлах и MC-абляциях не обнаружен вариант, который бы требовал совпадения removal-rank bins. Ранее тестировалось наличие rank в истории и его применение к симулируемому состоянию, но не условный поиск сценария по рангу.

## Единственное изменение кандидата

Кандидат основан на final SHA `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`. В `observationKeyEqual` удаление теперь совпадает, если оба rank-permille попали в один из четырёх равных bins диапазона 0–1000. Добавление по-прежнему требует точного совпадения длины. Остальные параметры MC — suffix depth, глубина сценария, окно истории, число trials, бюджет решений, seed, candidate gates и threshold — не менялись.

Изменён только helper. Оригинальный final/canonical/platform source не редактировался; кандидат лежит отдельно в `candidate.cpp`.

## Harness screen

Baseline и candidate собраны одним Apple Clang 17.0.0 командой:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic SOURCE.cpp -o BINARY
```

Оба бинарника прогнаны одним `tools/pipes_harness.py`, тем же `tools/interactor` и копиями официальных inputs 5/9/15 с одинаковыми SHA-256. Лимиты harness: 5 CPU-секунд и 256 MiB.

| Case | Вес | Trench baseline → q4 | KPI baseline → q4 | Δ KPI | CPU baseline → q4 | Peak RSS baseline → q4 |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 1 | 62 760 → 62 760 м | 0.810070108349 → 0.810070108349 | 0 | 0.0911 → 0.0899 с | 3.156 → 3.125 MiB |
| 9 | 1 | 61 960 → 61 960 м | 0.508392511298 → 0.508392511298 | 0 | 0.1100 → 0.1192 с | 3.063 → 3.094 MiB |
| 15 | 10 | 438 920 → 438 920 м | 0.954062243689 → 0.954062243689 | 0 | 2.1107 → 2.0908 с | 5.563 → 5.547 MiB |
| **Weighted sum** | **12** | — | **10.8590850565 → 10.8590850565** | **0** | — | — |

Все шесть runs завершились со статусом `ok`; лимиты не превышены. Повторный прогон, полный Open15 и holdout-v2 не выполнялись.

## Артефакты

- [`candidate.cpp`](candidate.cpp) — единственная изменённая копия.
- [`baseline` и `candidate`](baseline) — собранные бинарники; candidate binary находится по соседнему пути [`candidate`](candidate).
- [`screen_baseline/cases.csv`](screen_baseline/cases.csv) и [`screen_candidate/cases.csv`](screen_candidate/cases.csv) — per-case результат и ресурсы.
- [`manifest.json`](manifest.json) — SHA-256 исходника baseline/candidate, бинарников, всех трёх inputs, harness/interactor и результатов.

Решение остановиться после screen следует из заранее заданного критерия: полный Open15 разрешён только при более высокой взвешенной сумме. Изменения в финальную версию не переносились.
