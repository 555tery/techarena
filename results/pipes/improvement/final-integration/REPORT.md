# Canonical T46 integration report

## Frozen source and build

The requested frozen candidate was hash-checked before copying. Frozen source and canonical `src/pipes.cpp` both have SHA-256 `526ba58e955476105418593ebf0b3ef213dc4fe06fa601533e0aaf512a1dfec8`. The strict C++20 build succeeded with `-Wall -Wextra -Wconversion -Wshadow -pedantic -Werror`; canonical binary SHA-256 is `b4b50a560216d607bcecb9b2584b80967233b79346fee56a8b94ca627ba4bb84`.

## Fresh official open run

Canonical T46 passed **15/15** open tests and scored **29.447164543483/32.1**. A fresh run of the S50 reference binary on the same inputs and interactor scored **28.939458940265/32.1**. The T46 improvement is **+0.507705603218** weighted points. Input hashes match case-by-case between both runs and all weights are identical.

T46 resource measurements: CPU sum/max **1.432275/1.055035 s**, maximum RSS **5.062 MiB**, harness wall sum/max **11.853/7.978 s**. The S50 reference run measured CPU sum/max **1.422812/0.983933 s**, maximum RSS **5.469 MiB**, harness wall sum/max **10.777/7.440 s**.

The algorithm uses W=2048 and S=60. For the selected free interval it places lengths up to 4 m at the right endpoint. A longer current pipe also uses the right endpoint when the last 46 positive placement lengths all equal the current length; otherwise it uses the left endpoint. Deletions do not reset this insertion-history run.

T46 was the best candidate in the checked sweep. This is not a proof of global optimality. Closed-test performance was **not measured**.

## Per-case results

The full per-case KPI, occupied length, trench length, input hash, and weighted delta to S50 are in [per_case_vs_s50.csv](per_case_vs_s50.csv). Full raw harness outputs are retained in [t46_fresh](t46_fresh/) and [s50_fresh](s50_fresh/); `verification.json` contains source, binary, interactor, input hashes and exact commands.

## Reproduction

```sh
g++ -O2 -std=c++20 -Wall -Wextra -Wconversion -Wshadow -pedantic -Werror src/pipes.cpp -o results/pipes/improvement/final-integration/pipes_t46_canonical
python3 tools/pipes_harness.py --solver results/pipes/improvement/final-integration/pipes_t46_canonical --name t46_canonical --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/final-integration/t46_fresh --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
python3 tools/pipes_harness.py --solver results/pipes/improvement/strategies/binaries/canonical_recent_unfit_s50_cxx20 --name s50_reference --interactor tools/interactor --tests data/pipes/open --out results/pipes/improvement/final-integration/s50_fresh --cpu-limit 5 --memory-limit-mb 256 --wall-timeout 120
```
