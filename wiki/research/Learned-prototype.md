# Отдельный learned prototype v1

17 октября 2026. Прототип завершён и отклонён для замены baseline. Работа полностью
локальная; сайт, рейтинг и отправки не использовались. Новые поиски по final не запущены.

## Полный локальный результат

| Solver | Open15 / 32.1 | Case 15, м |
|---|---:|---:|
| Сохранённый lab baseline | 30.074287976406 | 438 640 |
| Новое общее ядро, best-fit | 28.375837599373 | 441 520 |
| То же ядро + MLP | 28.311211422579 | 441 440 |

Сеть дала −80 м в case 15 против generic, но +2 800 м против старого baseline.
Её отдельный вклад в Open15 отрицателен: −0.064626176794 против generic.
Остальная разница с baseline связана с заменой прежнего алгоритма общим ядром.
Цель 30.5 не достигнута. Baseline, canonical и frozen final сохранены.

## Сначала измерение, затем обучение

На train исследованы 8 133 состояния / 125 588 действий: одна форсированная замена
и одинаковый полный suffix с best-fit продолжением. В 3 875 состояниях лучшее
действие задним числом экономило ≥20 м; средний headroom 42.52 м, медиана 0.
Это условный hindsight effect, который нельзя складывать или выдавать за online KPI.

Обучена MLP 128→32 ReLU→1, 4 161 параметр. После одного раунда состояний собственной
траектории: 157 203 действия / 10 176 состояний / 128 train inputs. Calibration:
24 других входа; выбраны epoch 15 и margin 0.5. Диагностический выигрыш +0.1569 м/state
при headroom 34.70 м/state оказался слабым и не перенёсся в полный rollout.

## Независимая проверка

Восемь новых семейств, по 12k/30k/200k команд: 24 входа, созданных после model freeze.
MLP против generic: −0.09226 п.п. KPI, exploratory family-bootstrap 95% interval
[−0.18408; −0.00963] п.п.; 4 победы, 14 поражений, 6 равенств.
На 200k: 6 поражений и 2 равенства. Generic без сети на этих семействах в среднем
сильнее старого baseline; это преимущество нового ядра, а не обучения.

Все 117 парных evaluation runs корректны и в лимитах. Максимум learned CPU —
1.851 с; RSS — 12.656 MiB. Экспорт Python/C++: 0 расхождений действий на всех
1 520 calibration states. Проверены физические инварианты, prefix independence,
model-disabled equivalence и отсутствие offline reader в production.

## Артефакты и ограничения

- [Полный отчёт](../../prototypes/pipes_learned_v1/REPORT.md),
  [протокол до оценки](../../prototypes/pipes_learned_v1/PROTOCOL.md),
  [manifest](../../prototypes/pipes_learned_v1/manifest.json).
- [Frozen model/source/binary hashes](../../prototypes/pipes_learned_v1/reports/model_freeze.json).
- [Новые семейства](../../prototypes/pipes_learned_v1/reports/evaluation_final/summary.json),
  [Open15](../../prototypes/pipes_learned_v1/reports/evaluation_open15/summary.json).

Набор из восьми вручную заданных семейств — ограниченный pilot. Отрицательный результат
относится к данной модели, features, labels и cadence; он не доказывает бесполезность
нейросетей вообще. После final/Open15 solver и веса не менялись.
