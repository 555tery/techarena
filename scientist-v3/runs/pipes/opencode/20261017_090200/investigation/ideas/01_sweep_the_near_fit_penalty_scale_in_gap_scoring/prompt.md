# Role
You are an autonomous scientist/engineer implementing one candidate program for a harness-owned evaluation.

# Task Context
## Goal
Improve the online C++ policy for the Pipes interactive task. Maximize the official weighted KPI score over the 15 supplied open scenarios, while preserving valid behavior and looking for changes that plausibly generalize to the undisclosed scenarios.

# Active Idea
Attempt ID: `idea_pipes_unfit_penalty_scale_001_attempt_01`
Idea ID: `idea_pipes_unfit_penalty_scale_001`

Idea bundle (`./active_idea.json`):
```json
{
  "hypothesis": "The incumbent fit score weighs a gap's slack against the recent-window length and adds a flat un-fit penalty (kUnfitPenaltyScale = 60) for every window request larger than the slack. The relative weight of that penalty is mis-tuned: too small a value wastes near-fit gaps on sizes that rarely arrive, while too large a value pushes placements off small gaps into far slack or fresh digs, inflating trench growth. Sweeping the scale over {0, 30, 60, 120} on the frozen 15-case open set will expose a better operating point; the aggregate effect should be visible as per-case KPI deltas, with no case regressing beyond the incumbent, while allocator mechanics, protocol behavior, and resource use stay unchanged.",
  "idea_id": "idea_pipes_unfit_penalty_scale_001",
  "implementation_plan": [
    "Read the incumbent fit-score path in program_0/src/pipes.cpp: kUnfitPenaltyScale, scoreGap, bestFittingGapFromSet, and the RolloutState fitScore clone.",
    "Declare constexpr std::array<std::int64_t, 4> kUnfitPenaltyVariants{0, 30, 60, 120} and a constexpr std::size_t kSelectedUnfitPenaltyVariant index; make scoreGap and bestFittingGapFromSet read the selected scale as a local unfitPenaltyScale instead of the hard-coded constant.",
    "Evaluate each variant one at a time on the frozen 15 official open cases with the official harness; record combined_score, per-case KPI deltas vs the incumbent manifest, solver CPU, and peak RSS.",
    "Keep the variant with the highest combined_score; if no variant beats the incumbent, retain scale 60 and report the per-case deltas that justify rejection.",
    "Leave the final candidate source with the sweep table and selected index in place, edits confined to src/pipes.cpp, and confirm every case stays under 5 s CPU and 256 MiB RSS."
  ],
  "notes_for_agent": "The scoring sweep is the only sanctioned change this cycle; do not touch cohort slabs, geometric lanes, the Monte Carlo rollout, dig accounting, or any evaluator, test, or harness file. Keep the sweep table and selected index in the final source exactly as specified so the verification patterns match. Report results per case: a variant that wins in aggregate but regresses any single case relative to the incumbent must be described with those case-level regressions, not hidden in the aggregate. The frozen open set can overfit: an open-set gain is a signal about the penalty weight, not proof of closed-set performance, and the incumbent scale 60 must be restored if no variant wins. Determinism must be preserved: the sweep must not introduce randomness or timing-dependent behavior. Resource limits are hard; the sweep adds no per-placement work beyond reading one constant.",
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
      "description": "The candidate source implements the stated allocator hypothesis as a swept un-fit penalty scale: a variant table {0, 30, 60, 120}, a selected-variant index, and gap scoring that reads the selected scale, with no other behavioral change to placement, removal, or expansion logic.",
      "id": "unfit_penalty_scale_variant_table_implemented",
      "type": "implementation",
      "verification": {
        "patterns": [
          "kUnfitPenaltyVariants{0, 30, 60, 120}",
          "kSelectedUnfitPenaltyVariant",
          "kUnfitPenaltyVariants[kSelectedUnfitPenaltyVariant]"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "The change keeps the online protocol and the scoring loop intact: per-response flush of the N D placement line, the coordinate response for negative PID commands, immediate silent exit on command 0, and the window-based miss counting inside the fit score must all remain present in src/pipes.cpp.",
      "id": "fit_score_and_protocol_invariants_preserved",
      "type": "implementation",
      "verification": {
        "patterns": [
          "std::cout << digs << ' ' << start << '\\n' << std::flush",
          "while (std::cin >> command)",
          "for (int request = static_cast<int>(slack) + 1; request <= 40; ++request)"
        ],
        "type": "source_contains"
      }
    }
  ],
  "title": "Sweep the near-fit penalty scale in gap scoring"
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
    "description": "The candidate source implements the stated allocator hypothesis as a swept un-fit penalty scale: a variant table {0, 30, 60, 120}, a selected-variant index, and gap scoring that reads the selected scale, with no other behavioral change to placement, removal, or expansion logic.",
    "id": "unfit_penalty_scale_variant_table_implemented",
    "type": "implementation",
    "verification": {
      "patterns": [
        "kUnfitPenaltyVariants{0, 30, 60, 120}",
        "kSelectedUnfitPenaltyVariant",
        "kUnfitPenaltyVariants[kSelectedUnfitPenaltyVariant]"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "The change keeps the online protocol and the scoring loop intact: per-response flush of the N D placement line, the coordinate response for negative PID commands, immediate silent exit on command 0, and the window-based miss counting inside the fit score must all remain present in src/pipes.cpp.",
    "id": "fit_score_and_protocol_invariants_preserved",
    "type": "implementation",
    "verification": {
      "patterns": [
        "std::cout << digs << ' ' << start << '\\n' << std::flush",
        "while (std::cin >> command)",
        "for (int request = static_cast<int>(slack) + 1; request <= 40; ++request)"
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
