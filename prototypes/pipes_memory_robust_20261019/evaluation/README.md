# Calibration and sealed final inputs

This directory contains fixed synthetic command streams for evaluating generalization of the current Pipes candidate. The generator does not invoke a solver or calculate KPI. It validates command count, pipe lengths, sequential PID creation, active-PID deletions, peak live volume, and positive final live length while building each stream.

`calibration/` has 26 inputs: ordinary streams use a 32–1000 live-pipe band, with IID length profiles, FIFO/LIFO/size-biased lifetime patterns, temporal regime switches, correlated cohort/size/age deletions, and six exact Open15 prefixes followed by different continuations. `C17`–`C19` are the only 200,000-operation calibration stresses: high live set, long/short regime shifts intended to create many reusable gaps, and a small live set intended to expose frequent short rollouts.

The short calibration subset is recorded in `calibration/manifest.json`: `C01`, `C03`, `C05`, `C07`, `C09`, `C11`, `C13`, `C15`, `C18`, `C19`, `C22`, and `C26`. It spans baseline IID, extreme lengths, lifetime bias, regime changes, correlated removals, stress, and an Open15-prefix switch.

`sealed-final/` contains eight different fixed inputs and seeds, including two 200,000-operation stresses and Open15-prefix switches. Its inputs and manifest are read-only. Do not inspect or run them until the parent freezes the candidate. The planned comparison is the frozen `candidate-physical` against plain Best-Fit from the same starting command streams; do not compare against the superseded round2 variant.

`sealed-final-extra/` is a separate, additive catalog of 16 more fixed inputs (10 ordinary, correlated, and regime-shift streams plus six new Open15-prefix switches). These use 12,000–40,000 operations and a 32–2000 live-pipe band. They have distinct seeds from calibration and the first sealed catalog. The parent will evaluate the combined 24 final streams only after freezing the candidate. Generate this catalog with `python3 generate_extra.py`; the script refuses to overwrite it and leaves `sealed-final/` untouched.

`confirmation/` is the separate blind confirmation catalog for the delayed-reliability-gate hypothesis: 12 ordinary/correlated/regime-shift streams, eight Open15-prefix switches, and four 200,000-operation resource stresses. Its 24 fixed seeds are `202610198001` through `202610198024`; its manifest and all inputs are read-only. Generate it with `python3 generate_confirmation.py`. Do not evaluate it until the second hypothesis is frozen.

Run `python3 generate_suite.py` only when both output directories are absent. It refuses to overwrite either suite. Manifests record the seeds, families, full generation parameters, input hashes, operation counts, and structural validity counters. These checks are not a substitute for running the official interactor during calibration; no solver/harness evaluation has been performed here.
