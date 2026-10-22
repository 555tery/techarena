# Run-48: fresh synthetic paired check

## Краткий результат

Сравнены frozen final и сохранённый run-48 на 8 заранее зафиксированных synthetic streams (468,000 операций суммарно). На всех 8 streams совпали KPI, длина траншеи и judge output побайтно. Score delta равен 0. Это нейтральный результат на небольшой выборке, а не подтверждение обобщения на закрытые тесты.

Набор зафиксирован до запуска solver: разные размеры задач, распределения длин труб, удаления random/FIFO/LIFO/shortest/longest, batch-drain режимы и изменения фаз. Сгенерированные SHA-256 не совпали ни с одним из 147 ранее сохранённым `.in` файлов в `data/pipes` и `results/pipes` (82 уникальных hashes). Параметры после результатов не менялись.

## Per-stream результаты

| Stream (ops) | Режимы длин / удалений по фазам | KPI baseline → run-48 | Δ KPI | Траншея baseline → run-48 (м) | CPU baseline / run-48 (с) | RSS baseline / run-48 (MiB) | Выходы |
|---|---|---:|---:|---:|---:|---:|---|
| `large_four_phase_shift` (180,000) | 0-45000: long-heavy, churn=0.30, delete=random, batch=720, repeat=0.05; 45000-90000: short-heavy, churn=0.56, delete=oldest, batch=360, repeat=0.15; 90000-135000: long-heavy, churn=0.46, delete=newest, batch=600, repeat=0.20; 135000-180000: uniform, churn=0.39, delete=longest, batch=0, repeat=0.00 | 0.865308277027 → 0.865308277027 | +0.000000000000 | 94,720 → 94,720 | 1.701421 / 1.700376 | 4.578 / 4.562 | identical |
| `medium_bimodal_sticky_shortest` (30,000) | 0-30000: bimodal, churn=0.50, delete=shortest, batch=280, repeat=0.78 | 0.873782771536 → 0.873782771536 | +0.000000000000 | 10,680 → 10,680 | 0.307244 / 0.306170 | 3.016 / 3.125 | identical |
| `medium_long_newest` (24,000) | 0-24000: long-heavy, churn=0.45, delete=newest, batch=240, repeat=0.00 | 0.931250000000 → 0.931250000000 | +0.000000000000 | 5,760 → 5,760 | 0.176727 / 0.177807 | 3.297 / 3.406 | identical |
| `medium_uniform_random` (12,000) | 0-12000: uniform, churn=0.38, delete=random, batch=320, repeat=0.00 | 0.465667574932 → 0.465667574932 | +0.000000000000 | 7,340 → 7,340 | 0.089238 / 0.089781 | 2.969 / 3.047 | identical |
| `phase_long_to_short` (70,000) | 0-35000: long-heavy, churn=0.48, delete=oldest, batch=520, repeat=0.08; 35000-70000: short-heavy, churn=0.34, delete=newest, batch=260, repeat=0.20 | 0.212358642973 → 0.212358642973 | +0.000000000000 | 12,380 → 12,380 | 0.501829 / 0.495045 | 4.906 / 4.969 | identical |
| `phase_short_to_long` (40,000) | 0-20000: short-heavy, churn=0.22, delete=random, batch=0, repeat=0.15; 20000-40000: long-heavy, churn=0.58, delete=longest, batch=400, repeat=0.10 | 0.000376992676 → 0.000376992676 | +0.000000000000 | 92,840 → 92,840 | 0.293094 / 0.295809 | 4.203 / 4.250 | identical |
| `small_short_oldest` (2,000) | 0-2000: short-heavy, churn=0.20, delete=oldest, batch=96, repeat=0.00 | 0.409375000000 → 0.409375000000 | +0.000000000000 | 960 → 960 | 0.016968 / 0.016664 | 2.625 / 2.719 | identical |
| `three_phase_mixed_removals` (110,000) | 0-36667: uniform, churn=0.36, delete=random, batch=640, repeat=0.00; 36667-73334: bimodal, churn=0.53, delete=oldest, batch=0, repeat=0.82; 73334-110000: short-heavy, churn=0.45, delete=shortest, batch=360, repeat=0.12 | 0.562393767705 → 0.562393767705 | +0.000000000000 | 14,120 → 14,120 | 0.789997 / 0.797552 | 5.500 / 5.500 | identical |

Сумма KPI по этим восьми входам (weight=1 каждый): baseline 4.320513026848, run-48 4.320513026848, Δ +0.000000000000. Максимальная CPU: 1.701421s / 1.700376s; максимальный RSS: 5.500 / 5.500 MiB. Все варианты уложились в 5s CPU / 256 MiB.

## Состав fixed set

Все потоки детерминированы seed и строятся по ходу генерации из активного состояния и текущей фазы. Границы фаз заданы заранее по номеру операции; поток команд полностью передаётся обоим solver одинаково.

## Hashes и воспроизводимость

Полные SHA-256 исходников, бинарников, harness, interactor, генератора, входов и judge outputs — в [`comparison.json`](comparison.json); рецепты и входные hashes — в [`input_manifest.json`](input_manifest.json). Полные логи official harness лежат в [`runs/`](runs/). Frozen final и canonical source не менялись; платформа не использовалась.

Run-48 меняет только `kSameLengthRightRun: 46 → 48`. Проверенный SHA frozen final: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`; canonical: `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`; run-48: `95d662fff63be90146b5ebddeff43ce4b551f34b8de5351513ba33f53be55b39`.

### Ограничение вывода

Отсутствие регрессий на восьми детерминированных потоках — узкая проверка устойчивости. Она не доказывает, что малый выигрыш Open15 переносится на скрытые данные; выборка мала, и большинство текущих алгоритмических состояний/режимов может не покрывать неизвестные распределения.
