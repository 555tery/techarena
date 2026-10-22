# Case 15: условная high-side ориентация при near-LIFO churn

## Краткий результат

Новый причинный кандидат `near_lifo_edge.cpp` **не прошёл screening**: сумма взвешенных баллов по официальным входам cases 5, 9 и 15 снизилась с **10.859085056537428** до **10.856830478304271** (Δ **−0.002254578233156**). На case 15 траншея выросла на 80 м; на case 5 — на 40 м; case 9 не изменился. По правилу эксперимента отрицательный результат останавливает эту линию: полный Open-15, holdout и новые варианты политики не запускались.

`results/pipes/final/solution.cpp`, `src/pipes.cpp` и тестовая платформа не изменялись.

## Гипотеза и проверенное изменение

В case 15 виден near-LIFO компонент: в прежней трассовой диагностике медианный ранг удаления относительно самых новых PID был 1. При этом действующий baseline выбирает сторону размещения по длине и другим локальным сигналам. Гипотеза состояла в том, что при устойчивом near-LIFO сигнале одинаковое направление укладки будет плотнее группировать недавно размещённые трубы, которые чаще удаляются в обратном порядке, и последующие освобождения будут чаще объединяться.

Кандидат считает удаление near-newest, если его наблюдаемый ранг не выше 50‰. Он включает `nearLifoEdgeMode`, когда минимум 64 удаления в скользящем окне из 128 дают долю near-newest не ниже 80%; выключает режим ниже 60%. В этом режиме размещение идёт с high side в уже выбранном промежутке. Оценка пригодности и выбор промежутка не менялись. Внутри текущего режима не использовались будущие команды, идентификатор теста или просмотр входного файла. Состояние детектора также перенесено в bounded Monte Carlo simulator, чтобы его текущие rollout-решения отражали ту же онлайн-политику.

Это один изолированный вариант, а не подтверждённый метод. Его ухудшение показывает, что наблюдаемого near-LIFO ранга недостаточно, чтобы оправдать глобальную смену стороны размещения.

## Результаты official harness

Оба бинарника строго собраны Apple Clang с `-O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic` и проверены через `tools/pipes_harness.py` / официальный интерактор. CPU — solver child, RSS — solver child. Лимиты: 5 секунд CPU и 256 MiB памяти на кейс. Все прогоны завершились `ok`; лимиты не превышены.

| Case | Вес | Нижняя граница | Baseline: траншея / score | Candidate: траншея / score | Δ траншеи | CPU, baseline → candidate | RSS, baseline → candidate |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 1 | 53,360 м | 62,760 м / 0.810070108349267 | 62,800 м / 0.809554140127389 | +40 м | 0.103195 → 0.099396 с | 3.1875 → 3.21875 MiB |
| 9 | 1 | 47,500 м | 61,960 м / 0.508392511297611 | 61,960 м / 0.508392511297611 | 0 м | 0.133182 → 0.134144 с | 3.09375 → 3.171875 MiB |
| 15 | 10 | 418,780 м | 438,920 м / 9.540622436890550 | 439,000 м / 9.538883826879271 | +80 м | 1.370603 → 1.384503 с | 6.4375 → 6.65625 MiB |
| **Сумма (веса учтены)** | **12** | — | **10.859085056537428** | **10.856830478304271** | **Δ −0.002254578233156** | — | — |

Это screening только на трёх официальных открытых кейсах, не полный официальный набор из 15. Веса использованы такими, как указаны в самих тестах. Baseline и кандидат на case 9 дали побайтно одинаковый judge output.

## Воспроизводимость и SHA-256

Команды сборки:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/final/solution.cpp -o results/pipes/improvement/case15_phase/bin/baseline
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/case15_phase/source/near_lifo_edge.cpp -o results/pipes/improvement/case15_phase/bin/near_lifo_edge
```

Команды screening:

```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_phase/bin/baseline --name baseline --interactor tools/interactor --tests results/pipes/improvement/case15_phase/tests --out results/pipes/improvement/case15_phase/screen/baseline --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_phase/bin/near_lifo_edge --name near_lifo_edge --interactor tools/interactor --tests results/pipes/improvement/case15_phase/tests --out results/pipes/improvement/case15_phase/screen/near_lifo_edge --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

| Артефакт | SHA-256 |
|---|---|
| Baseline source `results/pipes/final/solution.cpp` | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` |
| Candidate source `source/near_lifo_edge.cpp` | `70f9ebeae2c38d8e09232a53ecea338aff1e6b8ac7558198290c59e450ebf322` |
| Baseline binary | `ee9ae15f8f4879eaca8da9a0c5fdb1caeb05311893279a4eaf0734c167427290` |
| Candidate binary | `9dbce97908441f5ce28195cc930ff1c3f106fa674b4fa560cd355adaff56562a` |
| Official interactor `tools/interactor` | `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a` |
| Case 5 input | `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b` |
| Case 9 input | `cfb711efa3a9ccccc17e7170fc7c2ea19c12ed45b789da3a4b2c80750d7ca128` |
| Case 15 input | `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353` |
| Case 5 baseline judge output | `e78bb7900ad184037e578f13012eaae1cb8d854700ee7ddc520ac6c8a113bb63` |
| Case 5 candidate judge output | `b55a85a249cc0ff9df12d4acc4743333f365e978fc49bce4b6b75d80b33fdc94` |
| Case 9 baseline and candidate judge output | `fc4bea23ad81727480ab7d95fcabc46c2e029f41d9ec016466557b9c00f7cc7f` |
| Case 15 baseline judge output | `0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e` |
| Case 15 candidate judge output | `68372557dc38937127fa7b0c5e3a12c59f59093ecdecbfeb315ef362f64ef7e4` |

Полные строки CSV, ресурсы, JSON-сводки и сырые ответы интерактора сохранены в `screen/{baseline,near_lifo_edge}/`.
