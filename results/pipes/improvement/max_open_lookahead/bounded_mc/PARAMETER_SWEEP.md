# Corrected MC parameter sweep

Источник для обоих вариантов — замороженный corrected MC `cohort_owner_mc_rollout.cpp`, SHA-256 `fadbe93b0ae2d1dd1ff2ebce3dbdf384f3969272865f108729092b9d8cb98be3`. Исходник и canonical не менялись. Каждый вариант — отдельная копия, в которой изменена ровно одна константа; model, seed, threshold, и decision budget оставлены прежними.

## Результат полного open-прогона

Порог сохранения кандидата: строго выше **29.781127**. Baseline corrected MC набрал **29.77315080574852**.

| Вариант | Изменённый параметр | Open score (15/15) | Δ к baseline | Δ к порогу | Максимум CPU / RSS |
|---|---:|---:|---:|---:|---:|
| T18/D4/B32 | trials: 12 → 18 | 29.765467090815918 | −0.007683714932604 | −0.015659909184082 | 1.434117 с / 7.234375 МиБ |
| T12/D6/B32 | depth: 4 → 6 | 29.735135557949320 | −0.038015247799201 | −0.045991442050680 | 0.972707 с / 7.718750 МиБ |

Оба варианта прошли harness на всех 15 официальных open-кейсах, но оба набрали меньше frozen baseline и не достигли порога. Поэтому повторный open, holdout-v2 и стресс-прогоны для этих вариантов не запускались.

Изменения локальны: T18/D4/B32 теряет улучшение baseline в кейсе 12 (weighted delta `−0.007683714932602`), сохраняя кейс 7. T12/D6/B32 теряет кейс 7 (`−0.022677484787018`) и ухудшает кейс 12 (`−0.015337763012182`). Остальные per-case значения приведены в [`parameter-sweep-per-case.csv`](parameter-sweep-per-case.csv), включая SHA-256 каждого входа.

## Изолированные исходники и сборки

- Baseline source SHA-256: `fadbe93b0ae2d1dd1ff2ebce3dbdf384f3969272865f108729092b9d8cb98be3`
- T18/D4/B32 source: [`sweep_t18_d4_b32/candidate.cpp`](sweep_t18_d4_b32/candidate.cpp), SHA-256 `0719483f6f62d529f5e6dcf8dab92673a28ae224795926c2e9874608421a0517`
- T18/D4/B32 binary: [`sweep_t18_d4_b32/solver`](sweep_t18_d4_b32/solver), SHA-256 `9f0fdc8694411549efd4a289250f83ea7a30b6f4435d51cba25f9b39d8c23d38`
- T12/D6/B32 source: [`sweep_t12_d6_b32/candidate.cpp`](sweep_t12_d6_b32/candidate.cpp), SHA-256 `fbaa1b7125a0dde945a8b6a772e4e5184db162fb439c9a4f1faf4560ec5c7a61`
- T12/D6/B32 binary: [`sweep_t12_d6_b32/solver`](sweep_t12_d6_b32/solver), SHA-256 `989bee45afa1f91f993449d44bd95058dc565e70fb16ec259b64b3f7ff47dff4`

Both were compiled with `clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror`. The official harness is `tools/pipes_harness.py` (SHA-256 `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d`), and the interactor is `tools/interactor` (SHA-256 `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`). Per-variant summaries and all run outputs are in each variant's `open/` directory. [`parameter-sweep-manifest.json`](parameter-sweep-manifest.json) records paths, hashes, and exact harness invocations.
