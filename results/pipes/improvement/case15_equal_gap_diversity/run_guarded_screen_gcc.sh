#!/bin/sh
set -eu

ROOT=/work
EXP=results/pipes/improvement/case15_equal_gap_diversity
cd "$ROOT"

g++ -O2 -std=c++20 -pipe "$EXP/source/highside_equal_gap_rollout.cpp" \
    -o "$EXP/bin/highside_equal_gap_rollout_gcc_guarded"
g++ -O2 -std=c++17 -pipe -I scientist-v3/tasks/pipes/vendor \
    scientist-v3/tasks/pipes/vendor/interactor.cpp \
    -o "$EXP/bin/interactor_gcc_exact"

run_one() {
    label=$1
    solver=$2
    test_file=$3
    output=$4
    rc=0
    python3 tools/pipes_harness.py \
        --solver "$solver" \
        --interactor "$EXP/bin/interactor_gcc_exact" \
        --tests "$test_file" \
        --out "$output" \
        --name "$label" \
        --response-timeout 5 --cpu-limit 5 --memory-limit-mb 256 \
        --wall-timeout 180 || rc=$?
    printf '%s_rc=%s\n' "$label" "$rc" >> "$EXP/runs/guarded-screen-status.txt"
}

mkdir -p "$EXP/runs"
: > "$EXP/runs/guarded-screen-status.txt"
for case_id in 5 9 15; do
    run_one "baseline-case-$case_id" \
        "$EXP/bin/baseline_gcc_prior_gate" \
        "data/pipes/open/$case_id.in" \
        "$EXP/runs/guarded-screen-case-$case_id-baseline"
    run_one "guarded-candidate-case-$case_id" \
        "$EXP/bin/highside_equal_gap_rollout_gcc_guarded" \
        "data/pipes/open/$case_id.in" \
        "$EXP/runs/guarded-screen-case-$case_id-candidate"
done
