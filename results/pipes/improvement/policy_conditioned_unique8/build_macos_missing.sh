#!/bin/sh
set -eu

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
BASE="results/pipes/improvement/policy_conditioned_unique8"
OUT="$ROOT/$BASE/bin/macos_native_20261017"

if [ -e "$OUT" ]; then
  printf '%s\n' "Refusing to overwrite existing native build: $OUT" >&2
  exit 2
fi
mkdir -p "$OUT"
cd "$ROOT"

printf '%s\n' 'Host:'
uname -a
sw_vers
printf '%s\n' 'Compiler:'
clang++ --version
printf '%s\n' 'Python:'
python3 --version

clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic \
  results/pipes/final/solution.cpp \
  -o "$OUT/frozen_final_macos"
clang++ -O2 -std=c++20 -pipe -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror \
  results/pipes/improvement/policy_conditioned_unique8/src/policy_conditioned.cpp \
  -o "$OUT/policy_conditioned_macos"
clang++ -O2 -std=c++17 -pipe \
  vendor/pipes_official/interactor.cpp \
  -o "$OUT/interactor_macos"

shasum -a 256 \
  "$OUT/frozen_final_macos" \
  "$OUT/policy_conditioned_macos" \
  "$OUT/interactor_macos"
