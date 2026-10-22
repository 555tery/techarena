# Case 15: перенос двух архивных политик на frozen final

## Краткий результат

Обе причинные политики перенесены на отдельные копии `results/pipes/final/solution.cpp` и проверены на официальном локальном case 15. Ни одна не улучшила case 15; полный Open15 и holdout-v2 не запускались.

| Вариант | Case 15: траншея | Δ к frozen | KPI | Δ weighted score (вес 10) | CPU / RSS |
|---|---:|---:|---:|---:|---:|
| Frozen baseline | 438,920 м | — | 0.954062244 | — | 2.210 с / 7.391 MiB |
| `adaptive_live_mean_overlay` | 438,920 м | 0 м | 0.954062244 | 0 | 1.092 с / 9.453 MiB |
| `transition_model_overlay` | 438,980 м | +60 м | 0.953931842 | −0.001304018 | 1.110 с / 9.000 MiB |

Все прогоны получили `ok`; лимиты не превышены.

## Что было перенесено

- **Adaptive live-mean sticky mode.** Same-length placement run от 32 запросов включает sticky/segregated mode, когда размер входящей трубы относительно текущего среднего live-размера не выше 2.1; режим выключается на отношении 2.4. В режиме используется остаток предыдущего размещения для трубы того же размера и чередуется край по PID parity. В overlay триггер не читает номер теста или абсолютную позицию команды. Архивная матрица приписывает бинарнику `adaptive_live_mean` 438,360 м на case 15, но текущий исходник и старый бинарник расходились: строгая свежая сборка исходника давала 438,920 м. Перенесённая причинная логика также дала 438,920 м, поэтому старый per-case выигрыш не удалось воспроизвести из проверяемого исходника.
- **Transition-model-v1.** По последним 128 переходам между последовательными положительными длинами прогнозируется следующая длина, если уникальный лидер имеет support ≥4 и долю ≥80%. Выбирается свободный промежуток, сохраняющий этот размер после текущей трубы, если цена остатка увеличивается не более чем на 40 м. В архивном full-Open15 matrix этот алгоритм был per-case winner для **case 7**, а не case 15; на case 15 он проигрывал frozen на 2,600 м. Перенос на текущий frozen final проиграл на 60 м.

Это не портирование старых итоговых транскриптов: оба кандидата собраны из frozen-final source с добавлением соответствующего причинного правила. Ни один не использует test ID.

## Воспроизведение

Из корня `/Users/555tery/techarena`:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/archive_transfer/source/adaptive_live_mean_overlay.cpp -o results/pipes/improvement/case15_fast_candidates/archive_transfer/bin/adaptive_live_mean_overlay
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/archive_transfer/source/transition_model_overlay.cpp -o results/pipes/improvement/case15_fast_candidates/archive_transfer/bin/transition_model_overlay
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_fast_candidates/archive_transfer/bin/adaptive_live_mean_overlay --name adaptive_live_mean_overlay --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_fast_candidates/tests --out results/pipes/improvement/case15_fast_candidates/archive_transfer/runs/adaptive_live_mean_overlay --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_fast_candidates/archive_transfer/bin/transition_model_overlay --name transition_model_overlay --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_fast_candidates/tests --out results/pipes/improvement/case15_fast_candidates/archive_transfer/runs/transition_model_overlay --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Папка `tests/` — та же изолированная копия официального `15.in`, что и в родительском experiment.

## SHA-256

| Артефакт | SHA-256 |
|---|---|
| Frozen final source | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` |
| Canonical `src/pipes.cpp` (не менялся) | `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8` |
| Case 15 input | `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353` |
| Interactor | `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a` |
| Historical adaptive policy source | `32ee2907511918b0b5cf174fd67786557855a04f70814d2365b673c05e86da6a` |
| Historical adaptive policy base | `277eda6f269127c62ff27edd0f5fe5377438030c747b2ea8180ee126cfcddcc0` |
| Historical transition-model source | `88d8283ecb14e3f1b97a9ca479f6780a4eae602a8f56ce9864ff79553e70fe9b` |
| Adaptive overlay source / binary | `1f9d5529681eeee8ad4742971b13430eea8aaf689f015a0f7b85e90011f7b291` / `7a0f05b31759ce4408177e1fa2b75a19c7d1957582457d51f6ce3b1803a2f475` |
| Transition overlay source / binary | `9f268690081e036a6d8eee52349c09a70f4f09961b7a640bcd8d76f1dc8a3728` / `4eb3ed5ffdcf4fb3872914d3add34d684f34bb2d30f9fb461a61099d710564da` |

Подробные harness-строки сохранены в `runs/*/cases.csv`; проверка ограничена case 15.

## Два новых правила по трассе case 15

Проверены два отдельных механизма, использующих только прошлые положительные длины:

- **Pair-class reserve.** По окну из 128 переходов прогнозируются два следующих размера (support ≥4, уникальный лидер, confidence ≥80%). Если лучший текущий gap не оставляет место под оба размера, кандидат ищет минимальный gap, сохраняющий суммарный остаток пары; дополнительный slack ограничен 40 м.
- **Pair-class split.** При том же прогнозе выбирается gap с местом под оба размера, затем текущая труба укладывается внутри него так, чтобы слева остался первый прогнозируемый размер, а справа — не меньше второго. Это меняет геометрию границ, а не только адрес выбранного края.

| Вариант | Case 15: траншея | Δ к frozen | KPI | Δ weighted score (вес 10) | CPU / RSS |
|---|---:|---:|---:|---:|---:|
| Frozen baseline | 438,920 м | — | 0.954062244 | — | 2.210 с / 7.391 MiB |
| `pair_class_reserve` | 438,920 м | 0 м | 0.954062244 | 0 | 1.148 с / 9.609 MiB |
| `pair_class_split` | 438,920 м | 0 м | 0.954062244 | 0 | 1.132 с / 9.469 MiB |

Обе версии выдали **те же координаты всех 130,255 размещений**, что и frozen baseline. Причина видна в префиксе case 15: в том же скользящем окне возникли только 2 валидных прогноза следующей длины и ни одного валидного двухшагового прогноза. Следовательно, новые правила на этой трассе ни разу не получили пару классов для работы. Полный Open15 и holdout-v2 не запускались.

Компиляция и локальная проверка только case 15:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/archive_transfer/source/pair_class_reserve.cpp -o results/pipes/improvement/case15_fast_candidates/archive_transfer/bin/pair_class_reserve
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/archive_transfer/source/pair_class_split.cpp -o results/pipes/improvement/case15_fast_candidates/archive_transfer/bin/pair_class_split
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_fast_candidates/archive_transfer/bin/pair_class_reserve --name pair_class_reserve --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_fast_candidates/tests --out results/pipes/improvement/case15_fast_candidates/archive_transfer/runs/pair_class_reserve --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_fast_candidates/archive_transfer/bin/pair_class_split --name pair_class_split --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_fast_candidates/tests --out results/pipes/improvement/case15_fast_candidates/archive_transfer/runs/pair_class_split --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

SHA-256 новых артефактов: `pair_class_reserve.cpp` — `891255e01f0a23e143b40213fd02bd6c3ecb8e56c33b628609d48c7591d3b0ba`; binary — `300a0d6244f2d2580b4171dcaf9f30cd1319b7b4a439553bbb010536cb211d88`. `pair_class_split.cpp` — `4c71a8bdb15dc8d485aacdce6c18eb314e4ecf1a926ec63a4755baca9e1768f2`; binary — `74c05960c03c73d7aefc8597a50020728dc3e9cf0cd99dd9a1807dbb31d84a79`.
