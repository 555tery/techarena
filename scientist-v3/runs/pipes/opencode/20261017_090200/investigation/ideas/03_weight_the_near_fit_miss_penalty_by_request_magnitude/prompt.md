# Role
You are an autonomous scientist/engineer implementing one candidate program for a harness-owned evaluation.

# Task Context
## Goal
Improve the online C++ policy for the Pipes interactive task. Maximize the official weighted KPI score over the 15 supplied open scenarios, while preserving valid behavior and looking for changes that plausibly generalize to the undisclosed scenarios.

# Active Idea
Attempt ID: `idea_pipes_miss_penalty_magnitude_003_attempt_01`
Idea ID: `idea_pipes_miss_penalty_magnitude_003`

Idea bundle (`./active_idea.json`):
```json
{
  "hypothesis": "The incumbent gap-fit score charges a flat penalty (scale 60) for every request length in the post-placement miss window (slack, 40], so a placement that destroys capacity for large future pipes costs only the same flat term per missed length regardless of how large the missed request is. Weighting each miss by its request magnitude (per-miss term = unfitPenaltyScale multiplied by request raised to a small exponent) should make the allocator systematically prefer placements that preserve large-gap capacity on scenarios with wide request-length spread, while leaving behavior on uniform scenarios nearly unchanged. The variant table {0, 1, 2} (exponent 0 reproduces the legacy flat scoring exactly, 1 is linear magnitude weighting, 2 is quadratic) is swept with the selected default index 1 (linear); the change is confined to the three miss-accumulation sites (Allocator::scoreGap, Allocator::bestFittingGapFromSet, RolloutState::fitScore) with the miss-window loop, placement, removal, expansion, rollout configuration, and protocol untouched. Acceptance requires combined_score above the incumbent manifest value on the same frozen 15-case open set with per-case KPI deltas reported; open-set wins are treated as overfittable signals, never closed-set predictions.",
  "idea_id": "idea_pipes_miss_penalty_magnitude_003",
  "implementation_plan": [
    "Clone program_0 to program_1 by plain filesystem copy per the stage hard boundaries; restrict all edits to program_1/src/pipes.cpp.",
    "Declare constexpr std::array<int, 3> kMissWeightExponentVariants{0, 1, 2} and constexpr int kSelectedMissWeightExponentVariant = 1 alongside the other allocator constants.",
    "In Allocator::scoreGap, Allocator::bestFittingGapFromSet, and RolloutState::fitScore, replace the flat per-miss term with a weight loop that exponentiates the missed request length up to kMissWeightExponentVariants[kSelectedMissWeightExponentVariant]; keep the miss-window loop from slack+1 through 40 unchanged; accumulate in a 64-bit type (request is bounded by 40, so the largest term stays near 60 * 1600).",
    "Touch nothing else: placement, removal, expansion, parity cohort slabs, LIFO lane, the kMc* rollout constants and gates, the counterfactual comparison, protocol responses, per-response flushes, and immediate silent exit on command 0; keep the build self-contained C++20 and deterministic.",
    "Leave evaluation to the harness's single official run on the frozen 15-case open set; report per-case KPI deltas vs the incumbent manifest and name regressed cases individually; if the gate fails, nominate exponent 0 (flat, incumbent-equivalent) as the retained configuration and record the rejection as case-level evidence."
  ],
  "notes_for_agent": "One allocator hypothesis per cycle, tested against the same frozen 15-case open set. The selected variant is exponent 1 (linear magnitude weighting); index 0 is the flat legacy fallback and index 2 the quadratic probe for later re-selection. Overflow safety: request is bounded by 40, so the maximum weighted term is 60 * 1600 and a 64-bit accumulator is ample; keep the accumulation integral so scoring stays deterministic. Do not run evaluate.py, tests, or benchmarks during execution - the harness owns the single official evaluation; keep internal diagnostics out of stdout because the interactor protocol is authoritative for acceptance. Note the recurring data point: cycles 1 and 2 recorded correct=false at combined_score 0.0 for near-incumbent configurations with the cause unavailable per task guidance - if that recurs, do not attribute failure to this allocator change without per-case evidence, keep the flat configuration (index 0) re-selectable, and treat acceptance as unestablished rather than as a scoring defect. Report regressions case by case with KPI deltas; per-case open-set signals are overfittable and are not closed-set predictions.",
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
      "description": "The candidate source implements the stated allocator hypothesis as a magnitude-weighted miss penalty: a variant table {0, 1, 2} of exponents applied to the missed request length, a selected-variant index defaulting to 1 (linear magnitude weighting), and the three miss-accumulation sites (Allocator::scoreGap, Allocator::bestFittingGapFromSet, RolloutState::fitScore) computing the per-miss weight by exponentiating the request length up to the selected exponent (exponent 0 reproduces the legacy flat penalty), with no other behavioral change to placement, removal, expansion, or rollout configuration.",
      "id": "magnitude_weighted_miss_penalty_variants_implemented",
      "type": "implementation",
      "verification": {
        "patterns": [
          "kMissWeightExponentVariants{0, 1, 2}",
          "kSelectedMissWeightExponentVariant = 1",
          "for (int exponent = 0; exponent < kMissWeightExponentVariants[kSelectedMissWeightExponentVariant]; ++exponent) weight *= request"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "The near-fit miss window, rollout configuration, and online protocol are preserved: the miss scan from slack+1 through 40, the kMc* rollout constants and gates, per-response flush of the N D placement line, the coordinate response for negative PID commands, and immediate silent exit on command 0 must all remain present in src/pipes.cpp.",
      "id": "miss_window_rollout_and_protocol_invariants_preserved",
      "type": "implementation",
      "verification": {
        "patterns": [
          "for (int request = static_cast<int>(slack) + 1; request <= 40; ++request)",
          "std::cout << digs << ' ' << start << '\\n' << std::flush",
          "while (std::cin >> command)"
        ],
        "type": "source_contains"
      }
    }
  ],
  "title": "Weight the near-fit miss penalty by request magnitude"
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
    "description": "The candidate source implements the stated allocator hypothesis as a magnitude-weighted miss penalty: a variant table {0, 1, 2} of exponents applied to the missed request length, a selected-variant index defaulting to 1 (linear magnitude weighting), and the three miss-accumulation sites (Allocator::scoreGap, Allocator::bestFittingGapFromSet, RolloutState::fitScore) computing the per-miss weight by exponentiating the request length up to the selected exponent (exponent 0 reproduces the legacy flat penalty), with no other behavioral change to placement, removal, expansion, or rollout configuration.",
    "id": "magnitude_weighted_miss_penalty_variants_implemented",
    "type": "implementation",
    "verification": {
      "patterns": [
        "kMissWeightExponentVariants{0, 1, 2}",
        "kSelectedMissWeightExponentVariant = 1",
        "for (int exponent = 0; exponent < kMissWeightExponentVariants[kSelectedMissWeightExponentVariant]; ++exponent) weight *= request"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "The near-fit miss window, rollout configuration, and online protocol are preserved: the miss scan from slack+1 through 40, the kMc* rollout constants and gates, per-response flush of the N D placement line, the coordinate response for negative PID commands, and immediate silent exit on command 0 must all remain present in src/pipes.cpp.",
    "id": "miss_window_rollout_and_protocol_invariants_preserved",
    "type": "implementation",
    "verification": {
      "patterns": [
        "for (int request = static_cast<int>(slack) + 1; request <= 40; ++request)",
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
