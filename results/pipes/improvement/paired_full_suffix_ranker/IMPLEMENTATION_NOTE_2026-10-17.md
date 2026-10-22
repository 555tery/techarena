# Generator implementation note

The preregistered stream matrix and seeds are unchanged. During generation, the repository generator's `shortest` and `longest` policies were observed scanning the complete active list for every deletion, which made a 200,000-command validation input impractically slow. Before any solver ran on validation data and before any validation labels existed, generation was stopped and switched to a local Fenwick/heap implementation copied from the prior `learned_gap_value/qualification_generator.py`.

The replacement was checked against `tools/generate_pipes_synthetic.py` on 30 previously unused 5,000-command streams, covering all length profiles, deletion policies, and both preregistered regimes. Command vectors matched exactly in all 30 checks. Per-check command hashes and both generator source hashes are in `inputs/generator-equivalence.json`. The input manifest records the local and repository generator hashes.

One child process from the stopped slow-generation attempt was later observed writing validation seed `2026101938` (200,000, uniform, longest, steady). It had exited by the time it was inspected for termination, so I rebuilt only that input with the verified fast generator after confirming no generator process remained. Its final SHA-256 is `933410f9df65c26f957840398fd902e330d0ad320bab5f63a7714641a70c35c9`, unchanged from the manifest entry; the full input manifest hashes were recomputed. The training pipeline reads train inputs only.

This is an implementation-only change; it did not change the seed ranges, stream matrix, candidate, gate, or labels. The original slow generation attempt was stopped before validation solver runs/labels; the preregistered inputs are regenerated with the verified equivalent implementation.
