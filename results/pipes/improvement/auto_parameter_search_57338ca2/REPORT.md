# Автоматический поиск параметров на frozen Pipes source

Исходник: `results/pipes/final/solution.cpp`, SHA-256 `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`. Final source не менялся.

## Метод

Проверены 20 конфигураций: frozen baseline и 19 уникальных точек seeded randomized Latin-hypercube search (seed `20261016`). Каждый вариант прошёл полный официальный open-набор из 15 тестов; screening не применялся. Цель — точная сумма `weighted_score` по этим 15 кейсам. Менялись только числовые константы `kUnfitPenaltyScale`, `kSameLengthRightRun`, `kRightEdgeMaxPipeLength`, `kMcMinimumMeanSavingM`, `kMcDecisionBudget`. Parity trigger и allocator logic не менялись. Полные исходники, бинарники и harness output каждого прогона сохранены в `configs/`.

## Результат

Лучший результат — исходная конфигурация: **29.785293754007**. Лучший новый вариант `03-p60-run32-edge4-save16-budget48` получил **29.727169061612** (дельта **-0.058124692395**). Ни одна из 19 новых конфигураций baseline не превзошла; новых кандидатов для переноса нет.

| Ранг | Конфигурация | Параметры (penalty/run/edge/minSaving/budget) | Open weighted sum | Δ к baseline | Max CPU | Max RSS |
|---:|---|---|---:|---:|---:|---:|
| 1 | `00-p60-run46-edge4-save1-budget32` | 60/46/4/1/32 | 29.785293754007 | +0.000000000000 | 0.958601s | 9.500 MiB |
| 2 | `03-p60-run32-edge4-save16-budget48` | 60/32/4/16/48 | 29.727169061612 | -0.058124692395 | 0.967432s | 9.484 MiB |
| 3 | `04-p120-run46-edge4-save1-budget32` | 120/46/4/1/32 | 29.716967582161 | -0.068326171847 | 0.956759s | 9.391 MiB |
| 4 | `15-p80-run32-edge4-save4-budget16` | 80/32/4/4/16 | 29.683306262742 | -0.101987491266 | 1.089926s | 9.016 MiB |
| 5 | `14-p60-run72-edge6-save8-budget24` | 60/72/6/8/24 | 29.387884129831 | -0.397409624177 | 1.039811s | 9.531 MiB |

Полный ranking и SHA-256: [`open-ranking.csv`](open-ranking.csv), [`search-results.json`](search-results.json); per-case разность лучшего нового варианта к baseline: [`best-challenger-per-case.csv`](best-challenger-per-case.csv).

## Проверки top-ranked winner

Frozen baseline с тем же SHA прошёл open15: 15/15, **29.785293754007**, max 0.958601s CPU / 9.500 MiB RSS.

После выбора на open были выполнены фиксированные дополнительные наборы: holdout-v2 — 12/12, weighted sum **5.135264324280**, max 0.205803s / 4.203 MiB; synthetic development modes — 4/4, sum **1.844130426987**, max 0.152727s / 3.562 MiB.

## Caveat по split и переобучению

Все 15 open cases использованы непосредственно для отбора максимума среди 19 случайных конфигураций и baseline, поэтому результат на open настроен по этому набору. Holdout-v2 и четыре synthetic development режима запускались только после выбора; однако эти файлы и ранее использовались в экспериментах, отражённых в репозитории, поэтому их нельзя считать полностью нетронутыми независимыми holdout-наборами.

Точный frozen source hash, команды, input hashes, per-case CPU/RSS, артефакты и перечень всех 20 вариантов — в [`manifest.json`](manifest.json). Повторный запуск поиска: `python3 results/pipes/improvement/auto_parameter_search_57338ca2/search.py`.
