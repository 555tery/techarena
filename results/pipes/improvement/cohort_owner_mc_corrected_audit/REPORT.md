# Независимый аудит corrected `cohort_owner_mc_rollout`

Дата: 2026-10-16. Аудирован замороженный исходник с SHA `fadbe93b0ae2d1dd1ff2ebce3dbdf384f3969272865f108729092b9d8cb98be3`. Его hash совпал с заявленным перед сборкой и после всех прогонов. `results/pipes/final/solution.cpp`, `src/pipes.cpp` и прежний `cohort_owner_mc_audit/REPORT.md` не изменялись; этот отчёт сохранён отдельно.

## Итог

Свежая строгая сборка прошла, официальный harness завершился `15/15 ok`: **29.773150805748521 / 32.1**. Текущий owner, независимо пересобранный из `final/solution.cpp` и прогнанный тем же harness/interactor на тех же открытых входах, набрал **29.731837411671535 / 32.1**. Разница кандидата — **+0.041313394076987**. Только кейсы 7 и 12 отличаются: суммарная длина траншеи уменьшилась на 60 м и 20 м соответственно; в остальных 13 кейсах выход совпадает.

На парном reused `final-holdout-v2` оба solver прошли `12/12`: кандидат — **5.135264324280470 / 12.0**, owner — **5.135100030340453 / 12.0**, разница **+0.000164293940017**. Улучшение есть только в кейсах 1 и 10 и составляет 20 м траншеи в каждом. Этот набор ранее уже использовался в проверках; результат не является независимым подтверждением обобщения.

Пиковый solver CPU кандидата — **1.060927 s** (open case 15) при лимите **5 s**; максимальный RSS — **9.515625 MiB** при лимите **256 MiB**. Во всех четырёх свежих прогонах не было CPU/RSS превышений. По исходнику нарушений online-каузальности не найдено: алгоритм строит сценарии только из ранее принятых операций и симулирует их на копии текущего состояния; он не читает идентификатор теста, score-файлы или будущие команды.

## Исходники, сборки и harness

| Артефакт | SHA-256 |
|---|---|
| Кандидат `max_open_lookahead/bounded_mc/cohort_owner_mc_rollout.cpp` | `fadbe93b0ae2d1dd1ff2ebce3dbdf384f3969272865f108729092b9d8cb98be3` |
| `results/pipes/final/solution.cpp` (owner) | `2cce753dfaa9aa6f625cefee9550edff6d8c4ce8c915e9cb77cbfbb0c3dc3583` |
| `src/pipes.cpp` | `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8` |
| Свежий strict binary кандидата | `5fc2b93efc0e3a80fe52dd13d069e9379ac800a9295654d7ad071e331483583a` |
| Свежий strict binary owner | `4d319523b909cb789521c80988e28bcf3b3d7565b5a0922b56f88de5341bba50` |
| Официальный interactor binary | `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a` |
| `vendor/pipes_official/interactor.cpp` | `85672e4c3ad9fdcb97d8b601758de1f1d1b5e86d6dd20252e0f72acdb9cb122a` |
| `tools/pipes_harness.py` | `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d` |

Кандидат и owner свежо собраны на Apple Clang 17.0.0, target `arm64-apple-darwin25.6.0`, без предупреждений и ошибок:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/max_open_lookahead/bounded_mc/cohort_owner_mc_rollout.cpp -o results/pipes/improvement/cohort_owner_mc_corrected_audit/bin/cohort_owner_mc_rollout
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/final/solution.cpp -o results/pipes/improvement/cohort_owner_mc_corrected_audit/bin/cohort_owner
clang++ -O2 -std=c++17 -pipe vendor/pipes_official/interactor.cpp -o results/pipes/improvement/cohort_owner_mc_corrected_audit/bin/interactor
```

Проведены четыре свежих harness-прогона: candidate и owner на `data/pipes/open`, затем candidate и owner на `data/pipes/synthetic/final-holdout-v2`. Во всех командах были `--cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120`; открытый набор — официальный `data/pipes/open`. Все входные SHA и порядок кейсов совпадают внутри каждой пары.

```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/cohort_owner_mc_corrected_audit/bin/cohort_owner_mc_rollout --name cohort-owner-mc-rollout-corrected-independent-audit --interactor results/pipes/improvement/cohort_owner_mc_corrected_audit/bin/interactor --tests data/pipes/open --out results/pipes/improvement/cohort_owner_mc_corrected_audit/open-mc --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/cohort_owner_mc_corrected_audit/bin/cohort_owner --name cohort-owner-corrected-audit-open-owner --interactor results/pipes/improvement/cohort_owner_mc_corrected_audit/bin/interactor --tests data/pipes/open --out results/pipes/improvement/cohort_owner_mc_corrected_audit/open-owner --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/cohort_owner_mc_corrected_audit/bin/cohort_owner_mc_rollout --name cohort-owner-mc-rollout-corrected-audit-holdout-v2 --interactor results/pipes/improvement/cohort_owner_mc_corrected_audit/bin/interactor --tests data/pipes/synthetic/final-holdout-v2 --out results/pipes/improvement/cohort_owner_mc_corrected_audit/holdout-mc --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/cohort_owner_mc_corrected_audit/bin/cohort_owner --name cohort-owner-corrected-audit-holdout-v2 --interactor results/pipes/improvement/cohort_owner_mc_corrected_audit/bin/interactor --tests data/pipes/synthetic/final-holdout-v2 --out results/pipes/improvement/cohort_owner_mc_corrected_audit/holdout-owner --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

## Online-каузальность и корректность rollout-модели

`main` читает одну текущую целочисленную команду из stdin и отвечает на placement/removal с flush (`cohort_owner_mc_rollout.cpp:778-799`). Текущий placement добавляется в историю только после выдачи ответа, removal — после обработки текущего PID (`:363-376`, `:390-414`). История ограничена 256 предыдущими событиями (`:443-446`).

`sampleScenario` берёт до четырёх операций из ранее записанного окна последних максимум 128 событий. Индекс начала ограничен `start <= n - depth`, поэтому последний выбранный элемент не превышает `n-1` и будущее из stdin не читается (`:473-506`). Перед выбором кандидата симулятор копирует текущие свободные интервалы, активные трубы, счётчики и режим cohort (`:538-557`). Xorshift seed детерминирован текущим allocator state и placement length, без времени, внешней случайности или системных данных (`:466-471`, `:581-585`). На decision применяется не более 12 исторических сценариев глубины 4 к максимум трём gap-кандидатам; лимит — 32 MC-решения, активация только при достаточной истории и не более 64 gaps/4096 active pipes (`:22-28`, `:561-615`).

Исправленная версия согласовала выбор симулируемой щели с реальным allocator: `RolloutState::bestGap` после первой допустимой щели каждого размера подавляет другие щели того же размера (`:155-185`), что соответствует проходу `Allocator::bestFittingGapFromSet` через `upper_bound` к следующему размеру (`:650-687`). Прежнее расхождение high-side tie-break по одинаковым размерам этим устранено.

Оставшееся ограничение — приближённое представление removal. История хранит для удаления rank-from-newest permille, а совпадение контекста считает равными все removal независимо от ранга (`:30-34`, `:461-464`). При rollout этот квантованный ранг применяется к текущему counterfactual active-list (`:261-278`). Это не чтение будущего, но конкретный исторический PID не воспроизводится; поэтому оценка будущего — эвристическая и может искажаться при другой структуре активных труб.

Проверка исходника на `ifstream/ofstream`, `fopen/freopen`, `open`, `getenv`, `system`, `argv`, `score.txt`, пути к тестам и часовую/внешнюю энтропию совпадений не дала. Диагностический макрос, если его отдельно включить, печатает только два счётчика в `stderr` при команде `0`; в строгой сборке он не включался (`:785-789`).

## Официальные open-тесты: paired owner / corrected MC

Fresh owner score — `29.731837411671535 / 32.1`; corrected MC — `29.773150805748521 / 32.1`; `Δ=+0.041313394076987`. В таблице приведены weighted score, trench и CPU/RSS процесса solver по каждому кейсу.

| Кейс | Траншея owner → MC, м | Weighted score owner → MC | Δ score | CPU owner / MC, s | RSS owner / MC, MiB |
|---:|---:|---:|---:|---:|---:|
| 1 | 20 → 20 | 0.090000000000 → 0.090000000000 | 0.000000000000 | 0.002160 / 0.006605 | 1.312500 / 2.125000 |
| 2 | 20 → 20 | 1.000000000000 → 1.000000000000 | 0.000000000000 | 0.002129 / 0.002141 | 1.312500 / 2.125000 |
| 3 | 20 → 20 | 0.750000000000 → 0.750000000000 | 0.000000000000 | 0.002262 / 0.002386 | 1.312500 / 2.125000 |
| 4 | 60 → 60 | 0.666666666667 → 0.666666666667 | 0.000000000000 | 0.002085 / 0.002626 | 1.312500 / 2.140625 |
| 5 | 62 800 → 62 800 | 0.809554140127 → 0.809554140127 | 0.000000000000 | 0.039894 / 0.043790 | 1.937500 / 2.734375 |
| 6 | 20 → 20 | 0.900000000000 → 0.900000000000 | 0.000000000000 | 0.001888 / 0.002035 | 1.312500 / 2.125000 |
| 7 | 1 760 → 1 700 | 0.952840909091 → 0.986470588235 | +0.033629679144 | 0.003484 / 0.004982 | 1.359375 / 2.640625 |
| 8 | 4 700 → 4 700 | 0.984468085106 → 0.984468085106 | 0.000000000000 | 0.029306 / 0.031186 | 1.609375 / 2.640625 |
| 9 | 63 980 → 63 980 | 0.492341356674 → 0.492341356674 | 0.000000000000 | 0.048095 / 0.048639 | 2.265625 / 3.078125 |
| 10 | 15 380 → 15 380 | 0.800000000000 → 0.800000000000 | 0.000000000000 | 0.044327 / 0.051483 | 1.906250 / 2.687500 |
| 11 | 22 620 → 22 620 | 0.900132625995 → 0.900132625995 | 0.000000000000 | 0.045768 / 0.055658 | 1.812500 / 3.031250 |
| 12 | 10 340 → 10 320 | 3.964796905222 → 3.972480620155 | +0.007683714933 | 0.008437 / 0.011181 | 1.468750 / 2.671875 |
| 13 | 3 280 → 3 280 | 3.892682926829 → 3.892682926829 | 0.000000000000 | 0.045022 / 0.053758 | 1.734375 / 2.765625 |
| 14 | 37 820 → 37 820 | 3.987731359069 → 3.987731359069 | 0.000000000000 | 0.103586 / 0.125360 | 2.718750 / 4.125000 |
| 15 | 438 920 → 438 920 | 9.540622436891 → 9.540622436891 | 0.000000000000 | 0.941063 / 1.060927 | 8.328125 / 9.515625 |

## Reused holdout-v2: paired owner / corrected MC

Fresh owner score — `5.135100030340453 / 12`; corrected MC — `5.135264324280470 / 12`; `Δ=+0.000164293940017`. SHA входов и порядок всех 12 кейсов совпадают попарно.

| Кейс | Траншея owner → MC, м | Weighted score owner → MC | Δ score | CPU owner / MC, s | RSS owner / MC, MiB |
|---|---:|---:|---:|---:|---:|
| case-01 | 330 100 → 330 080 | 0.999697061497 → 0.999757634513 | +0.000060573016 | 0.183480 / 0.177920 | 2.859375 / 3.984375 |
| case-02 | 480 → 480 | 0.014583333333 → 0.014583333333 | 0.000000000000 | 0.169716 / 0.172481 | 2.625000 / 3.671875 |
| case-03 | 360 → 360 | 0.144444444444 → 0.144444444444 | 0.000000000000 | 0.167791 / 0.175684 | 2.625000 / 3.718750 |
| case-04 | 315 260 → 315 260 | 0.999942904269 → 0.999942904269 | 0.000000000000 | 0.168365 / 0.171960 | 2.812500 / 4.093750 |
| case-05 | 300 → 300 | 0.320000000000 → 0.320000000000 | 0.000000000000 | 0.168709 / 0.169595 | 2.625000 / 3.687500 |
| case-06 | 300 → 300 | 0.103333333333 → 0.103333333333 | 0.000000000000 | 0.167252 / 0.170893 | 2.625000 / 3.468750 |
| case-07 | 467 960 → 467 960 | 0.994946149244 → 0.994946149244 | 0.000000000000 | 0.179486 / 0.184878 | 2.843750 / 3.984375 |
| case-08 | 820 → 820 | 0.264634146341 → 0.264634146341 | 0.000000000000 | 0.167291 / 0.173901 | 2.640625 / 3.703125 |
| case-09 | 300 → 300 | 0.093333333333 → 0.093333333333 | 0.000000000000 | 0.167629 / 0.173588 | 2.640625 / 3.718750 |
| case-10 | 192 680 → 192 660 | 0.999143657878 → 0.999247378802 | +0.000103720924 | 0.179464 / 0.181922 | 2.812500 / 3.953125 |
| case-11 | 180 → 180 | 0.116666666667 → 0.116666666667 | 0.000000000000 | 0.169474 / 0.172376 | 2.640625 / 3.718750 |
| case-12 | 320 → 320 | 0.084375000000 → 0.084375000000 | 0.000000000000 | 0.168975 / 0.171695 | 2.640625 / 3.796875 |

## Риск переобучения и артефакты

Open-прирост сосредоточен в двух кейсах из 15: case 7 даёт `+0.033629679144`, case 12 — `+0.007683714933`; остальные результаты совпали. На reused holdout-v2 изменились также только два кейса, но суммарный выигрыш `0.000164293940017` очень мал. Это не показывает ухудшения на проверенных наборах, однако открытые тесты могли использоваться для выбора MC-эвристики, а holdout-v2 уже запускался ранее. Поэтому риск переоценить обобщение на неизвестные входы остаётся существенным; статистически независимого подтверждения здесь нет.

Сохранённые данные:

- Open owner: [summary.json](open-owner/summary.json), [cases.csv](open-owner/cases.csv).
- Open MC: [summary.json](open-mc/summary.json), [cases.csv](open-mc/cases.csv).
- Holdout owner: [summary.json](holdout-owner/summary.json), [cases.csv](holdout-owner/cases.csv).
- Holdout MC: [summary.json](holdout-mc/summary.json), [cases.csv](holdout-mc/cases.csv).

Summary содержит SHA-256 каждого входного кейса, статусы и ресурсы solver/interactor. Корневой `score.txt` после прогонов сохранил значение `0.5`.
