# Preregistered experiment: paired full-suffix candidate ranker

Status: frozen before generating this experiment's inputs or labels.

## Question and scope

Test whether a pairwise linear ranker trained on paired counterfactual outcomes over the complete remaining command suffix can improve the existing frozen Pipes allocator. The prior `learned_gap_value` used regression trees, a 512-command target, baseline-only training trajectories, and its earlier action/scoring setup; this experiment changes the target and adds one candidate-trajectory data-aggregation round.

The first experiment intentionally preserves the existing candidate set and edge policy: at most the three best-fit feasible free-gap starts with slack at most 40 m, same edge as the underlying allocator, only when the baseline gap is among the candidates. No interior placements, voluntary digging, new candidate kinds, per-test rules, or parameter sweeps are included.

## Data partitions

All seeds below are new for this experiment. Solver runtime receives only the online command stream and its own state; seed, stream name, test index, and future commands are unavailable.

- Train: 30 streams, 40,000 commands each, one stream for every combination of 3 length profiles (`uniform`, `short-heavy`, `long-heavy`), 5 deletion policies (`random`, `oldest`, `newest`, `shortest`, `longest`), and 2 regimes. Seeds are 2,026,101,800 through 2,026,101,829. Steady uses churn 0.42 and batch 0; periodic drain uses churn 0.38 and batch 500.
- Validation gate: 60 streams, one stream for every combination of 2 horizons (16,384 and 200,000), the same 3 length profiles, 5 deletion policies, and 2 regimes. Seeds are 2,026,101,900 through 2,026,101,959. Regime parameters match train. Validation is never used to fit, select, or tune the model.
- Training states are sampled every 1,000 command indices after index 360 when at least two candidate actions exist. Baseline trajectory states are labelled first. After the initial model is fit, candidate outputs on the same training inputs provide one additional trajectory set; the ranker is then refit once on the combined train-only data. This is a fixed DAgger-style round, not iterative tuning.

## Counterfactual labels and fitting

For each sampled state, score each eligible candidate by applying that first action and then replaying the exact remaining command suffix through EOF under one fixed continuation policy: the deterministic frozen greedy allocator without nested Monte Carlo. Every action in the state receives the identical command suffix and continuation rule. Label is final trench growth from the pre-action trench. PID deletions are replayed by exact PID, not approximated deletion rank. Future commands appear only in the offline labeler.

Fit one linear RankNet-style pairwise model over the existing 180 action features. For every within-state action pair, form a soft preference from their paired final-growth difference using a fixed 20 m temperature. Standardize feature coordinates from train rows only; optimize pairwise cross-entropy with fixed L2 regularization, 1,000 full-batch Adam steps, fixed learning rate 0.03, and fixed seed 20261018. Runtime selects the candidate with the lowest ranker score, retaining the existing baseline action on exact score ties. There is no hyperparameter search.

## Confirmatory gate

Run the frozen candidate and frozen-final baseline on identical validation input bytes using the local official interactor. All 120 interactions must be valid and consume exactly the declared commands. Calculate per-stream KPI as final occupied length / final trench length; each stream has weight 1. Paired delta is candidate KPI minus baseline KPI.

Pass only if:

1. The lower endpoint of a 95% two-sided percentile CI for the equally weighted mean of 60 paired stream deltas is strictly above zero. Use 20,000 whole-stream bootstrap replicates with replacement and seed 2026101817; sort replicate means and use linear percentile interpolation.
2. The mean paired delta across the 30 streams with 200,000 commands is nonnegative.
3. There are no invalid transcripts, solver crashes, or resource-limit violations (5 CPU seconds and 256 MiB RSS per stream).

On failure, stop this branch as NO-GO; do not change the action set, model, features, training seeds, or validation set and do not test on Open15 or holdout-v2. On pass, freeze source/model hashes first, then run one local Open15 and holdout-v2 comparison against the same frozen-final baseline. No website, leaderboard, submission, or Docker is used.

## Integrity notes

- Protected source: `results/pipes/final/solution.cpp`, expected SHA-256 `c4b737b9a14588dd9895450acaff804b140691ef4d41bf1a0d68b6f13232a991`.
- Protected canonical source: `src/pipes.cpp`, expected SHA-256 `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`.
- A discrepancy exists in the previous `learned_gap_value` report: its prose says 534 training states, while its manifest records 310 training states and 534 validation states. This experiment will report train and validation counts from its own machine-readable manifest; the old report is not edited here.
