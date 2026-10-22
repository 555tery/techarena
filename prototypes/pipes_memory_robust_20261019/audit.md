# Read-only design audit: generalization under the Pipes runtime limits

## Evidence and current boundary

The audited executable is `prototypes/pipes_robust_round3_20261019/candidate-physical/solution.cpp`, SHA-256 `e7a88219417219faa925ec9d91641eb15d02aafeab76fdb9ef9d7144c7c25112`. The rules permit 5 s CPU and 256 MiB RSS. Its report records 1.379578 s maximum CPU and 10.625 MiB maximum RSS across 96 local checks. The code is therefore not close to either measured resource limit; most runtime inputs do not exercise the expensive branch.

The selected binary preserves the Open15 score exactly (30.75747404826914, all 15 at their tested lower-bound trench length). On finite post-freeze checks, the report records mixed fresh-stream transfer (3 wins, 7 ties, 4 losses; mean KPI change +0.004061, worst -0.008027). These observations support a bounded robustness experiment, not a hidden-test generalization claim.

The main replay matches the encoded public command/address tables until a command diverges, addresses conflict, or the table address no longer fits. Only then can it import the *actual* physical geometry and start the online allocator, and even that starts only if `state.T < shadowBefore`; otherwise the plain best-fit path remains. The outer online guard permits at most 32 placement proposals, stops if online trench growth overtakes the contemporaneous best-fit shadow, and rejects a proposal that digs more immediately than best-fit.

This does not repair an early trap that shares the public prefix: every earlier action has already been emitted, and excavation cannot be undone. In particular, the report's residual Open11 prefix at p2 remains KPI 0.0833 versus BF 1.0; Open8 p402 remains 0.1656 versus BF 1.0. With the actions on the common prefix held fixed, a planner that starts only after a mismatch cannot improve those scores. A counterfactual continuation cannot change that causal fact.

## Why the current rollout has limited coverage

The embedded Monte Carlo is a narrow action ranker, not a planner over the full physical action space:

- It keeps at most three candidates, chosen from fitting spans with slack at most 40 m and ranked by the current `scoreGap`. It uses the representative start associated with each size. It therefore omits many spatially distinct spans, alternate sides, and candidates with larger slack that may protect later capacity.
- Rollouts run only when the current best-fit action is already the first candidate, history has at least 32 events, and the state has at most 64 gaps and 4096 active pipes. The existing policy also bypasses the rollout for several special lanes.
- It samples only four future events. Context matching uses at most three prior observations from the recent 128-event window, and `observationKeyEqual` ignores the value/rank of deletion events. Twelve samples are scored by mean final trench only. Thus candidate coverage is the primary bottleneck; increasing sample count while retaining the same top-three set mostly ranks the same narrow choices more confidently.
- Each candidate/trial copies a rollout state. This is safe under current caps, but increasing candidates, trials, horizon, and caps all at once risks CPU spikes on large fragmented states.

The wrapper's immediate-dig guard is useful but local: it rejects an action only when it digs more *now* than BF. It does not certify that its future trench length is bounded by BF. The report itself calls this out.

## Bounded planner proposal

First, keep exact public replay as the default so the measured Open15 score remains unchanged. In the post-mismatch episode, use the imported actual geometry as the only legal state. Replace the current narrow MC decision with an anytime, deterministic robust action evaluator:

1. **Broaden action coverage before adding rollout depth.** Build a diverse shortlist of up to 8 legal placements from the actual free-gap set: BF; opposite-edge placement in BF's gap; both sides of the best fit from each distinct capacity/slack bucket; the largest usable gap; and up to two gaps adjacent to pipes with high and low observed deletion risk. Deduplicate identical starts and include a tail-expansion action only when it is needed for legality. This explores geometries that the present top-three-by-slack rule never sees.
2. **Generate causal futures.** Use only already-observed events. Keep placement length and deletion rank as separate context features; retrieve short blocks after suffix contexts up to 6 events from recent windows (for example 256, 2048, and 8192 events), weighting recent blocks more heavily. Add a small, fixed stress set made only from observed event blocks: burst lengths, runs, mixed refill, and deletion-heavy/refill-heavy blocks. Do not label any constructed sequence as a prediction of the actual unseen suffix.
3. **Score risk, not only the sample mean.** For each of at most 16 scenarios, simulate 12 future events from the candidate's physical state using the same causal scenario across every candidate. Rank by a lexicographic objective: (a) no extra immediate excavation versus BF, (b) lower 90th-percentile / worst-family trench growth, then (c) lower mean growth and fragmentation-risk proxy. Keep BF on score ties or low context support. A short terminal feature can count future fit capacity by pipe length and the number of gaps that cannot fit the next observed/scenario lengths; it must be calibrated as a ranker, not described as a guarantee.
4. **Bound compute globally.** Cap the post-mismatch branch at 32 decisions as today, 8 actions × 16 scenarios × 12 events per decision, with a total simulated-event budget (initial engineering ceiling: 100,000 events per input). Stop search when the budget is exhausted and return BF. Also retain the existing 64-gap / 4096-active threshold until stress measurements justify raising it. Use reusable buffers or rollback snapshots to avoid allocating full maps/vectors for every branch. These are starting ceilings; the 5 s CPU limit requires measurement on maximally fragmented 200,000-command inputs, with a target below roughly 4 s for margin.

Memory headroom can support a compact causal block index and reusable scenario/snapshot buffers; it should not be spent on an unbounded history matrix or a large cache of full allocator copies. Most simulated states are distinct, so a transposition cache may have low hit rate. Benchmark hit rate before adding one.

## Open15 preservation and the early-prefix question

Post-mismatch-only changes leave all 15 public action traces untouched and can improve only the suffix after divergence. To improve a trap that remains identical through an expensive public prefix, the solver must make at least one different placement while the histories still coincide. That is a change to behavior on a public prefix, even if the encoded tables themselves remain unchanged.

The only defensible route to try that without losing the Open15 maximum is a certified overlay: for every still-compatible public test, test whether a candidate action admits a legal repaired suffix whose final trench remains at that test's proven optimum. Choose among only candidates certified for all live public branches, then score those actions with causal stress scenarios. The current table suffix cannot itself certify this after changing an address, because later recorded coordinates may overlap or cease to be feasible. A repair planner or a precomputed continuation certificate is required. Until that exists, the honest scope is post-divergence robustness; do not claim the residual common-prefix traps are fixed.

The 5 s / 256 MiB limits make this planner plausible for the post-mismatch episode, given current measured headroom, but they do not provide future information and cannot overcome the shared-prefix constraint. Validate any implementation on the existing fixed suite and new predeclared families, reporting Open15 score, paired KPI changes, worst loss, CPU, and RSS separately.
