# Memory Log

## Context
- cycle_index: 3; idea_id: cycle03_stakes_gated_trial_reallocation; idea_dir_name: 03_stakes_gated_trial_reallocation_with_incumbent_equivalent_floor
- Task: improve the online C++ policy for the Pipes interactive task on the 15 frozen open scenarios; incumbent best_program_manifest score 30.074287976405728 (correct, source_attempt_id=bootstrap).
- Prior evidence: cycle01 attempt failed on execution artifacts (rubric_status.json invalid); cycle02 attempt ran clean with combined_score 30.04392677668611, correct=true, but scored below the incumbent so the combined_score gate failed (rubric_overall_pass=false).

## Idea Discoveries
- Alternatives considered: (1) raise kMcTrialsMax/share of the cycle02 anytime extension — rejected: the extension fired and still scored below the byte-compatible incumbent, so more stake-blind trials are not evidence-backed; (2) pivot the deadline machinery to move-priority ordering — deferred: too large a behavioral change without isolating first; (3) selected: reframe the same deadline-bounded extension as stakes-gated trial reallocation with an incumbent-equivalent floor.
- Selected hypothesis: extra unbiased i.i.d. re-simulation trials are spent only on high-stakes decisions (longest remaining pipe lengths, declared kStakesLengthThreshold); every other decision keeps exact incumbent behavior (12-trial core, RNG, candidate ordering, tie-break, fallback move). Extended trials re-simulate the single current decision with a fresh RNG stream reseeded from base_seed + decision index (no shared-scenario state), bounded by verified wall-clock bookkeeping, per-turn deadline, safety margin under the 5 s solver CPU limit, and strict-improvement-only acceptance.
- Why this cycle decision is best from recent evidence: cycle02's only scientific signal is a small below-incumbent delta from a stake-blind extension whose default path was byte-compatible; gating the same mechanism to high-stakes decisions isolates whether stake-blind trial spending was the cause, without invalidating the reusable deadline machinery.

## Program Evaluations
- none this stage (idea generation only; no execution permitted during idea generation)

## Failures / Regressions
- cycle02 (data): combined_score 30.04392677668611 < incumbent 30.074287976405728, correct=true; failure category = scientific underperformance of a stake-blind anytime trial extension, not an execution failure (rubric_status_valid=true, run_exit_code=0). Root-cause hypothesis on record: extra shared-scenario trials changed low-value decisions for the worse.

## Next Hypotheses
- Execution recommendation: implement program_1/src/pipes.cpp per idea_bundle.json implementation_plan; evaluate on the same frozen open-test set; report per-case deltas by scenario id vs 30.074287976405728, not just the aggregate.
- Branch guide (also in notes_for_agent): rare extension fires → widen stakes coverage or raise kExtendedTrialsCap; long-pipe per-case losses → added trials are noise in the MC estimate, pivot to candidate priority ordering; gate fails despite all non-negative per-case deltas → incumbent score is timing-sensitive, pivot to deterministic tie-breaks.

## Program Evaluations
- 2026-10-17T13:54:23Z (attempt stage): none this stage. The official evaluation is harness-run after exit; no evaluate/test execution was permitted, so no score evidence exists yet. Report must be per-case deltas by scenario id vs incumbent 30.074287976405728 when the harness report is available.

## Candidate Implementation (attempt)
### 2026-10-17T13:54:23Z | step=edit | scope=attempt
- attempt_id: cycle03_stakes_gated_trial_reallocation_attempt_01; idea_id: cycle03_stakes_gated_trial_reallocation; program_id: program_1.
- summary: candidate implemented per implementation_plan in program_1/src/pipes.cpp by cloning program_0 with plain filesystem copy (program_spec.toml unchanged, entrypoint present). Changes kept the incumbent default path byte-compatible (same 12-trial MC core, xorshift scenario sampler, candidate ordering, tie-break, and incumbent return value reproduced as fallback_move before any extension). Added: (1) steady-clock round bookkeeping - runStart, per-command verifyClockBookkeeping monotonicity sanity, timeBookkeepingVerified gate - so the allocator stays off unless bookkeeping is verified; (2) stakes gate: bool high_stakes = pipe_length >= kStakesLengthThreshold (kStakesLengthThreshold=24, long pipes consume the most trench) and trials = high_stakes ? kExtendedTrialsCap (96) : kIncumbentTrialsPerDecision (12); (3) unbiased i.i.d. re-simulations of the single current decision over the incumbent candidate set with a fresh mt19937_64 reseeded per decision via rng.seed(base_seed + decision_index), no shared-scenario state across decisions; (4) per-turn deadline bounded extension: remaining_ms = total_time_limit_ms (5000) - elapsed_ms minus 400 ms safety margin, divided over remaining kMcDecisionBudget slots, turn_deadline enforced every extended trial with immediate break; (5) strict-improvement-only acceptance under identical tie-breaks and the incumbent mean-saving bar, with the incumbent-equivalent fallback move emitted otherwise; extension only selects within existing gaps through incumbent consumeAtSide plumbing, so trench can never grow beyond incumbent behavior (cap 100,000,000 m untouched).
- evidence: all 9 rubric source_contains patterns present verbatim (verified by grep); g++ -std=c++20 -O2 -Wall -Wextra compile passes with zero warnings (compile-only to a temp object; binary never executed); no diagnostics on stdout (stdout protocol untouched); memory bounded (mt19937_64 + small arrays).
- next_action: harness runs the only official evaluation after exit; report per-case deltas by scenario id vs incumbent 30.074287976405728, not just the aggregate; interpret per the branch guide in notes_for_agent (rare extension fires -> widen threshold or raise cap; long-pipe losses -> pivot to candidate priority ordering; gate fails with non-negative deltas -> pivot to deterministic tie-breaks).
