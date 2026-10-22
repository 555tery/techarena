# Open15: exact-suffix diagnosis of frozen MC actions

Status: protocol and diagnostic source are frozen before any Open15 replay or
counterfactual suffix outcome. Only the first actual MC invocation in each
eligible case is counterfactually evaluated; no MC-decision frequency or share
over Open15 will be reported.

## Question and scope

For the **first actual MC invocation in each eligible Open15 case only**, does
the shortlist omit physical gap-edge actions that finish with a shorter trench
under the same exact remaining command suffix and frozen allocator
continuation? At that same first invocation, when a better action is in the
shortlist, does frozen MC choose another action with a longer exact-suffix
outcome?

This is a retrospective ranking diagnosis on Open15. Exact suffixes are
unavailable online. Any measured advantage is hindsight regret under a frozen
continuation, not an online gain or evidence of hidden-test improvement. No
policy will be selected or tuned from this diagnosis.

## Frozen artifacts and inputs

- Baseline source: `results/pipes/final/solution.cpp`, SHA-256
  `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Frozen baseline binary: SHA-256
  `dabb6910bde7550dbf4ab03d6d7b450d0a91f53a90dc06e52d6b271c8602000c`.
- Instrumented source: `src/diagnostic.cpp`; SHA-256 is recorded below.
- Diagnostic binary: SHA-256 is recorded below; compile with Apple Clang 17.0.0
  and `-O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic
  -DPIPES_ACTION_DIAG`.
- Official interactor binary SHA-256
  `47994e837450bc4b0b683736194c2dce8023dd30f257c316c1e8e69245d15b9a`;
  harness SHA-256
  `65aaa7043ffad3f0894dbdd5990b31bd713328d8546511b143ef57dca31dd20d`.
- Raw-stdout tee wrapper: `scripts/capture_raw_harness.py`; its SHA-256 is
  recorded below. It imports the unchanged `tools/pipes_harness.py` and
  monkeypatches only `harness.start_line_reader` and `harness.run_case`:
  `run_case` supplies the current case directory; `start_line_reader` wraps
  only the solver stream in `TeeReader`, whose `readline()` saves the raw bytes
  and returns the same bytes to the original reader. The original harness
  continues to run the official interactor and score every case unchanged.
- Frozen-final raw-output reference prerequisite: after independent review gives
  GO, first run the already frozen binary above once on all 15 Open inputs with
  this same tee wrapper and unchanged official harness. Store each original
  solver byte stream as `reference_frozen/runs/{1..15}/solver_stdout.raw` and
  freeze a JSON manifest containing case number, input SHA-256, raw-output
  SHA-256, harness status, weighted score, total solver CPU time, and peak RSS
  before starting the instrumented no-force run. This captures the missing raw
  bytes directly;
  interactor-normalized `judge_output.txt` is not an exact-byte reference.
  If any reference case is invalid or a raw output is missing, stop before the
  diagnostic no-force run. The reference manifest is UTF-8 JSON Lines, one row
  per case in numeric order, fixed key order `case`, `input_sha256`,
  `raw_stdout_sha256`, `status`, `weighted_score`, `solver_cpu_total_s`,
  `solver_peak_rss_mb`, compact separators `(',', ':')`, and LF endings
  including a final LF. `case` is an integer; `input_sha256` and
  `raw_stdout_sha256` are computed from the corresponding exact files. The
  remaining fields are strings copied exactly from the matching `cases.csv`
  columns (`status`, `weighted_score`, `solver_cpu_total_s`, and
  `solver_peak_rss_mb`). Preserve the RSS value as reported in MiB; do not
  convert or round it to bytes. Hash the exact manifest bytes. Do not rebuild
  or modify the frozen binary.
- Input files: `data/pipes/open/{1..15}.in`; hashes are in
  `results/pipes/final/manifest.json`. The 15 headers contain exactly 280,156
  commands in total.
- Continuation: same input's unmodified suffix, in original order, and the
  frozen-final allocator after the forced action. No command is skipped or
  changed.

## Baseline trace and fixed sample

After the frozen-final reference is complete and hashed, run the instrumented
no-force solver once on each Open15 input. It logs every actual MC invocation.
Freeze and hash all 15 raw `solver_stderr.txt` traces before deriving actions;
they are the source of MC shortlist order, estimates, target ordinals, and
state hashes. The exact-suffix sample is fixed to the first actual MC decision
(`decision ordinal 0`) in each case where one exists. No later state will be
substituted if that state is inconvenient or expensive. A case without an
actual MC decision contributes no counterfactual action rows.

For each sampled state, form unique physical pipe-start actions as follows:

1. Include every action in the logged MC shortlist, using its frozen
   `highSide` edge.
2. Form the expanded set from every physically fitting free gap at both edges;
   deduplicate actions by pipe start. Remove actions already in the shortlist.
3. Sort the remaining expanded actions by `(gap length, gap start, edge)`, with
   left edge before right edge. If there are at most eight, include all. If
   there are more than eight, include the eight at sorted indices
   `floor(j*(K-1)/7)` for `j=0..7`, where `K` is the number of remaining
   actions.

Action identity is its physical pipe start. In an exact-fit gap, the left and
right edges produce the same start; emit one expanded action and canonicalize
its manifest side as `0=left` (the alternative is `1=right`). When that
physical action is also in the shortlist, retain one manifest row and use the
same canonical side for forcing. For non-exact-fit shortlist actions, preserve
the logged `highSide`; for expanded actions, side `0` means left and side `1`
means right. The action manifest has one row for every unique feasible physical
pipe start in the union of the full expanded set and shortlist, including
expanded actions that are not selected for forcing. Fields, their exact order,
and types are: `case` (integer), `decision_ordinal` (integer), `gap_start`
(integer), `gap_end` (integer), `pipe_start` (integer), `side` (0 left or 1
right), `shortlist` (boolean), `expanded` (boolean), `shortlist_rank`
(zero-based integer or null), `x_sorted_rank` (zero-based integer or null),
`sampled` (boolean), `sample_rank` (zero-based integer or null), `mc_selected`
(boolean), `forced` (boolean), and `run_order` (integer or null).
`x_sorted_rank` is the position in the complete sorted non-shortlist expanded
set X; `sample_rank` is the zero-based selection index `j` among the at-most-
eight sampled X actions. `mc_selected` marks the baseline MC choice; `forced`
is true exactly for shortlist actions and sampled X actions. `run_order` is the
zero-based global replay sequence number or null if not forced. The selected
MC action is included in the shortlist and is the first replay for its case
(the control replay), with no duplicate run. Global `run_order` is assigned in numeric case
order; within each case it is selected-control first, then remaining shortlist
actions in logged shortlist order, then sampled X actions in increasing
`sample_rank`.

Canonical manifest bytes are frozen as follows: UTF-8 JSON Lines, no BOM, one
JSON object per row, fixed key order exactly as listed above, compact JSON
separators `(',', ':')`, `ensure_ascii=False`, decimal base-10 integers with no
leading zeroes, JSON `true`/`false`/`null`, and LF line endings including one
final LF. Rows are sorted numerically by `(case, decision_ordinal, pipe_start)`;
strings use ordinary JSON escaping. The SHA-256 is computed over these exact
bytes and recorded before reading any forced suffix outcome. No action,
membership, rank, or run order may be changed afterward.

The selected MC action is already in the shortlist. Its forced replay is the
control replay; do not run a duplicate. Before any counterfactual outcome is
read, serialize and hash the complete action manifest as specified above. No
action may be added, removed, reranked, or resampled afterward.

The exact number of forced replays is frozen by the baseline trace and this
rule:

`N = sum over eligible cases [shortlist size + min(8, non-shortlist expanded size)]`.

Because geometry and candidate counts require the baseline trace, the scalar
`N` is not knowable from input lengths alone; it must be computed and recorded
from that trace before suffix evaluation. The fixed hard cap is 165 forced
replays (11 per case). Each replay consumes at most the full case input; the
input-header upper bound is exactly 3,081,716 command applications across all
forced replays (11 times 280,156). In addition, the frozen-reference capture
and instrumented no-force baseline each process 280,156 commands, for a total
upper bound of 3,642,028 command applications. There is no time-based
truncation or outcome-dependent reduction. Also report the realized sum of
suffix command applications from each target onward.

## Instrumentation and validity checks

For every actual MC invocation, log per-case ordinal, request length, the
0-based ordinal of its nonterminal input command, `highSide`, baseline gap,
ordered shortlist gaps, each shortlist item's 12 rollout total-trench
estimate, selected candidate, and every physically fitting gap with cohort
and both edge starts. Each record includes a
deterministic pre-decision state hash over allocator fields that affect future
behavior; the Fenwick array is omitted because it is a deterministic aggregate
of the hashed active-PID flags. Before recording a target, fail fast if
`freeBySize`, cohort-size indices, or `freeBySizeShared` disagree with
`freeByStart` and `gapCohort`, or if a gap cohort is outside `{-1, 0, 1}`.

Every forced run must satisfy all of the following:

- All `MC_DIAG` records strictly before the target match the no-force baseline
  trace byte-for-byte, and the target pre-decision state hash matches.
- Using the target's 0-based nonterminal input-command ordinal, compare solver
  stdout byte-for-byte from its beginning through the response lines for all
  earlier commands against both the no-force baseline and the corresponding
  captured frozen-final raw reference. Each nonterminal input command has one
  solver-output line; ordinal zero therefore has an empty stdout prefix.
- The requested gap-edge action remains physically feasible at the target.
- The target emits exactly one `MC_FORCE` and zero `MC_FORCE_INVALID` records.
- The target command's stdout response is exactly one placement line. Parse the
  response line at index equal to the 0-based target command ordinal; require
  exactly the two integer fields `0 <manifest pipe_start>` and its terminating
  newline. This verifies that the response coordinate equals the forced action
  and no dig was requested. `MC_FORCE` also logs its computed `pipe_start`,
  which must equal the manifest value.
- Force is requested as
  `PIPES_DIAG_FORCE=<decision>,<gap_start>,<side>,<expected_state_hash>`;
  side `0` means left and `1` means right; exact-fit duplicate edges are
  canonicalized to side `0`. The expected hash comes from the no-force trace
  for the same target.
- The selected-action control replay produces byte-for-byte identical solver
  stdout to both the no-force baseline and captured frozen-final raw reference.
- The no-force instrumented Open15 replay produces byte-for-byte identical
  solver stdout to the captured frozen-final raw reference for all 15 cases, with all cases
  valid.

Do not begin any forced replay unless the frozen-reference capture and all 15
instrumented no-force cases are valid and their stdout files match byte-for-
byte. This is a global precondition, not a per-case check that can be deferred
until that case's counterfactual runs.

If a target is not reached, its state hash differs, the action is no longer
feasible, the force count is not exactly one, or baseline equivalence fails,
classify the replay as invalid and abort all remaining forced replays. Mark the
entire sampled decision invalid; report no regret/gain or minima for it, and do
not compute metrics on the surviving subset of actions. Preserve the frozen
manifest and all outputs through the failure. Do not repair the source or alter
the frozen policy after outcomes are available.

## Preregistered metrics

For each sampled decision `d`, let `S` be its shortlist, `X` the preregistered
sampled non-shortlist actions, and `T(a)` the final trench after forcing `a`
and replaying the exact suffix with frozen continuation. Report:

- `shortlist_selected_regret_m = T(MC-selected) - min(T(a): a in S)`.
  Positive means another shortlisted action does better under this exact
  suffix.
- `sampled_omitted_action_gain_m = min(T(a): a in S) -
  min(T(a): a in S union X)`. Positive means a sampled physical action omitted
  from the shortlist does better. Zero does not establish that no untested
  omitted action would do better.
- Per action: membership, `x_sorted_rank`, `sample_rank`, selected/forced
  flags, MC estimate if shortlisted, forced
  trench, validity, and exact-suffix command count.

Summarize cases separately and pooled counts only. Decision/action outcomes
share states and suffixes, so do not compute inferential confidence intervals
or interpret sums of per-decision improvements as attainable savings. Record
source/input/action-manifest hashes, output-equivalence results, CPU, peak RSS,
and wall time. Keep compact aggregates in the report and full rows in CSV/JSON.

## Frozen diagnostic artifacts

- Instrumented source SHA-256:
  `ec913c435abe052c4ad96e3ee71493c70a138f1e733501d95eef6e3baf2ab91c`.
- Diagnostic binary SHA-256:
  `c9840fcb02ad7f961b3d23ab5d27d2ec4dcca5802d40a0d15b1016a45c390082`.
- Raw-stdout tee wrapper SHA-256:
  `5e1fa4dffbeef1136968f6f99dadc421015e44e22e4397133d4217e75a9f73be`.

No Open15 solver replay, suffix outcome, test-site request, Docker run, holdout,
synthetic test, or optimization experiment is authorized before independent
review of this protocol and the frozen diagnostic source.
