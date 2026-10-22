# Case 9: geometric size-run alignment

## Итог

Лучший clean-кандидат — причинное выравнивание остатка gap по сетке предсказанного следующего размера трубы. Он сократил case 9 с **61 960 до 61 760 м** и поднял Open15 с **29.789717928594 до 29.791364277400** (`+0.001646348806`). На Open15 изменился только case 9; cases 5, 13 и 15, а также остальные 11 тестов совпали с frozen final по длине траншеи и выходной трассе. Цель 30.3 не достигнута.

## Причинное правило

Solver наблюдает последовательные runs размеров только по уже размещённым трубам. Прогноз активируется, если три последних runs имеют не менее 46 размещений каждый, размеры строго растут и совместимы с одной целочисленно округлённой геометрической последовательностью. Если размеры равны `older, previous, current`, проверяется

```text
2 * abs(current * older - previous * previous) <= older
```

Затем прогнозируется `round(current * previous / older)`; значения должны быть больше `current` и не больше 40. PID, номер теста и будущие команды не используются. При активном длинном run выбирается край подходящего gap, который оставляет остаток со стартовой координатой ближе к кратному прогнозируемой длине. При равенстве сохраняется исходное решение по когорте.

В первом изменившемся состоянии case 9: следующая труба имеет PID 2048 и длину 4; предыдущие runs — 1, 2, 4, текущий run уже содержит не менее 46 размещений, прогноз — 8. Для gap `[980,986)` исходный высокий край оставил остаток со стартом 980 (расстояние 4 до кратного 8); новый низкий край оставил остаток со стартом 984 (расстояние 0). Это диагностировано debug-сборкой; в проверяемом кандидате отладочного вывода нет.

## Проверки

| Вариант | Open case 9 | Open15 | Результат |
|---|---:|---:|---|
| Frozen final | 61 960 м; KPI 0.508392511298 | 29.789717928594 | baseline |
| Двойной край в MC shortlist | 61 960 м | не запускался | case 9 побайтно совпал с baseline |
| Инверсия cohort lanes | 62 100 м; KPI 0.507246376812 | не запускался | хуже baseline на case 9 |
| Alignment, узкий предиктор | 61 760 м; KPI 0.510038860104 | 29.791364277400 | +0.001646348806; только case 9 изменился |
| Alignment, общий геометрический предиктор | — | 29.791364277400 | тот же Open15 результат; остальные кейсы не изменились |

У узкого alignment-кандидата отдельно проверен holdout-v2: **5.135264324280**, без изменения относительно baseline; все 12 judge output совпали побайтно. Обобщённый кандидат на holdout-v2 не запускался. Это ограниченный положительный сигнал одного Open-теста, не подтверждение обобщения.

## Артефакты и воспроизводимость

- Clean source-кандидат: [`source/geometric_run_alignment.cpp`](source/geometric_run_alignment.cpp), SHA-256 `4d0eada1669b9a757b2d09bc82f46b3b7ef60f95f73f5f4e6d0c77ca00d95a8d`.
- Бинарник: [`build/geometric_run_alignment`](build/geometric_run_alignment), SHA-256 `65657bf43a20850e0074ad4083def127637a69cba5166b3176b038d1436622ec`.
- Frozen source до/после: `results/pipes/final/solution.cpp`, SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Canonical source до/после: `src/pipes.cpp`, SHA-256 `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.
- Подробная таблица score, траншей и judge-output hashes: [`per_case_comparison.csv`](per_case_comparison.csv). Команды и test hash: [`manifest.json`](manifest.json).
- Open15: 15/15; максимум на этом прогоне — 0.950605999 s CPU и 8.1875 MiB RSS, в пределах заданных лимитов.

Сборка:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
  results/pipes/improvement/case9_continuation/source/geometric_run_alignment.cpp \
  -o results/pipes/improvement/case9_continuation/build/geometric_run_alignment
```

Локальный Open15 harness:

```sh
python3 tools/pipes_harness.py \
  --solver results/pipes/improvement/case9_continuation/build/geometric_run_alignment \
  --interactor results/pipes/final/bin/interactor \
  --tests data/pipes/open \
  --out results/pipes/improvement/case9_continuation/runs/geometric_run_alignment-open15 \
  --name geometric-run-alignment-open15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Кандидат не продвигался в frozen final, платформа и Docker не использовались.
