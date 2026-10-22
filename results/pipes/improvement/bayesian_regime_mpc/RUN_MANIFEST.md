# Run manifest — Bayesian latent-regime MPC

Дата: 2026-10-17 local. Только native macOS / Apple Clang и локальный официальный harness/interactor; Docker, сайт, таблица лидеров не использовались. Ветка завершена с **NO-GO**, поэтому holdout-v2 и Open15 не запускались.

## Training и freeze

8 synthetic train streams использованы для pooled categorical prior и выбора `(hazard, concentration)` по leave-one-stream-out prequential log-loss. Выбран `h=1/512`, `κ=32`; posterior run-length cap 128. Hyperparameter scores и 48 вероятностей `p0` — в `model_params.json`.

До fresh validation заморожены candidate SHA `367062f40794f22a865cd0e866a975f900ed2da8c5a9bc6dca45d54f8a700810`, model-param SHA `72d1bf837cc977a7692198ad2a429e3cb1ee2b5f6c42f1a27e0ca176f76c629`, preregistered gate SHA `9e3ff61aa70a7cd2e792b3d0f44200c9afc6ed8403a0c859292633aa22aa2d55` и all 28 validation-input hashes. Freeze record — `freeze_manifest.json` (SHA `c63fafb1192c76f5cd2348797ef845b94cc8435911ec372a253dcbbe88c73d2d`). Повторная проверка перед анализом подтвердила неизменность candidate, frozen copy, model params, input manifest и gate.

## Основные hashes

| Артефакт | SHA-256 |
|---|---|
| frozen final `results/pipes/final/solution.cpp` и его snapshot | `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991` |
| canonical `src/pipes.cpp` | `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8` |
| candidate source `source/bayesian_regime_mpc.cpp` | `367062f40794f22a865cd0e866a975f900ed2da8c5a9bc6dca45d54f8a700810` |
| fitted synthetic model `model_params.json` | `72d1bf837cc977a7692198ad2a429e3cb1ee2b5f6c42f1a27e0ca176f76c629d` |
| train/validation input manifest | `1c2978aaa6bf88eb501081b24b79c822f43453498b09b94183c22d260524a31a` |
| source synthetic generator | `e6a540f372f486af62e1f86f3ebaa08394a6d7b629d8db40dcf80eb3fc79ae17` |
| frozen binary | `056ecc51faa74107259e99f8529e159820ef64a9d6ed3c8a38f85a1a84e921d0` |
| Bayesian candidate binary | `41f11dbabe49c72c3c4fc5ca5eb4954a6ff82f1a144ff9c9d1f0074daa706f53` |
| `tools/pipes_harness.py` | `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d` |
| official interactor binary | `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a` |

## Exact commands

From repository root:

```sh
python3 results/pipes/improvement/bayesian_regime_mpc/generate_data.py
python3 results/pipes/improvement/bayesian_regime_mpc/train_model.py
python3 results/pipes/improvement/bayesian_regime_mpc/build_candidate.py
python3 tools/compare_pipes_binaries.py --solver frozen=results/pipes/improvement/bayesian_regime_mpc/bin/frozen --solver bayesian=results/pipes/improvement/bayesian_regime_mpc/bin/bayesian --tests results/pipes/improvement/bayesian_regime_mpc/inputs/train --out results/pipes/improvement/bayesian_regime_mpc/runs/train_smoke_final --interactor results/pipes/final/bin/interactor --baseline frozen
python3 results/pipes/improvement/bayesian_regime_mpc/freeze_validation.py
python3 tools/compare_pipes_binaries.py --solver frozen=results/pipes/improvement/bayesian_regime_mpc/bin/frozen --solver bayesian=results/pipes/improvement/bayesian_regime_mpc/bin/bayesian --tests results/pipes/improvement/bayesian_regime_mpc/inputs/validation --out results/pipes/improvement/bayesian_regime_mpc/runs/validation --interactor results/pipes/final/bin/interactor --baseline frozen
python3 results/pipes/improvement/bayesian_regime_mpc/analyze_validation.py
```

Strict compilation used Apple clang 17.0.0 (`clang-1700.0.13.5`) and `-O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror`. `build_candidate.py` compiled the exact frozen snapshot and isolated candidate with the same flags.

## Validation result

All 28/28 streams passed for both solvers. Frozen weighted KPI sum was `23.9541007184`; candidate `23.9549085005`; paired mean Δ `+0.000028849`. Preregistered stratified paired bootstrap (20,000 resamples, seed `9801702026`, strata `family × size`) gave 95% CI `[-0.000535065, +0.000592482]`. The 200k mean was `-0.000502226`; only 5/7 family means were nonnegative. Thus multiple quality guards fail and the candidate does not qualify.

Candidate resource maxima: CPU `1.190035 s`, RSS `8.828 MiB`, below 5 s / 256 MiB. Detailed paired rows, including every input SHA, trench length, CPU and RSS: `stream_results.csv`; machine-readable gate: `analysis.json`; concise conclusion: `REPORT.md`. No source or binary was copied into frozen final or canonical locations.
