#!/bin/sh
set -eu

ROOT=/work
EXP=results/pipes/improvement/case15_equal_gap_diversity
cd "$ROOT"

mkdir -p "$EXP/bin" "$EXP/build" "$EXP/runs"
g++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
    "$EXP/source/baseline.cpp" -o "$EXP/bin/baseline_gcc"
g++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
    "$EXP/source/highside_equal_gap_rollout.cpp" \
    -o "$EXP/bin/highside_equal_gap_rollout_gcc"
g++ -O2 -std=c++17 -pipe \
    vendor/pipes_official/interactor.cpp -o "$EXP/bin/interactor_gcc"

run_pair() {
    label=$1
    tests=$2
    python3 tools/pipes_harness.py \
        --solver "$EXP/bin/baseline_gcc" \
        --interactor "$EXP/bin/interactor_gcc" \
        --tests "$tests" --out "$EXP/runs/$label-baseline" \
        --name "baseline-$label" --cpu-limit 5 --memory-limit-mb 256 \
        --wall-timeout 120
    python3 tools/pipes_harness.py \
        --solver "$EXP/bin/highside_equal_gap_rollout_gcc" \
        --interactor "$EXP/bin/interactor_gcc" \
        --tests "$tests" --out "$EXP/runs/$label-candidate" \
        --name "highside-equal-gap-rollout-$label" \
        --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
}

case "${1:-}" in
    screen)
        run_pair screen-case-05 data/pipes/open/5.in
        run_pair screen-case-09 data/pipes/open/9.in
        run_pair screen-case-15 data/pipes/open/15.in
        ;;
    open15)
        run_pair open15 data/pipes/open
        ;;
    holdout-v2)
        run_pair holdout-v2 data/pipes/synthetic/final-holdout-v2
        ;;
    fresh-synthetic)
        run_pair fresh-synthetic \
            results/pipes/improvement/run48_synthetic_independent/inputs
        ;;
    *)
        echo "usage: $0 {screen|open15|holdout-v2|fresh-synthetic}" >&2
        exit 2
        ;;
esac
