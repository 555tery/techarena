# Case 15: birth-time survival diagnostics

## Scope

Read-only replay of the public case-15 request trace (`15.in`, SHA-256 `0b37a067bbe01429414ba20096e0a30fc9c424f7f364d101f71c32b85fe3a353`). It covers 200,000 request operations and 130,255 allocation births. No solver was run for this diagnostic; no Validation/holdout data or platform was accessed. Baseline identity: `solution.cpp` SHA-256 `c19945111834e5969e2f58f0b6503851b35e7642a9bd77f9f70c118ee3bb736c`.

The script uses only birth-time features for grouping: requested length, current position in a consecutive positive-request run, immediately preceding operation, and PID distance from the most recent deletion. Deletion outcomes are retrospective labels. A full-trace operation quartile is used only to expose nonstationarity; it is not proposed as a policy rule. Completed-run first/middle/last labels use future operations and are explicitly hindsight-only. Allocations still alive at EOF are right-censored, so `deleted by EOF` is not a lifetime estimate. Fixed-horizon probabilities include only births with the full follow-up horizon remaining.

## Main results

Overall, 69,745/130,255 births (53.5%) are deleted before EOF. Deletion within the next 20,000 operations is 53,143/120,361 (44.2%); the shorter-horizon rates are 29.5% within 100, 40.2% within 1,000, and 43.1% within 5,000 operations.

| Birth length | Births | Deleted by EOF | Share of all deletions | Deleted within next 20k* |
|---|---:|---:|---:|---:|
| 1 | 11,347 | 37.3% | 6.1% | 27.3% |
| 2–3 | 23,107 | 34.7% | 11.5% | 25.6% |
| 4–7 | 45,736 | 35.7% | 23.4% | 26.4% |
| 8–15 | 12,081 | 80.6% | 14.0% | 78.5% |
| 16–31 | 24,226 | 83.2% | 28.9% | 80.5% |
| 32+ | 13,758 | 81.9% | 16.1% | 79.7% |

\* Denominator is births with at least 20,000 later operations.

This very large length association is entangled with request-regime changes. Descriptive operation quartiles contain 40,156 births in Q1, 40,034 in Q2, 24,969 in Q3, and 25,096 in Q4. Q1–Q2 are overwhelmingly small requests; Q3–Q4 are overwhelmingly 8+ requests. Eventual deletion by EOF is 27.1%, 44.2%, 89.3%, and 75.2%, respectively. Even at the same length, deletion differs substantially between Q1 and Q2 (e.g. length 4–7: 24.8% vs 28.1% within 20k), while Q3 vs Q4 also differs (e.g. length 16–31: 82.8% vs 76.5%). This warns against treating pooled deletion rates as a stable lifetime law.

The proposed transient/survivor proxies add little after coarse birth-time and length conditioning:

- **Consecutive-insert position:** pooled, position 1 has 56.4% deletion within 20k and position 8+ has 26.8%, but these groups have different size/regime composition. Within length and operation quartile, the large cells are mostly flat and non-monotone. For length 4–7, position buckets vary by about 1–3 percentage points within Q1/Q2; for length 16–31, by about 1–4 points within Q3/Q4. The apparent global signal is therefore mostly a regime mixture.
- **Previous operation:** pooled `delete` births have 56.4% deletion within 20k vs 38.9% after `insert`, but within length × quartile the gap is typically 0–2 points. It is not a reliable independent cue here.
- **Distance from last deleted PID:** pooled distance 65+ looks much riskier (65.0% within 20k) than the 5–16 bin (34.6%), but this strongly tracks where the trace is in its size regime. Within length × quartile, rates show no stable monotone ordering; most well-populated bins differ only by a few points.
- **Completed-run position:** singleton/first/middle/last can be summarized retrospectively, but completion of the run is not known at birth, so it cannot support an online birth-time policy.

## Interpretation

Among these candidate birth-time cues, requested length is the only strong signal, and its predictive value is not stationary across this one trace. Consecutive-insert streak, previous operation, and distance to the most recently deleted PID do not provide a robust extra discriminator once coarse trace regime and length are controlled. This does not prove that every dynamic cue is useless; it means these specific cues do not presently justify a solver rule. A next hypothesis should use an online estimate of the changing request-size mix or a structural allocator mechanism, then be tested on fresh synthetic streams before screening Open15 again.

The operation-quartile splits, deletion outcomes, and completed-run labels are retrospective diagnostics for this trace only. No exact operation/PID boundary or Open15 fingerprint is proposed for production.

## Reproduction

```sh
/Users/555tery/techarena/shinka-pipes/.venv/bin/python -B \
  /Users/555tery/techarena/research-campaigns/20261018T131350+0700/branches/case15/birth_survival_diagnostic.py
```

Machine-readable tables: [`birth-survival-diagnostic.json`](birth-survival-diagnostic.json). Provenance and screened-variant records: [`branch-manifest.json`](branch-manifest.json).
