# Role
You are an autonomous scientist/engineer implementing one candidate program for a harness-owned evaluation.

# Task Context
## Goal
Improve the online C++ policy for the Pipes interactive task. Maximize the official weighted KPI score over the 15 supplied open scenarios, while preserving valid behavior and looking for changes that plausibly generalize to the undisclosed scenarios.

# Active Idea
Attempt ID: `cycle01_deadline_aware_effort_allocator_attempt_01`
Idea ID: `cycle01_deadline_aware_effort_allocator`

Idea bundle (`./active_idea.json`):
```json
{
  "hypothesis": "Allocator hypothesis: the incumbent online policy spends its per-turn compute budget without regard to the remaining round clock or remaining unresolved work, so easy turns waste wall-clock while hard turns are starved. Replacing fixed-effort turns with a deadline-aware, anytime allocator \u2014 steady_clock-based elapsed tracking, per-turn budget = remaining_ms / max(1, turns_left), an improvement search that can stop at any budget check, and an incumbent-equivalent fallback move \u2014 will convert spare time budget into extra search quality on hard scenarios without changing behavior on easy ones. Expected outcome: combined_score above the incumbent 30.074287976405728 on the same frozen 15 open scenarios with zero validity failures, judged on per-case score deltas rather than the aggregate alone.",
  "idea_id": "cycle01_deadline_aware_effort_allocator",
  "implementation_plan": [
    "Read the incumbent src/pipes.cpp; locate the turn loop, any fixed iteration caps, and existing stdout flush points.",
    "Add a round clock: record round_start with std::chrono::steady_clock at startup and track remaining milliseconds against a safety margin below the documented CPU limit.",
    "Compute turn_budget_ms = remaining_ms / max(1, turns_left) at the start of every turn so effort is allocated proportionally to remaining time and remaining turns.",
    "Make the per-turn improvement search anytime: track the best candidate move continuously and break out of the search loop the moment turn_elapsed_ms reaches turn_budget_ms.",
    "Add the safety fallback: if the budgeted search finds no improving move, emit the incumbent-equivalent fallback move so every response stays valid.",
    "Evaluate on the frozen 15 open scenarios; tabulate per-case score deltas versus the incumbent and accept only if the weighted aggregate improves with no single case regressing."
  ],
  "notes_for_agent": "Use only the documented candidate interface: the interactor protocol on stdin/stdout plus the wall clock via std::chrono. Do not assume extra observations, losses, or labels, and keep internal diagnostics out of solver responses. Preserve validity by construction: the fallback move must equal what the incumbent policy would emit, so no scenario can regress to invalid. Stay inside the documented solver CPU and memory limits; leave a safety margin under the deadline rather than racing it. Judge acceptance on the same frozen 15 open scenarios with per-case score deltas versus the incumbent, not just the weighted aggregate; report any regressing case explicitly. If the incumbent already adapts effort per turn, pivot the same allocation machinery to move/connection ordering (priority allocation over unresolved work) rather than abandoning the deadline infrastructure. The task-level task.md was missing from the results root during idea generation, so scenario specifics are unknown; consult it first when available before tuning scenario-specific behavior.",
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
      "description": "The solver measures round time with std::chrono::steady_clock (round_start captured at startup, round_elapsed_ms derived from it) and, at the start of each turn, derives a per-turn millisecond budget turn_budget_ms as remaining_ms divided by max(1, turns_left), so per-turn effort is allocated proportionally to remaining time and remaining turns.",
      "id": "deadline_aware_turn_budget",
      "type": "implementation",
      "verification": {
        "patterns": [
          "long long round_elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - round_start).count();",
          "turn_budget_ms = remaining_ms / std::max(1, turns_left);"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "The per-turn move search is anytime: it keeps turn_elapsed_ms updated inside the search loop, tracks the best candidate continuously, and breaks out of the search loop as soon as turn_elapsed_ms reaches turn_budget_ms.",
      "id": "anytime_budgeted_search",
      "type": "implementation",
      "verification": {
        "patterns": [
          "if (turn_elapsed_ms >= turn_budget_ms) break;",
          "if (candidate_score > best_score) { best_score = candidate_score; best_move = candidate_move; }"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "When the budgeted search finds no improving move before the turn budget expires, the solver emits the incumbent-equivalent fallback move (fallback_move assigned to best_move when found_improvement is false) so every response stays valid on all scenarios.",
      "id": "incumbent_fallback_move",
      "type": "implementation",
      "verification": {
        "patterns": [
          "bool found_improvement = false;",
          "if (!found_improvement) { best_move = fallback_move; }"
        ],
        "type": "source_contains"
      }
    }
  ],
  "title": "Deadline-Aware Anytime Effort Allocator for the Pipes Online Policy"
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
    "description": "The solver measures round time with std::chrono::steady_clock (round_start captured at startup, round_elapsed_ms derived from it) and, at the start of each turn, derives a per-turn millisecond budget turn_budget_ms as remaining_ms divided by max(1, turns_left), so per-turn effort is allocated proportionally to remaining time and remaining turns.",
    "id": "deadline_aware_turn_budget",
    "type": "implementation",
    "verification": {
      "patterns": [
        "long long round_elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - round_start).count();",
        "turn_budget_ms = remaining_ms / std::max(1, turns_left);"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "The per-turn move search is anytime: it keeps turn_elapsed_ms updated inside the search loop, tracks the best candidate continuously, and breaks out of the search loop as soon as turn_elapsed_ms reaches turn_budget_ms.",
    "id": "anytime_budgeted_search",
    "type": "implementation",
    "verification": {
      "patterns": [
        "if (turn_elapsed_ms >= turn_budget_ms) break;",
        "if (candidate_score > best_score) { best_score = candidate_score; best_move = candidate_move; }"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "When the budgeted search finds no improving move before the turn budget expires, the solver emits the incumbent-equivalent fallback move (fallback_move assigned to best_move when found_improvement is false) so every response stays valid on all scenarios.",
    "id": "incumbent_fallback_move",
    "type": "implementation",
    "verification": {
      "patterns": [
        "bool found_improvement = false;",
        "if (!found_improvement) { best_move = fallback_move; }"
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
