# Screen: увеличенные контекст и горизонт MC

## Итог

По указанию координатора этот отдельный sweep остановлен после заранее запланированного screen на официальных кейсах 5, 9 и 15. Ни один из трёх вариантов не превысил baseline по взвешенной сумме screen: все получили `10.859085056537428`, разница равна нулю. Поэтому полный Open15, holdout-v2 и synthetic-наборы для этих вариантов не запускались. `results/pipes/final/solution.cpp` и `src/pipes.cpp` не менялись.

Это не результат Open15 и не основание ранжировать варианты по полному набору. Кейс 15 имеет вес 10; в screen он совпал с baseline по траншее и KPI. Для B/C transcript case 15 отличается, но score и trench не изменились.

## Предварительная проверка повторов

До подготовки вариантов прочитаны `sampleScenario` и отчёты:

- `max_open_lookahead/REPORT.md` и `bounded_mc/REPORT.md`;
- `bounded_mc/PARAMETER_SWEEP.md`;
- `current_sensitivity/REPORT.md` и `experiment-results.json`.

В них уже проверяли `kMcDepth=6` на более раннем source; тот результат был отрицательным и не повторялся. Sensitivity sweep текущего source менял пороги и budget, но оставлял `kMcDepth=4` и контекст до 3. Здесь проверены только три различающихся заранее заявленных варианта, касающихся максимального контекста и/или глубины. Повтор параметров trials/seed/model не делался.

В текущем генераторе сценариев выбираются только непрерывные блоки из уже наблюдённой истории: `start <= n-depth`, источник ограничен недавним окном; при сопоставлении поиск идёт от самого длинного доступного suffix-context к короткому. Непрочитанные команды не используются.

## Результаты screen

Baseline — frozen source `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` с `context=3`, `depth=4`. Варианты независимо скопированы из него:

| Конфигурация | Единственные изменения | Source SHA-256 | Binary SHA-256 | Weighted screen | Δ к baseline | Max solver CPU / RSS |
|---|---|---|---|---:|---:|---:|
| Baseline | — | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` | `14613b0b51d87bd0f258bfb03c1ec5950e25849812748203d94b1826a7aaca98` | 10.859085056537428 | 0 | 1.186243 s / 7.53125 MiB |
| A: context 6, depth 4 | `maxContext: 3 → 6` | `2364bea3198e0fbcd5cf4e3d1c5ef4e7df13ed32d8a2aa28be0000bb62f93b46` | `8f98b5823c511d2fc2b0bae22799a91a493f3d7867e79155d162bb9b13819c81` | 10.859085056537428 | 0 | 1.120104 s / 6.90625 MiB |
| B: context 3, depth 8 | `kMcDepth: 4 → 8` | `94156f8202cb412cb05a14b2919757595f2847a558d587285011e7d60c7f64b5` | `830b2d913c9123749c6f5c30404217503c3714dd8b8fc08385b001f19893e541` | 10.859085056537428 | 0 | 1.434695 s / 5.59375 MiB |
| C: context 6, depth 8 | both changes above | `3907a4e878ea998157641cf1902e2648657221fad49d59b1e4aa2a6ace2cab46` | `ea585070914fa3c5f78541d82be62799599766b5d4539fe31dd653d9831d4281` | 10.859085056537428 | 0 | 1.888752 s / 5.625 MiB |

Every case returned `ok` under the official harness, with limits 5 s CPU / 256 MiB RSS. Per-case values were identical for all variants:

| Case | Weight | Trench | Weighted score | Input SHA-256 | Judge output SHA-256 |
|---:|---:|---:|---:|---|---|
| 5 | 1 | 62,760 m | 0.810070108349267 | `bae469c3ed43bba21ab4a9cd9ecef4c53bb2f99fbd9f6cc246f9c3e082f1b32b` | `e78bb7900ad184037e578f13012eaae1cb8d854700ee7ddc520ac6c8a113bb63` |
| 9 | 1 | 61,960 m | 0.508392511297611 | `cfb711efa3a9ccccc17e7170fc7c2ea19c12ed45b789da3a4b2c80750d7ca128` | `fc4bea23ad81727480ab7d95fcabc46c2e029f41d9ec016466557b9c00f7cc7f` |
| 15 | 10 | 438,920 m | 9.540622436890550 | `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353` | baseline/A `0382b67c434136d5a015c37ccd4749d35624418ec61eece53af28fe74221bd0e`; B/C `68b8ba5502cb14154bd0d5b4797dc42a326e0afc17ed613b78bb57f248e0e249` |

## Воспроизводимость

- Исходник запуска и рецепт вариантов: [`run_screen.py`](run_screen.py), SHA-256 `c29f65a3ecd5dc66f38387014afa1c8f7d4618b0ff5d41b8aceb6ce7242a9c10`.
- Итоговые данные: [`screen-results.json`](screen-results.json), SHA-256 `56d544affcd921f245d63f932527e743e8b67b5fa84499cbfd705e492a62c084`; [`screen-ranking.csv`](screen-ranking.csv), SHA-256 `36208dea85e5516cf58d8cef880f735af20dc0f66f43b0b92695bc6b468b5e55`.
- Официальный harness `tools/pipes_harness.py`: SHA-256 `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d`.
- Официальный interactor `tools/interactor`: SHA-256 `47994e837450bc4b0b683736194c2dce8023dd30f257c3161e8e69245d15b9a`.
- Замороженный final source после screen: SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- `src/pipes.cpp` после screen: SHA-256 `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.

Точная команда strict build находится в `run_screen.py`; harness-артефакты, stdout/stderr, таблицы и отдельные frozen исходники сохранены в этом каталоге. Дальнейший sweep context/depth не проводился.
