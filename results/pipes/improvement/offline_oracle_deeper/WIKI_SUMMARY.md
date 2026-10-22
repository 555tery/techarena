# Pipes offline oracle: короткая wiki-сводка

**Статус:** no-go для нового causal online-gate; online policy не менялась.

## Baseline и проверка

- Frozen `results/pipes/final/solution.cpp`: SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Canonical `src/pipes.cpp`: SHA-256 `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.
- Runner `results/pipes/improvement/offline_longbeam/longbeam`: SHA-256 `9e6c9f360381b6fc6f868d9fbaf687dc5d5a352def45579f95c5b2ae00ba904a`.
- 30/30 новых запусков: code 0, полная baseline-трасса сверена по output tokens, baseline-control full replay точно совпал с исходным final.

## Окна, бюджеты и результаты

Порядок значений ниже: width/action-cap `4/6, 16/6, 64/6; 4/12, 16/12, 64/12`. Все размеры окон и стартовые операции 1-based.

| Поток | Окно / baseline expansions | Budget-конфигурации | Witness saving | Максимум CPU / wall / RSS |
|---|---|---|---:|---:|
| Open5 | op 5121, 64 команд / 63 расширения | все шесть | `0,0,0;0,0,0` м | 14.167 / 15.487 с; 286.453 MiB |
| Open9 | op 7681, 64 команд / 64 расширения | все шесть | `0,0,0;0,0,0` м | 28.440 / 28.706 с; 509.094 MiB |
| Open15 | op 111489, 32 команды / 3 расширения | все шесть, включая завершённый `64/12` | `0,0,0;0,0,0` м | 22.085 / 26.902 с; 1 518.750 MiB |
| holdout-v2 case-07 | op 38657, 64 команд / 19 расширений | все шесть | `0,0,0;0,0,0` м | 16.061 / 18.093 с; 1 159.797 MiB |
| development uniform | op 2561, 96 команд / 7 расширений | все шесть | `140,120,160;20,160,140` м | 2.235 / 2.258 с; 126.062 MiB |

Ранее пропущенный Open15 width64/cap12 теперь выполнен отдельно по фиксированному окну. Он дал 0 м экономии; лучший путь совпал с baseline и не имел первой divergence. Пик процесса составил 1 518.750 MiB (лимит 256 MiB на macOS не enforced). Это завершает ранее заданную бюджетную лестницу для Open15.

Метрики каждой конфигурации и расширенная validation: `run_resource_summary.csv`, `window_summary.csv`, `execution_validation.json`. Воспроизводимый анализ первых расхождений: `witness_divergences.json`.

## Вывод

- Open15 high-budget (`width64/action-cap12`): экономии 0 м; peak RSS 1 592 524 800 B = 1 518.75 MiB ≈ 1.48 GiB. Это результат ограниченного beam-поиска, не доказательство оптимальности и не сертификат.

Единственное новое короткое окно с положительным hindsight saving — development uniform, 20–160 м. Дополнительный high-budget Open15 запуск также дал 0 м и воспроизвёл baseline path. Holdout-v2 case-07 менял решения, но saving оставался 0. Прежние длинные свидетели Open5/Open9 имеют разные механизмы: сдвиг в новом tail, выбор другой fitting gap и противоположный край той же gap. Число fitting gaps в положительных примерах меняется от 0 до 78; у нулевого holdout-примера — 157. Повторяемый причинный признак для online-gate не выявлен.

**Caveat:** witness знает будущие команды внутри окна и оценивается по полному суффиксу. Он показывает достижимый hindsight-путь, не является online-правилом и не доказывает оптимальность. macOS не enforced лимит 256 MiB; RSS измерен фактически, некоторые диагностические поиски превысили конкурсный memory budget.

## Артефакты

Рабочая папка: `results/pipes/improvement/offline_oracle_deeper/`.

- Полный отчёт: `REPORT.md`.
- Зафиксированный выбор окон и план budget ladder: `selection_manifest.json`.
- Результаты, логи и ресурсы: `runs/`, `logs/`, `resources/`.
- Хэш-перечень: `artifact_manifest.json`.
- Анализ дивергенций: `analyze_witnesses.py` и `witness_divergences.json`.
- Проверка и табличная сводка: `summarize_runs.py`, `execution_validation.json`, CSV-файлы выше.
