# Synthetic robustness: W32/B10 против policy4 и `recent_unfit_s50`

Проверен существующий бинарник W32/B10 без изменения solver и параметров. Suite содержит 10 заранее замороженных синтетических потоков; manifest и SHA-256 всех входов сверены. Для policy4 и `recent_unfit_s50` использованы уже сохранённые official-harness отчёты; их input hashes совпали с manifest и новым прогоном W32/B10. Все три варианта прошли 10/10 потоков.

| Solver | Весовой score / 10 | Δ к policy4 | Δ к s50 | Максимум CPU, s | Максимум RSS, MiB |
|---|---:|---:|---:|---:|---:|
| `policy4` | 8.4383723976 | +0.0000000000 | +0.1481933697 | 0.221494 | 2.2656 |
| `recent_unfit_s50` | 8.2901790280 | -0.1481933697 | +0.0000000000 | 0.226387 | 2.2812 |
| `demand_w32_b10` | 8.3234129820 | -0.1149594156 | +0.0332339540 | 0.234786 | 2.3438 |

По сравнению с policy4 W32/B10 уступает **0.1149594156** балла; по сравнению с s50 выигрывает **0.0332339540**. На кейсах: против policy4 3 выигрыша / 2 проигрыша / 5 равенств; против s50 — 5 / 2 / 3.

## Покейсовая таблица

См. [`per_case_robustness_frozen.csv`](./per_case_robustness_frozen.csv): KPI, длины траншеи, взвешенные вклады и парные дельты для всех потоков.

## Рекомендация

На этой заранее замороженной диагностической suite W32/B10 занимает промежуточное положение: выше s50 на 0.0332, ниже policy4 на 0.1150 из 10 баллов. Самая заметная деградация относительно обоих — short-skew random; при этом W32/B10 улучшает s50 при удалении длиннейших труб и на uniform random. Эти 10 специально сконструированных synthetic-потоков не являются официальными или hidden тестами и не дают оценки ожидаемого конкурсного score. Это полезная проверка переносимости, но оснований менять зафиксированный winner только по этой suite недостаточно.

## Идентификация

- W32/B10 binary: `/Users/555tery/techarena/results/pipes/improvement/independent/bin/demand_w32_b10`, SHA-256 `af7a92b61c12ae3b9c96b010e7f3a3f1c489ded50dd3305441b723fe9310b805`.
- policy4 binary SHA-256: `fee43fb4630cd2a09ce58eb112de6e213bf12d4c619bb4a98ca27bcecd79f3db`.
- `recent_unfit_s50` binary SHA-256: `5c9efebc85b11d7b176ffe77a9ac002d58a78debfd045d535249a65ff2bd2e93`.
- Seed master: `94719261`; generator SHA-256: `d5afa078349a68af9bda1afbcb35f5ca0b8a269896f84fe88a89ed34d250d50a`.
- Official interactor SHA-256 (identical for all three reports): `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`.
- Результаты W32/B10: `runs/robustness-frozen-demand-w32-b10/summary.json`.
- Результаты policy4 и s50: сохранённые отчёты в `results/pipes/improvement/strategies/reports/robustness-frozen/`.
