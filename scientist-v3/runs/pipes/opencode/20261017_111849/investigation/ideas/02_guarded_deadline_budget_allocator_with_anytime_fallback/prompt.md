# Role
You are an autonomous scientist/engineer implementing one candidate program for a harness-owned evaluation.

# Task Context
## Goal
Improve the online C++ policy for the Pipes interactive task. Maximize the official weighted KPI score over the 15 supplied open scenarios, while preserving valid behavior and looking for changes that plausibly generalize to the undisclosed scenarios.

# Active Idea
Attempt ID: `cycle02_guarded_deadline_budget_allocator_attempt_01`
Idea ID: `cycle02_guarded_deadline_budget_allocator`

Idea bundle (`./active_idea.json`):
```json
{
  "hypothesis": "The incumbent online Pipes policy expends per-turn search effort without regard to the global wall-clock deadline, so time-rich scenarios waste deadline headroom while deadline-pressed ones face abrupt truncation, and unmanaged effort is exactly where the ~2.03 weighted points of headroom hide. Allocating each turn a search budget proportional to the remaining time divided by the remaining turns (turn_deadline = now + remaining_ms / max(1, turns_left)), running the per-turn search as an anytime loop that breaks at the deadline or on exhaustive completion, and emitting an incumbent-equivalent fallback move whenever the budgeted search yields no improvement will raise the weighted combined_score above the 30.074287976405728 incumbent on the same frozen 15-scenario open set, with every case remaining valid and no case regressing. Because cycle 1's attempt failed before producing any score evidence (cause unknown), this cycle adds a guarded-integration requirement: the default code path must stay byte-compatible with the incumbent, and the allocator activates only after time bookkeeping is verified, isolating execution failure from scientific failure.",
  "idea_id": "cycle02_guarded_deadline_budget_allocator",
  "implementation_plan": [
    "Start from the incumbent src/pipes.cpp; keep its default move-selection path byte-identical so scenario validity cannot regress by construction.",
    "Add turn bookkeeping once per turn: elapsed_ms, remaining_ms (total_time_limit_ms - elapsed_ms), and turns_left; compute turn_budget_ms = max(1, remaining_ms / max(1, turns_left)) with a safety margin kept under the solver CPU limit.",
    "Convert the inner search into an anytime loop with explicit deadline checks that break at turn_deadline or on exhaustive completion, preserving the incumbent ordering of candidate moves.",
    "Emit the incumbent-equivalent fallback move whenever the budgeted search finishes without a better move, so every turn still produces a valid response within the official protocol.",
    "Place internal state only in solver-local variables; emit nothing beyond the documented stdin/stdout protocol."
  ],
  "notes_for_agent": "Cycle 1's attempt died before evaluation (run_exit_code=1, cause unknown), so allocate most of this attempt's risk to keeping the build and protocol small: integrate behind the guarded default path and get program_1 running before deep-tuning budgets. Report per-case deltas against the program_0 incumbent on the identical frozen open set \u2014 never the aggregate alone; a single-case regression must be called out by scenario id. If evidence shows the incumbent already adapts effort per turn, pivot the same deadline machinery to connection/move priority ordering instead of time budgeting. Assume only the documented stdin/stdout interactor protocol plus wall clock; do not inspect evaluator internals and keep diagnostics out of solver responses. CPU/memory: keep an explicit margin under the limits; if budget arithmetic risks overshoot on low-time scenarios, clamp to remaining milliseconds minus the margin.",
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
      "description": "src/pipes.cpp computes a per-turn budget from remaining wall-clock time and remaining turns, keeping a safety margin below the solver CPU limit instead of racing the deadline.",
      "id": "deadline_aware_turn_budget",
      "type": "implementation",
      "verification": {
        "patterns": [
          "turn_budget_ms = std::max(1LL, remaining_ms / std::max(1LL, turns_left))",
          "remaining_ms = total_time_limit_ms - elapsed_ms"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "The per-turn search is an anytime loop with explicit deadline checks that terminates at the turn deadline or on exhaustive completion.",
      "id": "anytime_budgeted_search",
      "type": "implementation",
      "verification": {
        "patterns": [
          "if (std::chrono::steady_clock::now() >= turn_deadline) break",
          "turn_deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(turn_budget_ms)"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "The guarded default path emits the incumbent-equivalent fallback move whenever the budgeted search yields no improvement, so default behavior stays byte-compatible with the incumbent program.",
      "id": "incumbent_fallback_move",
      "type": "implementation",
      "verification": {
        "patterns": [
          "if (!found_move) move = fallback_move"
        ],
        "type": "source_contains"
      }
    }
  ],
  "title": "Guarded Deadline-Budget Allocator with Anytime Fallback"
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
    "description": "src/pipes.cpp computes a per-turn budget from remaining wall-clock time and remaining turns, keeping a safety margin below the solver CPU limit instead of racing the deadline.",
    "id": "deadline_aware_turn_budget",
    "type": "implementation",
    "verification": {
      "patterns": [
        "turn_budget_ms = std::max(1LL, remaining_ms / std::max(1LL, turns_left))",
        "remaining_ms = total_time_limit_ms - elapsed_ms"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "The per-turn search is an anytime loop with explicit deadline checks that terminates at the turn deadline or on exhaustive completion.",
    "id": "anytime_budgeted_search",
    "type": "implementation",
    "verification": {
      "patterns": [
        "if (std::chrono::steady_clock::now() >= turn_deadline) break",
        "turn_deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(turn_budget_ms)"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "The guarded default path emits the incumbent-equivalent fallback move whenever the budgeted search yields no improvement, so default behavior stays byte-compatible with the incumbent program.",
    "id": "incumbent_fallback_move",
    "type": "implementation",
    "verification": {
      "patterns": [
        "if (!found_move) move = fallback_move"
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
