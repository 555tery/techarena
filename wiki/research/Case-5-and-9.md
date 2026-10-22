# Cases 5 и 9

Оба теста были значимы в историческом разборе разрыва с лидером, но механизмы потерь и результаты локальных изменений различаются.

## Run-48: парный результат относительно frozen final

Изменение порога наблюдаемой серии с 46 до 48 подняло Open15 с `29.789717928594` до `29.790219562101` (`+0.000501633507`). В case 5 траншея сократилась на `140 м`; в case 9 выросла на `160 м`. Значения и подробности зафиксированы в [локальной qualification](../../results/pipes/improvement/run48_qualification/REPORT.md).

На 8 свежих синтетических потоках run-48 совпал с frozen final по KPI, траншее и judge output. Это нейтральный ограниченный transfer check, не оценка неизвестного распределения.

## Другие диагностики

- Case 5: [new policy](../../results/pipes/improvement/case5_new_policy/REPORT.md), [next analysis](../../results/pipes/improvement/case5_next/REPORT.md).
- Case 9: [adaptive policy](../../results/pipes/improvement/case9_adaptive/REPORT.md), [policy report](../../results/pipes/improvement/case9_policy/REPORT.md), [long-beam diagnosis](../../results/pipes/improvement/offline_longbeam_longanchors/REPORT.md).
- Обе темы в контексте всего набора: [диагностика 15 тестов](../../results/pipes/improvement/all_tests_diagnosis/REPORT.md).

Архивный PID-parity preprobe имел Open15 score `29.791529008364`, но его последующая локальная квалификация была остановлена пользователем и не завершена. Не считать его подтверждённым улучшением и не использовать имя теста/номер кейса в алгоритме.
