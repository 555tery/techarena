# Case 5 relative parity + scale-gated expansion composition

Дата: 2026-10-18. Все проверки локальные; сайт и Docker не использовались.

## Результат

Композиция двух уже существовавших причинных механизмов дала **30.0716292112 / 32.1** на локальном Open15, 15/15 тестов пройдены. Это на **+0.0018769952** выше parity-only кандидата (30.0697522160) и на **+0.0266630165** выше предшествовавшего scale-gated лидера (30.0449661947). Цель 30.3 пока не достигнута: разрыв — **0.2283707888**.

| Вариант | Open15 | Изменение к parity-only |
|---|---:|---:|
| scale-gated expansion до case 5 доработки | 30.0449661947 | −0.0247860213 |
| относительный parity predictor | 30.0697522160 | 0 |
| parity predictor + scale-gated expansion | **30.0716292112** | **+0.0018769952** |

Сравнение по отдельным кейсам показывает, что композиция сохранила выгоду case 5 и восстановила эффект scale-gate на case 15, заплатив за это 40 м на case 14:

| Кейс | Scale-gated, м | Parity-only, м | Композиция, м | Дельта композиции к parity-only |
|---:|---:|---:|---:|---:|
| 5 | 56 040 | 54 440 | 54 440 | 0 м |
| 14 | 37 860 | 37 820 | 37 860 | +40 м |
| 15 | 438 640 | 438 920 | 438 640 | −280 м |

Остальные 12 кейсов совпали у всех трёх вариантов. В score-вкладах composition относительно parity-only: case 14 **−0.0042131340**, case 15 **+0.0060901292**, чистый итог **+0.0018769952**.

## Отдельные проверки 14/15

- Case 14: KPI 0.9958795563, траншея 37 860 м, CPU 0.397587 с при отдельном запуске, RSS 3.375 MiB.
- Case 15: KPI 0.9546712566, траншея 438 640 м, CPU 2.001397 с при отдельном запуске, RSS 8.421875 MiB.
- Оба завершились успешно в лимитах 5 CPU-с / 256 MiB.

## V2 synthetic staircase suite

Проверены все восемь ранее объявленных V2 потоков; parity predictor активировался в каждом. Число `COHORT_START` из сохранённой диагностической трассы: early_stop_rel1 — 7, even_count_rel0_full — 5, late_stop_rel0 — 9, odd_count_rel0_full — 5, odd_count_rel1_full — 15, phase_shift_varcounts_rel1 — 9, two_phase_rel0 — 4, varcounts_rel0_full — 5.

Композиция дала **точный tie с parity-only на всех 8 V2 потоках** (сумма взвешенных score 6.0974448723; приращение композиции 0). Это говорит, что scale-gate не добавил выгоды на этом наборе, но и не добавил новых регрессий относительно parity-only. При этом parity-only и композиция вместе сохраняют ранее зафиксированную слабость относительно A+B: два потока `odd_count_rel0_full` и `odd_count_rel1_full` регрессируют, итоговая разница на V2 — **−0.1142971111**. Поэтому это Open15-положительный экспериментальный вариант, а не доказательство переносимости.

## Ресурсы и исполнение

Полный Open15: максимум по кейсам **1.743995 CPU-с** и **9.75 MiB RSS**. Все 15 кейсов `ok`, CPU/RSS лимиты не превышены. Прогоны выполнены на macOS arm64 с Apple clang 17.0.0; Linux/GCC отдельно не проверялся.

## Реализация и контрольные хеши

Композиция — копия parity-only источника с точечным переносом механизма expansion gate из scale-gated версии: активная труба индексируется по правому концу, проверяются наблюдённая LIFO deletion confidence и молодой сосед на краю хвоста; при достаточной уверенности новая секция размещается справа. Порогов и условий gate не подбирали заново.

- A+B ancestor: `../case5_additive_next_alignment_20261017/src/staircase_plus_additive_next_alignment.cpp`, SHA-256 `4c3a3590eb1ad4251640af32f10f7e5b506b8cfac8ee6b9d0edaa6d4e231caae`.
- Parity-only исходник, сохранён без изменений: `src/relative_cohort_prediction.cpp`, SHA-256 `efa587a7181ba4098b3d656fa26c9f681aff4603dd7d16d42ca20c543779b86d`.
- Scale-gate исходник, сохранён без изменений: `../case15_expansion_edge_cf/source/lifo_young_offset_scale_gt4096.cpp`, SHA-256 `a280146cdc55c0fe8fbb6d4b7fda158f4e2189fa3463ce9d046f02a070a3571a`.
- Композиция: `src/relative_cohort_plus_scale_gate.cpp`, SHA-256 `b1712f18ff3ecfb1e63e86eed038dea32e1b597c94b0d54a7d07f5836c120bf5`.
- Бинарник композиции: SHA-256 `f7ec39aa5a419d0dadb40a754326eea6a6277fcca49290c89d7080205477228c`.

Полные команды запуска, test hashes, per-case scores и результаты сохранены в `manifest.json` и `runs/composition_open15/`, `runs/composition_case14/`, `runs/composition_case15/`, `runs/composition_relative_v2/`.
