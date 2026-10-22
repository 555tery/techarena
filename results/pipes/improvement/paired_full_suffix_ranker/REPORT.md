# Paired full-suffix ranker — NO-GO

Дата: 2026-10-17. Отдельный кандидат; `results/pipes/final/solution.cpp` и `src/pipes.cpp` не менялись.

## Вывод

Кандидат **не продвигается**. На заранее отложенных синтетических потоках средняя парная ΔKPI положительная (`+0.000859131`), но 95% bootstrap CI включает ноль: `[-0.000293354, +0.002114108]`. Предварительно заданный gate поэтому завершился **NO-GO**. Одноразовая локальная диагностика подтвердила смешанную картину: Open15 ухудшился на `0.101020274`, а reused holdout-v2 улучшился на `0.022736004`. После заморозки кандидата параметры не менялись и повторных прогонов для подгонки не было.

Все 60 baseline и 60 candidate synthetic-транскриптов корректны; нарушения лимитов отсутствуют. Максимум CPU/RSS: baseline `1.257008 s / 7.953 MiB`, candidate `1.567266 s / 7.844 MiB` на поток.

## Метод

Вместо регрессии с 512-командным горизонтом обучен линейный pairwise RankNet ранжировщик на 180 существующих признаках. Для каждой точки сравнивались те же прежние действия: до трёх лучших допустимых gap starts с тем же краем и slack ≤40 м; baseline action оставался среди кандидатов. Каждое действие получало общий полный суффикс входа до EOF и одну фиксированную continuation policy — deterministic frozen greedy без вложенного MC. Будущее использовалось только офлайн для меток; финальный solver получает команды по одной и не видит seed, id теста или остаток потока.

Обучение: 30 заранее заданных train streams, cadence 1,000 команд; первый набор — 288 states / 823 action rows. Один DAgger-style раунд собрал траектории initial ranker и добавил 289 states / 834 rows. Финальная модель обучена на 577 states / 1,657 rows; два train streams не дали точки с двумя и более кандидатами. Pairwise soft labels использовали temperature 20 м, L2 0.01, 1,000 Adam steps, learning rate 0.03, seed 20261018. Подбор параметров не проводился.

Gate использовал 60 новых seed-streams: 30 × 16,384 и 30 × 200,000 команд; равный вес каждого потока. Парный bootstrap по streams: 20,000 повторов, seed 2026101817.

| Метрика synthetic gate | Результат |
|---|---:|
| Средняя ΔKPI | +0.000859131 |
| 95% percentile CI | [−0.000293354, +0.002114108] |
| Победы / поражения / ничьи | 21 / 21 / 18 |
| Δ на 30 потоках по 200,000 команд | +0.000603081 |
| Решение | **NO-GO** — нижняя граница CI не выше 0 |

Эффект неоднороден: среднее Δ на steady потоках `+0.001888`, на periodic-drain `−0.000170`; при удалении longest `+0.004611` (12 потоков), shortest `−0.000980` (12 потоков), newest дал 12 ничьих. Эти разрезы — диагностика фиксированного набора, не основание для новой настройки.

## Одноразовая локальная диагностика после freeze

Запуск разрешён addendum к протоколу от 2026-10-17 07:01 Novosibirsk: выполнить одну локальную пару Open15 + holdout-v2 после заморозки кандидата независимо от score gate, если синтетические транскрипты и лимиты корректны. Они были корректны. Эти наборы используются только диагностически; по ним ничего не обучалось и не настраивалось.

| Набор | Frozen final | Candidate | Δ | Победы / поражения / ничьи |
|---|---:|---:|---:|---:|
| Open15, сумма score / 32.1 | 29.789717929 | 29.688697654 | −0.101020274 | 1 / 4 / 10 |
| Holdout-v2, сумма score / 12 | 5.135264324 | 5.158000328 | +0.022736004 | 1 / 1 / 10 |

На Open15 кандидат сэкономил 160 м в case 5, но добавил 80 м в case 7, 20 м в case 8, 20 м в case 12 и 40 м в case 13. Holdout-v2 выигрыш целиком пришёлся на case 5 (−20 м траншеи); case 1 добавил 40 м. Holdout-v2 уже использовался в прежних экспериментах и не считается независимым подтверждением. Все Open15 и holdout interactions завершились со статусом `ok`; максимумы CPU/RSS на Open15: baseline `0.998314 s / 7.031 MiB`, candidate `0.984733 s / 6.313 MiB`; на holdout: baseline `0.200217 s / 4.250 MiB`, candidate `0.201510 s / 3.844 MiB`.

## Протокол и целостность

- Данные: [manifest.json](inputs/manifest.json), 30 train + 60 validation inputs. Официальный генератор и ускоренный Fenwick/heap generator совпали по векторам команд на 30 проверках по 5,000 команд; подробности и hashes в [generator-equivalence.json](inputs/generator-equivalence.json).
- Зафиксированный seed `2026101938` validation input имеет SHA-256 `933410f9df65c26f957840398fd902e330d0ad320bab5f63a7714641a70c35c9`; процесс генератора завершился до повторной генерации, параллельной записи не было. См. [implementation note](IMPLEMENTATION_NOTE_2026-10-17.md).
- Старый `learned_gap_value/REPORT.md` указывает 534 training states, но его manifest содержит 310 train и 534 validation states. Здесь counts взяты из собственных model JSON и training manifest; старый отчёт не переписывался.
- Не использовались сайт, leaderboard или Docker.

| Артефакт | SHA-256 |
|---|---|
| Замороженный baseline source | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` |
| Candidate source | `b752cb71c06c2b7f91380e43bc5dc0358afc6c4db39f4ddcbdcc016911a8519e` |
| Candidate model header | `087210dc28ce7083ed5147119bcb4e7ebef15b02558defab8a91d5b593edba22` |
| Candidate binary | `466979ba77c9cd07358dfbdd8dc6aeeea38ae57852801837375959743415f972` |
| Candidate lock | `6757bb5a4947f727c908b049dba0ef829ab6c02cec00d901dc98275275f5b396` |
| Input manifest | `64b8f89cda15119499f636981532a34b75ba928c8d20588d9c0d56e215a76056` |
| Training manifest | `2ef6b822737d15139f7e79879a057cba485dff3157816cee10cdb20236b0a926` |
| Synthetic gate JSON | `3b78b67e8e387b5b7529c7efdac1f8ee05bb6d12b76e50bc7e37cb1c47b35bcf` |
| Official diagnostic manifest | `9f808aa34db2c1c5e1bfc48ec79320b146c519e8adabd1af03387ff28a067fa4` |
| Synthetic paired streams CSV | `0416d0d03d5594e41faced2d975d58d6594aac1a517adcf5b1272b1de8443895` |
| Open15 per-case CSV | `303abf512b7b29a1b07f64fdb2abcc8cd8accb51a6d213f8830fd5bc92c86cf5` |
| Holdout-v2 per-case CSV | `0ce58af513ab17c764a6cf8b9cd976719222005c317b70e4de3923599e326ede` |

## Воспроизведение

Из корня репозитория; результаты и полные per-case материалы сохраняются в этой папке:

```sh
python3 results/pipes/improvement/paired_full_suffix_ranker/prepare_streams.py
python3 results/pipes/improvement/paired_full_suffix_ranker/run_training.py
python3 results/pipes/improvement/paired_full_suffix_ranker/freeze_candidate.py
python3 results/pipes/improvement/paired_full_suffix_ranker/evaluate_gate.py
python3 results/pipes/improvement/paired_full_suffix_ranker/evaluate_official.py
```

`evaluate_official.py` выполняется только один раз и требует неизменённый candidate lock и корректный synthetic protocol/resource check. Сборка candidate: `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic`.
