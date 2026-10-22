# Результаты ограниченного sweep для regime gate

## Краткий вывод

Проверены три порога автокорреляционного `lift`: 0.15, 0.20 и 0.25. На официальных открытых тестах лучший кандидат среди gate-вариантов — `.20`/`.25`: оба дали одинаковые результаты, **28.864355346/32.1**, все 15 кейсов прошли. Это на **+0.488517746** выше P4, но на **−0.075103594** ниже S50.

На уже просмотренной development synthetic suite оба варианта `.20` и `.25` в точности совпали с P4 по всем 10 итоговым KPI и длинам траншеи: **8.438372398/10**. S50 получил **8.290179028/10**. Это Pareto-компромисс между двумя известными наборами: gate `.25` улучшает open относительно P4 и сохраняет P4 на этой synthetic suite; S50 имеет более высокий open, но хуже на synthetic. Synthetic suite использовалась при разработке gate и **не является независимой валидацией**. Превосходство на скрытых или новых потоках не установлено.

Для отдельной preregistered validation разумно заморозить `.25`, P4 и S50 как сравниваемые варианты. `.25` выбран только потому, что при равных известных результатах у него более строгий критерий активации, а не потому, что он победил `.20` в измерениях. Подбор параметров на текущем sweep завершён.

## Что делает gate

Gate использует только предыдущие команды вставки и действует только при выборе среди уже подходящих внутренних свободных промежутков. Текущее значение длины трубы в историю попадает после размещения. Удаления не попадают в историю. История содержит не более 128 длин.

1. До накопления 9 вставок применяется P4.
2. В окне находится наиболее частая длина `d`, её доля `p`.
3. Если `p >= 0.65`, demand-aware оценка включается. Если `p < 0.25`, остаётся P4.
4. В промежуточном диапазоне для индикатора `length == d` считается совпадение на лагах 1–8 (только лаги как минимум с 6 парами). Из доли совпадений вычитается ожидаемая доля для независимых наблюдений `p² + (1-p)²`. Gate включается, если хотя бы для одного лага превышение не меньше заданного порога `.15`, `.20` или `.25`.
5. При включённом gate промежуток со slack `r` оценивается как `r * history_size + 50 * count(history lengths > r)` для `1 <= r <= 40`; иначе используется P4 best-fit. Равенство оцениваемых вариантов разрешается в пользу меньшего промежутка, затем меньшего адреса. Выкопка/обработка хвоста остаётся как в P4.

Классификации тестов, номеров кейсов и просмотра будущих команд нет. Поскольку сигнал рассчитывается по ограниченной истории, возможны как ложное включение на случайной последовательности, так и пропуск режима, которому S50 помогает.

## Сравнение результатов

Официальный score — взвешенная сумма KPI, знаменатель для open равен 32.1. Для synthetic suite знаменатель равен 10. Все варианты прошли соответствующие кейсы без protocol error.

| Вариант | Open, 15 кейсов | Δ к P4 | Development synthetic, 10 потоков | Δ к P4 |
|---|---:|---:|---:|---:|
| P4 | 28.375837599 / 32.1 | 0 | 8.438372398 / 10 | 0 |
| S50 | 28.939458940 / 32.1 | +0.563621341 | 8.290179028 / 10 | −0.148193370 |
| Gate `.15` | 28.856701298 / 32.1 | +0.480863698 | 8.422103512 / 10 | −0.016268886 |
| Gate `.20` | 28.864355346 / 32.1 | +0.488517746 | 8.438372398 / 10 | 0 |
| Gate `.25` | 28.864355346 / 32.1 | +0.488517746 | 8.438372398 / 10 | 0 |

### Изменения по отдельным потокам

Для `.25` относительно P4 на open изменились только четыре кейса:

| Кейс | KPI P4 → gate `.25` | Длина траншеи P4 → gate `.25` |
|---:|---:|---:|
| 2 | 0.500000 → 1.000000 | 40 → 20 м |
| 8 | 0.980297 → 0.984468 | 4720 → 4700 м |
| 12 | 0.989286 → 0.991199 | 10360 → 10340 м |
| 13 | 0.967273 → 0.961446 | 3300 → 3320 м |

Остальные 11 open-кейсов совпали с P4. В частности, gate не повторяет весь выигрыш S50 на кейсе 15: у S50 траншея 438500 м против 441520 м у P4, а у gate `.20`/`.25` остаётся 441520 м. Поэтому S50 и gate не доминируют друг друга по двум использованным наборам.

На development synthetic `.20` и `.25` совпали с P4 по всем десяти KPI и траншеям. Наиболее наглядные потери S50 относительно P4: `short_skew_random_50k` — 7480 против 7060 м, `uniform_delete_longest_30k` — 3940 против 2800 м, `uniform_random_50k` — 21100 против 20300 м. Эти synthetic результаты — диагностика уже просмотренных режимов, а не оценка на свежей выборке.

### Ресурсы

Для gate `.25` на open: суммарное CPU solver-процессов 1.449875 с, максимум на одном кейсе 1.022311 с, максимум RSS 5.390625 MiB. На synthetic suite: 1.931794 с суммарного CPU, максимум 0.230951 с на кейсе и 2.296875 MiB максимального RSS. Метрики CPU/RSS относятся к дочернему solver-процессу; wall time включает запуск harness и interactor.

## Воспроизводимость и проверка

Сборка кандидатов выполнялась с такими strict C++20 командами из корня репозитория:

```sh
g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror \
  results/pipes/improvement/regime_gate/regime_gate.cpp \
  -o results/pipes/improvement/regime_gate/binaries/regime_gate_lift015_cxx20

g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror \
  results/pipes/improvement/regime_gate/regime_gate_lift020.cpp \
  -o results/pipes/improvement/regime_gate/binaries/regime_gate_lift020_cxx20

g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror \
  results/pipes/improvement/regime_gate/regime_gate_lift025.cpp \
  -o results/pipes/improvement/regime_gate/binaries/regime_gate_lift025_cxx20
```

Official open runs:

```sh
python3 tools/compare_pipes_binaries.py \
  --solver regime_gate_lift015=results/pipes/improvement/regime_gate/binaries/regime_gate_lift015_cxx20 \
  --solver s50=results/pipes/improvement/strategies/binaries/canonical_recent_unfit_s50_cxx20 \
  --solver policy4=results/pipes/improvement/strategies/binaries/policy4_baseline \
  --tests data/pipes/open \
  --out results/pipes/improvement/regime_gate/reports/open-lift015 \
  --baseline policy4

python3 tools/compare_pipes_binaries.py \
  --solver regime_gate_lift020=results/pipes/improvement/regime_gate/binaries/regime_gate_lift020_cxx20 \
  --solver regime_gate_lift025=results/pipes/improvement/regime_gate/binaries/regime_gate_lift025_cxx20 \
  --solver s50=results/pipes/improvement/strategies/binaries/canonical_recent_unfit_s50_cxx20 \
  --solver policy4=results/pipes/improvement/strategies/binaries/policy4_baseline \
  --tests data/pipes/open \
  --out results/pipes/improvement/regime_gate/reports/open-lift020-025 \
  --baseline policy4
```

Development synthetic runs (suite was already viewed during earlier robustness work and again served as development data for this gate):

```sh
python3 tools/compare_pipes_binaries.py \
  --solver regime_gate_lift015=results/pipes/improvement/regime_gate/binaries/regime_gate_lift015_cxx20 \
  --solver s50=results/pipes/improvement/strategies/binaries/canonical_recent_unfit_s50_cxx20 \
  --solver policy4=results/pipes/improvement/strategies/binaries/policy4_baseline \
  --tests results/pipes/improvement/strategies/robustness_inputs \
  --out results/pipes/improvement/regime_gate/reports/dev-synthetic-lift015 \
  --baseline policy4

python3 tools/compare_pipes_binaries.py \
  --solver regime_gate_lift020=results/pipes/improvement/regime_gate/binaries/regime_gate_lift020_cxx20 \
  --solver regime_gate_lift025=results/pipes/improvement/regime_gate/binaries/regime_gate_lift025_cxx20 \
  --solver s50=results/pipes/improvement/strategies/binaries/canonical_recent_unfit_s50_cxx20 \
  --solver policy4=results/pipes/improvement/strategies/binaries/policy4_baseline \
  --tests results/pipes/improvement/strategies/robustness_inputs \
  --out results/pipes/improvement/regime_gate/reports/dev-synthetic-lift020-025 \
  --baseline policy4
```

| Артефакт | Путь | SHA-256 |
|---|---|---|
| Gate `.15` source | `results/pipes/improvement/regime_gate/regime_gate.cpp` | `444aeb5158cbae414de6558bd58ecb19169cb78bfb42334ac72f606f42961aff` |
| Gate `.20` source | `results/pipes/improvement/regime_gate/regime_gate_lift020.cpp` | `186b50f5879b9c51584ce545a5930ddeb4f091a12900403a786adee3c1eca5bb` |
| Gate `.25` source | `results/pipes/improvement/regime_gate/regime_gate_lift025.cpp` | `892eb04ecddd187612efecd287da548eb26dd5201f2d912c452fb1d7a0a266c2` |
| Gate `.15` binary | `results/pipes/improvement/regime_gate/binaries/regime_gate_lift015_cxx20` | `7ccb075937e8d7a47785371946b20a7a2c91179dec5a43b9bdeefcb3967ca231` |
| Gate `.20` binary | `results/pipes/improvement/regime_gate/binaries/regime_gate_lift020_cxx20` | `f7aa17c504cb9324ff9339d35755e08e6ba88bc090faa83d100aa746d24de1e2` |
| Gate `.25` binary | `results/pipes/improvement/regime_gate/binaries/regime_gate_lift025_cxx20` | `b03e72a6f321219789f1bbb56cab43ede998ff56b4a78d654052cb602cd34480` |
| P4 source | `results/pipes/improvement/strategies/policy4_baseline.cpp` | `a524195683fc0fb2aa4815faed12a0fea37df66dc6c4bdb1ffbf53de8d0e8ae3` |
| P4 binary | `results/pipes/improvement/strategies/binaries/policy4_baseline` | `fee43fb4630cd2a09ce58eb112de6e213bf12d4c619bb4a98ca27bcecd79f3db` |
| S50 source | `results/pipes/improvement/shrinkage/source/recent_unfit_s50.cpp` | `002f5bb77c131f829fc5ccfb0a310204113b6d8164d09d8dc7ed001e96833095` |
| S50 binary | `results/pipes/improvement/strategies/binaries/canonical_recent_unfit_s50_cxx20` | `02afda1259200b6a692c1c7a9232289979aba7a288c3a4f4fb1eb96eb9893acf` |
| Interactor | `tools/interactor` | `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a` |
| Comparison harness | `tools/compare_pipes_binaries.py` | `2a84a5973fb446ea0dab18bbacb62a9b44e1ca52b0e09eb23766c6979c694eee` |

Манифесты сравнений в JSON содержат SHA-256 каждого входного `.in` файла, interactor hash, бинарные хеши, итоговый score, CPU/RSS и статус каждого запуска. Подробные результаты по кейсам находятся в `per-case-comparison.csv` и в отдельных `cases.csv`; сами журналы запусков сохранены рядом.

- Open `.15`: `results/pipes/improvement/regime_gate/reports/open-lift015/comparison.json`
- Open `.20`/`.25`: `results/pipes/improvement/regime_gate/reports/open-lift020-025/comparison.json`
- Synthetic `.15`: `results/pipes/improvement/regime_gate/reports/dev-synthetic-lift015/comparison.json`
- Synthetic `.20`/`.25`: `results/pipes/improvement/regime_gate/reports/dev-synthetic-lift020-025/comparison.json`
