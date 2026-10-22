# Маленький маршрутизатор поверх baseline

17 октября 2026. Прототип завершён, улучшение не подтверждено. Работа полностью
локальная; платформа, рейтинг и отправки не использовались.

## Архитектура и измерение

Точная копия lab baseline c1994511…bb736c с механически добавленным hook.
Сохранены slab/cohort, alignment, geometric/rearmed, capacity, parity, LIFO,
история, Fenwick, MC budgets и расширение. Router выбирает до четырёх локальных
вариантов только в обычной existing-gap ветке каждый 16-й placement.

Сначала клонировалось полное состояние и измерялось одно forced action с тем же
полным реальным suffix и **исходным baseline continuation**. Train: 1 882 состояния,
4 466 действий; 444 состояния с gain≥20 м; mean hindsight gain 16.142 м, median 0.
Это не online gain, не аддитивная величина и не предел всех изменений baseline.

Обучена MLP 128→16→1 (2 081 параметр). Один aggregate-data round собственной
траектории дал 247 новых состояний после удаления 196 точных дубликатов.
Итого 5 103 действия / 2 129 состояний / те же 64 train input groups.
Два fit по одному recipe; final epoch 13, margin 0.5. Calibration labeled saving
+0.195 м/state не перенеслась в полный алгоритм.

## Результат и safety gate

Full calibration: 16 потоков, 5 побед /3 поражения /8 равенств;
family-macro ΔKPI −0.18332 п.п. По заранее заданному gate кандидат отклонён.
Для использования оставлен исходный baseline; abstaining router отдельно повторил
его stdout на 80 потоках /576k команд.

После model/source/binary freeze созданы 24 fresh final inputs (12k/30k/200k):
7 побед /12 поражений /5 равенств; ΔKPI −0.01932 п.п., exploratory family-bootstrap
95% interval [−0.15407; +0.12972] п.п. Он пересекает ноль, улучшение не подтверждено.
Семейства отложены относительно текущего train, но их механизмы использовались
в прошлом прототипе; это свежие входы, а не неизвестные всему проекту процессы.

| Solver | Один post-freeze локальный Open15 | Case 15, м |
|---|---:|---:|
| Исходный baseline | 30.074287976406 | 438 640 |
| Отключённый router | 30.074287976406 | 438 640 |
| Активный router | 29.995671715360 | 438 740 |

Open15: 0 побед /5 поражений /10 равенств; цель 30.5 не достигнута.
После этих измерений gates, weights и threshold не менялись. Сохранение сильных
веток не гарантирует прежний score при изменении ранней fallback геометрии.

## Проверки и артефакты

Все 165 evaluation runs корректны и в лимитах. Forced checks: 32k команд,
1 179 ветвлений и 195 protected no-ops; Python/C++: 0 choice mismatches на
509 calibration states. Проверены prefix independence и отсутствие future reader
в production. Исходный baseline, canonical/frozen и прежний learned-v1 сохранены.

- [Полный отчёт](../../prototypes/pipes_baseline_router_v1/REPORT.md),
  [протокол](../../prototypes/pipes_baseline_router_v1/PROTOCOL.md),
  [manifest](../../prototypes/pipes_baseline_router_v1/manifest.json).
- [Safety gate](../../prototypes/pipes_baseline_router_v1/reports/calibration_gate.json),
  [final](../../prototypes/pipes_baseline_router_v1/reports/evaluation_final/summary.json),
  [Open15](../../prototypes/pipes_baseline_router_v1/reports/evaluation_open15/summary.json).
