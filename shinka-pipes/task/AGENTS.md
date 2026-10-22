# Pipes candidate task

- The coding agent proposes changes in its response. Shinka applies and evaluates them.
- Do not launch runs, compilers, tests, websites, or other agents yourself.
- Use the candidate and feedback supplied in the prompt; do not inspect raw inputs,
  other results, or holdout data.
- Change only the EVOLVE-BLOCK region. Preserve all other source text.
- The candidate must be causal and online, self-contained C++20, with no filesystem,
  network, subprocess, test-ID, or future-command access.
- Open15 improvements are search results and do not establish hidden-test performance.
