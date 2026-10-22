# Harmonic-fit v1 — no-go

## Вывод

Проверен exact-length вариант с Harmonic-классами и динамическими страницами по 40 м. На case 15 потребовалось **519 520 м** траншеи против **438 920 м** у текущего champion (**+80 600 м**). Все шесть новых synthetic-потоков также дали более длинную траншею. Open15 и holdout не запускались.

## Правило и отличие от прошлых проверок

Длина `L` относится к Harmonic-типу `j=floor(40/L)`, то есть к интервалу `(40/(j+1), 40/j]`. Каждый выделяемый объект занимает ровно `L` метров — округления buddy здесь нет. Пространство состоит из 40-метровых страниц, каждая страница обслуживает только один тип `j`; в ней ведётся свободный-gap список, соседние gaps сливаются после удаления. Когда страница освобождается полностью, она возвращается в общий пул пустых страниц и может быть передана другому типу. Для типа `j` проверяется инвариант `livePipes ≤ j`: `j+1` объектов длиной `>40/(j+1)` не помещаются в 40 м.

Это отличается от ранее проверенных [coarse size-class arenas](../case15_size_arenas/REPORT.md), где интервалы получали owner одного из трёх диапазонов `1–10 / 11–20 / 21–40`, а mixed-owner слияния попадали в shared pool с fallback к champion; тот вариант дал case15 **+5 680 м**. От [bimodal/churn gate](../case15_arena_bimodal_gate/REPORT.md) здесь нет гистограммного триггера и shared/global fallback; тот gated-вариант дал **+120 м**. Harmonic-классификация следует классической разметке Lee–Lee, но их гарантия для online bin packing не переносится на Pipes с удалениями и адресными интервалами ([первоисточник](https://doi.org/10.1145/3828.3833)).

## Результаты

| Поток | Champion, м | Harmonic-fit, м | Δ, м | Δ KPI |
|---|---:|---:|---:|---:|
| Open case 15 | 438 920 | 519 520 | +80 600 | −0.148016 |
| stationary uniform + random delete | 57 520 | 67 200 | +9 680 | −0.130504 |
| short → wide + LIFO delete | 11 180 | 11 800 | +620 | −0.052213 |
| wide → short + FIFO delete | 76 700 | 100 040 | +23 340 | −0.041597 |
| harmonic-boundary mix + recent/random delete | 34 820 | 38 200 | +3 380 | −0.079163 |
| periodic class-boundary sizes + cohort delete | 53 220 | 62 320 | +9 100 | −0.136590 |
| three-phase sizes + old-biased delete | 92 100 | 100 040 | +7 940 | −0.073294 |

Сумма KPI на synthetic уменьшилась с **4.83158099819** до **4.31821905476**. Все 14 прогонов прошли локальный interactor. Buddy CPU/RSS: case15 `1.541 с / 5.875 MiB`, максимум по synthetic `0.446 с / 2.234 MiB`; лимиты соблюдены. Причина no-go соответствует гипотезе: class-exclusive 40 м страницы оставляют свободные остатки недоступными трубам другого класса, а отдельное деление страниц не возвращает это пространство в общий пул, пока страница не опустеет.

## Воспроизведение

Команды из корня проекта:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror -pedantic results/pipes/improvement/harmonic_fit_v1/source/harmonic_fit.cpp -o results/pipes/improvement/harmonic_fit_v1/bin/harmonic_fit
python3 results/pipes/improvement/harmonic_fit_v1/generate_synthetic.py
cp data/pipes/open/15.in results/pipes/improvement/harmonic_fit_v1/tests/case15/15.in
python3 tools/pipes_harness.py --solver results/pipes/improvement/harmonic_fit_v1/bin/harmonic_fit --name harmonic_fit_case15 --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/harmonic_fit_v1/tests/case15 --out results/pipes/improvement/harmonic_fit_v1/runs/case15/candidate --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name champion_case15_control --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/harmonic_fit_v1/tests/case15 --out results/pipes/improvement/harmonic_fit_v1/runs/case15/champion --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
python3 tools/pipes_harness.py --solver results/pipes/improvement/harmonic_fit_v1/bin/harmonic_fit --name harmonic_fit_synthetic --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/harmonic_fit_v1/synthetic --out results/pipes/improvement/harmonic_fit_v1/runs/synthetic/candidate --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
python3 tools/pipes_harness.py --solver results/pipes/improvement/case9_causal_profiles/bin/champion_cohort_slabs --name champion_on_harmonic_synthetic --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/harmonic_fit_v1/synthetic --out results/pipes/improvement/harmonic_fit_v1/runs/synthetic/champion --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 180
```

## Хеши

- [Исходник](source/harmonic_fit.cpp) SHA-256 `b99f2ad6a55cf73b64b15f4723a2206ac838184ea8c955f3c4dda67cf3f3f06b`.
- Candidate binary SHA-256 `a1c23960cae98a8dfcdee45a4b6a82649fee56425bb7a81040736beecdf8529f`.
- Generator SHA-256 `a505ec62ca5e50ba9173675d4c3c2372b44964ee47e40186ac173e0854f5d5b9`; [synthetic manifest с SHA входов](synthetic/manifest.json) `588cd63807470e7dffd08e9521adfdb865a80d3d52b186dea4e6698e7e27b7eb`.
- Champion source/binary SHA-256 `43bfbdadbae18ac180d1e59b6631342cfe1bef99190a449838f0470d6f220200` / `e4b79d8eb55a1fdc03a8c62505142ee615304401e821895bf6ab7f3712e54049`.
- Case15 input SHA-256 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`; interactor SHA-256 `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`.
- Candidate/champion case15 transcript SHA-256 `6123af01dd2ea6757ae3f0baf65dbd7bc698d8a2e8bf7da4c12597b58177df9f` / `0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e`.
- [Полный SHA256SUMS](SHA256SUMS) покрывает код, inputs, CSV/summary и judge outputs.

Canonical/frozen source, сайт и Docker не затрагивались.
