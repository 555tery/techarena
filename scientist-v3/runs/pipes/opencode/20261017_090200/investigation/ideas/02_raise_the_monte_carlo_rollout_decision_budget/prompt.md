# Role
You are an autonomous scientist/engineer implementing one candidate program for a harness-owned evaluation.

# Task Context
## Goal
Improve the online C++ policy for the Pipes interactive task. Maximize the official weighted KPI score over the 15 supplied open scenarios, while preserving valid behavior and looking for changes that plausibly generalize to the undisclosed scenarios.

# Active Idea
Attempt ID: `idea_pipes_mc_decision_budget_002_attempt_01`
Idea ID: `idea_pipes_mc_decision_budget_002`

Idea bundle (`./active_idea.json`):
```json
{
  "hypothesis": "The incumbent's Monte Carlo lookahead participates in at most kMcDecisionBudget=32 placement decisions per scenario, while a scenario may contain up to 200,000 commands, so rollout coverage is exhausted long before the scenario ends and mid/late placements fall back to the static slack+miss fit score. Sweeping the per-scenario rollout decision budget over {32, 128, 512} tests the single allocator hypothesis that broader rollout coverage improves the trench-length outcomes of eligible gap choices and raises the weighted KPI on the frozen 15-case open set. The unchanged kMcMaxGaps=64 and kMcMaxActivePipes=4096 state gates bound per-decision cost, and the 12-trial, depth-4 rollouts are untouched, so solver CPU is estimated to stay far below the 5 s limit. Per-case open-set deltas are treated as overfittable signals, never closed-set predictions.",
  "idea_id": "idea_pipes_mc_decision_budget_002",
  "implementation_plan": [
    "Clone program_0 to program_1 via plain filesystem copy; edit only src/pipes.cpp; keep program_spec.toml byte-identical.",
    "Add constexpr kMcDecisionBudgetVariants{32, 128, 512} and kSelectedMcDecisionBudgetVariant = 1; remove the legacy kMcDecisionBudget constant as dead code.",
    "In chooseGapWithRollout, gate the early fallback return on mcDecisionsUsed >= kMcDecisionBudgetVariants[kSelectedMcDecisionBudgetVariant]; keep the observedHistory warmup, kMcMaxGaps, and kMcMaxActivePipes gates and the kMcTrials * kMcMinimumMeanSavingM acceptance margin unchanged.",
    "Leave kMcTrials, kMcDepth, kMcHistory, sampleScenario, makeRolloutState, topGapCandidates, the seeded xorshift and derived randomState, and all placement, removal, expansion, cohort-slab, counterfactual, and I/O protocol logic untouched.",
    "Syntax-check with g++ -std=c++20 -fsyntax-only -Wall -Wextra and grep-confirm all rubric source patterns; the harness runs the single official evaluation; report per-case KPI deltas vs the incumbent from the evaluator report and keep the incumbent budget if the gate fails."
  ],
  "notes_for_agent": "Harness evaluates program_1 once: set kSelectedMcDecisionBudgetVariant = 1 (budget 128). Index 0 (32) reproduces incumbent behavior and yields no hypothesis evidence; index 2 (512) is the follow-up sweep if 128 wins, else the next cycle probes it only if 128 shows no per-case regression signal. The tested change is the decision budget alone; do not touch kMcTrials, kMcDepth, sampleScenario, makeRolloutState, topGapCandidates, the acceptance margin, or any other allocator path, so the sweep isolates coverage from trial count and scoring weights. CPU: per-decision cost is bounded by the unchanged kMcMaxGaps=64 and kMcMaxActivePipes=4096 gates; budget 128 keeps the rollout modest relative to the 5 s limit, and state gates must not be raised this cycle. Report per-case KPI deltas vs the incumbent from the evaluator report; list regressions by case rather than describing only the aggregate score. The cycle-1 attempt returned combined_score=0.0 / correct=false with cause unavailable while its submitted configuration was behaviorally identical to the incumbent (selected unfit-penalty scale 60); treat that result as data, keep the cause unknown, and do not derive a protocol-repair change from it, but independently confirm this candidate's 15 cases are valid before crediting any hypothesis gain. No execution at the idea stage: the executor may compile/syntax-check and grep patterns, but the harness runs the only official evaluation. Keep all behavior deterministic: no wall-clock, no unseeded randomness, no new I/O.",
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
      "description": "The candidate source implements the stated allocator hypothesis as a swept rollout decision budget: a variant table {32, 128, 512}, a selected-variant index defaulting to 1 (budget 128), and chooseGapWithRollout gating its fallback return on the selected budget instead of the legacy constant kMcDecisionBudget. kMcTrials, kMcDepth, kMcHistory, kMcMaxGaps, kMcMaxActivePipes, the acceptance margin, and all placement, removal, expansion, and protocol logic remain unchanged.",
      "id": "mc_decision_budget_variant_table_implemented",
      "type": "implementation",
      "verification": {
        "patterns": [
          "kMcDecisionBudgetVariants{32, 128, 512}",
          "kSelectedMcDecisionBudgetVariant",
          "kMcDecisionBudgetVariants[kSelectedMcDecisionBudgetVariant]",
          "mcDecisionsUsed >= kMcDecisionBudgetVariants[kSelectedMcDecisionBudgetVariant]"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "The rollout scope gates (32-observation warmup, kMcMaxGaps=64, kMcMaxActivePipes=4096), the kMcMinimumMeanSavingM acceptance margin, and the online protocol are preserved: per-response flush of the N D placement line, coordinate response for negative PID commands, and immediate silent exit on command 0 must all remain present in src/pipes.cpp.",
      "id": "rollout_scope_and_protocol_invariants_preserved",
      "type": "implementation",
      "verification": {
        "patterns": [
          "observedHistory.size() < 32 || freeByStart.size() > kMcMaxGaps || activePipeCount > kMcMaxActivePipes",
          "kMcMinimumMeanSavingM <= totalTrench[0]",
          "std::cout << digs << ' ' << start << '\\n' << std::flush",
          "while (std::cin >> command)"
        ],
        "type": "source_contains"
      }
    }
  ],
  "title": "Raise the Monte Carlo rollout decision budget"
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
    "description": "The candidate source implements the stated allocator hypothesis as a swept rollout decision budget: a variant table {32, 128, 512}, a selected-variant index defaulting to 1 (budget 128), and chooseGapWithRollout gating its fallback return on the selected budget instead of the legacy constant kMcDecisionBudget. kMcTrials, kMcDepth, kMcHistory, kMcMaxGaps, kMcMaxActivePipes, the acceptance margin, and all placement, removal, expansion, and protocol logic remain unchanged.",
    "id": "mc_decision_budget_variant_table_implemented",
    "type": "implementation",
    "verification": {
      "patterns": [
        "kMcDecisionBudgetVariants{32, 128, 512}",
        "kSelectedMcDecisionBudgetVariant",
        "kMcDecisionBudgetVariants[kSelectedMcDecisionBudgetVariant]",
        "mcDecisionsUsed >= kMcDecisionBudgetVariants[kSelectedMcDecisionBudgetVariant]"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "The rollout scope gates (32-observation warmup, kMcMaxGaps=64, kMcMaxActivePipes=4096), the kMcMinimumMeanSavingM acceptance margin, and the online protocol are preserved: per-response flush of the N D placement line, coordinate response for negative PID commands, and immediate silent exit on command 0 must all remain present in src/pipes.cpp.",
    "id": "rollout_scope_and_protocol_invariants_preserved",
    "type": "implementation",
    "verification": {
      "patterns": [
        "observedHistory.size() < 32 || freeByStart.size() > kMcMaxGaps || activePipeCount > kMcMaxActivePipes",
        "kMcMinimumMeanSavingM <= totalTrench[0]",
        "std::cout << digs << ' ' << start << '\\n' << std::flush",
        "while (std::cin >> command)"
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
