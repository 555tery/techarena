# Memory Log

## Context
- idea_id: cycle05_bounded_regret_switch_veto
- title: Bounded Per-Trial Regret Veto on Rollout Switches
- attempt: cycle_0005_attempt_01_1792250102621270000 (idea stage)
- incumbent: program_0 (bootstrap), combined_score=30.074287976405728, correct=true
- scientific acceptance: official harness evaluation on the frozen 15-scenario open set; report per-case deltas by scenario id vs incumbent 30.074287976405728, never the aggregate alone

## Idea Discoveries
### 2026-10-17T16:50:00+00:00 | step=idea
- summary: Authored idea `cycle05_bounded_regret_switch_veto` ("Bounded Per-Trial Regret Veto on Rollout Switches"). Cycle-4 (top-6 window + relaxed entry gate + baseline-anchored acceptance) regressed to 30.05161049161871 vs incumbent 30.074287976405728; its source RETAINED the slack<=40 scan break, so the regression is attributable to window widening + gate relaxation. Hypothesis: the mean-only switch bar over the shared 12-trial CRN pool (kMcTrials=12, bar kMcTrials * kMcMinimumMeanSavingM, anchored at totalTrench[0]) accepts noise-driven switches; record per-trial trench per rollout candidate from the existing loop and veto any switch whose worst paired trial trails the reference move by more than kMcPerTrialMaxLossM=4 m. Switch suppression only — the accepted-switch set is a subset of the incumbent's, so per-case deltas measure exactly the incumbent's least-credible switches. Conclusions.md gate=updated; trigger=b+d.
- evidence: incumbent rollout block read verbatim (task/program_0/src/pipes.cpp lines 1113-1142: seeding 1113, xorshift guard 1117, scenario sampling 1121, totalTrench decl 1124, per-trial accumulation 1130, argmin 1134-1137, two-line acceptance 1138-1141, fallback 1142) plus window truncation line 1089 and entry gate line 1107; all 7 restore/machinery rubric patterns verified verbatim against incumbent source; prior art arXiv:1410.6782v2, arXiv:1506.04986v1, arXiv:1708.08526v4 retrieved via webfetch (Semantic Scholar HTTP 429, skipped); idea_bundle.json + target_rubrics.json written with identical target_rubrics arrays.
- next_action: run attempt — implement program_1/src/pipes.cpp per implementation_plan; grep-verify all 13 rubric source patterns verbatim on single exact lines; evaluate on the frozen open set; report per-case deltas by scenario id vs incumbent 30.074287976405728.

## Program Evaluations
- (none yet; the harness runs the only official evaluation after exit)

## Failures / Regressions
- (none yet)

## Next Hypotheses
- exactly flat => incumbent switches are already regret-robust on the open set; pivot to rollout depth or scenario-sampler coverage without stretching trial counts.
- per-case regressions => incumbent switches were net-beneficial; revert the veto and treat the rollout layer as saturated (pivot to deterministic placement outside chooseGapWithRollout).
- combined_score strictly above 30.074287976405728 => tune kMcPerTrialMaxLossM only with per-case evidence, never on the aggregate alone.
