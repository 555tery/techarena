# Policy-conditioned rollout, depth 16: fresh-seed follow-up

## Статус

Это **post-hoc exploratory extension** после depth-4 пробы: там точная полная цель часто улучшалась при продолжении P4 после хода P4, но короткая оценка редко меняла выбор. Здесь проверено ровно одно изменение — длина rollout увеличена до **16 событий при 16 сценариях**. Остальная causal/history-only процедура и пара политик сохранены. Параметры по новым validation-данным не подбирались.

## Проверка и gate

Все train и validation потоки сгенерированы заново, на новых seed, не использованных в первом эксперименте. Всего 9 train и 18 validation-потоков по 1 800 команд: три профиля длин (`uniform`, `short-heavy`, `long-heavy`) × три политики удалений (`random`, `oldest`, `newest`), churn 0.48. Все 27 потоков сверены по каждой команде с бинарниками frozen-noMC и P4. Полные seed и SHA-256 находятся в [`input_manifest.json`](input_manifest.json).

Состояния выбраны из одной frozen-noMC trajectory через 60 команд после прогрева; сравниваются только различающиеся первые действия baseline и P4, если обе политики нашли внутренний fitting gap. Baseline-continuation оценщик продолжает оба первых действия baseline-политикой. Conditioned оценщик продолжает baseline-действие baseline-политикой, а P4-действие — P4. Для оценивания pairwise ranking обе используют одинаковые 16 сценариев, взятые только из уже наблюдённой истории. Известный suffix используется только как offline target.

Заранее применён gate: на новых целых validation streams paired-bootstrap 95% CI должен исключать ноль в пользу conditioned ranking по pairwise accuracy и top-1 regret; эффект не должен зависеть от единственного length-profile. Последнее проверяется направлением эффекта во всех трёх профилях; профильные интервалы также приведены ниже. Это exploratory подтверждение выбранной гипотезы, не формальная preregistered оценка.

## Результаты

Разность означает `conditioned − baseline-continuation`; bootstrap повторно выбирает целые потоки с равным весом, 20 000 реплик, seed `20261022`.

| Split | Candidate states | Информативные states | Pairwise accuracy, Δ (95% CI) | Top-1 regret, Δ м (95% CI) | Информативные потоки |
|---|---:|---:|---:|---:|---:|
| Train | 53 | 37 | +0.0625 [+0.0139, +0.1181] | −10.83 [−22.78, −2.22] | 6 / 9 |
| Validation | 115 | 86 | +0.0760 [+0.0387, +0.1172] | −12.17 [−23.27, −3.93] | 14 / 18 |

На validation 9 из 14 информативных потоков улучшили pairwise accuracy, ни один не ухудшил; 5 были равны. Для regret также 9 потоков улучшились, 0 ухудшились, 5 равны. Profile deltas направлены одинаково: long-heavy `+0.0278` accuracy / `−2.00 м` regret; short-heavy `+0.0708` / `−10.17 м`; uniform `+0.1429` / `−27.40 м`. На long-heavy профильные интервалы касаются нуля, тогда как short-heavy и uniform интервалы исключают ноль.

Проверка зависимости от одного профиля: по очереди исключён каждый profile, а paired stream bootstrap повторён на оставшихся. Во всех трёх случаях оба 95% интервала по-прежнему исключают ноль:

| Исключённый профиль | Осталось потоков / состояний | Accuracy Δ (95% CI) | Regret Δ м (95% CI) |
|---|---:|---:|---:|
| long-heavy | 9 / 57 | +0.1028 [+0.0532, +0.1551] | −17.83 [−32.96, −5.99] |
| short-heavy | 9 / 55 | +0.0789 [+0.0313, +0.1358] | −13.29 [−28.78, −2.30] |
| uniform | 10 / 60 | +0.0493 [+0.0167, +0.0875] | −6.08 [−12.34, −1.42] |

Значит, совокупный эффект не объясняется одним length-profile, хотя сам по себе long-heavy профиль подтверждён слабее.

### Выбор первых действий и flips

На 115 validation states baseline-continuation оценщик выбрал первый ход frozen baseline **101** раз и P4 **14** раз. Conditioned оценщик выбрал frozen baseline **86** раз и P4 **29** раз. Рекомендация изменилась в **15 / 115 (13.0%)** состояний, или **11 / 86 (12.8%)** информативных состояний. По точному mixed-policy suffix target лучшим оказался P4 ход в 85 состояниях, baseline — в 1, ещё 29 были равны; это hindsight target, а не онлайн-подсказка.

Продолжение P4 после своего первого хода уменьшило exact terminal target против baseline-продолжения в 78/115 состояниях, увеличило в 7, не изменило в 30; средняя разность составила **−62.43 м**. Это подтверждает исходную причину проверить более длинный rollout. Сам depth-16 оценщик меняет только 13% рекомендаций, но на новых синтетических потоках эти flips заметно повышают ranking качества.

**Gate пройден на данном синтетическом протоколе:** общие paired 95% интервалы положительны для accuracy и отрицательны для regret, а точечные дельты направлены в пользу conditioning во всех профилях. Это допускает отдельный следующий локальный этап, но не подтверждает score на официальных тестах и не снимает post-hoc статус. Open15, holdout, сайт и leaderboard не использовались.

## Стоимость и пределы

Все 27 потоков, replay и анализ заняли **16.06 с wall** на macOS arm64. Это диагностический runtime с точными полными suffix-target replay; он не является CPU/RSS замером contest solver. Лимиты решения 5 с CPU и 256 MiB на командных входах до 200 000 операций для этого прототипа не измерялись. Linux/GCC и candidate solver не запускались.

Состояния всё ещё выбираются только из frozen-noMC trajectory; тестируются два фиксированных policy action, не полный набор gap-кандидатов и не смешанная policy trajectory. Не делается вывод о достижении KPI без дальнейшей реализации и отдельной проверки.

## Воспроизведение

Из корня репозитория:

```sh
python3 results/pipes/improvement/policy_conditioned_rollout/depth16_fresh/generate_streams.py
mkdir -p results/pipes/improvement/policy_conditioned_rollout/depth16_fresh/bin
clang++ -O2 -std=c++20 -DMC_ROLLOUT_DISABLED results/pipes/final/solution.cpp -o results/pipes/improvement/policy_conditioned_rollout/depth16_fresh/bin/frozen_nomc
g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/strategies/policy4_baseline.cpp -o results/pipes/improvement/policy_conditioned_rollout/depth16_fresh/bin/p4
python3 results/pipes/improvement/policy_conditioned_rollout/depth16_fresh/depth16_probe.py --baseline results/pipes/improvement/policy_conditioned_rollout/depth16_fresh/bin/frozen_nomc --p4 results/pipes/improvement/policy_conditioned_rollout/depth16_fresh/bin/p4
```

Per-state ranking, выборы и flips: [`ranking_states.csv`](ranking_states.csv). Агрегаты и 27 transcript checks: [`summary.json`](summary.json). Источники, входы, бинарники, команды, hashes и измерения: [`manifest.json`](manifest.json).
