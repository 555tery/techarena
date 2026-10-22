# Goal

Improve the online C++ policy for the Pipes interactive task. Maximize the official weighted KPI score over the 15 supplied open scenarios, while preserving valid behavior and looking for changes that plausibly generalize to the undisclosed scenarios.

# Constraints

- Edit only `program_0/src/pipes.cpp` in the candidate program. The evaluator, test inputs, official interactor, and harness define the task and must not be changed.
- The program receives one integer command at a time on stdin. For a positive pipe length `L` in `[1, 40]`, print `N D`; for a negative PID command, print the pipe's original coordinate. Flush after each response. On `0`, print nothing and exit immediately.
- The solver must be online: it cannot inspect future commands. It may retain state from commands already received.
- Every scenario must be valid, stay below 5 seconds of solver CPU and 256 MiB of solver RSS, and never extend the trench beyond 100,000,000 m. A scenario has at most 200,000 commands.
- The evaluator compiles C++20 with `g++`. The submitted program must be self-contained and must not require model/data files, network access, or third-party runtime packages.
- Open-test search can overfit. Do not claim that an open-test improvement establishes performance on the closed tests. Synthetic holdout and closed-test data are intentionally absent from this task snapshot.

# Evaluation

The evaluator runs all 15 official open inputs through the supplied official interactor. `combined_score` is the sum of `KPI × test weight`; its maximum for this subset is 32.1. An invalid case or a per-case resource-limit violation makes `correct` false. Use the per-case evaluator report to diagnose score changes.

# Rubrics

- All 15 open scenarios pass the official interactor and satisfy the solver CPU and memory limits.
- The candidate's `combined_score` exceeds the seeded baseline score of 29.4471645435 / 32.1.
- Each proposed change tests a stated allocator hypothesis and is evaluated against the same frozen open-test set; report regressions by case rather than describing only the aggregate score.
