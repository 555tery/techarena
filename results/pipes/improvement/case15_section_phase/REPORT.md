# Case 15: section-phase edge placement — no-go

## Что проверено

До эксперимента сверены отчёты `cyclic_next_fit`, `case15_fast_candidates/phase_micro`, `pseudorandom_ties` и геометрические slab-отчёты case 9. В них проверялись обход адресов, high-address/small-gap tie-break, hash среди равных cost и округление длины cohort slab к 20 м. Правила выбора края по фазе остаточного интервала относительно 20-метровой секционной сетки там не нашёл.

Новая причинная политика для выбранного свободного интервала `[a,b)` и трубы длины `q` сравнивает два остатка:

- при low-edge placement остаток — `[a+q,b)`;
- при high-edge placement остаток — `[a,b-q)`.

Для каждого конца вычисляется расстояние до ближайшей границы секции: `d(x)=min(x mod 20, 20−(x mod 20))`. Выбирается край с меньшей суммой расстояний концов остатка до сетки; при равенстве сохраняется сторона champion. Cost и выбор интервала не менялись. Тот же edge rule перенесён в Monte Carlo simulator. Политика использует только текущую геометрию и не читает тестовый номер или будущее.

## Результаты

На целевом case 15 траншея сократилась на **420 м**: `438 920 → 438 500 м`. Однако один из четырёх новых synthetic-потоков показал крупную регрессию, а полный Open15 в сумме стал хуже.

| Поток | Champion, м | Кандидат, м | Δ траншеи |
|---|---:|---:|---:|
| Open case 15 | 438 920 | 438 500 | −420 |
| Fresh 01 — uniform 1–40, random deletes | 12 620 | 12 600 | −20 |
| Fresh 02 — bimodal 8–12/28–40, FIFO | 10 800 | 11 800 | +1 000 |
| Fresh 03 — lengths 15–40, LIFO | 13 780 | 13 780 | 0 |
| Fresh 04 — short-to-wide phase shift, random deletes | 13 980 | 13 920 | −60 |

На четырёх synthetic streams сумма KPI уменьшилась с **3.613327855608** до **3.536717268377**; дельта — **−0.076610587231**; подробные значения и хэши — в `manifest.json`. Эта suite мала и специально покрывает разные delete/size modes, поэтому результат — сигнал о чувствительности, а не оценка частоты регрессии.

После выигрыша на case 15 выполнен локальный Open15: **29.932085817214 → 29.919298026064**, Δ **−0.012787791151**. Кандидат прошёл 15/15. Case 15 улучшился на 420 м и case 7 на 20 м; case 11 улучшился на 160 м. Но case 5 ухудшился на 500 м, case 9 — на 20 м, cases 12, 13 и 14 — по 20 м каждый. Эти потери перевесили выигрыш. Это **no-go**, кандидат не заменяет champion.

Максимальный solver CPU кандидата на Open15 — **2.550207 с**, RSS — **6.875 MiB**; на синтетическом gate максимум CPU — **2.721300 с**, RSS — **5.594 MiB**. Лимиты 5 с / 256 MiB не превышены. Все тесты завершились `ok`.

## Артефакты и воспроизведение

- Покейсовые сравнения: [Open15](comparison_open15.csv) и [case 15 + fresh streams](comparison_synthetic.csv).
- Исходник, бинарник, генератор, входы, baseline/candidate summary и CSV сохранены в этой папке; все provenance hashes в [manifest.json](manifest.json).
- Генератор свежих трасс: `python3 results/pipes/improvement/case15_section_phase/make_fresh.py`.
- Сборка из корня проекта: `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wshadow -pedantic -Werror results/pipes/improvement/case15_section_phase/source/section_phase_edge.cpp -o results/pipes/improvement/case15_section_phase/bin/section_phase_edge`.
- Pair-screen на target + четыре synthetic stream запускался командой `python3 tools/pipes_harness.py --solver <solver> --interactor results/pipes/final/bin/interactor --tests results/pipes/improvement/case15_section_phase/tests --out <output-dir> --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120`.
- Open15 запускался той же командой с `--tests data/pipes/open`. Сайт и Docker не использовались.
- Frozen final и `src/pipes.cpp` не менялись: SHA-256 `c4b737b9…32a991` и `526ba58e…1dfec8`.

Полная агрегированная и покейсовая численность, exact scores, input/output provenance и хэши находятся в манифесте; см. CSV для подробных данных.
