# Scope addendum — local official-data diagnostic

Recorded 2026-10-17 07:01 Novosibirsk, before any validation labels or solver results were produced.

The root coordinator clarified that the active user objective explicitly includes local Open15 and holdout evaluation. Therefore, regardless of the synthetic gate outcome, once the final ranker and candidate source are frozen and pass transcript/correctness checks, run exactly one comparison of that immutable candidate against the frozen-final baseline on local Open15 and holdout-v2. These are diagnostic evaluations only: no retraining, feature or threshold adjustment, candidate selection, or repeat run based on their results.

This addendum extends the earlier preregistered scope; it does not change the synthetic gate or its pass criteria. The synthetic gate remains the independent transfer qualification. The local tests use no website, leaderboard, submission, or Docker.

The stream-generation process had started immediately before this clarification but had not written validation labels or run either solver on validation streams. It was stopped before labels/results and will be restarted only after this addendum is recorded.
