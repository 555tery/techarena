# Open8/Open13 common-prefix compact plan

A pair-only lifetime-aware reordering of the 8,406 allocations in the union of Open8 and Open13 preserves both exact target ceilings and the 388-command shared prefix. The first two shared allocations move from `[688, 3064]` to `[20, 0]`; thus the old second allocation at 3064 moves to zero while the first allocation moves to 20. The full physical replays remain valid, with peak ends 4639/3219 and rounded ceilings 4640/3220. The per-case `F/T` values are unchanged: 4627/4640 and 3192/3220.

The search used the current round2 frozen tables as seeds, then 200 deterministic interval-ordering trials. It accepted only candidates matching both exact ceilings and minimized the two shared prefix coordinates lexicographically. The pair packer used every Open8/Open13 lifetime interval from the joint geometry data. A separate byte-occupancy replay validated both complete command streams and the common-prefix coordinates.

Artifacts: `geometry_tie.positions` maps the 8,406 sorted block IDs in `geometry_pair_provenance.json` to positions; `geometry_pair_audit.json` records the audit; `geometry_open8_13_pair.in` is the pair-only lifetime instance. This is pair-scoped evidence only: compatibility with allocations/lifetimes in other Open15 cases and the official harness remain unverified.
