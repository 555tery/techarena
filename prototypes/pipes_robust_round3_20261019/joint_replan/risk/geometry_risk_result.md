# Open8/Open13 full-prefix risk rerank

The frozen round2 source and its binary agree on the first five allocation positions for both Open8 and Open13: `[688, 3064, 2124, 0, 496]`. A direct run on each raw command stream reproduces these decoded positions with `fallback=0` and `table_conflict=0`.

A 200-trial bounded re-ranking required exact final ceilings and minimized the maximum cumulative `T/BF` over every command in both full streams, then integrated positive ratio excess with the common 388-command prefix counted once, then integrated meter excess, then early shared coordinates. The release source has full-stream max ratio 77.5 at command 2 (`T=3100`, `BF=40`). The previous compact plan `[20, 0, 2144, 26, 522]` lowered it to 54 at command 3. The risk-ranked plan is `[0, 6, 2144, 26, 522]`: max ratio remains 54, while shared-prefix-once integrated ratio excess improves from 22905.9731 to 22904.9731 and pair-summed meter excess improves by 40.

Both full physical replays pass at exact `T=4640/3220`; all 210 allocations in the common prefix have shared positions. Per-allocation position files are `geometry_risk_open8.positions` and `geometry_risk_open13.positions`; the global block mapping is in the parent `geometry_pair_provenance.json`. The full risk and physical audit is in `geometry_risk_audit.json`, with exact source-decoded/source-executed first allocations in `geometry_risk_provenance.json`.

This remains pair-scoped. Compatibility with the other 13 Open15 tables and the official harness have not been checked.
