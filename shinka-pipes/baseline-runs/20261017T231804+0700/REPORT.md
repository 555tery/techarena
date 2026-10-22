# Baseline: synthetic search, без эволюции

Дата: 2026-10-17T23:18:04.397384+07:00. Выполнен один сквозной прогон baseline через штатный search evaluator.

**Результат: 32/32 корректны, fitness `0.914983819101` из 1.**
Все 1 900 000 команд обработаны. Максимум solver CPU — 1.189802 s (< 5 s); RSS — 6.969 MiB (< 256 MiB).
Полное wall time evaluator со сборкой — 76.125 s; суммарный CPU solver — 10.272960 s.

## Что проверено

- Baseline скомпилирован в C++20; официальный interactor собран из закреплённых исходников.
- Пройдены 32 фиксированных search-потока, 16 семейств. Нет пропусков или дубликатов.
- Хеши source и входов совпали с манифестами; CPU/RSS измерены для каждого случая.
- Fitness независимо пересчитан из длин траншеи и объёмных нижних границ; совпал с evaluator.
- Эволюция не запускалась, запросов к модели — 0. Validation и Open15 не читались и не запускались этим прогоном.

## Метрика по семействам

| Семейство | Среднее B/T |
|---|---:|
| size_biased_deletion | 0.773809524 |
| drifting_sizes | 0.832677960 |
| uniform_churn | 0.857289442 |
| short_heavy | 0.865497076 |
| additive_cohorts | 0.866069206 |
| long_heavy | 0.877950311 |
| distribution_switch | 0.895644283 |
| geometric_cohorts | 0.897352617 |
| bimodal | 0.950832156 |
| size_lifetimes | 0.953041848 |
| section_boundaries | 0.960168102 |
| fifo | 0.965978277 |
| large_live_set | 0.967489837 |
| lifo | 0.986486486 |
| burst_drain | 0.989583333 |
| striped_recycling | 0.999870647 |

## Воспроизводимость и границы вывода

Baseline source SHA256 с EVOLVE-комментариями: `38b465cdbd570c4826d863ab8213f9b54352d7d0d783ba74842ece0c5a2668ce`.
Исходный source без добавленных комментариев: `c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c`.
Search manifest SHA256: `f02098b0140bd47146cd63ae8632b48b454ac31ce7e10e3e7e65a354a61a8336`.

Fitness — среднее по семействам от среднего `B/T` по их потокам; `B=20*ceil(peak_live_volume/20)`. Это другая шкала, чем Open15 score; объёмная граница не обязана быть достижимой.
Измерен baseline на фиксированном поисковом наборе. Улучшение алгоритма и перенос на другие данные здесь не проверялись.

Точная команда, compiler/version/flags, timestamps и хеши: `manifest.json`. Метрики: `evaluation/metrics.json`; полные покейсовые данные: `evaluation/harness/summary.json` и `cases.csv`; независимая проверка: `audit.json`.

Повтор запускает только baseline/search (без Shinka runner и модели):

```sh
/Users/555tery/techarena/shinka-pipes/.venv/bin/python /Users/555tery/techarena/shinka-pipes/task-synthetic/evaluate.py --program_path /Users/555tery/techarena/shinka-pipes/baseline-runs/20261017T231804+0700/baseline.cpp --results_dir /Users/555tery/techarena/shinka-pipes/baseline-runs/20261017T231804+0700/evaluation
```
Для повтора следует указать новую папку результатов, сохранив текущий прогон.
