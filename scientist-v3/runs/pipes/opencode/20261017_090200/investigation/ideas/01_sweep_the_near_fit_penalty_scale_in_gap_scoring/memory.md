# Memory Log

## Context
- 2026-10-17T16:15:00Z | scope=idea | cycle_index=1 | idea_id=idea_pipes_unfit_penalty_scale_001
- Task: improve the online C++ policy for the Pipes interactive task; maximize the official weighted KPI over the 15 frozen open scenarios (max 32.1) under 5 s solver CPU / 256 MiB RSS, trench cap 100,000,000 m, <=200,000 commands, lengths 1..40.
- Incumbent: best_program_manifest combined_score=30.074287976405728, correct=true, source_attempt_id=bootstrap, entrypoint src/pipes.cpp (seeded baseline threshold 29.4471645435).
- No prior ideas or attempts; conclusions.md was empty at cycle start.

## Idea Discoveries
- 2026-10-17T16:15:00Z | step=idea | idea_id=idea_pipes_unfit_penalty_scale_001
- Alternatives considered before selecting the hypothesis: (a) big-gap fallback before trench expansion (rejected after source inspection: bestFittingGapFromSet already evaluates the smallest fitting gap even when its slack > 40, so the hypothesized dead path does not exist); (b) raising the Monte Carlo lookahead budget (rejected for cycle 1: kMcMaxGaps=64 and the 4096-active-pipe gate disable rollouts in large states, so the effect would be confined to small cases and would conflate two changes); (c) magnitude-weighted miss penalties in the fit score (deferred as the follow-up refinement if the scale sweep plateaus).
- Selected hypothesis: the flat near-fit penalty scale kUnfitPenaltyScale=60 in scoreGap / bestFittingGapFromSet is mis-tuned relative to the slack × window-length term; sweeping {0, 30, 60, 120} is a single-factor, deterministic, resource-neutral test of that claim.
- Evidence: incumbent source inspected at task/program_0/src/pipes.cpp (lines 19, 974-985, 1302-1339); scoring prefers minimal slack with a 60-weighted miss penalty over window sizes above the slack.
- gate=updated; trigger=b; reason=first cycle opens the allocator-hypothesis category that conclusions.md did not yet cover.

## Program Evaluations
- (none yet this idea; evaluation happens in the execution loop)

### 2026-10-17T10:02:00Z | step=edit | attempt_id=idea_pipes_unfit_penalty_scale_001_attempt_01 | idea_id=idea_pipes_unfit_penalty_scale_001 | program_id=program_1
- Files changed: cloned program_0 -> program_1 (plain filesystem copy per prompt Hard Boundaries; the guarded clone utility is not applicable at index 0->1); edits confined to program_1/src/pipes.cpp; program_spec.toml left byte-identical to program_0.
- Change: added `constexpr std::array<std::int64_t, 4> kUnfitPenaltyVariants{0, 30, 60, 120}` and `constexpr std::size_t kSelectedUnfitPenaltyVariant = 2` at namespace scope; all three fit-score sites (Allocator::scoreGap, Allocator::bestFittingGapFromSet, RolloutState::fitScore) now read a local `unfitPenaltyScale = kUnfitPenaltyVariants[kSelectedUnfitPenaltyVariant]` instead of the hard-coded 60. The legacy kUnfitPenaltyScale constant was removed (dead code); RolloutState::fitScore was wired to the selected scale too so the rollout clone stays behaviorally identical to the allocator.
- Selected index: 2 (scale 60, incumbent). Rationale: this stage's Hard Boundaries forbid running evaluate.py, tests, or any candidate execution, so the sanctioned 4-variant sweep could not be executed here; with no measured winner the idea bundle mandates retaining scale 60. The sweep table and selected index are in the final source exactly as specified for harness-side verification; a later harness evaluation can flip the index to compare variants.
- Evidence: `g++ -std=c++20 -fsyntax-only -Wall -Wextra` passes clean; diff vs program_0 contains only the 3 scoring-site hunks + table declaration; all 6 required verification patterns (3 rubric + 3 protocol) grep-confirmed in program_1/src/pipes.cpp; no randomness, timing, or per-placement work added (one constexpr read).
- Limitation recorded: per-case KPI deltas vs the incumbent manifest and combined_score measurement are owned by the post-exit harness evaluation; they were NOT collected in this stage and must not be claimed.
- gate=kept; trigger=none; reason=conclusions.md already prescribes sweeping the near-fit penalty scale and this cycle produced no new evaluation evidence to refine or contradict it.

## Failures / Regressions
- (none yet)

## Next Hypotheses
- 2026-10-17T16:15:00Z | step=idea
- Next action for the execution agent: implement kUnfitPenaltyVariants{0, 30, 60, 120} with kSelectedUnfitPenaltyVariant, evaluate each variant against the frozen open set, report per-case deltas vs the incumbent, keep scale 60 if no variant wins, then consider magnitude-weighted misses as the follow-up hypothesis.
- 2026-10-17T10:02:00Z | step=final | attempt_id=idea_pipes_unfit_penalty_scale_001_attempt_01 | program_id=program_1
- Status: implementation complete; awaiting the harness-owned official evaluation. Recommended next step after evaluation: if the harness reveals the variant index is selectable pre-evaluation, sweep {0, 30, 120} (indices 0/1/3) in later cycles one index per cycle with per-case KPI deltas; if all variants regress, the mis-tuning hypothesis is wrong and the follow-up is magnitude-weighted miss penalties in the fit score.
