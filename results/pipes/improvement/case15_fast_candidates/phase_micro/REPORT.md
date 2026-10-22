# Case 15: phase shift, large-gap preservation, and micro-replay

## Итог

Проверил causal phase-tie, сохранение крупных интервалов до смены распределения и короткие синтетические продолжения. На case 15 ни один вариант не уменьшил траншею. Overlay сохранения крупных интервалов дал положительный результат на ранее использованном holdout-v2, но ухудшил полный Open15 и поэтому отклонён.

Актуальный champion `43bfbdad…f220200` набрал `29.932085817214`. Тот же champion с overlay набрал `29.903380843851` (`−0.028704973363`). Case 15 у обоих — `438 920 м`, KPI `0.954062243689`; нижняя граница — `418 780 м`.

## Гипотезы и результаты на case 15

Трасса меняет распределение длин около команды 100 000: до этого размещаются трубы длиной 1–7 м, после — преимущественно 8–40 м. Проверены два tie-правила после обнаружения роста среднего размера и отдельное правило, которое в низкосреднем режиме сохраняет большие gap, когда есть меньший подходящий.

| Вариант | Траншея | Δ к frozen | KPI | Δ взвешенного score, вес 10 |
|---|---:|---:|---:|---:|
| Frozen final | 438 920 м | — | 0.954062244 | — |
| Phase, high-address tie | 439 360 м | +440 м | 0.953106792 | −0.009554520 |
| Phase, small-gap tie | 438 920 м | 0 м | 0.954062244 | 0 |
| Preserve large gaps, frozen base | 438 920 м | 0 м | 0.954062244 | 0 |
| Current champion `43bf…` | 438 920 м | 0 м к frozen | 0.954062244 | 0 |
| Current champion + preserve overlay | 438 920 м | 0 м к champion | 0.954062244 | 0 |

Все case 15 запуски прошли локальный interactor. Кандидат не изменяет `results/pipes/final/solution.cpp` и `src/pipes.cpp`.

## Синтетические продолжения

Для двух префиксов case 15 (`99 999` и `150 000` команд) сгенерированы по 20 продолжений по 8 192 команды. Каждый суффикс собран block-bootstrap-ом блоков по 128 событий из наблюдаемой широкой фазы case 15; длины и относительный ранг удаляемой трубы сохранялись, PID удалений переназначались по текущему активному набору. Отрицательная Δ длины траншеи означает улучшение.

| Префикс | Правило | Средняя Δ траншеи | Лучше / хуже / равно |
|---|---|---:|---:|
| До смены фазы | Phase, high-address tie | −16 м | 4 / 0 / 16 |
| До смены фазы | Preserve large gaps | −12 м | 9 / 11 / 0 |
| После смены фазы | Phase, high-address tie | +48 м | 9 / 10 / 1 |
| После смены фазы | Preserve large gaps | −226 м | 18 / 1 / 1 |
| Все 40 трасс | Preserve large gaps | −119 м | 27 / 12 / 1 |

Это диагностический, не независимый результат: продолжения получены из уже известного case 15 распределения. На исходной трассе экономии нет. Микрореплей напрямую запускал solver и проверял валидность команд/формат ответов, но не прогонял синтетические потоки через interactor.

## Open15 и holdout-v2 против актуального champion

Полная покейсовая таблица Open15; `Δ score` — изменение взвешенного score кандидата относительно champion.

| Case | Траншея champion → кандидат | Δ м | KPI champion → кандидат | Δ score |
|---:|---:|---:|---:|---:|
| 1 | 20 → 20 | 0 | 0.900000000 → 0.900000000 | 0 |
| 2 | 20 → 20 | 0 | 1.000000000 → 1.000000000 | 0 |
| 3 | 20 → 20 | 0 | 0.750000000 → 0.750000000 | 0 |
| 4 | 60 → 60 | 0 | 0.666666667 → 0.666666667 | 0 |
| 5 | 62 620 → 62 620 | 0 | 0.811881188 → 0.811881188 | 0 |
| 6 | 20 → 20 | 0 | 0.900000000 → 0.900000000 | 0 |
| 7 | 1 700 → 1 700 | 0 | 0.986470588 → 0.986470588 | 0 |
| 8 | 4 700 → 4 740 | +40 | 0.984468085 → 0.976160338 | −0.008307748 |
| 9 | 48 540 → 48 540 | 0 | 0.648949320 → 0.648949320 | 0 |
| 10 | 15 380 → 15 380 | 0 | 0.800000000 → 0.800000000 | 0 |
| 11 | 22 620 → 22 540 | −80 | 0.900132626 → 0.903327418 | +0.003194792 |
| 12 | 10 320 → 10 320 | 0 | 0.993120155 → 0.993120155 | 0 |
| 13 | 3 280 → 3 300 | +20 | 0.973170732 → 0.967272727 | −0.023592018 |
| 14 | 37 820 → 37 820 | 0 | 0.996932840 → 0.996932840 | 0 |
| 15 | 438 920 → 438 920 | 0 | 0.954062244 → 0.954062244 | 0 |
| **Итого** | **29.932085817 → 29.903380844** |  |  | **−0.028704973** |

На holdout-v2 champion набрал `5.135264324280`, overlay — `5.142514235910` (`+0.007249911630`). Изменились только case 2 (`−20 м`, `+0.000634058`) и case 8 (`−20 м`, `+0.006615854`). Набор уже использовался ранее; его плюс не компенсирует ухудшение Open15.

Все 15 Open15 и 12 holdout-v2 запусков прошли. Максимум solver CPU на Open15 — около `1.30 с`, RSS — менее `8 MiB`; лимиты `5 с / 256 MiB` соблюдены.

## Воспроизведение

Сборка и генерация кандидатов из корня `/Users/555tery/techarena`:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/phase_micro/source/phase_high_address_tie.cpp -o results/pipes/improvement/case15_fast_candidates/phase_micro/bin/phase_high_address_tie
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/phase_micro/source/phase_small_gap_tie.cpp -o results/pipes/improvement/case15_fast_candidates/phase_micro/bin/phase_small_gap_tie
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/phase_micro/source/preserve_large_gaps.cpp -o results/pipes/improvement/case15_fast_candidates/phase_micro/bin/preserve_large_gaps
python3 results/pipes/improvement/case15_fast_candidates/phase_micro/micro_replay.py
python3 results/pipes/improvement/case15_fast_candidates/phase_micro/micro_replay_extended.py
python3 results/pipes/improvement/case15_fast_candidates/phase_micro/make_preserve_gap_current_champion.py
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_fast_candidates/phase_micro/source/preserve_large_gaps_on_current_champion.cpp -o results/pipes/improvement/case15_fast_candidates/phase_micro/bin/preserve_large_gaps_on_current_champion
```

Полный Open15 и holdout-v2 сравнивались локально через `tools/pipes_harness.py` с `results/pipes/final/bin/interactor`, `--cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120`. Точные CSV/JSON каждого прогона находятся в `runs/` рядом с этим отчётом. Для Open15 использованы solver `results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs` и `results/pipes/improvement/case15_fast_candidates/phase_micro/bin/preserve_large_gaps_on_current_champion`; для holdout-v2 — те же два solver и `--tests data/pipes/synthetic/final-holdout-v2`.

Точные команды последнего сравнения:

```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name current_champion_open15 --interactor results/pipes/final/bin/interactor --tests data/pipes/open --out results/pipes/improvement/case15_fast_candidates/phase_micro/runs/current_champion_open15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_fast_candidates/phase_micro/bin/preserve_large_gaps_on_current_champion --name preserve_large_gaps_on_current_champion_open15 --interactor results/pipes/final/bin/interactor --tests data/pipes/open --out results/pipes/improvement/case15_fast_candidates/phase_micro/runs/preserve_large_gaps_on_current_champion_open15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name current_champion_holdout_v2 --interactor results/pipes/final/bin/interactor --tests data/pipes/synthetic/final-holdout-v2 --out results/pipes/improvement/case15_fast_candidates/phase_micro/runs/current_champion_holdout_v2 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_fast_candidates/phase_micro/bin/preserve_large_gaps_on_current_champion --name preserve_large_gaps_on_current_champion_holdout_v2 --interactor results/pipes/final/bin/interactor --tests data/pipes/synthetic/final-holdout-v2 --out results/pipes/improvement/case15_fast_candidates/phase_micro/runs/preserve_large_gaps_on_current_champion_holdout_v2 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

## SHA-256

- Актуальный champion source: `43bfbdadbae18ac180d1e59b6631342cfe1bef99190a449838f0470d6f220200`.
- Актуальный champion binary: `e4b79d8eb55a1fdc03a8c62505142ee615304401e821895bf6ab7f3712e54049`.
- Candidate source: `f1347624fc432f1487c2a9c10215b7c47a55582a18f060931e8547dd9a5ca18a`.
- Candidate binary: `6dd2e809701f6ef9bd64185bf17af3d3fc4f4420c52e0713e4d52b9eb3f94e69`.
- Frozen final source (не менялся): `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Canonical source (не менялся): `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.
- Case 15 input: `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`.
- Interactor: `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`.
- Synthetic replay CSVs: `micro_replay.csv` `27312dae279b1686af518d8c51b0fc9d64b41f8625bba5a32b7f98403f628919`; `micro_replay_extended.csv` `a222b065d253d6144cd9ea1f2e048b6d9f9eba800282becf86bc3ba357a356d5`.
- Phase high-address source/binary: `e0284a21a1d503028f15a434f2b6a0a18f05765076d7b5612182ae15cf76597f` / `7bc3bec5ef99c50a9d89193aa69955e8431e9eb606fbb717f1aa0e2da552e92f`.
- Phase small-gap source/binary: `9c083befe68f6268a478a18aa791bb0c771ea764ade106c423ad178d8d049fa8` / `1e949868a55bcce39263c174884053b3cefa41d02a371ea834542bf154f47c5a`.
- Preserve-gap overlay on frozen source/binary: `1ba18b76d84e199b2bc377b0721d087779ddb0d87be5883c4c99af1681d1fe35` / `f1b2361d9fdbc405a4b0c1f779b0b05582bc3fbbc420532d2a6eb14dfbe6f835`.
