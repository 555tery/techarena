# Strategy matrix provenance

`summary.csv` and `matrix.json` are the corrected final **offline-simulator** sweep for the 15 open tests and the 13 deterministic generated streams. Reproduce them from the project root with:

```sh
g++ -O2 -std=c++17 -Wall -Wextra -pedantic experiments/pipes_sim.cpp -o experiments/pipes_sim
python3 experiments/benchmark_strategies.py
```

These are not official hidden-test results. The separately stored direct official-interactor checks for source policy 0 and policy 4 are in `results/strategy-runner-source-bestfit` and `results/strategy-source-policy4`; their open weighted totals are 28.366953399 and 28.375837609. Age-policy and holdout runs are managed by the coordinator/harness agent and are not included in these simulator files.

An earlier experimental simulator incorrectly ignored a usable free tail on allocation miss and reported 27.855659 for one mislabeled BF variant. That result was discarded and is absent from this matrix. Old `results/strategy-check-one`, `strategy-runner-check`, `strategy-source-bestfit`, and `strategy-source-bestfit-abs` directories are debugging/early runs; do not use them as the source of the reported matrix values.
