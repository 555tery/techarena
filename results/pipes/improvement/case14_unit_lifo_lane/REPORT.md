# Case14: единая сторона для длинного LIFO-run из труб 1 м

**Решение: no-go.** Гипотеза привязана к case14: в потоке 22 316 из 24 530 размещений имеют длину 1 м; 666 удалений, а среди последних 64 наблюдавшихся удалений после стабилизации все 64 были из новейшей пятой части PID. Проверенный кандидат заменяет чередование двух краёв одной непрерывной стороной только после такого сигнала и во время длинной серии труб 1 м. На целевом case14 итог не изменился: **37 820 м, KPI 3.987731359069** у baseline и кандидата. Open15 не запускался.

Case13 не запускался повторно: его trace-событие с сохранением 21-метровой дыры и пять близких reservation-вариантов уже разобраны в [предыдущем аудите расширений](../case13_expansion_review/REPORT.md), где ни один не улучшил исходный KPI. В доступных материалах не обнаружилось дополнительного причинного признака, который позволил бы проверить там новый, не дублирующийся вариант.

## Трасса и причинная гипотеза

По сохранённому текущему champion-транскрипту восстановлены последние 50 расширений. На последних десяти расширениях внутренние свободные интервалы не превышали 8 м; хвост перед запросом составлял 0–16 м при входящих трубах 15–20 м. Это непосредственная причина, по которой новый запрос не помещался, но не объяснение, какие ранние решения создали фрагментацию.

Сигнал нового правила стал доступен для очередной единичной трубы на операции 17 845. Транскрипт solver изменился начиная с операции 17 859: кандидат реально изменил размещения в активных единичных сериях. На case14 суммарное число расширений осталось 1 824, а число добавленных секций — 1 891; длина траншеи не изменилась. Из 4 473 изменённых ответов лишь четыре различались по числу добавленных секций на соответствующей операции, без суммарной экономии.

Это правило отличается от H32 survival-hazard: оно не прогнозирует индивидуальную жизнь трубы или соседей, а отменяет двухстороннее чередование адресов для однородной серии длины 1 после наблюдаемого LIFO-сигнала. Но целевой trace не подтверждает, что такая перестановка создаёт полезные крупные интервалы.

## Локальные результаты

| Поток | Baseline траншея / score | Кандидат траншея / score | Δ траншеи | Δ score | Статус |
|---|---:|---:|---:|---:|---|
| Официальный case14, вес 4 | 37 820 м / 3.987731359069 | 37 820 м / 3.987731359069 | 0 м | 0 | 1/1 |
| Fresh: LIFO release 10 → запрос 10 | 4 000 м / 1.000000000000 | 4 000 м / 1.000000000000 | 0 м | 0 | 1/1 |
| Fresh: LIFO → FIFO shift | 4 020 м / 0.995024875622 | 4 000 м / 1.000000000000 | −20 м | +0.004975124378 | 1/1 |
| Fresh: LIFO → random shift, seed 2026101702 | 4 020 м / 0.995024875622 | 4 020 м / 0.995024875622 | 0 м | 0 | 1/1 |
| Fresh: random control, seed 2026101703 | 4 020 м / 0.995024875622 | 4 020 м / 0.995024875622 | 0 м | 0 | 1/1 |

Синтетическая выгода появилась только в одном специально заданном phase-shift потоке; чистый LIFO witness нейтрален, а случайные варианты также нейтральны. Это недостаточное основание для Open15 при нулевом эффекте на целевом кейсе. Максимальный solver CPU на case14 — 0.147209 с, RSS — 3.906 MiB; на синтетиках — 0.035991 с и 2.438 MiB. Все запуски прошли официальный локальный interactor, лимиты 5 с / 256 MiB не превышены.

## Команды воспроизведения

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/case14_unit_lifo_lane/source/champion_base.cpp -o results/pipes/improvement/case14_unit_lifo_lane/bin/baseline
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/case14_unit_lifo_lane/source/single_lifo_unit_lane.cpp -o results/pipes/improvement/case14_unit_lifo_lane/bin/single_lifo_unit_lane
python3 tools/pipes_harness.py --solver results/pipes/improvement/case14_unit_lifo_lane/bin/baseline --interactor results/pipes/final/bin/interactor --tests data/pipes/open/14.in --out results/pipes/improvement/case14_unit_lifo_lane/runs/baseline_case14 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case14_unit_lifo_lane/bin/single_lifo_unit_lane --interactor results/pipes/final/bin/interactor --tests data/pipes/open/14.in --out results/pipes/improvement/case14_unit_lifo_lane/runs/candidate_case14 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 results/pipes/improvement/case14_unit_lifo_lane/synthetic/generate.py
python3 tools/pipes_harness.py --solver results/pipes/improvement/case14_unit_lifo_lane/bin/baseline --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case14_unit_lifo_lane/synthetic --out results/pipes/improvement/case14_unit_lifo_lane/runs/baseline_synthetic --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case14_unit_lifo_lane/bin/single_lifo_unit_lane --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case14_unit_lifo_lane/synthetic --out results/pipes/improvement/case14_unit_lifo_lane/runs/candidate_synthetic --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Покейсовые метрики, hashes исходников, входов, транскриптов и сводок находятся в [`per_case.csv`](per_case.csv) и [`manifest.json`](manifest.json). `results/pipes/final/solution.cpp` и `src/pipes.cpp` не менялись; сайт и Docker не использовались.

