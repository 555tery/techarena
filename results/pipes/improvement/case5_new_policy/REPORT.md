# Pipes: case 5 foreign-gap borrowing experiment

## Решение и результат

**Screen провален; кандидат отклонён.** Проверил причинную политику временного заимствования внутренней свободной ячейки, принадлежащей другой когорте. В режиме `parityCohortMode` она рассматривает такую ячейку только тогда, когда подходящих ячеек своей когорты и общих ячеек нет, а остаток после размещения короче текущей трубы. Поэтому остаток не вместит ещё одну трубу текущей длины. Новое правило синхронно добавлено в живой allocator и его ограниченный MC simulator.

Правило использует только текущую длину, наблюдённое состояние свободных интервалов и уже активированный причинный режим когорты. Оно не читает будущие команды или идентификатор теста. Гипотеза состояла в том, что некоторые внутренние интервалы другой когорты простаивают, хотя их остаток уже бесполезен для текущего режима.

На проверочном screen кейс 5 вырос с **62 760 м** до **63 180 м**: это `+420 м` траншеи и `−0.005385081442018` взвешенного KPI. Кейсы 9 и 15 не изменились. Общий score только трёх проверенных тестов упал с **10.859085056537 / 12** до **10.853699975095 / 12**. Полный Open15 и holdout-v2 не запускались: кандидат не прошёл установленный gate.

## Покейсные результаты

| Тест | Baseline: траншея / KPI | Кандидат: траншея / KPI | Δ траншеи | Δ weighted score | CPU baseline / кандидат | Peak RSS baseline / кандидат | Judge output совпал |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 5 | 62 760 м / 0.810070108349 | 63 180 м / 0.804685026907 | +420 м | −0.005385081442018 | 0.088634 / 0.093799 с | 3.171875 / 3.140625 MiB | нет |
| 9 | 61 960 м / 0.508392511298 | 61 960 м / 0.508392511298 | 0 м | 0 | 0.120926 / 0.117321 с | 3.078125 / 3.046875 MiB | да |
| 15 | 438 920 м / 0.954062243689 | 438 920 м / 0.954062243689 | 0 м | 0 | 1.348980 / 1.326250 с | 5.421875 / 5.468750 MiB | да |

Все шесть запусков получили статус `ok`; ограничение 5 секунд CPU и 256 MiB соблюдено. Case 15 имеет вес 10, кейсы 5 и 9 — вес 1 каждый. Хэши транскриптов, входов и точные числовые строки находятся в [per_case_comparison.csv](per_case_comparison.csv); полные результаты harness сохранены в `runs/`.

## Сопоставление с предыдущими экспериментами

Перед выбором гипотезы прочитаны текущий final и отчёты `case5_next`, `case9_next`, `cohort_mc_ablation`. Они уже проверяли метрики истории слияний, чередование cohort edge, общий пул MC-кандидатов и заимствование свободного хвоста. Текущая проверка отличается тем, что пробует занять **внутренний интервал другой когорты** только при отсутствии своих/общих подходящих интервалов и с ограничением по размеру остатка.

Этот вариант ухудшил целевой case 5 и не дал выигрыша на 9 или 15. Не рекомендую переносить его в final. Это отрицательный результат, а не свидетельство, что все формы ограниченного заимствования чужих интервалов бесполезны.

## Хэши и сборка

- Baseline: копия `results/pipes/final/solution.cpp`, source SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`; binary SHA-256 `2ca3e2a5617bd9f98e4836d8fefdb272779c71b297c42a9577b054882c270ea9`.
- Candidate: [borrow_dead_residual.cpp](src/borrow_dead_residual.cpp), source SHA-256 `1f904711822d1d645847639d7fc0057367c3e3bfc3e2486b2bd2932e6dd7ccc7`; binary SHA-256 `1aef35dc241352aee5dd1d9bb0dc36cc2b8029904a2386c9ee18b0f11bf77062`.
- Компилятор: Apple clang 17.0.0, arm64; флаги `-O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic`; обе строгие сборки прошли.
- Официальный interactor binary SHA-256 `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`; harness SHA-256 `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d`.
- Входы: case 5 `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b`; case 9 `cfb711efa3a9ccccc17e7170fc7c2ea19c12ed45b789da3a4b2c80750d7ca128`; case 15 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`.
- `src/pipes.cpp` не изменён; его SHA остался `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`. Final-файл также оставлен без изменений.

## Точные команды воспроизведения

Сборки:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case5_new_policy/src/current_final.cpp -o results/pipes/improvement/case5_new_policy/bin/current_final
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case5_new_policy/src/borrow_dead_residual.cpp -o results/pipes/improvement/case5_new_policy/bin/borrow_dead_residual
```

Harness screen:

```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_new_policy/bin/current_final --interactor results/pipes/final/bin/interactor --tests data/pipes/open/5.in --out results/pipes/improvement/case5_new_policy/runs/base5 --name base-case5 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_new_policy/bin/current_final --interactor results/pipes/final/bin/interactor --tests data/pipes/open/9.in --out results/pipes/improvement/case5_new_policy/runs/base9 --name base-case9 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_new_policy/bin/current_final --interactor results/pipes/final/bin/interactor --tests data/pipes/open/15.in --out results/pipes/improvement/case5_new_policy/runs/base15 --name base-case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_new_policy/bin/borrow_dead_residual --interactor results/pipes/final/bin/interactor --tests data/pipes/open/5.in --out results/pipes/improvement/case5_new_policy/runs/borrow5 --name dead-residual-case5 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_new_policy/bin/borrow_dead_residual --interactor results/pipes/final/bin/interactor --tests data/pipes/open/9.in --out results/pipes/improvement/case5_new_policy/runs/borrow9 --name dead-residual-case9 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_new_policy/bin/borrow_dead_residual --interactor results/pipes/final/bin/interactor --tests data/pipes/open/15.in --out results/pipes/improvement/case5_new_policy/runs/borrow15 --name dead-residual-case15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Hashes and machine-readable result details are also recorded in [manifest.json](manifest.json). No candidate from this experiment was copied to `results/pipes/final/` or submitted to the platform.
