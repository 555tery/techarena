# Case 15: фрагментация

## Зафиксированное состояние

В отчёте от 17 октября 2026 г. для frozen final указано: нижняя объёмная граница траншеи `418 780 м`, фактическая траншея `438 920 м`, разрыв `20 140 м`. Score кейса — `9.540622437 / 10`.

На EOF отчёт насчитал `4 954` свободных интервала общей длиной `20 163 м`: `4 027` deletion-only (`17 669 м`) и `927` mixed (`2 494 м`). В большинстве случаев поздняя труба не помещалась в отдельные интервалы, хотя общий свободный объём был достаточен.

## Что проверяли

- [Interval lineage](../../results/pipes/improvement/case15_interval_lineage/REPORT.md) — происхождение интервалов и их использование.
- [Surviving-gap ranks](../../results/pipes/improvement/case15_survivor_rank/REPORT.md) — ранги подходящих surviving gaps.
- [Точная телеметрия candidate/lineage](../../results/pipes/improvement/case15_exact_candidate_telemetry/README.md) и [аудит разнообразия равных gap-ов](../../results/pipes/improvement/case15_exact_candidate_telemetry/candidate-diversity-review.md) — проверка решений на baseline-траектории до первых последующих расширений.
- [Case 15 policy screen](../../results/pipes/improvement/case15_policy/REPORT.md) и [новые локальные правила](../../results/pipes/improvement/case15_new_policy/REPORT.md).
- [Фазовый tie и сохранение крупных gap](../../results/pipes/improvement/case15_fast_candidates/phase_micro/REPORT.md) — case 15 нейтрален, synthetic micro-replay положителен только как диагностический сигнал; overlay проиграл актуальному Open15 champion.
- [All-tests diagnosis](../../results/pipes/improvement/all_tests_diagnosis/REPORT.md) — нижние границы и вес каждого теста.

## Вывод и ограничения

Новая локальная проверка 17 октября на более поздней lab-базе (case15 438 640 м, Open15 30.074288) отвергла [deletion-seam policy](../../results/pipes/improvement/case15_coalescence_local_20261017/REPORT.md): после выбора на независимом development и freeze вариант дал 438 820 м, мелкие дыры ≤7 м выросли с 17 971 до 18 000 м. На 12 sealed streams mean ΔKPI −0.001873, 95% CI включает ноль. Frozen final из первого раздела не менялся.

Фрагментация подтверждена, но причинное онлайн-правило с устойчивой экономией не найдено. Гипотеза о дополнительном правом равнодлинном кандидате была проверена через rollout: кейс 15 остался на 438 920 м, а Open15 упал на 0.022677485 балла из-за case 7 (+40 м); вариант остановлен как no-go. Hindsight и offline beam используют будущее и служат только диагностикой; их результат нельзя выдавать за достижимый score онлайн-алгоритма. Точные версии и дата отчёта указаны в самих исследованиях.
