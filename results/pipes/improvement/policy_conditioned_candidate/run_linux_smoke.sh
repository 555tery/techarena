#!/bin/sh
set -eu
cd /workspace
g++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic results/pipes/final/solution.cpp -o results/pipes/improvement/policy_conditioned_candidate/bin/frozen_final_linux
g++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror -DPOLICY_SELECTOR_DIAGNOSTICS results/pipes/improvement/policy_conditioned_candidate/src/policy_conditioned.cpp -o results/pipes/improvement/policy_conditioned_candidate/bin/policy_conditioned_linux_diag
g++ -O2 -std=c++17 -pipe vendor/pipes_official/interactor.cpp -o results/pipes/improvement/policy_conditioned_candidate/bin/interactor_linux
python3 tools/pipes_harness.py \
  --solver results/pipes/improvement/policy_conditioned_candidate/bin/frozen_final_linux \
  --interactor results/pipes/improvement/policy_conditioned_candidate/bin/interactor_linux \
  --tests results/pipes/improvement/policy_conditioned_candidate/inputs/preflight/200000_uniform_random.in \
  --out results/pipes/improvement/policy_conditioned_candidate/preflight/smoke_baseline \
  --name frozen-final-smoke --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py \
  --solver results/pipes/improvement/policy_conditioned_candidate/bin/policy_conditioned_linux_diag \
  --interactor results/pipes/improvement/policy_conditioned_candidate/bin/interactor_linux \
  --tests results/pipes/improvement/policy_conditioned_candidate/inputs/preflight/200000_uniform_random.in \
  --out results/pipes/improvement/policy_conditioned_candidate/preflight/smoke_candidate \
  --name conditioned-diag-smoke --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
