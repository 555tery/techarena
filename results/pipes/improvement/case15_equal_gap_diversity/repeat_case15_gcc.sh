#!/bin/sh
set -eu

ROOT=/work
EXP=results/pipes/improvement/case15_equal_gap_diversity
cd "$ROOT"

g++ -O2 -std=c++20 -pipe \
    "$EXP/source/highside_equal_gap_rollout.cpp" \
    -o "$EXP/bin/highside_equal_gap_rollout_gcc_exact"
g++ -O2 -std=c++17 -pipe \
    -I scientist-v3/tasks/pipes/vendor \
    scientist-v3/tasks/pipes/vendor/interactor.cpp \
    -o "$EXP/bin/interactor_gcc_exact"

baseline_rc=0
python3 tools/pipes_harness.py \
    --solver "$EXP/bin/baseline_gcc_prior_gate" \
    --interactor "$EXP/bin/interactor_gcc_exact" \
    --tests data/pipes/open/15.in \
    --out "$EXP/runs/case15-repeat-baseline" \
    --name baseline-prior-gcc-gate-repeat \
    --response-timeout 5 --cpu-limit 5 --memory-limit-mb 256 \
    --wall-timeout 180 || baseline_rc=$?
candidate_rc=0
python3 tools/pipes_harness.py \
    --solver "$EXP/bin/highside_equal_gap_rollout_gcc_exact" \
    --interactor "$EXP/bin/interactor_gcc_exact" \
    --tests data/pipes/open/15.in \
    --out "$EXP/runs/case15-repeat-candidate" \
    --name highside-equal-gap-rollout-prior-gcc-gate-repeat \
    --response-timeout 5 --cpu-limit 5 --memory-limit-mb 256 \
    --wall-timeout 180 || candidate_rc=$?
printf 'baseline_harness_rc=%s\ncandidate_harness_rc=%s\n' \
    "$baseline_rc" "$candidate_rc" > "$EXP/runs/case15-repeat-harness-status.txt"
