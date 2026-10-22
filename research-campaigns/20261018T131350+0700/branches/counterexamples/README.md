# Bounded counterexample diagnostics

Offline, bounded diagnostic tools and short synthetic traces for distinguishing
three things: a fixed baseline trajectory, a complete offline optimum, and an
action/state that an online policy can select from the observed prefix. These
artifacts do not change the production solver or Shinka configuration.

## Reproduction and proof contract

`bounded_oracle.py` enumerates all legal integer placement coordinates and all
20 m excavation increments below a known feasible upper bound. Pipe IDs and
their physical starts are explicit in the memoized state; deletion frees the
specified ID. It uses the peak-live-volume lower bound
`20 * ceil(peak_live_length / 20)`. If an enumerated legal witness reaches that
bound, the exact optimum is proven immediately. Otherwise, proof requires an
exhaustive search below a feasible upper bound. Hitting the state or time cap
returns `unknown`, never `optimal`.

The oracle sees the entire finite trace. It is for diagnosis only and is
forbidden as a production policy. It does not imply that a witness action can
be chosen online. `prefix_intersection.py` separately enumerates legal states
after an identical command prefix and checks exact suffix feasibility against
each already-proven optimum. That conclusion, when present, applies only to
that synthetic pair.

Run from the repository root with the project virtual environment:

```sh
shinka-pipes/.venv/bin/python -B research-campaigns/20261018T131350+0700/branches/counterexamples/bounded_oracle.py --self-check
shinka-pipes/.venv/bin/python -B research-campaigns/20261018T131350+0700/branches/counterexamples/bounded_oracle.py --suite research-campaigns/20261018T131350+0700/branches/counterexamples/suite-v1b/traces.json --out /tmp/counterexample-oracle.json --max-states 200000 --timeout-s 10
```

Each command performs the campaign quota gate first. `--reference-dir` may be
provided to `--suite` only with outputs from a legal local diagnostic run; each
response is replayed and validated before it is accepted as an incumbent.

## Evidence

Baseline is `campaign/baseline/solution.cpp`, SHA-256
`c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c`.
The exact reports cover 8 hand-authored short mechanism probes and two
parameterized 32-pair suites (138 trace rows total). All 138 rows reached a
feasible witness at the proven peak-volume lower bound. The search therefore
proved those listed finite optima; it did not estimate a contest score.

The official native checker evaluated the strong baseline on the 8-case
`suite-v1b` and on selected synthetic paired controls. In the 8-case suite,
`alternating-size-replacement` was 80 m for the baseline versus a proven 60 m
optimum; `fifo-wave` was 60 m versus a proven 40 m optimum. The other six were
already at their volume bound. This is evidence of short-trace opportunities,
not evidence that a new online policy can realize them broadly.

For `repeat-00`, the baseline ends at 60 m on the pressure suffix and 20 m on
the light suffix; exact optima are 40 m and 20 m. But all 24 legal shared-prefix
states under the 20 m cap were enumerated: 20 can reach both suffix optima.
The actual baseline prefix state is among them. Thus this pair does **not**
prove an online impossibility or require voluntary growth at the shared prefix.
The baseline's pressure result is a fixed-continuation failure. From its same
prefix state, a legal continuation reaches 40 m: after deleting PID 5, excavate
one section and place the 14 m pipe at 23; after deleting PID 7, place the 7 m
pipe at 16. The final 1 m pipe fits at 0. The exact replies are stored in and
replayed from `prefix-intersection.json`.

The 32-pair `paired-v1` suite holds the first 12 commands exactly fixed and
changes only the suffix. It is an ambiguity/control set, not a lower-bound
proof. `paired-v2` deliberately adds a synthetic cue: one warmup repeats an
ordered size motif and the other swaps two sizes. In 10 selected pairs (20
cases), the baseline was at the bound on all light controls; 4 pressure cases
were 20 m above their exact bound. Because that cue was designed into the
generator, this is only a mechanism check, not evidence of a matching signal
in contest data or of generalization.

All generated traces are new synthetic sequences; no Open15 or Validation
input was copied, opened, or evaluated. The native evaluator runs were local
synthetic-only diagnostics. The frozen/canonical solver, evaluator, old runs,
Validation and the platform were not modified or accessed.

## Artifact map

- `bounded_oracle.py` — exact bounded integer-placement oracle and trace generator.
- `prefix_intersection.py` — exact common-prefix/optimal-continuation check.
- `suite-v1b/`, `paired-v1/`, `paired-v2/` — inputs, traces and generation manifests.
- `oracle-v1/`, `paired-oracle-v1/`, `paired-oracle-v2/`, `paired-pair00/` — exact reports.
- `eval-v1b/`, `paired-eval-result-00/`, `paired-eval-result-v2/` — official native checker manifests and outputs.

Replay audit: all 138 report rows claim proven optimality; all 62 emitted oracle
witnesses and all 138 known-feasible witnesses replay to their recorded trench
lengths. The deliberately capped self-check returns `unknown`. No solver policy
was changed or proposed on this evidence alone.
