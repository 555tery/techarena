# Role
You are an autonomous scientist/engineer implementing one candidate program for a harness-owned evaluation.

# Task Context
## Goal
Improve the online C++ policy for the Pipes interactive task. Maximize the official weighted KPI score over the 15 supplied open scenarios, while preserving valid behavior and looking for changes that plausibly generalize to the undisclosed scenarios.

# Active Idea
Attempt ID: `cycle03_stakes_gated_trial_reallocation_attempt_01`
Idea ID: `cycle03_stakes_gated_trial_reallocation`

Idea bundle (`./active_idea.json`):
```json
{
  "hypothesis": "Cycle 2's guarded deadline-budget allocator scored slightly below the byte-compatible incumbent (30.04392677668611 vs 30.074287976405728) even though its default path was byte-compatible, so the stake-blind anytime extension of shared-scenario trials changed at least one decision for the worse. Hypothesis: converting the extension from stake-blind to stakes-gated removes that regression and turns it into a net gain. Specifically, extra simulation trials above the incumbent's fixed effort are spent only on high-stakes decisions (the longest remaining pipe lengths, where one placement consumes the most trench), and every other decision keeps exact incumbent behavior; extended trials are unbiased i.i.d. re-simulations of the single current decision with a fresh, deterministically reseeded RNG stream (no shared-scenario state), bounded by the verified wall-clock bookkeeping and a safety margin under the 5 s solver CPU limit. With an incumbent-equivalent floor and strict-improvement-only acceptance, the allocator can only deviate from incumbent behavior where added unbiased trials find a strictly better move, so the expected open-set delta should be non-negative and the 30.074287976405728 gate should be passed.",
  "idea_id": "cycle03_stakes_gated_trial_reallocation",
  "implementation_plan": [
    "Start from the incumbent program_0/src/pipes.cpp; keep the default 12-trial MC core, RNG, candidate ordering, tie-break, and fallback move byte-identical so non-extended decisions behave exactly as the incumbent.",
    "Add steady-clock round bookkeeping with per-turn time sanity verification; the allocator activates only when bookkeeping is verified, keeping a safety margin under the 5 s solver CPU limit.",
    "Classify each decision as high-stakes iff the current pipe length meets a declared kStakesLengthThreshold (e.g. derived from the longest remaining lengths); all other decisions keep incumbent trials and incumbent-equivalent selection plus the incumbent-equivalent fallback move.",
    "For high-stakes decisions only, run unbiased i.i.d. re-simulation trials of the single current decision with a fresh RNG stream reseeded from base_seed plus the decision index (no shared-scenario state), capped by kExtendedTrialsCap and by the per-turn deadline from remaining wall-clock headroom divided over remaining decision slots.",
    "Accept an extended-search move only if it strictly beats the incumbent-equivalent best candidate under identical tie-breaks; otherwise emit the incumbent-equivalent fallback move, and never extend the trench beyond 100,000,000 m.",
    "Place the result in program_1/src/pipes.cpp, verify it compiles with g++ -std=c++20, stays within CPU and 256 MiB RSS limits, and report any per-case score deltas by scenario id against the incumbent rather than only the aggregate."
  ],
  "notes_for_agent": "Edit only program_1/src/pipes.cpp; keep all incumbent default-path behavior identical (same trials, RNG, candidate ordering, tie-break, fallback). The allocator must stay off unless wall-clock bookkeeping is verified, and must never touch non-high-stakes decisions. Never print diagnostics on stdout: the official interactor reads the pipe protocol from stdout only, so any diagnostic must live in in-memory state or source comments. Evaluate on the same frozen open-test set as before and report per-case deltas by scenario id vs the incumbent 30.074287976405728, not just the aggregate; regressions must be reported per case. Interpretation guide for the next cycle: if extended searches rarely fire, widen kStakesLengthThreshold coverage or raise kExtendedTrialsCap within deadline headroom; if losses concentrate in long-pipe scenarios, the added unbiased trials are overfit noise in the MC estimate, and the pivot is movement-candidate priority ordering rather than more trials; if the gate still fails while all per-case deltas are non-negative, the incumbent score itself is run-dependent (timing-sensitive) and the safest next experiment is to make tie-breaks deterministic rather than effort-based.",
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
      "description": "Extra simulation trials above incumbent effort are granted only to high-stakes decisions (current pipe length meets declared kStakesLengthThreshold); every other decision keeps the incumbent trials and incumbent-equivalent move selection.",
      "id": "stakes_gated_trial_allocation",
      "type": "implementation",
      "verification": {
        "patterns": [
          "bool high_stakes = pipe_length >= kStakesLengthThreshold;",
          "int trials = high_stakes ? kExtendedTrialsCap : kIncumbentTrialsPerDecision;"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "Extended trials are unbiased i.i.d. re-simulations of the single current decision with a fresh deterministically reseeded RNG stream per decision, reusing no shared-scenario evaluation state from other decisions.",
      "id": "unbiased_reseeded_trial_stream",
      "type": "implementation",
      "verification": {
        "patterns": [
          "rng.seed(base_seed + static_cast<std::uint64_t>(decision_index));",
          "for (int trial = 0; trial < trials; ++trial)"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "The allocator is active only after verified wall-clock bookkeeping; extended trials are bounded by a per-turn deadline carrying a safety margin under the 5 s solver CPU limit, and extended search stops immediately at that deadline.",
      "id": "deadline_bounded_extension",
      "type": "implementation",
      "verification": {
        "patterns": [
          "remaining_ms = total_time_limit_ms - elapsed_ms;",
          "turn_deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(turn_budget_ms);",
          "if (std::chrono::steady_clock::now() >= turn_deadline) break;"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "When extended search yields no strict improvement under identical tie-breaks, the solver emits the incumbent-equivalent fallback move, keeping every response valid on all scenarios and default behavior byte-compatible with the incumbent.",
      "id": "incumbent_equivalent_fallback",
      "type": "implementation",
      "verification": {
        "patterns": [
          "bool found_improvement = false;",
          "if (!found_improvement) best_move = fallback_move;"
        ],
        "type": "source_contains"
      }
    }
  ],
  "title": "Stakes-Gated Trial Reallocation with Incumbent-Equivalent Floor"
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
    "description": "Extra simulation trials above incumbent effort are granted only to high-stakes decisions (current pipe length meets declared kStakesLengthThreshold); every other decision keeps the incumbent trials and incumbent-equivalent move selection.",
    "id": "stakes_gated_trial_allocation",
    "type": "implementation",
    "verification": {
      "patterns": [
        "bool high_stakes = pipe_length >= kStakesLengthThreshold;",
        "int trials = high_stakes ? kExtendedTrialsCap : kIncumbentTrialsPerDecision;"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "Extended trials are unbiased i.i.d. re-simulations of the single current decision with a fresh deterministically reseeded RNG stream per decision, reusing no shared-scenario evaluation state from other decisions.",
    "id": "unbiased_reseeded_trial_stream",
    "type": "implementation",
    "verification": {
      "patterns": [
        "rng.seed(base_seed + static_cast<std::uint64_t>(decision_index));",
        "for (int trial = 0; trial < trials; ++trial)"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "The allocator is active only after verified wall-clock bookkeeping; extended trials are bounded by a per-turn deadline carrying a safety margin under the 5 s solver CPU limit, and extended search stops immediately at that deadline.",
    "id": "deadline_bounded_extension",
    "type": "implementation",
    "verification": {
      "patterns": [
        "remaining_ms = total_time_limit_ms - elapsed_ms;",
        "turn_deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(turn_budget_ms);",
        "if (std::chrono::steady_clock::now() >= turn_deadline) break;"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "When extended search yields no strict improvement under identical tie-breaks, the solver emits the incumbent-equivalent fallback move, keeping every response valid on all scenarios and default behavior byte-compatible with the incumbent.",
    "id": "incumbent_equivalent_fallback",
    "type": "implementation",
    "verification": {
      "patterns": [
        "bool found_improvement = false;",
        "if (!found_improvement) best_move = fallback_move;"
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
