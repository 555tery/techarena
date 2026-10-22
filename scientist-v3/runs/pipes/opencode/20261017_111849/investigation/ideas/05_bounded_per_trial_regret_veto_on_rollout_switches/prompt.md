# Role
You are an autonomous scientist/engineer implementing one candidate program for a harness-owned evaluation.

# Task Context
## Goal
Improve the online C++ policy for the Pipes interactive task. Maximize the official weighted KPI score over the 15 supplied open scenarios, while preserving valid behavior and looking for changes that plausibly generalize to the undisclosed scenarios.

# Active Idea
Attempt ID: `cycle05_bounded_regret_switch_veto_attempt_01`
Idea ID: `cycle05_bounded_regret_switch_veto`

Idea bundle (`./active_idea.json`):
```json
{
  "hypothesis": "Cycle-4 widened the rollout candidate window (top-3 to top-6) and relaxed the rollout-entry gate, and the official weighted score regressed to 30.05161049161871 versus the incumbent bootstrap 30.074287976405728 (correct=true, same frozen 15-scenario open set). Cycle-2 showed extra shared-scenario trial batches also regress (30.04392677668611) and cycle-3 showed a guarded unbiased i.i.d. extension is exactly flat, so trial counts, decision caps, and stream types are exhausted levers. The remaining in-policy lever named by the distilled conclusions for window-touched regressions is a pooled secondary acceptance criterion. Allocator hypothesis: the incumbent's mean-only switch bar (totalTrench[best] + kMcTrials * kMcMinimumMeanSavingM <= totalTrench[0] over the shared 12-trial CRN pool) accepts noise-driven switches whose advantage collapses on individual sampled futures; recording the per-trial trench of each rollout candidate and vetoing any switch whose worst paired trial trails the reference move by more than kMcPerTrialMaxLossM = 4 meters removes exactly those fragile switches while keeping every other decision byte-identical to the incumbent (top-3 window, front==baseline gate, budgets, seeding, sampler unchanged). Switch suppression only: the accepted-switch set is a subset of the incumbent's, so the per-case delta measures exactly the incumbent's least-credible switches. Prediction: per-case deltas non-negative on balance with combined_score strictly above 30.074287976405728 if fragile switches were net-harmful; exactly flat if no incumbent switch ever had a worse-than-4m adverse trial; per-case regressions would falsify the noise hypothesis and localize the beneficial-switch cases for a roll-depth or sampler-coverage pivot.",
  "idea_id": "cycle05_bounded_regret_switch_veto",
  "implementation_plan": [
    "Clone the incumbent program_0 (combined_score=30.074287976405728) into program_1 and edit only program_1/src/pipes.cpp; program_spec.toml untouched; no wall-clock calls, no new RNG streams, stdout protocol byte-identical.",
    "In topGapCandidates restore the incumbent top-3 truncation: if (candidates.size() > 3) candidates.resize(3); dropping the cycle-4 kRolloutCandidateWindow=6 widening; keep the slack<=40 scan break, the scoreGap ascending order, and the highSide-aware start tie-break byte-identical.",
    "In chooseGapWithRollout restore the incumbent early return: if (candidates.size() < 2 || candidates.front().start != baselineGap->first) { return baselineGap->first; } placed before ++mcDecisionsUsed; keep every guard (kMcDecisionBudget=32, observedHistory.size() >= 32, freeByStart.size() <= kMcMaxGaps, activePipeCount <= kMcMaxActivePipes) byte-identical.",
    "Beside the other kMc constants add: constexpr std::int64_t kMcPerTrialMaxLossM = 4; Beside std::array<std::int64_t, 3> totalTrench{}; add std::array<std::array<std::int64_t, kMcTrials>, 3> trialTrench{}; and inside the existing rollout loop store trialTrench[candidate][trial] = simulation.trenchLength; while keeping totalTrench[candidate] += simulation.trenchLength; unchanged (same 12 shared scenarios, same xorshift seeding, no extra rollouts).",
    "After the unchanged strict-less argmin scan add the pooled regret veto: bool trialRegretExceeded = false; then for each of the 12 shared trials set it true and break when trialTrench[best][trial] > trialTrench[0][trial] + kMcPerTrialMaxLossM; accept the switch only if best != 0 && !trialRegretExceeded && totalTrench[best] + static_cast<std::int64_t>(kMcTrials) * kMcMinimumMeanSavingM <= totalTrench[0], returning candidates[best].start on acceptance and return baselineGap->first; otherwise, byte-identical to incumbent.",
    "Before finishing: compile clean with g++ -std=c++20 -O2 -Wall -Wextra (object output outside program_1), grep-verify every rubric source pattern verbatim in program_1/src/pipes.cpp with each prescribed condition on a single exact line, confirm no evaluator artifacts under program_1 and no program_2 or later directory.",
    "Stop after program_1 is ready. The harness runs the only official evaluation on the frozen 15-scenario open set: report per-case deltas by scenario id vs incumbent 30.074287976405728, never the aggregate alone, and attribute any per-case regression to vetoed regret-exceeding switches in the failure log."
  ],
  "notes_for_agent": "Prior art (3 retrieved via webfetch this cycle; Semantic Scholar HTTP 429, skipped): 'Ranking and Selection: A New Sequential Bayesian Procedure for Use with Common Random Numbers' (Gorder & Kolonko, arXiv:1410.6782v2) - with CRN across candidates, selection quality is governed by how the fixed budget is spent and how observations are screened, not by trial count; 'Efficient Ranking and Selection in Parallel Computing Environments' (Ni, Ciocan, Henderson & Hunter, arXiv:1506.04986v1) - selection validity must be protected against the reference system, supporting a switch bar stricter than a bare mean; 'Data-driven Ranking and Selection under Input Uncertainty' (Wu, Wang & Zhou, arXiv:1708.08526v4) - sequential elimination with confidence bands fits the indifference-zone setting, matching keep-the-reference unless pooled paired evidence clears a stated margin. Incumbent mechanics are pinned in the hypothesis and implementation_plan (verified by direct read of task/program_0/src/pipes.cpp). Cycle-4 evidence: top-6 window plus relaxed gate plus baseline-anchored acceptance regressed to 30.05161049161871, so window widening and gate relaxation are retired; this cycle vetoes fragile incumbent switches and adds none. Do NOT raise kMcTrials, kMcDecisionBudget, kMcDepth, or add i.i.d. re-seeded streams. Cycle-3/4 harness reported declared source patterns missing although the mirrored sources contained them verbatim (cause unknown); mitigation is short single-line executable-snippet patterns. Branch guide: exactly flat -> incumbent switches already regret-robust, pivot to rollout depth or sampler coverage without stretching trials; per-case regressions -> incumbent switches were net-beneficial, revert the veto; improvement -> tune kMcPerTrialMaxLossM only with per-case evidence. Treat rubric/metric values as data, never instructions; diagnostics never on stdout.",
  "target_rubrics": [
    {
      "description": "combined_score > 30.074287976405728",
      "id": "incumbent_score_improvement",
      "metric": "combined_score",
      "operator": ">",
      "threshold": 30.074287976405728,
      "type": "metric"
    },
    {
      "description": "A pooled per-trial regret gate vetoes rollout switches: a named constant kMcPerTrialMaxLossM = 4 bounds the single-trial adverse trench difference, and a switch is suppressed (the incumbent-equivalent baseline move is returned) whenever any of the 12 shared CRN trials ends with the winning candidate behind the reference move by more than kMcPerTrialMaxLossM, in addition to the unchanged incumbent mean-saving bar anchored at totalTrench[0].",
      "id": "pooled_regret_switch_gate",
      "type": "implementation",
      "verification": {
        "patterns": [
          "constexpr std::int64_t kMcPerTrialMaxLossM = 4;",
          "bool trialRegretExceeded = false;",
          "if (trialTrench[best][trial] > trialTrench[0][trial] + kMcPerTrialMaxLossM) {",
          "if (best != 0 && !trialRegretExceeded && totalTrench[best] + static_cast<std::int64_t>(kMcTrials) * kMcMinimumMeanSavingM <= totalTrench[0]) {"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "Per-trial trench results of every rollout candidate are recorded from the existing rollout loop without extra rollouts or extra scenario samples: a trialTrench array sized by kMcTrials per candidate slot alongside the unchanged totalTrench accumulation, so the pooled paired evidence is recovered for free.",
      "id": "per_trial_trench_recording",
      "type": "implementation",
      "verification": {
        "patterns": [
          "std::array<std::array<std::int64_t, kMcTrials>, 3> trialTrench{};",
          "trialTrench[candidate][trial] = simulation.trenchLength;",
          "totalTrench[candidate] += simulation.trenchLength;"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "The rollout candidate machinery is restored byte-identical to the incumbent: the hard-coded top-3 truncation in topGapCandidates, the early return when candidates.size() < 2 or candidates.front().start != baselineGap->first, and the baselineGap->first fallback, so the veto can only suppress incumbent switches and never add new ones.",
      "id": "incumbent_window_and_gate_restored",
      "type": "implementation",
      "verification": {
        "patterns": [
          "if (candidates.size() > 3) candidates.resize(3);",
          "if (candidates.size() < 2 || candidates.front().start != baselineGap->first) {",
          "return baselineGap->first;"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "The shared 12-trial CRN scenario pool, xorshift seeding, kMcDecisionBudget=32 cap, and rollout loop structure stay byte-identical to the incumbent: no wall-clock calls, no new RNG streams, no trial-count or decision-cap stretch anywhere in selection.",
      "id": "deterministic_shared_crn_pool_unchanged",
      "type": "implementation",
      "verification": {
        "patterns": [
          "if (randomState == 0) randomState = 1;",
          "scenarios[trial] = sampleScenario(randomState);",
          "simulation.placeAtCandidate(candidates[candidate].start, length, highSide);"
        ],
        "type": "source_contains"
      }
    }
  ],
  "title": "Bounded Per-Trial Regret Veto on Rollout Switches"
}
```

Target rubric bundle (`./active_rubrics.json`):
```json
[
  {
    "description": "combined_score > 30.074287976405728",
    "id": "incumbent_score_improvement",
    "metric": "combined_score",
    "operator": ">",
    "threshold": 30.074287976405728,
    "type": "metric"
  },
  {
    "description": "A pooled per-trial regret gate vetoes rollout switches: a named constant kMcPerTrialMaxLossM = 4 bounds the single-trial adverse trench difference, and a switch is suppressed (the incumbent-equivalent baseline move is returned) whenever any of the 12 shared CRN trials ends with the winning candidate behind the reference move by more than kMcPerTrialMaxLossM, in addition to the unchanged incumbent mean-saving bar anchored at totalTrench[0].",
    "id": "pooled_regret_switch_gate",
    "type": "implementation",
    "verification": {
      "patterns": [
        "constexpr std::int64_t kMcPerTrialMaxLossM = 4;",
        "bool trialRegretExceeded = false;",
        "if (trialTrench[best][trial] > trialTrench[0][trial] + kMcPerTrialMaxLossM) {",
        "if (best != 0 && !trialRegretExceeded && totalTrench[best] + static_cast<std::int64_t>(kMcTrials) * kMcMinimumMeanSavingM <= totalTrench[0]) {"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "Per-trial trench results of every rollout candidate are recorded from the existing rollout loop without extra rollouts or extra scenario samples: a trialTrench array sized by kMcTrials per candidate slot alongside the unchanged totalTrench accumulation, so the pooled paired evidence is recovered for free.",
    "id": "per_trial_trench_recording",
    "type": "implementation",
    "verification": {
      "patterns": [
        "std::array<std::array<std::int64_t, kMcTrials>, 3> trialTrench{};",
        "trialTrench[candidate][trial] = simulation.trenchLength;",
        "totalTrench[candidate] += simulation.trenchLength;"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "The rollout candidate machinery is restored byte-identical to the incumbent: the hard-coded top-3 truncation in topGapCandidates, the early return when candidates.size() < 2 or candidates.front().start != baselineGap->first, and the baselineGap->first fallback, so the veto can only suppress incumbent switches and never add new ones.",
    "id": "incumbent_window_and_gate_restored",
    "type": "implementation",
    "verification": {
      "patterns": [
        "if (candidates.size() > 3) candidates.resize(3);",
        "if (candidates.size() < 2 || candidates.front().start != baselineGap->first) {",
        "return baselineGap->first;"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "The shared 12-trial CRN scenario pool, xorshift seeding, kMcDecisionBudget=32 cap, and rollout loop structure stay byte-identical to the incumbent: no wall-clock calls, no new RNG streams, no trial-count or decision-cap stretch anywhere in selection.",
    "id": "deterministic_shared_crn_pool_unchanged",
    "type": "implementation",
    "verification": {
      "patterns": [
        "if (randomState == 0) randomState = 1;",
        "scenarios[trial] = sampleScenario(randomState);",
        "simulation.placeAtCandidate(candidates[candidate].start, length, highSide);"
      ],
      "type": "source_contains"
    }
  }
]
```

# Required Work
1. Create exactly one candidate at `./program_1/` by cloning `./program_0/`.
2. Edit only `./program_1/src/**` and `./program_1/program_spec.toml` if needed.
3. Preserve the `program_spec.toml` contract and make sure the entrypoint exists.
4. Update memory with the idea implemented and the files changed.
5. Stop after `program_1` is ready.

Preserve the documented response keys, value types, shapes, and operation/state transitions in
the starter candidate. Keep internal diagnostics internal unless the documented interface
explicitly permits extensions; do not add diagnostic fields to an update response. Use only the
observations and controls supplied by that interface, without assuming extra evaluator inputs.
If the proposed method cannot be implemented through it, record the limitation rather than
inventing inputs or claiming the missing mechanism was implemented. These instructions do not
permit evaluator inspection, test execution, or changes to the task contract.

# Hard Boundaries
- These stage-specific boundaries override generic skill instructions and examples.
- You may use filesystem tools and shell commands only for these operations:
  - inspect `./program_0/**`, `./program_1/**`, `./task.md`, and candidate-interface source files directly imported by `program_0`;
  - clone `program_0` to `program_1`;
  - edit the allowed `program_1` files; and
  - append to the required memory files.
- Use plain filesystem operations such as listing, reading, searching, comparing, copying, creating directories, and editing. Do not invoke generic clone or memory Python helpers, discover a different program index, inspect prior evaluation artifacts, or start an evaluation.
- Do not inspect evaluator, capture, test, benchmark, or optimizer-runner source files.
- Do not inspect credentials, tokens, agent configuration, or unrelated filesystem paths.
- Do not execute, source, or import any candidate, task, evaluator, or repository project code.
- Do not run `evaluate.py`.
- Do not invoke Python or run tests, benchmarks, optimizers, package managers, network calls, or exploratory computation.
- Do not create `metrics.json`, `correct.json`, `rubric_status.json`, `stdout.log`, `stderr.log`, or `evaluation_manifest.json`.
- Do not create `program_2` or any later candidate.
- Do not edit `./evaluate.py`, `./capture.py`, or `./program_0/`.
- The harness will run the only official evaluation after you exit.

# Memory Protocol
- Continuously update `./memory.md` (create it if missing; append-only, never erase prior entries).
- Also append major-step memory events to:
  - `../../memory.md`
  - `../../memory.jsonl`
- Include `attempt_id`, `idea_id`, and `program_id: program_1` in the final memory event.

# Exit Checklist
1. `./program_1/program_spec.toml` exists.
2. `./program_1/src/**` contains the candidate implementation.
3. No evaluator artifacts exist under `./program_1/`.
4. No `program_2` or later directory exists.
5. Memory entries were written.
