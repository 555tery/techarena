# Policy-conditioned rollout candidate: локальная проверка

## Решение

**NO-GO.** Кандидат прошёл полный интерактивный протокол, но проиграл baseline-continuation selector и frozen-final на Open15 и holdout-v2. Новую synthetic validation не запускал: локальный score gate не пройден. Код оставлен отдельно для воспроизведения; frozen final, canonical solver, сайт и данные платформы не менялись.

Это receding-horizon MPC: на каждом реальном размещении сравнивается первый ход frozen-noMC с первым ходом P4; каждый ход продолжается своей фиксированной политикой в 16 сценариях длины 16. Выбранный первый ход выполняется, а на следующем размещении решение рассчитывается заново. Алгоритм не принимает обязательство следовать выбранной политике на реальном будущем.

## Сравнимые результаты

Candidate, frozen-noMC и baseline-continuation selector повторно запускались локально через один interactor. Для frozen-final использованы ранее сохранённые локальные harness результаты; покейсовые input SHA-256 совпали у всех четырёх вариантов. Полные input hashes, trench, KPI и разности находятся в [`comparison.csv`](comparison.csv) и [`comparison.json`](comparison.json).

| Набор | Policy-conditioned | Frozen-noMC | Baseline-continuation selector | Frozen-final | Δ к frozen-final |
|---|---:|---:|---:|---:|---:|
| Open15, сумма / 32.1 | 29.759356729 | 29.748404535 | 29.770563625 | **29.789717929** | **−0.030361200** |
| Holdout-v2, сумма / 12 | 5.135142555 | 5.135100030 | **5.135410591** | 5.135264324 | −0.000121769 |

Conditioning улучшил frozen-noMC на Open15 на `+0.010952194`, но проиграл selector-контролю на `−0.011206897` и frozen-final на `−0.030361200`. На holdout прирост к frozen-noMC составил только `+0.000042525`; кандидат проиграл selector-контролю на `−0.000268036` и frozen-final на `−0.000121769`. Это не переносимый выигрыш по целевому KPI.

Относительно frozen-final на Open15 изменились только случаи 7 и 12: кандидат выкопал на 40 м и 20 м больше соответственно. На holdout отличаются случаи 1 (`+20 м` траншеи), 7 (`−20 м`) и 10 (`+20 м`). В остальных случаях итоговая траншея совпала.

### Протокол и ресурсы

| Проверка кандидата | Open15 | Holdout-v2 |
|---|---:|---:|
| Полных ответов принято | 15/15 | 12/12 |
| Максимум CPU | 1.001944 с | 0.188043 с |
| Максимум RSS | 7.234375 MiB | 4.343750 MiB |
| Превышения 5 с / 256 MiB | 0 / 0 | 0 / 0 |

Open case 15 содержит ровно 200,000 команд. На нём solver использовал 16/16 rollout decisions, 12,288 continuation transitions и занял `1.001944 s CPU`, `7.234375 MiB RSS`. Бюджет ограничен причинно по истории и текущему состоянию: минимум 32 наблюдённых события, не более 64 дыр и 1,024 активных труб, максимум 16 оценок за поток. На строку stdout interactor проверял точное число целых чисел; после команды `0` лишних ответов не было. Исходные входы и принятые ответы сохранены в подкаталогах `runs/`.

### Выборы и переключения

| Набор | Оценённых пар действий | P4 выбрал conditioned selector | P4 выбрал baseline selector | Рекомендации разошлись |
|---|---:|---:|---:|---:|
| Open15 | 160 | 28 | 8 | 20 (12.5%) |
| Holdout-v2 | 192 | 63 | 37 | 30 (15.6%) |

По 16 оценок на поток — верхняя граница бюджета. Счётчики и покейсовая разбивка находятся в [`run_metrics.json`](run_metrics.json).

## Реализация и ограничения вывода

Исходник [`solution.cpp`](solution.cpp) создан как изолированная копия frozen final. Candidate compares only two first actions. P4 uses shortest fitting gap, lowest address, left edge, then tail. Scenarios are contiguous windows sampled from the last 128 observed events, preferring 1–3 event context matches to the current history suffix. Both selectors reuse the same sampled windows. Deletions in counterfactual state use observed rank-from-newest permille, so exact counterfactual PIDs and the future are not available.

Previous synthetic depth-16 ranking signal is exploratory and does not establish solver improvement. Its states came from frozen-noMC trajectories and only covered differing internal fitting-gap actions; its comparison mixed baseline-action/baseline-continuation with P4-action/P4-continuation. In this implementation the two recommenders are additionally compared against each other on the same realized Open15 and holdout inputs. That paired solver comparison does not support the conditioned selector. No new synthetic seeds, broad search, or parameter changes were run after this gate failed.

## Артефакты и целостность

- [`solution.cpp`](solution.cpp) — candidate source; SHA-256 `48ca01cfd7b5ee98e33db0e17ad832d1eddd44f5ec1fbe1382c29cb349635ebe`.
- [`config.json`](config.json) — политики, scenario sampling, gate and causal budget.
- [`manifest.json`](manifest.json) — exact commands, toolchain, test hashes, source and binary hashes.
- [`comparison.csv`](comparison.csv), [`comparison.json`](comparison.json) — case-by-case same-input comparisons.
- [`run_metrics.json`](run_metrics.json) — protocol, CPU/RSS, selector counts and protected hashes.

Verified protected hashes: frozen source `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`, frozen binary `dabb6910bde7550dbf4ab03d6d7b450d0a91f53a90dc06e52d6b271c8602000c`, canonical source `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`, interactor `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`.

## Точные команды

Сборка и прогон выполнялись локально на `macOS arm64`, Apple clang 17.0.0, без Docker:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic -DPOLICY_ROLLOUT_DIAGNOSTICS results/pipes/improvement/policy_conditioned_rollout/solver_candidate/solution.cpp -o results/pipes/improvement/policy_conditioned_rollout/solver_candidate/bin/policy_conditioned
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic -DPOLICY_ROLLOUT_DIAGNOSTICS -DPOLICY_BASELINE_CONTINUATION_SELECTOR results/pipes/improvement/policy_conditioned_rollout/solver_candidate/solution.cpp -o results/pipes/improvement/policy_conditioned_rollout/solver_candidate/bin/baseline_continuation_selector
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic -DMC_ROLLOUT_DISABLED results/pipes/final/solution.cpp -o results/pipes/improvement/policy_conditioned_rollout/solver_candidate/bin/frozen_nomc
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/strategies/policy4_baseline.cpp -o results/pipes/improvement/policy_conditioned_rollout/solver_candidate/bin/p4
python3 tools/pipes_harness.py --solver results/pipes/improvement/policy_conditioned_rollout/solver_candidate/bin/policy_conditioned --interactor results/pipes/final/bin/interactor --tests data/pipes/open --out results/pipes/improvement/policy_conditioned_rollout/solver_candidate/runs/open/policy_conditioned --name policy-conditioned-depth16 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/policy_conditioned_rollout/solver_candidate/bin/policy_conditioned --interactor results/pipes/final/bin/interactor --tests data/pipes/synthetic/final-holdout-v2 --out results/pipes/improvement/policy_conditioned_rollout/solver_candidate/runs/holdout-v2/policy_conditioned --name policy-conditioned-depth16 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Точные команды для остальных трёх вариантов и оба прогона находятся в `manifest.json`.
