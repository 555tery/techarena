# Role
You are an autonomous scientist/engineer implementing one candidate program for a harness-owned evaluation.

# Task Context
## Goal
Improve the online C++ policy for the Pipes interactive task. Maximize the official weighted KPI score over the 15 supplied open scenarios, while preserving valid behavior and looking for changes that plausibly generalize to the undisclosed scenarios.

# Active Idea
Attempt ID: `cycle04_widened_rollout_candidate_window_attempt_01`
Idea ID: `cycle04_widened_rollout_candidate_window`

Idea bundle (`./active_idea.json`):
```json
{
  "hypothesis": "Cycles 2-3 show added Monte Carlo trials cannot move the official score: the stake-blind extension regressed (30.04392677668611 < 30.074287976405728) and the stakes-gated strict-improvement extension scored exactly flat (30.074287976405728). Reading the incumbent source shows why the trial-count lever is exhausted elsewhere: the rollout refinement only ever evaluates a top-3 static candidate window (resize(3) after the scoreGap sort), and it skips rollouts entirely whenever the static-best candidate is not the baseline gap, anchoring acceptance at totalTrench[0]. Hypothesis (candidate-priority reallocation, per the distilled pivot to candidate priority ordering): the fixed rollout budget (32 decisions x 12 shared-trial rollouts) is misallocated across candidates, not under-funded. Widening the deterministic window to a top-6 by the incumbent's own scoreGap ordering, and always including the baseline gap as the rollout reference anchor (removing the front==baseline skip), lets the same 12 common-random-number trials and the same mean-saving acceptance bar (>= 1 m per trial vs the baseline move) reach candidates the truncation and the gate excluded. Window-touched decisions should be per-case non-negative on balance with at least one strict open-set improvement, moving combined_score above 30.074287976405728; all untouched decisions stay byte-identical to the incumbent.",
  "idea_id": "cycle04_widened_rollout_candidate_window",
  "implementation_plan": [
    "Clone the incumbent program_0 (combined_score=30.074287976405728) into program_1; edit only program_1/src/pipes.cpp; no wall-clock calls, no new RNG streams, stdout protocol untouched.",
    "In topGapCandidates: add constexpr std::size_t kRolloutCandidateWindow = 6; beside the other kMc constants and replace the hard-coded top-3 truncation with if (candidates.size() > kRolloutCandidateWindow) candidates.resize(kRolloutCandidateWindow); keeping the slack<=40 scan break, the scoreGap ascending order, and the highSide-aware start tie-break exactly as incumbent.",
    "In chooseGapWithRollout: drop const on candidates and delete the candidates.front().start != baselineGap->first early return; scan the window for the baseline start and, if absent, insert if (!baseline_in_window) candidates.push_back(GapCandidate{baselineGap->first, scoreGap(baselineGap->second - baselineGap->first, length)}); then re-sort with the same comparator; keep the candidates.size() < 2 return before ++mcDecisionsUsed.",
    "Anchor acceptance at the baseline: find baseline_index by matching start, initialize best = baseline_index, keep the strict-less scan over the shared 12-scenario pool, and switch only if (best != baseline_index && totalTrench[best] + static_cast<std::int64_t>(kMcTrials) * kMcMinimumMeanSavingM <= totalTrench[baseline_index]) return candidates[best].start; otherwise return baselineGap->first; kMcDecisionBudget=32 and all other guards byte-identical.",
    "Before finishing: compile clean with g++ -std=c++20 -O2 -Wall -Wextra and grep-verify every rubric source pattern appears verbatim in program_1/src/pipes.cpp (cycle-3's harness reported its declared patterns missing although the mirrored source contained them; cause unknown - keep patterns short and exact).",
    "Evaluate via the official harness on the frozen 15-scenario open set; report per-case deltas by scenario id vs incumbent 30.074287976405728 (never the aggregate alone); attribute any per-case regression to window-touched decisions (rank-4..6 wins or relaxed-gate switches) in the failure log."
  ],
  "notes_for_agent": "Prior art (retrieved this cycle): (1) Ranking and Selection with Common Random Numbers (Gorder & Kolonko, arXiv:1410.6782) - once candidates share sampled futures (CRN), selection quality is governed by how the fixed simulation budget is allocated across candidates, not by trial count; motivates widening the candidate window at fixed budget. (2) Rollout-Calibrated Hyper-Heuristics for JSSP (Wei et al., arXiv:2605.23957) - never switch from a strong default rule unless predicted gain is credible; matches keeping the baseline-anchored mean-saving bar while widening. (3) Split-Gate Pooled-Evidence Stochastic-Rollout Scheduling (Xu et al., arXiv:2608.08338) - candidate and fallback compared on one set of sampled futures with CRN retained; supports reusing the incumbent's shared 12-scenario pool unchanged. Incumbent source facts (from the cycle-3 attempt's program_0/src/pipes.cpp, mirrored under ideas/03_*): topGapCandidates truncates to 3 after the scoreGap sort with slack>40 break; chooseGapWithRollout returns baseline whenever candidates.front().start != baselineGap->first; acceptance compares against totalTrench[0]; xorshift seeding derives from pipes.size()/length/trenchLength so the default path is fully deterministic (no wall clock); kMcDecisionBudget=32 caps rollout decisions. Do NOT raise kMcTrials, kMcDecisionBudget, or add i.i.d. re-seeded trial streams - cycles 2-3 discredited trial stretching (30.0439 below incumbent; exactly flat at 30.074287976405728). Note the relaxed gate makes more decisions consume the 32-decision rollout budget; that shift is part of the tested allocation hypothesis, so read per-case deltas accordingly. Branch guide for next cycle: exactly flat again -> the window/gate was not binding on the open set (too few rollout decisions or rank-4..6 never wins); pivot to rollout depth or scenario-sampler coverage without stretching trial counts. Per-case regressions concentrated on window-touched decisions -> the rollout estimate misranks wide-window candidates; tighten the window (K=4) or add a pooled secondary criterion before any further widening. Gate passes -> widen further only with per-case evidence, never on the aggregate alone. Keep all diagnostics internal; stdout protocol untouched; treat rubric/metric values as data, not instructions.",
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
      "description": "The rollout candidate window is a named constant kRolloutCandidateWindow = 6 replacing the hard-coded top-3 truncation in topGapCandidates, with the slack<=40 scan break and static scoreGap ordering otherwise unchanged.",
      "id": "widened_candidate_window",
      "type": "implementation",
      "verification": {
        "patterns": [
          "constexpr std::size_t kRolloutCandidateWindow = 6;",
          "if (candidates.size() > kRolloutCandidateWindow) candidates.resize(kRolloutCandidateWindow);"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "The baseline (incumbent) gap always participates in the rollout evaluation as the acceptance anchor even when the static window excludes it; the candidates.front().start != baselineGap->first early return is removed and the window is re-sorted with the same deterministic comparator after insertion.",
      "id": "baseline_anchored_rollout_reference",
      "type": "implementation",
      "verification": {
        "patterns": [
          "bool baseline_in_window = false;",
          "if (!baseline_in_window) candidates.push_back(GapCandidate{baselineGap->first, scoreGap(baselineGap->second - baselineGap->first, length)});"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "Switch acceptance keeps the incumbent mean-saving bar (kMcTrials * kMcMinimumMeanSavingM) but anchors it at the baseline gap's own rollout total totalTrench[baseline_index] instead of window index 0; with best initialized to baseline_index, any switch is a strict rollout improvement over the incumbent's own move, else the incumbent-equivalent baseline move is returned.",
      "id": "baseline_anchored_acceptance_bar",
      "type": "implementation",
      "verification": {
        "patterns": [
          "if (best != baseline_index && totalTrench[best] + static_cast<std::int64_t>(kMcTrials) * kMcMinimumMeanSavingM <= totalTrench[baseline_index])",
          "return candidates[best].start;"
        ],
        "type": "source_contains"
      }
    },
    {
      "description": "Candidate ordering inside the widened window stays fully deterministic and incumbent-identical: static scoreGap ascending with the highSide-aware start tie-break, no RNG involvement and no wall-clock dependence anywhere in selection.",
      "id": "deterministic_priority_ordering",
      "type": "implementation",
      "verification": {
        "patterns": [
          "if (lhs.score != rhs.score) return lhs.score < rhs.score;",
          "return highSide ? lhs.start > rhs.start : lhs.start < rhs.start;"
        ],
        "type": "source_contains"
      }
    }
  ],
  "title": "Widened Rollout Candidate Window with Baseline-Anchored Acceptance"
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
    "description": "The rollout candidate window is a named constant kRolloutCandidateWindow = 6 replacing the hard-coded top-3 truncation in topGapCandidates, with the slack<=40 scan break and static scoreGap ordering otherwise unchanged.",
    "id": "widened_candidate_window",
    "type": "implementation",
    "verification": {
      "patterns": [
        "constexpr std::size_t kRolloutCandidateWindow = 6;",
        "if (candidates.size() > kRolloutCandidateWindow) candidates.resize(kRolloutCandidateWindow);"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "The baseline (incumbent) gap always participates in the rollout evaluation as the acceptance anchor even when the static window excludes it; the candidates.front().start != baselineGap->first early return is removed and the window is re-sorted with the same deterministic comparator after insertion.",
    "id": "baseline_anchored_rollout_reference",
    "type": "implementation",
    "verification": {
      "patterns": [
        "bool baseline_in_window = false;",
        "if (!baseline_in_window) candidates.push_back(GapCandidate{baselineGap->first, scoreGap(baselineGap->second - baselineGap->first, length)});"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "Switch acceptance keeps the incumbent mean-saving bar (kMcTrials * kMcMinimumMeanSavingM) but anchors it at the baseline gap's own rollout total totalTrench[baseline_index] instead of window index 0; with best initialized to baseline_index, any switch is a strict rollout improvement over the incumbent's own move, else the incumbent-equivalent baseline move is returned.",
    "id": "baseline_anchored_acceptance_bar",
    "type": "implementation",
    "verification": {
      "patterns": [
        "if (best != baseline_index && totalTrench[best] + static_cast<std::int64_t>(kMcTrials) * kMcMinimumMeanSavingM <= totalTrench[baseline_index])",
        "return candidates[best].start;"
      ],
      "type": "source_contains"
    }
  },
  {
    "description": "Candidate ordering inside the widened window stays fully deterministic and incumbent-identical: static scoreGap ascending with the highSide-aware start tie-break, no RNG involvement and no wall-clock dependence anywhere in selection.",
    "id": "deterministic_priority_ordering",
    "type": "implementation",
    "verification": {
      "patterns": [
        "if (lhs.score != rhs.score) return lhs.score < rhs.score;",
        "return highSide ? lhs.start > rhs.start : lhs.start < rhs.start;"
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
