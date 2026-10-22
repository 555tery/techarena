# Геометрический прогноз ёмкости для cohort slabs

## Решение

Поправка на capacity guard сохранила лучший Open15 результат: **29.932085817214 / 32.1**, изменение только case 9, **61 760 → 48 540 м**. По сравнению с исходным cohort-slab кандидатом Open15 и holdout-v2 не изменились. Текущий разрыв до 30.3 — **0.367914182786**.

Основной источник — отдельный [cohort_slabs_geometric_capacity.cpp](source/cohort_slabs_geometric_capacity.cpp), SHA-256 `540e61da1995fb92a1d4eb7c00162a3ac72730ded7bfd182779096cf725fc2ef`. Исходный кандидат с арифметическим guard сохранён без изменений.

## Зачем понадобилась поправка

В первой stress-suite арифметическая экстраполяция следующего размера `c+(c−b)` занижала размер после масштабного сдвига геометрической серии. В сценарии с блоками `1,2,4,8,16`, затем `3,6,12,24`, она на размере 24 предсказывала 36, хотя наблюдаемый новый режим продолжался до 48. Лишний slab ухудшил траншею на **840 м** относительно champion.

Capacity guard теперь использует три уже наблюдённых размера `a<b<c`. Если `c·a` согласуется с `b²` в пределах уже используемого геометрического допуска, ожидается `d=round(c·b/a)`. Slab допускается, только если `c<d≤40` и прогнозируемый объём удаляемой когорты вмещает не менее 64 труб размера `d`. Поэтому `1,2,4` даёт прогноз 8; `3,6,12` даёт 24; после `6,12,24` прогноз 48 отсекает следующий slab. Будущие команды не читаются.

## Проверка на свежих синтетических потоках

Созданы восемь новых входов с seed `202610171`: геометрический поток после масштабного сдвига 3× при двух размерах блоков; сдвиг с масштабом 5×; меняющиеся числа труб; случайные удаления; дрейф числа труб; неправильная монотонная серия и переход геометрической серии в арифметическую. Проверка SHA не нашла совпадений этих входов с Open15, holdout-v2 или первой stress-suite. Это целевой тест исправленной гипотезы, выбранный после обнаружения регрессии в первой suite; он не является независимой скрытой проверкой и не оценивает будущий contest score. См. [отдельный отчёт обоих stress-этапов](synthetic_stress/REPORT.md).

| Поток | Триггерные размеры | Champion, м | Кандидат, м | Δ траншеи, м |
|---|---:|---:|---:|---:|
| phase shift 3×, 256 труб/блок | 4, 8, 16, 12 | 16 260 | 12 980 | −3 280 |
| phase shift 3×, 384 труб/блок | 4, 8, 16, 12 | 24 380 | 19 420 | −4 960 |
| phase shift scale 5× | 4, 8, 16, 20 | 24 340 | 18 920 | −5 420 |
| block count wobble | — | 13 820 | 13 820 | 0 |
| random deletes | — | 10 520 | 10 520 | 0 |
| block count drift | — | 17 260 | 17 260 | 0 |
| irregular increasing sizes | 8 | 26 020 | 24 280 | −1 740 |
| geometric → arithmetic phase | 4, 8, 16 | 39 400 | 32 360 | −7 040 |

Сумма KPI по восьми синтетическим потокам: **4.379734599 → 4.995251938**, Δ **+0.615517339**; пять улучшений, три совпадения, ухудшений нет. Полные длины, KPI и SHA входов — в [per_case_comparison_v2.csv](synthetic_stress/per_case_comparison_v2.csv); генератор и полный манифест — рядом в `synthetic_stress/`.

## Open15 и holdout-v2

- Open15: **29.932085817214 / 32.1**, 15/15. Per-case отличается от champion только case 9 (61 760 → 48 540 м); остальные траншеи и score совпадают.
- Holdout-v2: **5.135264324280 / 12**, 12/12. Все длины траншей и judge outputs побайтно совпали с champion. Это известный ранее использовавшийся набор, не независимое свидетельство переносимости.
- Ресурсы: максимум Open15 **1.304327 CPU-с / 6.828 MiB RSS**; holdout-v2 **0.286490 CPU-с / 4.203 MiB RSS**, в пределах 5 с / 256 MiB.

## Ещё один проверенный вариант

Перестановка slab-слоёв, в которой удаляемая parity-когорта размещается у хвоста slab, дала в одном case9 screen **48 560 м** — на 20 м хуже зафиксированного кандидата. Полный Open15 не запускался. Исходник сохранён отдельно как [cohort_slabs_deleted_high.cpp](source/cohort_slabs_deleted_high.cpp), SHA-256 `f91ea9bb659148fa1d4afb97e3c6f6259ef7994b4808d63dc6c82353519e1ece`.

## Воспроизведение и provenance

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror results/pipes/improvement/case9_causal_profiles/source/cohort_slabs_geometric_capacity.cpp -o results/pipes/improvement/case9_causal_profiles/bin/cohort_slabs_geometric_capacity
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/cohort_slabs_geometric_capacity --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/case9_causal_profiles/runs/geometric-capacity-open15 --name geometric-capacity-open15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

- Binary SHA-256: `f9b582f4632cc7f3fd26f4b0598fb62b7afb389decf9a627f494f5899f43526a`.
- Open15 summary SHA-256: `ff6b742d19f48254d0ed939068f235f82e6126dc9faacde3aa0bfb39de4062cd`; cases CSV: `3d2ffe2761ae4610ce99225789ac86ef75cefd8f447c3f94bdb46620ed74c0db`.
- Holdout summary SHA-256: `96344aac4e3e4915641b6827710d5bedb26b55a2c5b671e9ce69982c5fa2ad7d`; cases CSV: `30e6b632f1fa19b934c2a57ee625aeab02b168a6f01d39b45d640fc1e8bf9f45`.
- Exact inputs, generator, baseline/candidate run hashes and trigger traces: [synthetic stress manifest](synthetic_stress/manifest_v2.json).
- Frozen final (`c4b737b9…32a991`) and canonical source (`526ba58e…1dfec8`) remain unchanged. No website or Docker used.
