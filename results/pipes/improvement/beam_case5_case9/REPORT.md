# Offline hindsight beam: cases 5 and 9

## Вывод

На exact trace текущего `results/pipes/final/solution.cpp` ограниченный offline beam не нашёл ни одного placement-пути, который снижает high-water trench в проверенных окнах case 5 или case 9. Это относится к нескольким размерам окна и ранней, средней и поздней стадиям. Поэтому здесь не возникла причинная online-гипотеза, которую стоило бы проверять на полном open-15; такой запуск не делался.

Эффект коротких hindsight-окон на case 15 остаётся малым. Повтор тех же окон по current final дал экономию **0, 40 и 80 м** на 64 командах. На case 5 и 9 найденная экономия равна **0 м** во всех завершённых suffix-окнах. В этом смысле локальный tiny-gap эффект case 15 не повторился как измеримое снижение траншеи на case 5/9.

При этом свободный объём на case 5/9 часто раздроблен: **1 856 из 1 977** ростовых размещений case 5 и **2 448 из 2 498** case 9 произошли, когда суммарный свободный объём уже не меньше новой трубы, но ни один отдельный gap не подходил по длине. Это подтверждает проблему фрагментации, но не показывает, какое наблюдаемое online решение должно изменить её заранее.

Приведённая ниже live-volume граница остаётся широкой: до **2 480 м** для выбранного окна case 5 и до **8 180 м** для case 9. Это верхние границы только по сохранению trench не ниже начального H и округлённого максимума live volume. Они предполагают, что свободный объём можно упаковать произвольно, поэтому не являются оценкой достижимой экономии и не противоречат нулевым beam-witness результатам. В свою очередь, bounded beam не доказывает, что оптимальное решение тоже экономит ноль.

## Протокол

- Замороженный источник: `results/pipes/final/solution.cpp`, SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`. Запуск, из которого взяты ответы, записан в `results/pipes/final/manifest.json`; он использовал этот source и бинарь `dabb6910bde7550dbf4ab03d6d7b450d0a91f53a90dc06e52d6b271c8602000c`.
- В каждом suffix-срезе начальный layout и все трубы до окна зафиксированы по official judge trace. Oracle получает ID удалений, происходящих только внутри выбранного окна. Полный будущий поток за окно не подаётся в beam.
- Beam width — 16; предварительный shortlist — до 128 состояний; gap cap — 12. В старых gaps проверяются выбранные крайние и центральные старты, в новой части tail — все допустимые целые старты. Точный official answer сохраняется в beam как feasible control.
- `oracle_saving_m` — лучший найденный feasible witness в этом bounded action space. Это не точный оптимум. Отдельная `best_possible_saving_upper_bound_m` равна `max(0, baseline_H_end - max(initial_H, ceil(peak_live/20)*20))`; это строгая, но слабая верхняя граница из live volume.
- Growth-fragmentation audit использует геометрию exact baseline trace. Он считает событие фрагментированным, только если до размещения суммарный free volume ≥ длины трубы, а maximum gap < длины трубы.

Фазы case 5 содержат по 125 размещений длины `k` и затем 63 удаления, для `k=1..40`. Проверены `k=1,10,20,40`. Фазы case 9 содержат 1 000 размещений длины `k` и затем 500 удалений, для `k=1,2,4,8,16,32`; выбраны ранний `k=1`, средний `k=4` и поздний `k=32`.

## Окна case 5

В каждом размере окна строки покрывают указанные четыре длины. Для каждого выбранного `k` baseline и beam trench совпали; найденная экономия — 0 м.

| Длина `k` | Начало фазы | Старт окон 64 / 128 / 188 команд | Состав окна 64 / 128 / 188 (P/D) | Верхняя граница экономии, м (64 / 128 / 188) |
|---:|---:|---:|---:|---:|
| 1 | 1 | 96 / 61 / 1 | 30/34, 65/63, 125/63 | 0 / 0 / 0 |
| 10 | 1 693 | 1 788 / 1 753 / 1 693 | 30/34, 65/63, 125/63 | 260 / 260 / 260 |
| 20 | 3 573 | 3 668 / 3 633 / 3 573 | 30/34, 65/63, 125/63 | 600 / 1 240 / 1 240 |
| 40 | 7 333 | 7 428 / 7 393 / 7 333 | 30/34, 65/63, 125/63 | 1 200 / 2 480 / 2 480 |

Итого — 12 окон; лучший найденный witness во всех строках — 0 м. Полные 188-командные фазы включают весь блок размещений и последовавшие за ним 63 удаления.

## Окна case 9

Для коротких окон старт сдвинут к границе между размещениями и удалениями: 64 команды включают 32/32 P/D, 128 — 64/64, 256 — 128/128, 512 — 256/256. Везде baseline и beam trench совпали.

| Длина `k` | Начало фазы | Старт окон 64 / 128 / 256 / 512 команд | Верхняя граница экономии, м (64 / 128 / 256 / 512) |
|---:|---:|---:|---:|
| 1 | 1 | 969 / 937 / 873 / 745 | 0 / 0 / 0 / 0 |
| 4 | 3 001 | 3 969 / 3 937 / 3 873 / 3 745 | 140 / 240 / 240 / 240 |
| 32 | 7 501 | 8 469 / 8 437 / 8 373 / 8 245 | 1 020 / 2 040 / 4 080 / 8 180 |

Лучший найденный witness во всех 12 окнах — 0 м. Дополнительно полностью посчитано раннее окно `start=1,count=1 500`: 1 000 размещений длины 1 и 500 удалений; baseline и beam оба заканчиваются на 1 000 м, экономия и live-volume ceiling равны 0 м. Позднее полное окно `start=7 501,count=1 500` не завершилось в разумном бюджете: процесс остановлен после 67,02 с wall / 64,67 с CPU, результата нет. Остальные, более короткие окна поздней фазы завершились.

## Проверка case 15 на current final

Тем же скриптом пересчитаны прежние 64-командные срезы по exact trace текущего final. Они дали 0 / 40 / 80 м на стартах 100 000 / 120 000 / 160 000. Старый отчёт case15_policy, считавший 20 / 40 / 60 м, использовал другой baseline source SHA `e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41`; здесь он приведён только как исторический ориентир. На current final максимальный локальный witness равен четырём 20-метровым шагам.

## Фрагментация по exact trace

| Case | Ростовые размещения | Суммарный рост trench | При free volume ≥ трубы и max gap < трубы | Доля событий / роста |
|---:|---:|---:|---:|---:|
| 5 | 1 977 | 62 760 м | 1 856 событий / 60 340 м | 93,9% / 96,1% |
| 9 | 2 498 | 61 960 м | 2 448 событий / 60 960 м | 98,0% / 98,4% |

Это сильный симптом фрагментации, но suffix-oracle не может менять расклад до начала окна. У case 5, например, в начале фазы длины 20 было 376 gaps, из которых 313 меньше 20 м; у case 9 перед поздним окном длины 32 все 1 168 исходных gaps меньше 32 м. Поэтому нулевой local witness не опровергает возможную ценность более раннего многофазного планирования; он лишь не выявляет из проверенных suffix окон устойчивый локальный сигнал для online-эвристики.

## Команды и ресурсы

Все completed окна рассчитаны командой вида:

```sh
python3 results/pipes/improvement/beam_case5_case9/offline_beam_windows.py \
  --input data/pipes/open/CASE.in \
  --judge-output results/pipes/final/open-run-size-cohort-lanes/runs/CASE/judge_output.txt \
  --out results/pipes/improvement/beam_case5_case9/caseX_wN.json \
  --windows STARTS --count N --width 16 --gap-cap 12
```

Точные значения `CASE`, `STARTS`, `N` и имена outputs:

```sh
python3 results/pipes/improvement/beam_case5_case9/offline_beam_windows.py --input data/pipes/open/5.in --judge-output results/pipes/final/open-run-size-cohort-lanes/runs/5/judge_output.txt --out results/pipes/improvement/beam_case5_case9/case5_w64.json --windows 96 1788 3668 7428 --count 64 --width 16 --gap-cap 12
python3 results/pipes/improvement/beam_case5_case9/offline_beam_windows.py --input data/pipes/open/5.in --judge-output results/pipes/final/open-run-size-cohort-lanes/runs/5/judge_output.txt --out results/pipes/improvement/beam_case5_case9/case5_w128.json --windows 61 1753 3633 7393 --count 128 --width 16 --gap-cap 12
python3 results/pipes/improvement/beam_case5_case9/offline_beam_windows.py --input data/pipes/open/5.in --judge-output results/pipes/final/open-run-size-cohort-lanes/runs/5/judge_output.txt --out results/pipes/improvement/beam_case5_case9/case5_w188.json --windows 1 1693 3573 7333 --count 188 --width 16 --gap-cap 12
python3 results/pipes/improvement/beam_case5_case9/offline_beam_windows.py --input data/pipes/open/9.in --judge-output results/pipes/final/open-run-size-cohort-lanes/runs/9/judge_output.txt --out results/pipes/improvement/beam_case5_case9/case9_w64.json --windows 969 3969 8469 --count 64 --width 16 --gap-cap 12
python3 results/pipes/improvement/beam_case5_case9/offline_beam_windows.py --input data/pipes/open/9.in --judge-output results/pipes/final/open-run-size-cohort-lanes/runs/9/judge_output.txt --out results/pipes/improvement/beam_case5_case9/case9_w128.json --windows 937 3937 8437 --count 128 --width 16 --gap-cap 12
python3 results/pipes/improvement/beam_case5_case9/offline_beam_windows.py --input data/pipes/open/9.in --judge-output results/pipes/final/open-run-size-cohort-lanes/runs/9/judge_output.txt --out results/pipes/improvement/beam_case5_case9/case9_w256.json --windows 873 3873 8373 --count 256 --width 16 --gap-cap 12
python3 results/pipes/improvement/beam_case5_case9/offline_beam_windows.py --input data/pipes/open/9.in --judge-output results/pipes/final/open-run-size-cohort-lanes/runs/9/judge_output.txt --out results/pipes/improvement/beam_case5_case9/case9_w512.json --windows 745 3745 8245 --count 512 --width 16 --gap-cap 12
python3 results/pipes/improvement/beam_case5_case9/offline_beam_windows.py --input data/pipes/open/9.in --judge-output results/pipes/final/open-run-size-cohort-lanes/runs/9/judge_output.txt --out results/pipes/improvement/beam_case5_case9/case9_w1500_early.json --windows 1 --count 1500 --width 16 --gap-cap 12
python3 results/pipes/improvement/beam_case5_case9/offline_beam_windows.py --input data/pipes/open/15.in --judge-output results/pipes/final/open-run-size-cohort-lanes/runs/15/judge_output.txt --out results/pipes/improvement/beam_case5_case9/case15_reference_w64.json --windows 100000 120000 160000 --count 64 --width 16 --gap-cap 12
python3 results/pipes/improvement/beam_case5_case9/trace_fragmentation.py 5 9
```

Ресурсы diagnostic CPU / память: `case5_w188` на одном окне `start=3573` — 2,22 с CPU, 2,29 с wall, 29,7 MB maximum resident set; case15 reference из трёх окон — 19,11 с CPU, 19,76 с wall, 99,4 MB maximum resident set. Батчи case5 64/128/188 заняли соответственно 0,33 / 2,23 / 12,67 с wall; case9 64/128/256/512 — 3,32 / 6,27 / 12,63 / 26,46 с wall. Ранний case9 full phase `count=1500` — 9,64 с CPU / 9,79 с wall. `trace_fragmentation.py` — 5,5 с wall. Поздний full-phase case9 остановлен на 67,02 с wall / 64,67 с CPU; на срезе около 51 с процесс использовал 17 776 KiB RSS, это не peak measurement.

Official run baseline ресурсы из final manifest: case 5 — 0,04528 с solver CPU / 3,09 MiB RSS; case 9 — 0,063619 с / 3,09 MiB. Harness trace использует official interactor; повторного official harness запуска для этой диагностики не было.

## Хэши

- Final source: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`; final manifest: `e38a8bcc529929dc7f18f159d626b092cb35d6c1b2e6a2863197087f1dff5537`.
- Final binary: `dabb6910bde7550dbf4ab03d6d7b450d0a91f53a90dc06e52d6b271c8602000c`; interactor binary: `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`.
- Inputs: case 5 `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b`; case 9 `cfb711efa3a9ccccc17e7170fc7c2ea19c12ed45b789da3a4b2c80750d7ca128`; case 15 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`.
- Exact judge outputs: case 5 `e78bb7900ad184037e578f13012eaae1cb8d854700ee7ddc520ac6c8a113bb63`; case 9 `fc4bea23ad81727480ab7d95fcabc46c2e029f41d9ec016466557b9c00f7cc7f`; case 15 `0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e`.
- `offline_beam_windows.py`: `8601e03b108f71205010984a605ecd4606f8835a0881da090f45796bd543c0d7`; `trace_fragmentation.py`: `e389263e3ed53def0aad93c17d88dfa99b656c8860646a924b073a29f39172d1`; `fragmentation.json`: `369ba383bb5a91778748d2464c158016f1fab6f27d5b05af2f723b040ddaef61`.
- Window JSON hashes and per-window metrics are preserved under this directory; see [artifact_manifest.json](artifact_manifest.json).

Ни `results/pipes/final/solution.cpp`, ни `src/pipes.cpp` не менялись. Источники не загружались на платформу.
