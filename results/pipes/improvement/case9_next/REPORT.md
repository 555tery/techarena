# Pipes: изолированная проверка cohort-lanes для case 9

**Promotion update:** этот exact source позже установлен как final; актуальные build, open15 и holdout-v2 результаты см. в [final README](../../final/README.md).

## Идея

В ветке уже существующего причинного детектора длинной серии труб одного размера, направление выбора края чередуется по локальному порядку размещений труб этого размера (`sizeCohort`): чётная когорта — левый край, нечётная — правый. Детектор опирается только на уже наблюдённый поток. В этой ветке решение не использует PID parity, предсказание удалений или будущие команды. Изменение синхронно внесено в rollout simulation и live allocator. Это отдельная гипотеза, не PID-parity preprobe.

## Проверка

Сравнение выполнено с текущим `results/pipes/final/solution.cpp`, source SHA-256 `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`. Кандидат source SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`. Кандидат бинарь SHA-256 `c5c781b3b74c5e89f7fc78d333529e320066be314227d809e583569a5e885de4`. Компиляторные флаги и команды запуска полностью записаны в `manifest.json`.

| Набор | Baseline | Cohort-lanes | Изменение | Валидность |
|---|---:|---:|---:|---:|
| Open-15, весовая сумма | 29.785293754007 / 32.1 | 29.789717928594 / 32.1 | +0.004424174587 | 15/15 |
| Holdout-v2, сумма | 5.135264324280 / 12 | 5.135264324280 / 12 | +0.000000000000 | 12/12 |

Open-15 изменился только в случаях: 5: 62800→62760 м (-40 м), 9: 62440→61960 м (-480 м). Для остальных 13 open-кейсов метры траншеи совпали. На holdout-v2 все 12 judge outputs побайтно совпадают между baseline и candidate; оценка не изменилась.

Изолированный повтор Open-15 совпал по test/judge-output/stderr hashes с исходным полным запуском: baseline 15/15, candidate 15/15.

Максимум по 15 open кейсам: solver CPU baseline 0.998420 с, candidate 0.999272 с; peak RSS baseline 9.547 MiB, candidate 6.844 MiB. По holdout-v2 максимумы: solver CPU baseline 0.421964 с / candidate 0.425731 с; solver RSS baseline 4.125 MiB / candidate 4.078 MiB. Дополнительно, максимум CPU interactor: open-15 1.457415/1.457983 с (baseline/candidate), holdout-v2 0.699633/0.707591 с; максимум RSS interactor: open-15 9.438/6.438 MiB, holdout-v2 5.703/5.125 MiB. Максимальное wall orchestration время: open-15 7.043/7.117 с, holdout-v2 9.187/9.259 с. Лимиты 5 секунд solver CPU и 256 MiB соблюдены всеми запусками.

## Артефакты и вывод

- Per-case сравнение, включая input/output hashes и ресурсы: `per_case_comparison.csv`.
- Полный manifest команд, хэшей, per-case результатов и исходных данных: `manifest.json`.
- Повторные исходные результаты: `open15/baseline-repeat/`, `open15/size-cohort-lanes-repeat/`; holdout: `holdout-v2/`.
- Финальный и canonical исходники не редактировались; кандидат не загружался на платформу и не продвигался в final.
- Это небольшое улучшение на открытом наборе (+0.004424174587) и нейтральный holdout. Доказательств улучшения скрытых тестов или лидерства нет; рекомендовать замену final только на этом основании нельзя.

Хэш этого отчёта фиксируется полем `report_sha256` в `manifest.json`.
