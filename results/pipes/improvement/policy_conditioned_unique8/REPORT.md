# Policy-conditioned unique-8 — protocol stop

## Итог

**Кандидат не квалифицирован; ветка остановлена по заранее заданным gates.** Получены 16 из 18 пар. Последние два потока — 200k long-heavy с удалениями oldest и newest — не запускались. Bootstrap по неполному набору не рассчитывался и не используется как свидетельство качества.

Два независимых условия уже нарушены:

- Для short-heavy/200k ΔKPI равны −0.001931791 (random), −0.001131822 (oldest) и 0 (newest): две регрессии и одно равенство; среднее −0.001021204.
- На 200k long-heavy/random транскрипт кандидата принят (200001 ответ), но CPU составил 6.145912 s, что превышает и safe gate 4.50 s, и лимит решателя 5 s. RSS — 35.41 MiB.

Максимумы среди 16 пар: 6.145912 s CPU и 35.41 MiB RSS; один CPU-limit violation, нарушений памяти нет. Частичные равновесные средние по 16 потокам: ΔKPI +0.000895925, Δtrench +5.0 m. Это только описательные значения: две пары не запускались, доверительные интервалы не вычислялись.

## Что проверено

- Требование selector: не менее 8 точных уникальных последовательностей из 16 наблюдённых сценариев. Остальные пороги и политика заморожены.
- Из 18 свежих потоков с уникальными seed завершены и приняты 16 baseline/candidate пар. Две незапущенные строки отмечены `not_run` в `validation/per_case.csv`.
- После прежнего Docker `unexpected EOF` восстановление шло строго последовательно: из пяти отсутствовавших пар завершены три, последние две не запускались после срабатывания no-go. Для `200000_short-heavy_oldest` сохранены старые неполные файлы и принятую пару поместили в отдельный каталог `validation/recovery_docker_eof_20261017/`. Принятая пара `200000_long-heavy_random` восстановлена в CSV по имеющимся summary; повторного запуска не было.
- Диагностические replay и telemetry не запускались. Open15 и holdout-v2 не входили в исходный synthetic qualification; отдельная локальная macOS post-hoc оценка описана ниже. Платформа и таблица лидеров не открывались.

## Отдельная post-hoc проверка на macOS

После protocol stop отдельно выполнено локальное сравнение замороженных бинарников на Open15 и holdout-v2. Это описательная проверка, она не меняет no-go по синтетической матрице и не подтверждает Linux CPU-лимит.

- Open15: 15/15 transcript приняты у обеих версий; все ответы, KPI и длины траншеи совпали. Сумма score — `29.789717929` у baseline и candidate.
- holdout-v2: 12/12 приняты у обеих версий; 11/12 ответов совпали. В `case-01` candidate хуже на `0.000121139` KPI и использует на `40 м` больше траншеи; по набору среднее ΔKPI `−0.000010095`, среднее Δtrench `+3.33 м`.
- Замеры CPU/RSS выполнены на macOS arm64 и не валидируют Linux-лимит. Подробные таблица, хеши и версия среды: [post-hoc отчёт](validation/posthoc_macos_open15_holdout_20261017/REPORT.md), [CSV](validation/posthoc_macos_open15_holdout_20261017/comparison.csv), [манифест запуска](validation/posthoc_macos_open15_holdout_20261017/run_manifest.json).

## Идентификаторы и хеши

- Candidate source SHA-256: `365e0967b2687ec71619f0cd38df95480a34b8f03e165a5e5ab75c6a0c0edfe7`.
- Frozen baseline `results/pipes/final/solution.cpp`: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Canonical `src/pipes.cpp`: `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.
- Fresh input manifest SHA-256: `4b2802956338d624cbb6e681ea37b80ee9a437b138e0942eec9043b86d2b7a14`.
- Итоговый CSV SHA-256: `2b6d55ba7398ed735a7de2cdc3933bd40528fe718cbe017286325f8976ba7a7c`.

См. `validation/per_case.csv`, `validation/partial_summary.json` и `manifest.json`. Не менять frozen final или canonical source по результатам этой ветки.
