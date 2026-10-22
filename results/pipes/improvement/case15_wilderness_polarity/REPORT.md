# Case 15: wilderness polarity — no-go

## Итог

Проверена новая геометрическая политика: менять сторону, с которой используется свободный хвост после вынужденного расширения траншеи. При расширении остаток можно оставить у растущего конца (обычный режим) либо у старого конца расширенного участка, превратив его во внутреннюю дыру. Проверены два фиксированных правила: чередовать стороны и всегда класть у правого края. Оба варианта ухудшили case 15; Open15 не запускался.

| Вариант | Траншея | Δ к champion | KPI case 15 | Δ weighted score | CPU, с | RSS, MiB |
|---|---:|---:|---:|---:|---:|---:|
| Champion | 438 920 м | — | 0.954062243689 | — | 2.096067 | 6.281 |
| Чередование left/right | 439 040 м | +120 м | 0.953801475948 | −0.002607677415 | 2.094015 | 7.156 |
| Всегда right-edge | 439 500 м | +580 м | 0.952803185438 | −0.012590582511 | 1.642265 | 7.500 |

Все три запуска завершились `ok` на одном и том же входе case 15; 200 001 команда интерактора, включая завершающий ноль. Лимиты 5 CPU-с и 256 MiB не превышены. Контрольный score champion на этом кейсе совпал с сохранённым результатом.

## Реализация и интерпретация

Политика меняет только сторону размещения после расширения, когда ни один свободный интервал не подходит. В режиме чередования первый рост сохраняет обычную ориентацию, следующий — правую; затем стороны чередуются. Режим always-right оставляет весь остаток на внутренней стороне расширения. Для симуляции Monte Carlo тот же счётчик ориентации переносится в клонируемое состояние, поэтому rollout и реальная политика используют одинаковое правило. Поведение cohort-режима champion оставлено без изменений.

Данные опровергают обе общие версии гипотезы на case 15. Простая ротация хвоста даёт небольшую, но измеримую регрессию; постоянное превращение хвостового остатка во внутренние дыры заметно хуже. Это не исключает условную ориентацию с дополнительным сигналом, но для неё пока нет причинного основания; параметры и дополнительные gates не подбирались.

## Воспроизведение

Сборка — Apple Clang, strict warnings:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/case15_wilderness_polarity/source/wilderness_polarity.cpp -o results/pipes/improvement/case15_wilderness_polarity/bin/wilderness_polarity
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/case15_wilderness_polarity/source/wilderness_right_edge.cpp -o results/pipes/improvement/case15_wilderness_polarity/bin/wilderness_right_edge
```

Парный harness на единственном целевом тесте:

```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name champion_case15 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_wilderness_polarity/tests --out results/pipes/improvement/case15_wilderness_polarity/runs/champion_case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_wilderness_polarity/bin/wilderness_polarity --name alternating_wilderness_polarity_case15 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_wilderness_polarity/tests --out results/pipes/improvement/case15_wilderness_polarity/runs/candidate_case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_wilderness_polarity/bin/wilderness_right_edge --name right_edge_wilderness_case15 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_wilderness_polarity/tests --out results/pipes/improvement/case15_wilderness_polarity/runs/right_edge_case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

## Артефакты и целостность

`comparison.csv` содержит попарные метрики; raw outputs и harness summaries сохранены в `runs/`. Хэши всех исходников, бинарников, входа, интерактора, frozen final и canonical source — в `manifest.json`. Frozen final и canonical source не менялись. Сайт и Docker не использовались.
