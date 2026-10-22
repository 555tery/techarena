# Policy-conditioned rollout: synthetic gate no-go

## Вывод

**No-go для продвижения к Open15/holdout.** На свежей validation-выборке короткий rollout, который продолжает действие P4 политикой P4, лишь немного улучшил ranking относительно оценки обоих первых ходов с продолжением frozen baseline. Парный 95% интервал включает ноль и для pairwise accuracy, и для top-1 regret. Улучшение не проявилось на long-heavy потоке и потому не подтверждено для всех профилей длин.

Это отдельная проверка относительно [`joint_gap_portfolio_probe`](../joint_gap_portfolio_probe/REPORT.md): там каждый альтернативный первый ход продолжался baseline-политикой. Здесь один из первых ходов выбирается P4 и после него сценарий продолжает сам P4. Не менялись canonical/frozen исходники, официальные входы и тесты; платформа и leaderboard не открывались.

## Протокол

- Frozen baseline: `results/pipes/final/solution.cpp`, собранный с `MC_ROLLOUT_DISABLED`, как в предыдущем joint-gap probe. P4: `results/pipes/improvement/strategies/policy4_baseline.cpp`.
- Использованы свежие полные потоки по 1 800 команд, churn 0.48, без batch-drain: 9 train-потоков и 18 validation-потоков. В каждом split представлены три профиля длин (`uniform`, `short-heavy`, `long-heavy`) и три политики удалений (`random`, `oldest`, `newest`). В validation — два разных seed на каждую пару профиль × удаление. Потоки не пересекались по seed; полные SHA и параметры записаны в [`input_manifest.json`](input_manifest.json).
- Состояния снимались на baseline-траектории с команды 180, далее каждые 60 команд. Включались только состояния, где baseline и P4 выбрали разные первые действия и оба нашли подходящую внутреннюю дырку. Поэтому проверяется ranking различающихся placement-действий, а не расширение хвоста.
- Контрольный оценщик продолжает оба первых действия baseline-политикой на 16 причинно выбранных сценариях глубины 4. Условный оценщик продолжает baseline-действие baseline-политикой, а P4-действие — фиксированной P4-политикой. Обе оценки используют одинаковые сценарии из уже наблюдённой истории.
- Offline target использует известный оставшийся суффикс только для оценки: baseline-действие продолжается baseline-политикой, P4-действие — P4. Для sanity отдельно сохранена цель, где оба хода продолжаются baseline. Метрики сравнивают два предсказания на одной и той же смешанной policy-conditioned цели.
- Сначала каждый Python replay сверялся по всем командам с бинарником соответствующего source. Совпали все **27/27** целых потоков для обоих алгоритмов. Validation не использовалась для выбора параметров.

## Результат

Основная величина — изменение метрики `conditioned predictor − baseline-continuation predictor`; интервалы построены paired percentile bootstrap по целым потокам с равным весом потоков.

| Split | Информативные состояния | Pairwise accuracy, Δ (95% CI) | Top-1 regret, Δ м (95% CI) | Потоки с информативными состояниями |
|---|---:|---:|---:|---:|
| Train | 34 / 50 | +0.0556 [0.0000, +0.1667] | −1.11 [−3.33, 0.00] | 6 / 9 |
| Validation | 82 / 138 | +0.01575 [0.00000, +0.03685] | −0.99 [−2.55, 0.00] | 14 / 18 |

Ни один validation интервал не исключает ноль. По профилям validation pairwise-дельта составила `0.000` на long-heavy, `+0.035` на short-heavy и `+0.009` на uniform. На всех трёх профильных bootstrap-интервалах граница равна нулю; убедительного эффекта без зависимости от профиля не получено.

При этом сама целевая траектория P4 отличалась от baseline-continuation: для P4 первого хода полное продолжение P4 дало меньший конечный прирост траншеи в 84 из 138 состояний; средняя разность против продолжения того же P4-хода baseline-политикой была −43 м на состояние. Однако 4-событийный rollout менял выбранный им первый ход лишь в 3 из 138 состояний. Это сигнал о возможной ценности длинного продолжения, но текущий causal ranking его не извлёк. Он не оправдывает более дорогой rollout без отдельного перспективного gate.

**Gate не пройден:** 95% интервалы включают ноль, нет устойчивого положительного эффекта во всех профилях. Open15/holdout не запускались. Полная метрика по всему суффиксу — hindsight target; она не является доступной финальному онлайн-решению.

## Стоимость и ограничения

Снятие 188 состояний, причинные rollout-оценки и точный replay оставшихся суффиксов заняли 17.85 с wall на macOS arm64. Это не оценка CPU solver-а: основная часть диагностики проигрывает точные суффиксы для counterfactual-целей. Для проверки ranking вычисление не оказалось чрезмерным; Linux/GCC, лимит 5 секунд на 200 000 команд и ресурсы потенциального solver-кандидата не проверялись, потому что gate отрицательный и C++-кандидат не создавался.

Данные получены только на состояниях baseline-траектории. P4-state portfolio, оценка всех возможных gap-ов и первая вставка без подходящей внутренней дыры не исследовались. Вывод относится к этой паре политик, 4-событийному прогнозу и заданному синтетическому протоколу, а не ко всем policy-conditioned методам.

## Повторение

Из корня репозитория:

```sh
python3 results/pipes/improvement/policy_conditioned_rollout/generate_streams.py
mkdir -p results/pipes/improvement/policy_conditioned_rollout/bin
clang++ -O2 -std=c++20 -DMC_ROLLOUT_DISABLED results/pipes/final/solution.cpp -o results/pipes/improvement/policy_conditioned_rollout/bin/frozen_nomc
g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/strategies/policy4_baseline.cpp -o results/pipes/improvement/policy_conditioned_rollout/bin/p4
python3 results/pipes/improvement/policy_conditioned_rollout/policy_conditioned_probe.py --baseline results/pipes/improvement/policy_conditioned_rollout/bin/frozen_nomc --p4 results/pipes/improvement/policy_conditioned_rollout/bin/p4
```

Полные per-state значения — [`ranking_states.csv`](ranking_states.csv), агрегаты и проверки transcript — [`summary.json`](summary.json), source/input/output hashes и окружение — [`manifest.json`](manifest.json).
