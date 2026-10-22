# Run manifest — shadow expert portfolio

Дата: 2026-10-17. Все прогоны локальные, macOS arm64; сайт и платформа не использовались. Заранее заданный gate не пройден, поэтому Open-15 и holdout-v2 не запускались.

## Источники и сборка

| Объект | SHA-256 |
|---|---|
| frozen final `results/pipes/final/solution.cpp` | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` |
| копия frozen final | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` |
| challenger PID/46 | `1a643a2b8a560de5c7dfd7efe0b288dc93785e96400d2ae6fd4ec7eea5f55f59` |
| сгенерированный portfolio source | `7046657e81b085773bbcc111832552170ad2c2aa8a8a6204851fe086f421efb1` |
| `build_portfolio.py` | `2a2fa99783c6616cfefeaa9ab148db3507d8356eb440a5b1f688147848ecd629` |
| генератор матрицы | `0947bf3646337219556c4eac535a3637ca4f15d7453705c772b01374b770784b` |
| использованный synthetic generator | `e6a540f372f486af62e1f86f3ebaa08394a6d7b629d8db40dcf80eb3fc79ae17` |
| официальный harness `tools/pipes_harness.py` | `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d` |
| официальный interactor binary | `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a` |

Компилятор: Apple clang 17.0.0 (`clang-1700.0.13.5`), флаги `-O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror`. Все три бинаря собраны из снимков в `source/`; строгая сборка прошла. SHA-256 бинарей: frozen `80c9d87308831466294e76a13dba7cc924da6708b6879a15122555fbbc70a054`; PID/46 `ffebbfe745fd9c2fbfcbd1a0e8255148de955171fb6b61e42afc1abeb01fce72`; portfolio `a1c0425aa729e6e79537757f33d5808ab0b3979969d98ede2e62e6427d045377`.

## Команды

```sh
python3 results/pipes/improvement/shadow_expert_portfolio/generate_matrix.py
python3 results/pipes/improvement/shadow_expert_portfolio/build_portfolio.py
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/shadow_expert_portfolio/source/frozen_final.cpp -o results/pipes/improvement/shadow_expert_portfolio/bin/frozen_final
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/shadow_expert_portfolio/source/pid46.cpp -o results/pipes/improvement/shadow_expert_portfolio/bin/pid46
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/shadow_expert_portfolio/source/shadow_portfolio.cpp -o results/pipes/improvement/shadow_expert_portfolio/bin/shadow_portfolio
python3 tools/compare_pipes_binaries.py --solver frozen=results/pipes/improvement/shadow_expert_portfolio/bin/frozen_final --solver pid46=results/pipes/improvement/shadow_expert_portfolio/bin/pid46 --solver portfolio=results/pipes/improvement/shadow_expert_portfolio/bin/shadow_portfolio --tests results/pipes/improvement/shadow_expert_portfolio/inputs --out results/pipes/improvement/shadow_expert_portfolio/runs/matrix --interactor results/pipes/final/bin/interactor --baseline frozen
python3 results/pipes/improvement/shadow_expert_portfolio/analyze_results.py
```

## Результат

36/36 потоков каждого solver завершились с `status=ok`; 6 семейств × 3 размера × 2 seed, от 5k до 200k команд. Frozen и PID/46 набрали одинаковую сумму KPI `16.9383052875`; portfolio — `16.9600377608`. Средняя парная разница portfolio−frozen `+0.000603680`; стратифицированный percentile bootstrap, 20 000 повторов, seed `87102317`: 95% CI `[-0.000865148, +0.002393385]`. Средняя положительна, но нижняя граница ниже нуля, значит gate = **NO-GO**.

Точность shadow-траншей: 0 расхождений с отдельными прогонами frozen и PID/46. Максимальные ресурсы portfolio: CPU `1.426922 s`, RSS `19.172 MiB`, при лимитах `5 s / 256 MiB`. Результаты по каждому потоку и хешу входа — `stream_results.csv` и `analysis.json`; сводка — `REPORT.md`. `results/pipes/final/solution.cpp` сверялся с неизменённой копией: SHA-256 в обоих случаях `c4b737…32a991`.
