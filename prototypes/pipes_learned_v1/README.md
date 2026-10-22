# Отдельный learned Pipes prototype v1

Все действия локальны. Сайт и платформа не используются. Старое решение,
canonical source и frozen final сохранены. Итог эксперимента — в [REPORT.md](REPORT.md),
заранее зафиксированный порядок работы — в [PROTOCOL.md](PROTOCOL.md).

## Основные файлы

- `baseline/solution.cpp` — точная копия lab baseline, SHA `c1994511…bb736c`.
- `src/allocator.hpp` — новое общее ядро: физические gaps, legal actions, causal features.
- `src/engine.cpp` — интерактивный solver; offline labeler доступен только при `OFFLINE_LABELS`.
- `src/trained_model.hpp` — одна сеть 128→32 ReLU→1 и зафиксированный margin.
- `train/final_fit/` — веса JSON, training log, диагностика и export manifest.
- `data/design_final_prerun.json` — заранее заданные семейства, seed и длины.
- `data/manifest.json` — происхождение и SHA всех входов; final создан после model freeze.
- `reports/model_freeze.json` — исходники, веса, binary hashes до final/Open15.
- `reports/evaluation_final/`, `reports/evaluation_open15/` — парные полные прогоны.

Один раунд добавления состояний из собственной траектории хранится под именем
`dagger_expanded`. Продолжение при разметке остаётся best-fit, поэтому это
ограниченная агрегация состояний, а не реализация всех предпосылок DAgger/AggreVaTe.

## Сборка и проверка

Из корня проекта, без дополнительных библиотек для production solver:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
  prototypes/pipes_learned_v1/src/engine.cpp \
  -o prototypes/pipes_learned_v1/bin/generic
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic -DUSE_LEARNED \
  prototypes/pipes_learned_v1/src/engine.cpp \
  -o prototypes/pipes_learned_v1/bin/learned
python3 prototypes/pipes_learned_v1/check_runtime.py
```

`measure.py` собирает полные suffix labels, `train/train_mlp.py` обучает сеть.
Точные команды обучения сохранены в `train/*_fit/train.log`; нужен Python с NumPy.
В проведённом эксперименте использован уже имевшийся bundled runtime без установки пакетов.

`check_parity.py MODEL PROBE CSV REPORT` проверяет scores и выбор действий на всех
строках CSV. `train/export_model.py` позволяет атомарно переэкспортировать JSON без
повторного обучения. Округления порога используют float32, как production C++.

`evaluate.py final` и `evaluate.py open15` запускают официальный локальный interactor
для трёх solver. Они проверяют hashes freeze и отказываются затирать готовый результат.
Повторная генерация final или настройка модели по нему не входят в этот эксперимент.

## Границы вывода

Labels содержат будущее только как offline target. В solver входят текущая геометрия
и уже наблюдавшаяся история. Test/stream ID, seed, action index и диагностический
`kind` не входят в 128 features. Разметка измеряет одну замену действия с общим
best-fit suffix; такие выигрыши нельзя складывать или выдавать за online KPI.
Calibration выбирает epoch/margin и поэтому не является независимой проверкой.
