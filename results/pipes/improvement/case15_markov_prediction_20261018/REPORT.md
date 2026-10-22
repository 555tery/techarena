# Case 15: проверка Markov-прогноза следующей длины

## Решение gate

**Policy-кандидат не строился; направление остановлено на диагностике.** На расширениях case 15 first-order Markov даёт небольшой прирост top-1, но не даёт полезного прогноза распределения: log-loss, Brier и калибровка хуже частотного baseline. Результат недостаточно силён для выбора slack по вероятностям будущих размеров.

Comparator — `relative_cohort_plus_scale_gate_unit_suppression.cpp`, SHA совпадает с переданным `4ac5d5c36220fc10610d82ce092e77907f80a1a1c425332d25f59316fa21d450`. На его транскрипте case 15 наблюдалось 17 639 расширений среди 130 255 установок; каждая прогнозная оценка использует только уже пришедшие длины.

## Фиксированная диагностика

Для установки длины `x_t` прогнозируется следующая положительная длина `x_(t+1)`; удаления пропускаются. Сравниваются:

- Markov-1: `P(x_(t+1) | x_t)` по переходам между длинами в скользящем окне из 2 048 установок;
- marginal: частоты длин в том же окне без условия на `x_t`.

Markov-оценка сглаживается к marginal распределению с фиксированной силой prior `α=8`; marginal использует Laplace-1. Наблюдение `x_t` и переход к нему включены до построения прогноза, поэтому будущее в признаках отсутствует. Расширения определены по ответам comparator (`digs > 0`). Для case 15 uncertainty по разности top-1/log-loss/Brier дополнительно оценена paired block bootstrap: блок 1 024 команды, 2 000 повторов, seed `20261018`.

## Case 15

| Метрика на расширениях | Markov-1 | Marginal | Разность Markov − marginal |
|---|---:|---:|---:|
| Следующие установки | 17 639 | 17 639 | — |
| Top-1 accuracy | 10.953% | 10.290% | **+0.663 п.п.**; block-bootstrap 95% ДИ `[+0.057, +1.268]` п.п. |
| Log-loss | 2.556 | 2.467 | **хуже на 0.089**; 95% ДИ разности log-loss gain `[-0.115, -0.064]` |
| Multiclass Brier | 0.8990 | 0.8942 | **хуже на 0.00484**; 95% ДИ Brier gain `[-0.00602, -0.00366]` |
| Top-confidence ECE | 0.0336 | 0.0138 | Markov хуже; примерно в 2.4 раза больше |

Top-1 прибавка мала: около 117 дополнительных правильных argmax из 17 639 прогнозов. При этом условные вероятности систематически переоценивают выбранные длины. По всем установкам (не только расширениям) top-1 разница почти нулевая: 9.944% против 9.837% (+0.107 п.п.; block-bootstrap 95% ДИ `[−0.085, +0.295]`); log-loss и Brier Markov также хуже. Row support на расширениях не разреженный: медиана 281 переход, 99.8% точек имеют не менее 8 переходов. Поэтому провал proper scores нельзя объяснить только отсутствием наблюдений для текущего размера.

**Интерпретация:** есть слабый rank-only сигнал на subset расширений, но оценка распределения для выбора `slack` хуже простой marginal. Для предполагаемого действия нужна полезность всей conditional distribution; критерий gate не пройден. Это не утверждение, что никакой predictor невозможен; проверенная фиксированная Markov-1 модель в текущем виде непригодна.

## Проверка шести новых synthetic streams

Потоки специально покрывают iid, Markov-устойчивость размера, цикл, random walk, смену фаз и anti-persistence. Каждый содержит 40 700 команд и 700 начальных активных труб; seed и SHA записаны в `synthetic/manifest.json`.

| Поток / режим | Top-1: Markov vs marginal | Log-loss gain marginal−Markov | Brier gain marginal−Markov | Вывод |
|---|---:|---:|---:|---|
| `markov_case_01`, iid | 3.23% vs 1.53% | −0.299 | −0.0223 | conditional overfit; proper scores хуже |
| `markov_case_02`, P(same)=0.75 | 66.80% vs 6.31% | +1.555 | +0.3575 | сильный сигнал обнаружен |
| `markov_case_03`, noisy cycle | 76.77% vs 7.68% | +1.088 | +0.4947 | сильный сигнал обнаружен |
| `markov_case_04`, size random walk | 49.59% vs 5.48% | +1.884 | +0.3305 | сильный сигнал обнаружен |
| `markov_case_05`, четыре iid-фазы | 9.14% vs 3.54% | +0.836 | +0.0633 | частичная предсказуемость фазового потока |
| `markov_case_06`, anti-persistent bands | 10.07% vs 8.20% | −0.025 | −0.0051 | top-1 слабый, распределение не лучше |

Знак `log-loss gain`/`Brier gain`: положительное значение означает преимущество Markov. Synthetic controls показывают, что диагностика выявляет сильную зависимость в намеренно предсказуемых потоках; case 15 больше похож на потоки без полезной калиброванной зависимости. На этих данных ничего не говорит о переносимости на неизвестные тесты.

## Воспроизводимость

Comparator собран локально Apple Clang 17.0.0 на macOS arm64; его case 15 и шесть synthetic прошли локальный interactor. Лимиты: 5 секунд CPU, 256 MiB. Сайт и Docker не использовались.

```sh
clang++ -std=c++20 -O2 -DNDEBUG -Wall -Wextra -Werror -pedantic \
  results/pipes/improvement/case15_markov_prediction_20261018/src/comparator.cpp \
  -o results/pipes/improvement/case15_markov_prediction_20261018/bin/comparator
python3 results/pipes/improvement/case15_markov_prediction_20261018/generate_synthetic.py
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_markov_prediction_20261018/bin/comparator \
  --name baseline_skill --interactor results/pipes/final/bin/interactor \
  --tests results/pipes/improvement/case15_markov_prediction_20261018/tests/all \
  --out results/pipes/improvement/case15_markov_prediction_20261018/runs/baseline_skill \
  --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Подробные per-placement метрики — `analysis/{15,01…06}.csv`, сводки — соответствующие JSON; case15 block bootstrap — `analysis/15_block_bootstrap.json`. Хеши источников, входов, ответов, диагностик и отчёта собраны в `manifest.json`. Frozen/canonical исходники, wiki и платформа не менялись.
