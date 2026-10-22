# Case 11: адаптивное размещение при LIFO-удалениях

## Итог

**No-go для Open15.** Направленная политика уменьшила траншею case 11 на 120 м, с 22 620 до 22 500 м. Но на полном Open15 кандидат набрал **29.906777984955 / 32.1** против текущего champion **29.932085817214**: регрессия **−0.025307832259**. Причина — case 13 ухудшился на 20 м (вес 4), а case 15 на 300 м (вес 10); выигрыш case 11 не компенсировал эти потери. Кандидат не продвигается.

## Проверяемая гипотеза

В case 11 первые примерно 5 000 команд состоят главным образом из длин 1–7, а удаление часто выбирает одну из самых новых активных труб. Гипотеза: кратковременно вести новые короткие трубы к расширяемому хвосту, чтобы LIFO-подобные удаления чаще освобождали хвостовой стек.

Режим включается причинно, если последние 64 удаления содержат не менее 80% труб с rank-from-newest ≤5%, зафиксировано не менее 64 недавних размещений, не менее 90% из них длиной ≤8, и текущая труба длиной ≤8. Номер кейса и будущие команды не используются.

## Этап 1 — tail-only stack lane, отклонён

Кандидат направлял все размещения при сигнале в хвостовой интервал или расширял траншею, игнорируя подходящие внутренние интервалы. Это оказалось слишком агрессивно: case 11 вырос с 22 620 до **34 020 м** (+11 400 м; score 0.900133 → 0.598501). Четыре синтетических потока совпали с baseline. Это показывает, что наблюдаемого LIFO-сигнала недостаточно для отказа от Best Fit по всей траншее.

## Этап 2 — сохранять Best Fit, менять только край

После первой регрессии проверен более узкий вариант: прежний Best Fit и rollout остаются, а для труб длиннее 4 м при том же сильном LIFO-сигнале размещение делается с высокого края выбранной дырки. Свободные внутренние интервалы не резервируются и не игнорируются.

| Набор | Baseline | Кандидат | Δ траншеи | Δ KPI |
|---|---:|---:|---:|---:|
| Open case 11 | 22 620 м / 0.900132626 | 22 500 м / 0.904933333 | −120 м | +0.004800707 |
| Synthetic: small LIFO | 21 760 м | 21 760 м | 0 м | 0 |
| Synthetic: small FIFO | 21 520 м | 21 520 м | 0 м | 0 |
| Synthetic: small random deletion | 21 940 м | 21 940 м | 0 м | 0 |
| Synthetic: small LIFO → wide random | 19 200 м | 19 200 м | 0 м | 0 |

Четыре synthetics — ограниченный targeted screen, не доказательство обобщения. Все локальные запуски завершились `ok`; у Open15 максимум solver CPU — 1.638 с, RSS — 7.30 MiB, ниже лимитов 5 с и 256 MiB.

## Open15: покейсовое сравнение

Полная таблица: [open15_comparison.csv](open15_comparison.csv). Изменились только:

| Кейс | Baseline, м | Кандидат, м | Δ траншеи | Δ weighted score |
|---:|---:|---:|---:|---:|
| 11 | 22 620 | 22 500 | −120 | +0.004800707 |
| 13 | 3 280 | 3 300 | +20 | −0.023592018 |
| 15 | 438 920 | 439 220 | +300 | −0.006516522 |

Остальные 12 кейсов совпали. Per-case candidate harness results сохранены в `runs/open15_high_side/`; исходная champion-таблица — `results/pipes/improvement/case9_causal_profiles/per_case_comparison.csv`.

## Воспроизведение

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic results/pipes/improvement/case11_lifo_stack/src/baseline_champion.cpp -o results/pipes/improvement/case11_lifo_stack/bin/baseline_champion
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic results/pipes/improvement/case11_lifo_stack/src/lifo_stack_lane.cpp -o results/pipes/improvement/case11_lifo_stack/bin/lifo_stack_lane
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic results/pipes/improvement/case11_lifo_stack/src/lifo_high_side.cpp -o results/pipes/improvement/case11_lifo_stack/bin/lifo_high_side
python3 tools/pipes_harness.py --solver results/pipes/improvement/case11_lifo_stack/bin/lifo_high_side --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/case11_lifo_stack/runs/open15_high_side --name lifo-high-side-open15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
```

For the four synthetic screens, see the input generator `generate_synthetic.py` and paired run directories `runs/{baseline,candidate_high_side}_<stream>/`. Source, binary, test, harness, interactor, CSV and summary SHA-256 values are listed in [manifest.json](manifest.json).

The champion source used as baseline is `results/pipes/improvement/case9_causal_profiles/source/champion_cohort_slabs.cpp`, SHA-256 `43bfbdadbae18ac180d1e59b6631342cfe1bef99190a449838f0470d6f220200`. Candidate high-side source SHA-256 is `0d91fd019211ae7f9fe02977c4b6f0b0f6a702fce085848d9bfb6b391713d672`. Frozen final and canonical source were not modified. No website or Docker used.
