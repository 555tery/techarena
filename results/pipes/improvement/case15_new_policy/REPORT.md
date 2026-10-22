# Case 15: исследование новых online-политик

## Вывод

Ни одна из двух новых политик не прошла заданный screening по взвешенной сумме случаев 5, 9 и 15. Полный Open15 после этого не запускался. Все три решения прошли официальный локальный интерактор; ресурсы остались ниже ограничений. Ни `results/pipes/final/solution.cpp`, ни `src/pipes.cpp` не менялись. На платформу ничего не загружалось.

Базой служила текущая версия `results/pipes/final/solution.cpp`, SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`. Она набрала на screening-сумме **10.859085057 / 12**. Первая идея ухудшила результат на **0.256779933**, вторая — на **0.022552612**.

| Вариант | Case 5: траншея / KPI | Case 9: траншея / KPI | Case 15: траншея / KPI | Сумма score / 12 | Δ к baseline | Max CPU / RSS |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 62,760 м / 0.810070108 | 61,960 м / 0.508392511 | 438,920 м / 0.954062244 | 10.859085057 | — | 1.002304 с / 5.953 MiB |
| Lifetime-gated tail lane | 62,760 м / 0.810070108 | 61,960 м / 0.508392511 | 451,060 м / 0.928384250 | 10.602305124 | −0.256779933 | 1.081953 с / 9.938 MiB |
| Lifetime-compatible equal-cost ties | 62,760 м / 0.810070108 | 61,960 м / 0.508392511 | 439,960 м / 0.951806982 | 10.836532444 | −0.022552612 | 1.302678 с / 14.328 MiB |

## Проверенные идеи

### 1. LIFO/lifetime-gated tail lane — отклонена

Политика выделяла отдельную хвостовую область только после одновременного появления нескольких наблюдаемых сигналов: последние 128 удалений показывали near-newest ранг минимум в 80% случаев; окно из 512 команд показывало сбалансированные размещения/удаления; в траншее было не менее 256 свободных промежутков, а общий объём свободного места превышал восемь крупнейших промежутков и 1,024 м. Для режима использовалась гистерезисная граница 60% near-newest.

После активации труба направлялась в хвостовую область, только если у её длины медиана последних завершённых сроков жизни (кольцо до 32 образцов, минимум 24) была не более 64 последующих размещений. Остальные трубы шли через исходный allocator. Это past-only правило, без номера кейса и просмотра будущих команд.

На case 15 траншея выросла на **12,140 м**. Вероятное объяснение, согласующееся с результатом: выборочная хвостовая зона слишком часто обходила уже доступные внутренние дыры, а наблюдаемая медиана срока жизни оказалась недостаточным основанием отказаться от их повторного использования.

### 2. Lifetime-compatible выбор среди равноценных дыр — отклонена

Для длин труб, по которым уже накопилось минимум 16 удалений, вычислялась медиана завершённого срока жизни. При обычном выборе свободного промежутка политика рассматривала до четырёх низких и четырёх высоких адресов среди промежутков с той же базовой cost. Для примыкающих активных труб остаточный срок оценивался как `max(0, median_lifetime - observed_age)`. Равноправная дыра могла заменить исходную только если прогнозируемые сроки удаления соседей были ближе к ожидаемому сроку жизни новой трубы хотя бы на 16 размещений. Первичная fit-cost не менялась; политика лишь меняла tie-break.

На case 15 траншея выросла на **1,040 м**. Совпадение медианных сроков жизни не оказалось надёжным сигналом для размещения в этой выборке. Этот результат также показывает, что даже узкое вмешательство в равноправные кандидаты способно заметно менять последующее состояние аллокатора.

## Покейсовые данные и ресурсы

| Тест | Вес | Нижняя граница | Baseline | Tail lane | Lifetime ties |
|---:|---:|---:|---:|---:|---:|
| 5 | 1 | 53,360 м | 62,760 м; 0.810070108 | 62,760 м; 0.810070108 | 62,760 м; 0.810070108 |
| 9 | 1 | 47,500 м | 61,960 м; 0.508392511 | 61,960 м; 0.508392511 | 61,960 м; 0.508392511 |
| 15 | 10 | 418,780 м | 438,920 м; 0.954062244 | 451,060 м; 0.928384250 | 439,960 м; 0.951806982 |

CPU/RSS — максимум среди трёх screening-кейсов. Все шесть candidate-прогонов и три baseline-прогона получили `ok`; превышений лимитов 5 с CPU и 256 MiB RSS нет.

## Воспроизведение

Сборка выполнена Apple Clang 17.0.0 с `-O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic`:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic results/pipes/improvement/case15_new_policy/source/baseline.cpp -o results/pipes/improvement/case15_new_policy/bin/baseline
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic results/pipes/improvement/case15_new_policy/source/lifo_lifetime_lane.cpp -o results/pipes/improvement/case15_new_policy/bin/lifo_lifetime_lane
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic results/pipes/improvement/case15_new_policy/source/lifetime_equal_cost_ties.cpp -o results/pipes/improvement/case15_new_policy/bin/lifetime_equal_cost_ties
```

Все варианты запускались одним и тем же официальным harness и интерактором:

```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_new_policy/bin/baseline --name baseline --interactor tools/interactor --tests results/pipes/improvement/case15_new_policy/tests --out results/pipes/improvement/case15_new_policy/screen/baseline --cpu-limit 5 --memory-limit-mb 256
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_new_policy/bin/lifo_lifetime_lane --name lifo_lifetime_lane --interactor tools/interactor --tests results/pipes/improvement/case15_new_policy/tests --out results/pipes/improvement/case15_new_policy/screen/lifo_lifetime_lane --cpu-limit 5 --memory-limit-mb 256
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_new_policy/bin/lifetime_equal_cost_ties --name lifetime_equal_cost_ties --interactor tools/interactor --tests results/pipes/improvement/case15_new_policy/tests --out results/pipes/improvement/case15_new_policy/screen/lifetime_equal_cost_ties --cpu-limit 5 --memory-limit-mb 256
```

Сырые official-interactor ответы, CSV с per-case ресурсами и JSON-сводки лежат в `screen/{baseline,lifo_lifetime_lane,lifetime_equal_cost_ties}/`. В `tests/` находятся неизменённые копии официальных входов 5, 9 и 15.

## SHA-256

| Артефакт | SHA-256 |
|---|---|
| Baseline source snapshot | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` |
| Baseline binary | `ee9ae15f8f4879eaca8da9a0c5fdb1caeb05311893279a4eaf0734c167427290` |
| Lifetime-gated tail lane source | `0bb8bce986e12895d36b52bc7c88dc6dfb0704ee51d332740c26c8c1fb5eedfe` |
| Lifetime-gated tail lane binary | `9c83d464ad5db289834fc8c33d9b27e6eddae4f8548164799d2c2855dcc6fb89` |
| Lifetime-compatible ties source | `ff319ace53d8f825c2733b9b6c05de2293f5c81b8a9f27a2bc51701fe9e90f50` |
| Lifetime-compatible ties binary | `5d5f1d46a6327a89d1a3ab898ca7ec53065f5be3e932c4b49481aa3bf20b1762` |
| Official interactor binary (`tools/interactor`) | `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a` |
| Case 5 input | `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b` |
| Case 9 input | `cfb711efa3a9ccccc17e7170fc7c2ea19c12ed45b789da3a4b2c80750d7ca128` |
| Case 15 input | `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353` |
