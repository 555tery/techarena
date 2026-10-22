# Маленький маршрутизатор поверх baseline

Старое решение сохранено без изменений в `baseline/solution.cpp`.
Этот прототип добавляет router только в обычную existing-gap ветку прежнего
allocator. Его continuation, история, индексы, резервирование, MC budget и
сильные правила остаются исходными. Сайт и отправки не используются.

Итог: [REPORT.md](REPORT.md). Порядок работы до измерений: [PROTOCOL.md](PROTOCOL.md).

## Карта файлов

- `build_fork.py` механически создаёт `src/baseline_fork.hpp` из точного baseline.
  Любое неожиданное изменение базового source вызывает ошибку; diff сохраняется.
- `src/router_members.inc` — причинные features, до четырёх routes, protected gates.
- `src/engine.cpp` — interactive driver и отдельно compile-gated offline labeler.
- `src/trained_router.hpp` / `train/final_fit/model.json` — сеть 128→16→1, 2 081 вес.
- `measure.py` — clone/force/full-suffix labels с исходным baseline continuation.
- `train/` — фиксированный trainer/exporter, команды и логи обоих fit.
- `data/manifest.json` — дизайн, seed и SHA synthetic inputs; final создан после freeze.
- `reports/candidate_snapshot.json` — source/model/binaries до full calibration gate.
- `reports/calibration_gate.json` — решение по полным calibration rollouts.
- `reports/model_freeze.json` — окончательные hashes до final и Open15.
- `reports/evaluation_*` — парные таблицы, usage и официальный локальный interactor.

## Сборка из корня проекта

```sh
python3 prototypes/pipes_baseline_router_v1/build_fork.py
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
  prototypes/pipes_baseline_router_v1/src/engine.cpp \
  -o prototypes/pipes_baseline_router_v1/bin/instrumented
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic -DUSE_ROUTER \
  prototypes/pipes_baseline_router_v1/src/engine.cpp \
  -o prototypes/pipes_baseline_router_v1/bin/router_candidate
```

`bin/router_candidate` — активная исследовательская модель. Она не считается
допущенной по одному положительному counterfactual score. При провале calibration
gate `bin/router_deploy` собирается с `-DUSE_ROUTER -DROUTER_ABSTAIN` и всегда
сохраняет baseline. Его побайтовое совпадение проверено отдельно.
Поле `deployable` в JSON trainer относится лишь к выбранной оценке одиночных
действий; окончательное решение хранится в `reports/calibration_gate.json`.

Offline labeler требует `-DOFFLINE_LABELS`; learned roll-in дополнительно требует
`-DUSE_ROUTER`. Без этого он откажется выдавать baseline states за model states.
Сборка production исключает чтение полного будущего входа. История будущего
используется только при offline targets, никогда в features.

## Воспроизведение и границы

`check_baseline.py`, `check_runtime.py`, `check_parity.py` и `src/check_branches.cpp`
проверяют exact baseline equivalence, prefix independence, inference, реальные
protected no-ops, clone independence и физическую допустимость клеточной моделью.
Точные команды обучения записаны в `train/*_fit/train.log`; нужен Python с NumPy.
Использован существующий bundled runtime, ничего не устанавливалось.

`evaluate.py calibration|final|open15` проверяет сохранённые hashes и отказывается
перезаписывать готовый результат. Open15 разрешён только как один post-freeze
diagnostic и никогда не используется для выбора gates, features, weights или margin.
Свежие synthetic inputs не являются официальным скрытым набором. Механизмы
отложенных семейств уже встречались в предыдущем эксперименте; это проверка
свежих входов, а не доказательство переноса на совершенно неизвестные механизмы.
