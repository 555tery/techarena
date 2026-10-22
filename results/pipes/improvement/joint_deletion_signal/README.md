# Joint deletion signal study

Статус: v3 source/protocol готов к review. Synthetic streams, smoke, Open15/holdout traces и predictive metrics не запускались. Local per-case trace hash manifest ещё не создан: для него нужен отдельный hash-only freeze после review, а raw trace files в этой ревизии не читались.

## Протокол

- [`PREREGISTERED.md`](PREREGISTERED.md) — estimand, pair cap, сравниваемые модели, warmup, scores и общие gates.
- [`Synthetic-DGP.md`](Synthetic-DGP.md) — finite-OR positive control, валидные Pipes-команды, seeds и точный synthetic file set.
- [`Local-traces.md`](Local-traces.md) — exact Open15/holdout case sets, manifest freeze и проверка SHA до scoring.

## Исходный код

- [`pipes_common.py`](pipes_common.py) — общий matcher, deterministic `PAIR_CAP=256`, features и DGP-константы.
- [`generate.py`](generate.py) — gated synthetic генератор и отдельные каталоги `eval/` и `train-smoke/`.
- [`trace.py`](trace.py) — replay только после gates: проверка геометрии и извлечение snapshots/outcomes.
- [`model.py`](model.py), [`prequential_eval.py`](prequential_eval.py) — marginal/joint модели, proper scores, calibration, stream bootstrap.
- [`freeze_local_manifest.py`](freeze_local_manifest.py) — отдельный gated hash-only freeze; в этой ревизии не запускался.
- [`smoke.py`](smoke.py), [`evaluate_saved.py`](evaluate_saved.py) — отдельные gates; evaluator требует exact file sets и hashes до parser/scoring.
- [`SOURCE_SHA256SUMS`](SOURCE_SHA256SUMS) — frozen manifest всех protocol/source файлов; сам hash-файл не включает созданный позднее `local-trace-manifest.json`.
