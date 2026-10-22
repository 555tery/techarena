# Финальный артефакт Pipes: size cohort lanes

`solution.cpp` — побайтная копия проверенного кандидата `results/pipes/improvement/case9_next/source/size_cohort_lanes.cpp`. Предыдущий финал сохранён в `solution_alternating_delete_parity_edges.cpp`; более ранние corrected-MC + scoped-run и cohort-owner версии остаются в отдельных файлах. Канонический `src/pipes.cpp` не менялся.

## SHA-256

- Текущий source: `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Финальный solver binary: `dabb6910bde7550dbf4ab03d6d7b450d0a91f53a90dc06e52d6b271c8602000c`.
- Предыдущая parity-edge версия: `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`.
- Corrected-MC + scoped-run backup: `e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41`.
- Cohort-owner backup: `2cce753dfaa9aa6f625cefee9550edff6d8c4ce8c915e9cb77cbfbb0c3dc3583`.
- Canonical `src/pipes.cpp`: `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.
- Official interactor binary: `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`.

## Строгая сборка и harness

Сборка прошла на Apple Clang 17.0.0, target `arm64-apple-darwin25.6.0`:

```sh
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/final/solution.cpp -o results/pipes/final/bin/solution
python3 tools/pipes_harness.py --solver results/pipes/final/bin/solution --interactor results/pipes/final/bin/interactor --tests data/pipes/open --out results/pipes/final/open-run-size-cohort-lanes --name final-size-cohort-lanes --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/final/bin/solution --interactor results/pipes/final/bin/interactor --tests data/pipes/synthetic/final-holdout-v2 --out results/pipes/final/holdout-run-size-cohort-lanes --name final-size-cohort-lanes-holdout-v2 --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```

Open15: **15/15**, `29.789717928594 / 32.1`. Максимум solver CPU `1.021344 s`, RSS `7.687500 MiB`; wall orchestration максимум `7.178252 s`. Holdout-v2: **12/12**, `5.135264324280 / 12.0`; outputs совпали с предыдущим финалом по всем 12 кейсам. Максимум CPU `0.189368 s`, RSS `4.171875 MiB`; wall orchestration максимум `1.360109 s`. Лимиты harness — 5 s CPU и 256 MiB RSS на кейс; превышений нет.

Полные case-by-case outcomes, входные hashes, CPU и RSS находятся в `manifest.json`, `open-run-size-cohort-lanes/cases.csv` и `holdout-run-size-cohort-lanes/cases.csv`. Root `score.txt` остался `0.5`.

## Дельта и ограничения

Относительно предыдущего финала (parity-edge, `29.785293754007 / 32.1`) open score вырос на `0.004424174587`. Изменились только два случая: case 5 `62,800 → 62,760 м`, case 9 `62,440 → 61,960 м`. На holdout-v2 прироста нет: score и все judge outputs совпадают.

Правило переключает edge по наблюдаемой когорте размещений конкретной длины внутри уже обнаруженной длинной same-length серии. Это причинная политика, но открытый выигрыш остаётся на двух open-кейсах; нейтральный holdout не доказывает перенос на скрытые или иные потоки. В MC rollout удаления задаются quantized rank-permille и применяются к counterfactual active list; восстановленный PID может отличаться и менять последующее срабатывание детектора. Поэтому оценки rollout приблизительны.

Экспериментальный отчёт и исходная проверка: [case9_next/REPORT.md](../improvement/case9_next/REPORT.md). Полный hash manifest: `manifest.json`.
