# Frozen local traces v3

Open15 and holdout-v2 здесь — использованные ранее, только описательные datasets. Этот протокол не перезапускает frozen-final solver и не считает их независимым holdout.

## Точные наборы

- Open15: ровно 15 inputs `data/pipes/open/1.in` … `15.in`; ровно 15 replies `results/pipes/final/open-run-size-cohort-lanes/runs/1/judge_output.txt` … `runs/15/judge_output.txt`. Input hashes сверяются с `results/pipes/final/open-run-size-cohort-lanes/cases.csv`.
- Holdout-v2: ровно `data/pipes/synthetic/final-holdout-v2/case-01.in` … `case-12.in`; ровно replies `results/pipes/final/holdout-run-size-cohort-lanes/runs/case-01/judge_output.txt` … `case-12/judge_output.txt`. Input hashes сверяются с `data/pipes/synthetic/final-holdout-v2/manifest.json`.
- Пропущенный, добавленный или переименованный `*.in` или `judge_output.txt`, неправильный case count, повторный case либо другой input/reply/source-manifest SHA — hard fail. Пути в frozen manifest должны быть точными относительными путями из этого перечня.

## Hash-only freeze и scoring gate

После отдельного review source v3 `freeze_local_manifest.py` с токеном `local-trace-freeze-reviewed-v3` создаёт `local-trace-manifest.json` рядом с кодом. Он сначала проверяет exact file sets/counts и authoritative input hashes, затем сохраняет для каждого case:

- относительные пути и SHA-256 input и reply;
- combined trace SHA-256: `SHA256(UTF8("PipesTrace-v1\n" + input_sha256 + "\n" + reply_sha256))`;
- SHA-256 authoritative case manifest (`cases.csv` или `manifest.json`);
- SHA-256 `SOURCE_SHA256SUMS`, чтобы связать trace manifest с reviewed source.

Freeze tool не парсит команды, не извлекает outcome и не считает score. Он создаёт manifest в exclusive-create mode: повторный запуск не перезаписывает замороженный файл. Если traces изменились после freeze, scoring остановится на проверке hash.

Перед чтением trace evaluator проверяет source hashes, точные наборы и количества файлов, SHA authoritative input manifest, per-case input/reply/combined trace hashes всего выбранного dataset. Только после успешной проверки всех файлов он вызывает parser. SHA reviewed `local-trace-manifest.json` передаётся через `--approved-manifest-sha256`; для scoring также нужен токен `local-diagnostics-reviewed-v3`. Open15 и holdout-v2 всегда оцениваются по отдельности.
