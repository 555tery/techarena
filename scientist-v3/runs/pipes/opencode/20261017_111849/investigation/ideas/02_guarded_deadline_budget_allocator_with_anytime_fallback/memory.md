# Memory Log

## Context
- attempt_id: `cycle02_guarded_deadline_budget_allocator_attempt_01`
- idea_id: `cycle02_guarded_deadline_budget_allocator`
- program_id: `program_1`
- Task: improve the online C++ policy for the Pipes interactive task; maximize the official weighted `combined_score` on the frozen 15 open scenarios (subset max 32.1). Incumbent `program_0` = 30.074287976405728.
- Stage boundaries honored: no evaluation runs, no candidate execution, no program_2, no evaluator artifacts; the harness runs the only official evaluation after exit.

## Idea Discoveries
### 2026-10-17T13:01:37Z | step=idea | scope=idea
- summary: Translated the "Guarded Deadline-Budget Allocator with Anytime Fallback" bundle onto the actual incumbent. The incumbent's per-turn search is the bounded MC rollout in `chooseGapWithRollout` (kMcDecisionBudget=32 lifetime decisions, kMcTrials=12, kMcDepth=4, shared-scenario CRN per batch). Key interpretation decision: the only knowable "remaining turns" for the budgeted search are the remaining rollout-decision slots (`kMcDecisionBudget - mcDecisionsUsed`); a per-command share (remaining_ms / remaining commands under the documented 200,000-command cap) would be ~0.025 ms and make the allocator inert, so the deadline share is divided across remaining decision slots while per-turn bookkeeping is still updated once per command.
- evidence: full read of `program_0/src/pipes.cpp` (1481 lines); `active_idea.json` hypothesis + rubric patterns; `task.md` limits (5 s solver CPU, 256 MiB RSS, <=200,000 commands, <=100,000,000 m trench).
- next_action: implement in `program_1/src/pipes.cpp` behind verified time bookkeeping.

### 2026-10-17T13:05:30Z | step=edit | scope=attempt
- summary: `program_1` created and implemented. Files changed: **only `program_1/src/pipes.cpp`** (plus the untouched byte-identical `program_spec.toml` from the clone). Changes: (1) added `<chrono>`; (2) added constants `kTotalTimeLimitMs=5000`, `kSolverSafetyMarginMs=750`, `kMaxCommands=200000`, `kMinimumAnytimeBudgetMs=1`, `kMcTrialsMax=64`; (3) added Allocator time-bookkeeping members, constructor seeding `sessionStart`, and `beginTurn()` (clock-sanity guard that deactivates the allocator on a malformed clock; literal formulas `remaining_ms = total_time_limit_ms - elapsed_ms;`, `turn_budget_ms = std::max(1LL, remaining_ms / std::max(1LL, turns_left));` with a clamp to remaining-minus-margin, and `turn_deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(turn_budget_ms);`); (4) `chooseGapWithRollout` keeps the incumbent 12-trial core byte-identical (same RNG seed, same scenario draws, same candidate ordering and `best` tie-break, same acceptance at `trialsRun == kMcTrials`), then runs an anytime extension — extra `kMcTrials`-sized shared-scenario batches over the same candidate ordering, bounded by `turn_deadline` and the `kMcTrialsMax=64` exhaustive-trial cap, with the verbatim deadline break — only when the incumbent evidence accepted no move && `budgetAllocatorActive`; acceptance threshold scales with `trialsRun` so departures must beat the candidate-0 baseline by >=1 m mean saving per trial; (5) final move selection uses the verbatim `if (!found_move) move = fallback_move;` with `fallback_move = baselineGap->first` (the incumbent-equivalent move); (6) `main()` calls `allocator.beginTurn()` once per non-zero command; exit-on-0, response prints, and invalid-PID fallback untouched; extension counters are solver-local only (diagnostics stay behind the existing `MC_ROLLOUT_DIAGNOSTICS` ifdef, not emitted).
- evidence: all 5 rubric source patterns present verbatim (grep on lines 510, 513, 519, 1214, 1243); `g++ -std=c++20 -fsyntax-only -Wall -Wextra` passes for both the default build and the `MC_ROLLOUT_DISABLED` guarded build with zero warnings; `diff -rq program_0 program_1` shows only `src/pipes.cpp` differs; `program_1/program_spec.toml` byte-identical to incumbent spec.
- next_action: stop after program_1 is ready; the harness runs the official evaluation.

## Program Evaluations
- (none recorded yet — official evaluation runs after this attempt exits; per-case deltas vs program_0 on the identical frozen open set must be reported by scenario id, never aggregate alone)

## Failures / Regressions
### 2026-10-17T13:01:37Z | step=idea | scope=idea
- cycle 1's attempt died before producing any score evidence (`run_exit_code=1`, cause unknown). Root-cause mitigation carried into this cycle: guarded integration — default move-selection path kept byte-compatible with the incumbent by construction, allocator activates only after time bookkeeping is verified, and a `-fsyntax-only` parity check (default + `MC_ROLLOUT_DISABLED` builds) isolates build failure from scientific failure. No candidate/regression behavior was executed locally.

## Next Hypotheses
- If `combined_score <= 30.074287976405728`: inspect the per-case report for regressions by scenario id first. If every case is ~identical to the incumbent, the anytime extension likely rarely fired (turn budgets are small when decision slots divide large headroom); next lever is raising `kMcTrialsMax` / the per-decision share (deep-tune budgets) per the idea notes.
- Pivot option recorded by the idea bundle: if the incumbent already adapts effort per turn (it does cap effort at 32 lifetime decisions), the same deadline machinery can be pivoted to connection/move priority ordering instead of time budgeting.
- Keep the incremental search strictly incumbent-ordered (topGapCandidates order) with the >=1 m mean-saving bar; that bar is the main guard against open-test overfit.
