# Квалификация и диагностика прежних вариантов

Это навигация по отдельным проверкам; их версии не подменяют текущую lab-базу.

- [Run-48 qualification](../../results/pipes/improvement/run48_qualification/REPORT.md) — локальный Open15, holdout-v2 и development streams; отдельный отчёт.
- [Первый MC-вызов: exact-suffix diagnosis](../../results/pipes/improvement/current_action_forecast_diagnosis/REPORT.md) — 48/48 replay валидны; нулевой shortlist regret на девяти первых MC-состояниях и единственный sampled gain 160 м в case 5. Только hindsight, без online-вывода; см. [полную таблицу действий](../../results/pipes/improvement/current_action_forecast_diagnosis/per_action.csv).
- [Совместное удаление соседних труб](../../results/pipes/improvement/joint_deletion_signal/LOCAL_DIAGNOSTICS_REPORT.md) — Open15 не установил улучшения прогноза; ранее переиспользованный holdout-v2 положителен, но не подтверждает переносимость. Проверка прогноза, не allocator-эксперимент.
- [Свежие синтетические потоки для run-48](../../results/pipes/improvement/run48_synthetic_independent/REPORT.md) — нейтральное сравнение на восьми новых потоках.
- [Case 9 next report](../../results/pipes/improvement/case9_next/REPORT.md) — отдельный отчёт по ветке case 9. PID-parity preprobe прошёл локальную факторную проверку, но остаётся исследовательским; см. [карту артефактов](../solution/Artifacts.md) и [отчёт квалификации](../../results/pipes/improvement/pid_lane_run48_factorial/REPORT.md).
- [Инвентаризация архива run-48](../../results/pipes/improvement/run48_archive_inventory/NO_GO.md) — создана до последующего разрешения qualification; читать вместе с более поздними материалами.
- [Факторная проверка PID-lane × порог 46/48](../../results/pipes/improvement/pid_lane_run48_factorial/REPORT.md) — PID/46 улучшил Open15 на 0.001811080 к frozen final только за счёт case 5; holdout и синтетический перенос нейтральны. Переносимость проверена на Linux/GCC в [отдельном gate](../../results/pipes/improvement/pid_lane_run48_factorial/linux_gcc_check/REPORT.md); алгоритмическое преимущество не обобщилось.

[Общий индекс](Index.md) · [Текущий статус](../project/Current-state.md)
