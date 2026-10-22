# Scale-offset gate: activation stress test

## Результат

Проверил текущий scale-offset candidate против A+B на четырёх новых fixed-seed synthetic-потоках по 105 000 команд. В каждом потоке active count гарантированно оставался выше 4096: минимум **5 000**, максимум **21 002**. Длины и deletion regime менялись по заранее описанным фазам; synthetic-3 содержит 6.25% wide-размеров в одной фазе, остальные запросы короткие.

**Scale-offset сработал во всех четырёх потоках, но проиграл A+B на каждом:** дополнительные **20–40 м траншеи**. Сумма KPI по четырём synthetic снизилась с **3.992313261** до **3.990746355** (Δ **−0.001566905**). Это отрицательная переносимость именно offset-механизма, хотя Open15 ранее показывал небольшой выигрыш. Никаких параметров по этим потокам не подбирал.

| Stream | Pattern | Commands | Active min–max | Gate opportunities | Offset passes | A+B, м | Scale-offset, м | Δ trench | Δ KPI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gate_stress_01 | Фазовые короткие длины; newest-5% удаления | 105 000 | 5 000–21 002 | 3 326 | 2 687 | 66 480 | 66 520 | +40 | −0.000600907 |
| gate_stress_02 | Смена коротких size-band; 85% newest-5%, иначе FIFO | 105 000 | 5 000–21 002 | 3 700 | 3 191 | 73 960 | 74 000 | +40 | −0.000537464 |
| gate_stress_03 | Короткие длины с 6.25% wide pulse; 90% newest-5% | 105 000 | 5 000–21 002 | 4 804 | 3 557 | 96 060 | 96 080 | +20 | −0.000208008 |
| gate_stress_04 | Короткие size-фазы; удаления random → mixed → 95% newest-5% | 105 000 | 5 000–21 002 | 4 532 | 942 | 90 620 | 90 640 | +20 | −0.000220527 |
| **Итого** | — | — | — | **16 362** | **10 377** | — | — | **+120 м суммарно** | **−0.001566905** |

`offset passes` — фактический счётчик полного условия `offsetGate`, включающего расширение с положительным хвостовым slack, `activePipeCount > 4096`, near-LIFO/short-length confidence и young tail neighbor. Значит, предыдущие synthetic-ties из отчёта scale-offset были неинформативны из-за нулевых активаций; эта проверка закрывает тот пробел.

Все 8 candidate/control запусков завершились `ok`. Максимум solver candidate: **1.640 CPU-с / 4.47 MiB RSS**; лимиты 5 с / 256 MiB соблюдены. Измерения выполнены на macOS arm64.

## Воспроизведение

```sh
python3 results/pipes/improvement/case15_scale_offset_activation_20261018/generate_synthetics.py
clang++ -std=c++20 -O2 -DNDEBUG -Wall -Wextra -Werror -pedantic -DMC_ROLLOUT_DIAGNOSTICS results/pipes/improvement/case15_scale_offset_activation_20261018/source/ab_candidate.cpp -o results/pipes/improvement/case15_scale_offset_activation_20261018/bin/ab_candidate
clang++ -std=c++20 -O2 -DNDEBUG -Wall -Wextra -Werror -pedantic -DMC_ROLLOUT_DIAGNOSTICS results/pipes/improvement/case15_scale_offset_activation_20261018/source/scale_gt4096.cpp -o results/pipes/improvement/case15_scale_offset_activation_20261018/bin/scale_gt4096
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_scale_offset_activation_20261018/bin/ab_candidate --name AB_four_gate_stress --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_scale_offset_activation_20261018/synthetic --out results/pipes/improvement/case15_scale_offset_activation_20261018/runs/AB --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
python3 tools/pipes_harness.py --solver results/pipes/improvement/case15_scale_offset_activation_20261018/bin/scale_gt4096 --name scale_gt4096_four_gate_stress --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_scale_offset_activation_20261018/synthetic --out results/pipes/improvement/case15_scale_offset_activation_20261018/runs/scale_gt4096 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
```

Покейсовые protocol statuses, trench, CPU/RSS, stderr-диагностика gate, outputs и input hashes собраны в [`manifest.json`](manifest.json); сырые файлы лежат в `runs/`.

## Границы вывода

Это четыре специально спроектированных stress-потока для проверки переносимости offset-условия, а не случайная выборка распределения всех возможных потоков. Они показывают небольшой устойчивый проигрыш на четырёх текущих конструкциях, но не доказывают, что offset вреден на любом LIFO-потоке. Текущие ранее измеренные Open15 значения A+B `30.043089199538` и scale-offset `30.044966195` не пересчитывались здесь. Полный Open15, сайт и Docker не использовались. Frozen final и canonical source не менялись.
