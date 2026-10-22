# Case 5: повторный запуск lane-политики на длинных size-блоках

## Гипотеза

В кейсе 5 поток состоит из 40 блоков по 125 установок одинаковой длины (длины 1–40), после каждого блока удаляются 63 трубы с чередующимися PID. В frozen solver обнаружение плавного роста трёх размеров навсегда включает `runLeftDisabledBySmoothTrend`; из-за этого поздние длинные однородные блоки теряют lane-размещение.

Проверен узкий механизм: разрешать cohort lanes после фактически наблюдённых 46 или 48 подряд одинаковых размещений, даже если trend-флаг уже установлен. В обратной ориентации cohort 0 (чётная occurrence parity, удаляемая в этом потоке) идёт с высокого края интервала, cohort 1 — с низкого. Это причинное правило, не использующее номер теста или будущие команды. Оно не гарантирует, что cohort 0 будет удаляться в других потоках.

## Быстрый screen на case 5

| Вариант | Порог | Ориентация | Траншея | KPI | Δ траншеи к frozen |
|---|---:|---|---:|---:|---:|
| Frozen final | 46 | действующая | 62 760 м | 0.810070108349267 | — |
| Re-arm | 46 | действующая | 63 880 м | 0.795867251095805 | +1 120 м |
| Re-arm | 48 | действующая | 63 960 м | 0.794871794871795 | +1 200 м |
| Re-arm | 46 | обратная | **62 600 м** | **0.812140575079872** | **−160 м** |

Обычное повторное включение lanes ухудшает case 5. Выигрыш появился только при обратной ориентации cohort; его размер равен 160 м и не превышает сигнал из предыдущей hindsight-диагностики.

## Проверка лучшего варианта

`rearm_reverse_cohort.cpp` прошёл локальный Open15: **29.790642260839 / 32.1**, против frozen **29.789717928594**; разница **+0.000924332245**.

| Case | Frozen: траншея / KPI | Candidate: траншея / KPI | Δ траншеи |
|---:|---:|---:|---:|
| 5 | 62 760 м / 0.810070108349 | 62 600 м / 0.812140575080 | −160 м |
| 9 | 61 960 м / 0.508392511298 | 62 100 м / 0.507246376812 | +140 м |
| Остальные 13 | без изменений | без изменений | 0 м |

Judge transcripts дополнительно различаются в cases 8, 13 и 14, но траншея и KPI там совпадают. Cases 1–4, 6–7, 10–12 и 15 совпали с frozen по транскриптам.

На holdout-v2 score точно совпал: **5.135264324280 / 12**; все 12 judge transcripts побайтно совпали с frozen. Открытый прирост мал, состоит из обмена 160 м выигрыша в case 5 против 140 м регрессии в case 9 и не подтверждён holdout-выигрышем. Кандидат остаётся исследовательским; frozen final и canonical source не менялись.

Все 15 Open и 12 holdout запусков завершились `ok`. Максимальные ресурсы candidate на Open15: 0.947320 CPU-с и 8.109375 MiB RSS; на holdout-v2: 0.247372 CPU-с и 4.109375 MiB RSS. Проверка проведена локально на macOS, Apple Clang 17.0.0; сайт и Docker не использовались. Linux/GCC отдельно не проверялся.

## Артефакты и hashes

- Frozen source: `results/pipes/final/solution.cpp`, SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Frozen binary: SHA-256 `dabb6910bde7550dbf4ab03d6d7b450d0a91f53a90dc06e52d6b271c8602000c`.
- Лучшая версия: [`src/rearm_reverse_cohort.cpp`](src/rearm_reverse_cohort.cpp), SHA-256 `88cdde2fe63a3681292ff1f06c201a087707379fa7d4060b462beb558ffa0ba4`.
- Лучшая версия binary: `bin/rearm_reverse_cohort`, SHA-256 `3dffb3017dc3b3447963264be4195b641ddc7240460d174123b748e0eb132d1b`.
- Case 5 input SHA-256 `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b`.
- Interactor SHA-256 `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`; harness SHA-256 `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d`.
- Полные покейсовые данные: [`Open15 cases.csv`](runs/reverse_open15/cases.csv), [`holdout-v2 cases.csv`](runs/reverse_holdout_v2/cases.csv), [`screen case 5 cases.csv`](runs/reverse5/cases.csv).
- Hashes summary/CSV/report приведены в [`SHA256SUMS.txt`](SHA256SUMS.txt).

## Воспроизведение

Сборка строгими флагами: `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic`.

Локальные прогоны выполнялись `tools/pipes_harness.py` с frozen interactor, лимитами 5 CPU-с и 256 MiB: сначала каждый вариант на `data/pipes/open/5.in`, затем лучший на `data/pipes/open` и `data/pipes/synthetic/final-holdout-v2`.
