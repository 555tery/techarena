# PID/46 window gate: первичный validation-прогон

## Статус результата

**Uninformative / null contrast.** Этот прогон не идентифицировал разницу между политиками и не является свидетельством против гипотезы.

Кандидат использовал заранее заданное правило: при активном `runLeft` переходить с c4 size-cohort lane на PID-parity lane, только если окно последних 64 удалений содержит не менее 32 событий и одна PID-парность занимает не менее 75%. Источники baseline и candidate сохранены рядом с результатами.

На 36 validation-потоках было 18 292 размещения, где `runLeft` и gate были одновременно активны. Во всех 18 292 случаях выбор стороны совпал с baseline: **0 lane divergences**. Поэтому выходы, итоговые траншеи и оценки совпали на всех 36 потоках. Входы/сводки лежат в `validation/`, `validation-baseline-run/`, `validation-candidate-run/`, а машинная сводка — в `analysis.json`.

Причина — четность фаз и длины одноразмерных серий в сгенерированном наборе: PID parity и size-cohort parity синхронизировались. Сравнение не включало фактическое лечение политикой кандидата, поэтому нулевые дельты нельзя интерпретировать как нулевой причинный эффект.

## Provenance

- Baseline/frozen-final source SHA-256: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Candidate source SHA-256: `91aba259929fc45ce0f520b5a8ff22dea7cce203ea6d9c28aae687babf71ecc4`.
- Исходный preregistration: `PRE_REGISTRATION.json`; результаты exposure и paired analysis: `analysis.json`, `paired_validation.csv`.
- Полный причинный контраст был отдельно запланирован в `exploratory_v1/`; это новый post-hoc exploratory набор с новыми seeds, а не переинтерпретация этого результата.
