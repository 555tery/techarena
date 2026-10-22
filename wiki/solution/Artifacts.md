# Артефакты и происхождение версий

| Обозначение | Путь | SHA-256 / оценка | Назначение |
|---|---|---|---|
| Canonical source | `src/pipes.cpp` | `526ba58e…dfec8` | Источник для обычных корневых Make targets; не frozen final. |
| Frozen final | `results/pipes/final/solution.cpp` | `c4b737b9…32a991`; `29.789717929 / 32.1` | Проверенный закреплённый артефакт. |
| Run-48 | `results/pipes/improvement/run48_qualification/sources/run-48.cpp` | `95d662ff…55b39`; `29.790219562 / 32.1` | Порог серии 48 вместо 46; отдельный кандидат и отдельная отправка. |
| PID-parity preprobe / PID-46 | `results/pipes/improvement/case9_next/preliminary_pid_lane_excluded/source/proactive_pid_lanes_preprobe.cpp` | `1a643a2b…f55f59`; `29.791529008 / 32.1` | Прошёл локальные Open15/holdout и Linux/GCC 14.2 gate; +0.001811080 к c4 на Open15 за счёт case 5, но holdout и свежие потоки нейтральны. Исследовательский кандидат, не продвигается. См. [факторный отчёт](../../results/pipes/improvement/pid_lane_run48_factorial/REPORT.md) и [Linux/GCC gate](../../results/pipes/improvement/pid_lane_run48_factorial/linux_gcc_check/REPORT.md). |

Полные SHA и сборка frozen final находятся в [final README](../../results/pipes/final/README.md) и [manifest](../../results/pipes/final/manifest.json). Не подменяй артефакты копированием в `src/`; если пользователь возобновит работу, сначала сверяй версии и hashes.
