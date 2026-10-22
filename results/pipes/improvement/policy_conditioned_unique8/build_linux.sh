#!/bin/sh
set -eu
cd /workspace
g++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
  results/pipes/final/solution.cpp \
  -o results/pipes/improvement/policy_conditioned_unique8/bin/frozen_final_linux
g++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror \
  results/pipes/improvement/policy_conditioned_unique8/src/policy_conditioned.cpp \
  -o results/pipes/improvement/policy_conditioned_unique8/bin/policy_conditioned_linux
g++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror \
  -DPOLICY_SELECTOR_DIAGNOSTICS \
  results/pipes/improvement/policy_conditioned_unique8/src/policy_conditioned.cpp \
  -o results/pipes/improvement/policy_conditioned_unique8/bin/policy_conditioned_linux_diag
g++ -O2 -std=c++17 -pipe \
  vendor/pipes_official/interactor.cpp \
  -o results/pipes/improvement/policy_conditioned_unique8/bin/interactor_linux
python3 results/pipes/improvement/policy_conditioned_unique8/verify_python_rng.py
