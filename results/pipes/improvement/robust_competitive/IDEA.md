# Robust / competitive online allocation — no-go

## Решение

Не найдено отдельного причинного правила для реализации. Одношаговый minimax оценивает те же gaps/tail, многократный minimax — adversarial-вариант rollout/beam. Код, сборки и тесты не запускались.

## Пересечение с проверенными семействами

| Идея | Почему не новая | Покрытие |
|---|---|---|
| Худший следующий размер / capacity profile | State-potential по текущим дыркам и tail с иной агрегацией. | [Gap/tail](../policy_tail/REPORT.md), [potential](../potential/REPORT.md) |
| Minimax на несколько операций | Max вместо среднего при тех же действиях/состояниях; удаление любого PID раздувает ветвление. | [MC/lookahead](../max_open_lookahead/REPORT.md), [equal-gap](../case15_equal_gap_diversity/REPORT.md), [beam](../beam_diagnosis/REPORT.md) |
| Adversarial lifetime | Будущая длительность неизвестна; lifetime/hazard уже тестировались. | [Lifetime](../lifetime/REPORT.md), [hazard](../survival_hazard/REPORT.md) |
| DSA coloring | Отдельная архитектура не исключена, но полного текста/точного алгоритма для port-а нет. Size-cohort/segregation — лишь близкие аналоги, не доказанная эквивалентность. Competitive bound сама по себе не обещает выигрыш Pipes KPI. | [Segregation](../segregated_allocator/final_architecture_check/REPORT.md), [frozen solver](../../final/README.md) |

## Граница переноса теории

Локальная [литературная сводка](../literature/REPORT.md) рассматривает DSA bounds по объёму адресного пространства относительно offline-решения / пикового live-набора. Pipes оценивает конечную занятую длину относительно необратимого high-water траншеи с шагом 20 м; длины труб 1–40 м, будущие удаления неизвестны. Поэтому DSA bound не ранжирует политики на фиксированных потоках и не гарантирует меньше секций. [SIAM-аннотация Luby–Naor–Orda](https://epubs.siam.org/doi/10.1137/S089548019325647X) сообщает, что coloring-алгоритм достигает competitive ratio First Fit, но не о преимуществе на Pipes. No-go ограничен просмотренными материалами; он не доказывает невозможность нового алгоритма.

Проверены `wiki/research/Index.md`, `wiki/research/Methods.md`, а также отчёты по voluntary dig, interior placement и cyclic next-fit. Платформа и Docker не использовались.

## Хеши контрольных исходников

- Frozen final `results/pipes/final/solution.cpp`: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Canonical `src/pipes.cpp`: `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.
- Оба SHA перепроверены; исходники не менялись.
