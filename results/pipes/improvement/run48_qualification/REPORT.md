# Run-48: независимая квалификация

Дата: 2026-10-17. Проверка проведена на замороженном final source; финальный исходник, canonical `src/pipes.cpp` и платформа не менялись.

## Вывод

Кандидат `run-48` подтверждён и собран. Он меняет только порог `kSameLengthRightRun: 46 → 48`. На полном Open15 повторно получено **29.790219562101 / 32.1**, то есть на **+0.000501633507** выше baseline. На holdout-v2 и четырёх development synthetic score не ухудшился: совпали итоговый score, длины траншеи и выходные файлы по всем кейсам. Все прогоны прошли; ресурсные ограничения соблюдены.

Изолированная submission-ready копия подготовлена в [`submission-ready/solution.cpp`](submission-ready/solution.cpp). **Загрузка на платформу не выполнялась.**

## Идентичность и сборка

| Артефакт | SHA-256 |
|---|---|
| Frozen final source | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` |
| Candidate source | `95d662fff63be90146b5ebddeff43ce4b551f34b8de5351513ba33f53be55b39` |
| Submission-ready copy | `95d662fff63be90146b5ebddeff43ce4b551f34b8de5351513ba33f53be55b39` |
| Baseline binary | `ee9ae15f8f4879eaca8da9a0c5fdb1caeb05311893279a4eaf0734c167427290` |
| Candidate binary | `9fef88bbc46f0fcd62304f4439548dafa090902b034705676e8e517caac78448` |
| Official harness | `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d` |
| Interactor | `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a` |

Проверка source diff выполнена байтово: candidate получен из указанного frozen final единственной заменой `46` на `48` в инициализации `kSameLengthRightRun`. Перед компиляцией оба исходника скопированы в изолированный каталог. Сборка обоих вариантов прошла с `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror`.

Хеши всех входных файлов по трём наборам записаны в `qualification.json`; для каждого кейса там же сохранены SHA-256 official judge output обоих вариантов, фактические score, траншея, CPU и RSS.

## Независимые прогоны

| Набор | Вариант | Пройдено | Сумма весов | Weighted score | Максимум CPU | Максимум RSS |
|---|---|---:|---:|---:|---:|---:|
| Open15 | baseline | 15/15 | 32.1 | 29.789717928594 | 1.132481 s | 7.094 MiB |
| Open15 | run-48 | 15/15 | 32.1 | 29.790219562101 | 1.178511 s | 7.359 MiB |
| holdout-v2 | baseline | 12/12 | 12.0 | 5.135264324280 | 0.423357 s | 3.719 MiB |
| holdout-v2 | run-48 | 12/12 | 12.0 | 5.135264324280 | 0.229453 s | 4.172 MiB |
| development synthetic (4) | baseline | 4/4 | 4.0 | 1.844130426987 | 0.143699 s | 3.500 MiB |
| development synthetic (4) | run-48 | 4/4 | 4.0 | 1.844130426987 | 0.170879 s | 3.359 MiB |

Каждый запуск использовал лимиты solver 5 секунд CPU и 256 MiB. Ни один кейс не превысил CPU или memory limit. Самый тяжёлый свежий прогон кандидата: Open15 case 15, 1.178511 s CPU и 7.359 MiB RSS.

## Изменения по кейсам Open15

Веса открытых кейсов в сумме равны 32.1. Кандидат изменил judge output на кейсах 5, 8, 9 и 13; фактическая длина траншеи и score изменились только на кейсах 5 и 9.

| Кейс | Вес | Baseline: траншея | Run-48: траншея | Δ траншеи | Baseline weighted score | Run-48 weighted score | Δ weighted score |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 1 | 62760 m | 62620 m | -140 m | 0.810070108349 | 0.811881188119 | +0.001811079770 |
| 8 | 1 | 4700 m | 4700 m | +0 m | 0.984468085106 | 0.984468085106 | +0.000000000000 |
| 9 | 1 | 61960 m | 62120 m | +160 m | 0.508392511298 | 0.507083065035 | -0.001309446262 |
| 13 | 4 | 3280 m | 3280 m | +0 m | 3.892682926829 | 3.892682926829 | +0.000000000000 |

Итоговый weighted прирост — чистая сумма улучшения на case 5 (**+0.001811079770**) и ухудшения на case 9 (**−0.001309446262**); остальные кейсы не изменили score. Значит, это небольшое улучшение общей суммы, а не доминирование над baseline по каждому открытому тесту. На holdout-v2 (12/12) и development synthetic (4/4) у кандидата нет per-case score regression, изменений trench или расхождений output hash.

## Повторяемость и диагностика 15 кейсов

Свежий Open15 run-48 совпал с сохранённым результатом прежнего screening по всем 15 judge-output SHA-256 и по score `29.7902195621014`. Свежий baseline также совпал по всем 15 output hash с прогоном замороженного final, а его score повторился как `29.789717928594047`. Это подтверждает воспроизводимость на тех же открытых входах, но не независимую обобщающую оценку: Open15 использовался при настройке.

Отдельная подробная диагностика по всем 15 baseline-кейсам — trench, peak live-volume lower bound, loose per-case score ceiling, weighted headroom и trace-классификация потерь — уже сохранена в [`../all_tests_diagnosis/REPORT.md`](../all_tests_diagnosis/REPORT.md), с полными таблицами в `per_case.csv` и `manifest.json`. Её manifest фиксирует тот же final source SHA, что и эта квалификация; свежие baseline case score и trench сверены со всеми 15 строками диагностики, расхождений нет. Верхние границы там являются свободно-объёмными необходимыми границами, а не обещанием достижимого результата.

## Файлы и ограничения

- `qualification.json` — полный machine-readable manifest: exact input/output/source/binary/harness/interactor hashes, score/trench per case, лимиты и ресурсы.
- `runs/` — полные свежие official-harness outputs и traces для baseline и run-48.
- `sources/` и `binaries/` — неизменённые проверенные источники и результаты строгой сборки.
- `submission-ready/solution.cpp` — изолированная копия кандидата, готовая для последующего рассмотрения.

Вывод ограничен тремя указанными наборами. Отсутствие регрессий на holdout-v2 и четырёх локальных synthetic — полезный regression gate, но не доказывает превосходство на закрытых тестах и не гарантирует более высокий leaderboard rank.
