# Case 5: сохранение ёмкости под предсказанный следующий размер

## Результат

**No-go по порогу: выигрыш case 5 равен 0 м при требовании не менее 500 м.** Кандидат изменил 86 строк ответа на case 5, но итоговая траншея осталась 62 620 м, KPI — 0.811881188119. На всех шести новых synthetic traces ответы совпали с baseline; счёт не изменился. Open15 не запускал, так как целевой gate не пройден.

Перед блоком длины 40 baseline имеет 63 свободных интервала, вмещающих по одной трубе длины 40; максимальный интервал — 67 м. Поэтому текущая политика получает максимум 63 размещения длины 40 из этих интервалов, а оставшиеся размещения требуют расширения траншеи. Кандидат не увеличил эту ёмкость.

## Проверенная политика

Использовать только наблюдённую линейную последовательность трёх размерных серий, каждая длиной не менее 46 запросов. Если существующий предиктор размеров по прошлому префиксу даёт следующий размер `F > L`, ранжировать свободные интервалы сначала по потере ёмкости для `F` после размещения текущей трубы `L`: `floor(g/F) - floor((g-L)/F)`. При равной потере оставить исходную стоимость и разрешение равенств. Та же оценка применена в live allocator и rollout simulator.

В прежней стоимости учитывались эмпирические частоты уже наблюдавшихся запросов. До появления класса `F` его частота равна нулю, поэтому именно этот дополнительный член в baseline отсутствовал. Правило не читает будущие команды, PID или номер теста. Проверен один вариант без перебора коэффициентов.

## Покейсные результаты

| Поток | Baseline, м | Кандидат, м | Δ траншеи | Baseline KPI | Кандидат KPI | Ответы совпали |
|---|---:|---:|---:|---:|---:|:---:|
| Open case 5 | 62 620 | 62 620 | 0 | 0.811881188119 | 0.811881188119 | нет, различаются 86 строк |
| S01 increasing + FIFO | 5 400 | 5 400 | 0 | 0.888888888889 | 0.888888888889 | да |
| S02 increasing + LIFO | 4 400 | 4 400 | 0 | 0.863636363636 | 0.863636363636 | да |
| S03 increasing + random deletion | 4 820 | 4 820 | 0 | 0.740456431535 | 0.740456431535 | да |
| S04 step-2 sizes + random deletion | 4 520 | 4 520 | 0 | 0.759292035398 | 0.759292035398 | да |
| S05 rising/falling + FIFO | 4 960 | 4 960 | 0 | 0.919354838710 | 0.919354838710 | да |
| S06 disjoint support shifts + random deletion | 13 260 | 13 260 | 0 | 0.679638009050 | 0.679638009050 | да |

Все 14 запусков завершились `ok`, без превышения 5 CPU-с и 256 MiB. Все per-case строки, время CPU, входные и transcript hashes находятся в [comparison.csv](comparison.csv); входы и полные результаты сохранены в соседних `synthetic/`, `baseline_case5/`, `candidate_case5/`, `synthetic_baseline/` и `synthetic_candidate/`.

## Исходники и воспроизведение

- Baseline source SHA-256: `43bfbdadbae18ac180d1e59b6631342cfe1bef99190a449838f0470d6f220200` — `results/pipes/improvement/case9_causal_profiles/source/champion_cohort_slabs.cpp`.
- Baseline binary SHA-256: `e4b79d8eb55a1fdc03a8c62505142ee615304401e821895bf6ab7f3712e54049`.
- Candidate: [next_class_capacity.cpp](src/next_class_capacity.cpp), SHA-256 `0b3da4989785661e4edc9effe4c3e445c35d15d5e6f6e57f1a6efcb0619572d5`.
- Candidate binary SHA-256: `8ca130cc7202f5843956ab3f0bfa1299282465a9070a360acb65a37326222dfc`.
- Build: `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case5_new_structural_20261017/src/next_class_capacity.cpp -o results/pipes/improvement/case5_new_structural_20261017/bin/next_class_capacity`.
- Baseline case 5: `python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --interactor tools/interactor --tests data/pipes/open/5.in --out results/pipes/improvement/case5_new_structural_20261017/baseline_case5 --name champion-case5 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120`.
- Candidate case 5: `python3 tools/pipes_harness.py --solver results/pipes/improvement/case5_new_structural_20261017/bin/next_class_capacity --interactor tools/interactor --tests data/pipes/open/5.in --out results/pipes/improvement/case5_new_structural_20261017/candidate_case5 --name candidate-case5 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120`.
- Synthetic baseline/candidate commands with the same limits are recorded in [manifest.json](manifest.json).

Тестирование было только локальным. Frozen/canonical файлы не менялись; их проверенные SHA-256: `results/pipes/final/solution.cpp` — `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`, `src/pipes.cpp` — `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`. Сайт и Docker не использовались.
