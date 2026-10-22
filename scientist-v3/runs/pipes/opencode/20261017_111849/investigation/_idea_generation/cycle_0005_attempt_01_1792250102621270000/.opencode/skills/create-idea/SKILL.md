---
name: create-idea
description: Create one next-step idea bundle and matching rubric bundle for iterative optimization. Use during idea generation runs (for example via scripts/idea.sh) when `idea_bundle.json` and `target_rubrics.json` must be produced.
---

# What the skill is about
Produce one concrete, testable next experiment idea with machine-readable rubrics.


# Output creation
Write both required JSON files directly with the available file-writing tools.
Do not depend on command execution. When command execution is explicitly available,
this optional helper can create starter files:
```bash
# the script path is relative to the skill file
python ./scripts/create_idea_placeholder.py <working_dir> [--cycle-index N]
```
- `<working_dir>`: the agent's current working directory (idea output directory).
- `--cycle-index N`: cycle index for the `idea_id` prefix (falls back to `CYCLE_INDEX` env var, then defaults to 1).

The optional script creates `idea_bundle.json` and `target_rubrics.json` with TODO
placeholders for every required field.  Replace each TODO value with the
actual content.


# What to do
1. Read task context:
- `../../task/task.md`
- `Improve the online C++ policy for the Pipes interactive task. Maximize the official weighted KPI score over the 15 supplied open scenarios, while preserving valid behavior and looking for changes that plausibly generalize to the undisclosed scenarios.`
- `- All 15 open scenarios pass the official interactor and satisfy the solver CPU and memory limits.
- The candidate's `combined_score` exceeds the seeded baseline score of 29.4471645435 / 32.1.
- Each proposed change tests a stated allocator hypothesis and is evaluated against the same frozen open-test set; report regressions by case rather than describing only the aggregate score.`
2. Use cycle and history context:
- `cycle_index=5`
- recent ideas and attempts from the prompt context
- best-known manifest from the prompt context
3. Prior-art scan (do this before fixing the idea; keep it to 2-4 quick lookups):
- Check how the algorithmic family you are about to propose is handled in public practice. Use whatever web access the run provides: the `webfetch` tool, or `curl -s -L` via the shell. Plain GET endpoints that return JSON/text:
  - arXiv (works without a key): `curl -s -L "https://export.arxiv.org/api/query?search_query=all:<url-encoded terms>&max_results=5"`
  - Semantic Scholar (without an API key it may return HTTP 429 from rate limiting; retry once after a short pause, otherwise continue): `curl -s -L "https://api.semanticscholar.org/graph/v1/paper/search?query=<url-encoded terms>&limit=5&fields=title,abstract,url,year"`
  - a general search results page via `webfetch` when a search endpoint is reachable.
- Try the next endpoint when one fails (redirects need `-L`; rate limiting returns 429). Mark the scan unavailable only when every attempt fails.
- Search for the mechanism you plan to change (for example "budgeted anytime allocation", "deadline-aware scheduling", "online inventory reallocation"), not for the whole task.
- Record 2-4 findings, one line each: `technique — source (title or URL) — how it informs this idea`.
- Copy each source title verbatim from the tool output. If you cannot quote it exactly from what you retrieved, drop that source - never cite a source you did not retrieve.
- Summarize the findings in `notes_for_agent`; name the most relevant source in `hypothesis` only when it actually motivated the change.
- If web access is unavailable or the lookups fail, write `prior_art: unavailable (<reason>)` in `notes_for_agent` and continue. The scan must never fail the run.
4. Write exactly these files directly (or use the optional placeholder helper when execution is allowed):
- `./idea_bundle.json`
- `./target_rubrics.json`
5. `./idea_bundle.json` must be a JSON object with keys:
- `idea_id` (string)
- `title` (string)
- `hypothesis` (string)
- `implementation_plan` (non-empty array of short strings)
- `target_rubrics` (non-empty array of `{id, description, type}`)
- `notes_for_agent` (string)
6. Rubric rules:
- include at least one `metric` rubric
- include at least one `implementation` rubric
- use stable snake_case rubric ids
- keep rubric descriptions concrete and measurable
7. Ensure `./target_rubrics.json` is exactly equal to `idea_bundle.json.target_rubrics`.
8. Apply the active harness rules exactly:

Harness mode is enabled. The harness injects a canonical structured `combined_score > incumbent` gate from the evaluator-validated baseline/current best. Do not invent score thresholds or derived metric expressions; agent-authored metric rubrics are replaced. Correctness is already mandatory. Each implementation rubric must include `verification` as `{"type": "source_contains", "patterns": ["distinct executable snippet", ...]}`. Use 1 to 8 specific literal snippets, each at most 1024 characters, that the implementation agent will place in `program_1/src/**`. Patterns are matched independent of whitespace, quote style, and numeric formatting; do not use generic imports, comments, or docstrings as evidence.

When a rubric includes `verification`, `verification` must be a JSON object, never a prose string.
For harness implementation rubrics, use exactly this shape:

```json
{
  "verification": {
    "type": "source_contains",
    "patterns": ["specific executable snippet"]
  }
}
```

9. Before finishing, reread both files and confirm every implementation rubric satisfies the active harness rules.
10. Do not modify files outside the required output files.
