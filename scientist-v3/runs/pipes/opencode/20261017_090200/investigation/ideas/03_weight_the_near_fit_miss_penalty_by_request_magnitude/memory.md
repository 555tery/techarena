# Memory Log

## Context
- Campaign: improve the online C++ allocator policy for the Pipes interactive task; incumbent manifest combined_score=30.074287976405728 / 32.1 (correct=true, bootstrap), seeded baseline 29.4471645435.
- Cycle 3 idea step. Cycles 1 (flat near-fit penalty scale sweep, submitted at incumbent scale 60) and 2 (MC rollout decision-budget raise, submitted at budget 128) both returned combined_score 0.0 / correct=false with cause unavailable; treated as unestablished, not as allocator defects.

## Idea Discoveries
### 2026-10-17T11:10:00Z | step=idea | idea_id=idea_pipes_miss_penalty_magnitude_003 | cycle_index=3
- Selected hypothesis: magnitude-weighted miss penalties. The incumbent gap-fit score charges a flat penalty (scale 60) per missed request length in the post-placement miss window (slack, 40]; weighting each miss by its request magnitude (per-miss term unfitPenaltyScale x request^exponent) should bias placement toward preserving large-gap capacity on wide-request-spread scenarios while leaving uniform scenarios nearly unchanged (exponent 0 reproduces legacy scoring exactly).
- Variant sweep: kMissWeightExponentVariants{0, 1, 2}, kSelectedMissWeightExponentVariant = 1 (linear weighting); index 0 = flat legacy fallback, index 2 = quadratic probe, re-selectable in later cycles. Change confined to the three miss-accumulation sites (Allocator::scoreGap, Allocator::bestFittingGapFromSet, RolloutState::fitScore); miss-window loop bounds, placement, removal, expansion, cohorts, LIFO lane, kMc* rollout constants and gates, counterfactual comparison, and protocol untouched.
- Alternatives considered and rejected: re-probing MC budget index 2 (512) — conditional per cycle-2 memory, but magnitude weighting was the explicitly recorded next lead and pairs naturally with the untouched fit-score term; re-sweeping flat penalty-scale indices {0, 30, 120} — no usable per-case evidence from cycle 1 (correct=false), so the sweep spends the single harness evaluation without a new hypothesis; keeping the flat scale exactly — no new information, incumbent already in the manifest.
- gate=updated; trigger=b; reason=cycle opens the magnitude-weighted miss-penalty lead (new category) plus an acceptance caveat for the two zero-score submissions, neither previously covered in conclusions.md.

## Program Evaluations
- none yet this cycle; the harness owns the single official evaluation after exit.

## Failures / Regressions
- Recurring acceptance anomaly (cycles 1-2): correct=false at combined_score 0.0 for near-incumbent configurations with no per-case deltas; root-cause kept unknown per task guidance; not attributed to allocator changes without evidence.

## Next Hypotheses
- Execution agent implements the variant table + selected index 1 in program_1/src/pipes.cpp only; harness runs official evaluation; report per-case KPI deltas vs incumbent; if the gate fails, re-select exponent 0 (flat) next cycle; if linear wins, probe quadratic (index 2) as the follow-up confirmation.
- Overflow note: request <= 40 keeps the maximum weighted term near 60 * 1600; 64-bit accumulation is ample.

## Edit Step
### 2026-10-17T11:05:00Z | step=edit | attempt_id=idea_pipes_miss_penalty_magnitude_003_attempt_01 | idea_id=idea_pipes_miss_penalty_magnitude_003 | program_id=program_1
- Cloned program_0 to program_1 with the trusted clone utility (src.investigation.program_clone); verified via directory diff that program_1/src/pipes.cpp was byte-identical to the incumbent before editing.
- Implemented the magnitude-weighted miss penalty in program_1/src/pipes.cpp only: added `constexpr std::array<int, 3> kMissWeightExponentVariants{0, 1, 2}` and `constexpr int kSelectedMissWeightExponentVariant = 1` next to kUnfitPenaltyScale; rewrote the three miss-accumulation sites (RolloutState::fitScore, Allocator::scoreGap, Allocator::bestFittingGapFromSet) to accumulate a 64-bit `weightedMisses` where each miss term is weighted by an inner exponentiation loop `weight *= request` up to the selected exponent (index 1 = linear; exponent 0 reproduces the legacy flat penalty exactly).
- Untouched by design: miss-window loop bounds (slack+1 .. 40), placement, removal, expansion, parity cohort slabs, LIFO lane, kMc* rollout constants and gates, counterfactual comparison, protocol responses (`std::cout << digs << ' ' << start << '\n' << std::flush`, negative-PID coordinate response, `while (std::cin >> command)`, silent exit on command 0), program_spec.toml.
- Guardrails kept: no evaluation artifacts created, no evaluate.py run, no diagnostics added, no program_2; `int misses` accumulation sites now count zero elsewhere in the source (verified by search), so flat scoring survives only via exponent index 0.
- gate=updated; trigger=b; reason=edit step confirmed within the already-open magnitude weighting category; conclusions.md unchanged.

