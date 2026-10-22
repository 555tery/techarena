# Pipes SEARCH v2 candidate task

- Propose code in the response. Shinka applies and evaluates it.
- Do not run compilers, tests, experiments, websites or other agents yourself.
- Use only code, literature hypotheses and SEARCH feedback supplied in the prompt.
- Do not inspect raw inputs, other runs, validation or Open15 files or results.
- Change only the EVOLVE-BLOCK region. Preserve all other source text and protocol.
- The candidate must be causal and online, self-contained C++20; no relocation,
  future commands, test IDs, filesystem access, network or subprocesses.
- Target one explicit algorithmic mechanism per proposal, identify overlap with
  existing code and explain a failure mode and an ablation. Parameter tuning alone
  is not the research objective. Literature motivates hypotheses, not guaranteed gains.
- Prepared hypotheses H1–H6 include production-allocator transfers. Prefer the
  smaller H4/H5/H2 mechanisms before exploratory region reuse; this is not a budget.
  Check actual parent overlap and use a same-parent one-mechanism ablation. Keep
  exact pipe lengths and global fitting-gap fallback; do not add speculative reserve.
- Fitness uses the fixed 128 SEARCH-v2 inputs only, with equal family weights.
- The user explicitly selected SEARCH-v1 generation 2 as this run's initial program.
  Re-evaluate that supplied code on SEARCH-v2 before evolution; the old score is not a v2 result.
- If patch application fails, use the supplied error and previous parent/response
  to return the complete corrected patch for the same algorithmic proposal.
  Preserve exact SEARCH whitespace, blank lines and comments. Each repair starts
  from the original parent; resubmit all blocks, not only the failed block.
  Up to two feedback corrections stay within the same generation. Do not run tools.
