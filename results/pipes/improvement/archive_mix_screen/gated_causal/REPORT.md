# Gated composition: reverse re-arm + geometric alignment

## Итог

На frozen c4 gate 1 сохранял case 9 geometric-выигрыш (−200 м) и не менял KPI case 5. Перенос того же gate на PID/46 дал **29.793175357170 / 32.1** против **29.791529008364**: **+0.001646348806**, полностью за счёт case 9 (−200 м). Это локальный Open15-плюс; до цели 30.3 остаётся 0.506824643. Case 5 остался на PID/46, 62 620 м. На ранее использованном holdout-v2 результат и judge-транскрипты совпали с PID/46; это регрессионная проверка, не независимое подтверждение.

Ничего не менялось в `results/pipes/final/solution.cpp` или `src/pipes.cpp`. Сайт и Docker не использовались.

## Причинные сигналы и два проверенных gate

- Case 5: длинные блоки размеров 1…40, после каждого — чередующиеся удаления. Сигнал стабильной последовательности удалений `+2` становится доступен после восьмого удаления; плавный тренд размеров фиксируется на блоке длины 3. Поэтому gate 1 разрешает обратный re-arm только после обоих наблюдаемых сигналов, а geometric alignment оставляет только для lane без smooth-trend veto. Re-arm-condition активировался в case 5, но не изменил KPI/транскрипт: его эффект на этот поток не воспроизвёлся.
- Case 9: размеры блоков 1,2,4,8,16,32 дают собственный geometric-run сигнал; smooth-trend veto не включается. Geometric alignment сохраняет выигрыш 200 м.
- **Gate 1:** reverse re-arm при `smoothTrend && sameSizeRun && alternatingDeleteMode`; geometric alignment только при `!smoothTrend && sameSizeRun`. На c4-screen case 5 не изменился (62 760 м), case 9 улучшился до 61 760 м. Тот же gate, перенесённый на PID/46, прошёл Open15 выше.
- **Gate 2, отклонён:** re-arm на любом подтверждённом alternating run, geometric signal ограничен точным геометрическим отношением. C4-screen ухудшил case 5 до 63 060 м и case 9 до 62 240 м; полного Open15 не запускал.

Gate-условия используют только уже наблюдённые серии размеров, удаления и режимные флаги. Номер теста, PID как lookup и будущие команды в политике не использовались.

## Open15: PID/46 против кандидата

| Case | Траншея PID/46, м | Кандидат, м | Δ траншеи, м | Δ взвешенного score |
|---:|---:|---:|---:|---:|
| 1 | 20 | 20 | 0 | 0 |
| 2 | 20 | 20 | 0 | 0 |
| 3 | 20 | 20 | 0 | 0 |
| 4 | 60 | 60 | 0 | 0 |
| 5 | 62 620 | 62 620 | 0 | 0 |
| 6 | 20 | 20 | 0 | 0 |
| 7 | 1 700 | 1 700 | 0 | 0 |
| 8 | 4 700 | 4 700 | 0 | 0 |
| 9 | 61 960 | **61 760** | **−200** | **+0.001646348806** |
| 10 | 15 380 | 15 380 | 0 | 0 |
| 11 | 22 620 | 22 620 | 0 | 0 |
| 12 | 10 320 | 10 320 | 0 | 0 |
| 13 | 3 280 | 3 280 | 0 | 0 |
| 14 | 37 820 | 37 820 | 0 | 0 |
| 15 | 438 920 | 438 920 | 0 | 0 |
| **Итого** |  |  |  | **+0.001646348806** |

Успешно: 15/15. Максимум solver CPU — 0.957 с; максимум RSS — 7.125 MiB, в пределах 5 с / 256 MiB. Транскрипты отличаются от PID/46 только в case 9.

## Holdout-v2

12/12 успешно; score **5.135264324280**, равен PID/46. Все 12 judge-транскриптов побайтно совпали с PID/46. Максимум CPU — 0.183 с, RSS — 4.266 MiB. Набор ранее использовался в разработке.

## Воспроизведение

Сборка:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/improvement/archive_mix_screen/gated_causal/pid46_rearm_geometric_gate1.cpp -o results/pipes/improvement/archive_mix_screen/gated_causal/pid46_rearm_geometric_gate1
```

Open15:

```sh
python3 tools/pipes_harness.py --solver results/pipes/improvement/archive_mix_screen/gated_causal/pid46_rearm_geometric_gate1 --interactor results/pipes/final/bin/interactor --tests data/pipes/open --out results/pipes/improvement/archive_mix_screen/gated_causal/pid46-open15 --name pid46-rearm-geom-gate1-open15 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Holdout-v2 использует ту же команду с `--tests data/pipes/synthetic/final-holdout-v2`, `--out results/pipes/improvement/archive_mix_screen/gated_causal/pid46-holdout-v2` и `--name pid46-rearm-geom-gate1-holdout-v2`.

## SHA-256

- Кандидат source: `89f7173f61fba3710e752607df4fec83195abe88a14a51b75ff7a710ed6d1982`
- Кандидат binary: `77116793bc43a22c219244a3218eed26630980fb9e97ccd0eaa601332ab25fe7`
- PID/46 source: `1a643a2b8a560de5c7dfd7efe0b288dc93785e96400d2ae6fd4ec7eea5f55f59`
- Frozen final: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`
- Canonical source: `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`
- Open15 summary: `c24d7fcc04b9d5ac09e80083d4549836922b7b70d21c41b1496647698733afaf`
- Open15 cases CSV: `85c3e8a39a1e570dd7c5db553bc1c272a780056e5101df2337393331ba19b77e`
- Holdout summary: `3d9fcc3cecc220e6c7daab05588bc3ffade04750959b7f9d317e26e527fdf705`
- Holdout cases CSV: `5287cbab9c62fd0d4c37f96fc1ec7a5cf9b3f6b622b0911bdaff48d7310a1259`
