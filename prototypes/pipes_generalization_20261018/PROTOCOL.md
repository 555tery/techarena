# Independent mechanism-shift comparison, 2026-10-18

Direct user authorization: compare trial22, BF and SS on new mechanisms with
regime shifts and early termination. GPT-6.1 Sol implements the two baselines
and a separately isolated generator; the coordinator audits and evaluates.
This is a bounded local comparison. No platform reads or submissions, no old
Shinka or autonomous campaign restart, no old validation or release-seed reuse.

## Fixed algorithms

- trial22: unchanged source SHA256
  `988927c690b4034f3a26c839ee00bc2c0d0956e6ea9f5b6369c9d45e961242e4`.
- BF: smallest fitting coalesced physical gap, then lowest start address;
  allocate at its left endpoint.
- SS: minimize exact change in `Phi=sum_h count(h)^2`, considering all fitting
  coalesced physical gaps including the free tail. Tie: smallest gap, then
  lowest start address; allocate at the left endpoint. Empty residuals are not
  gaps. Exact fill gives `-2*c[h]+1`; split gives `-2*c[h]+2*c[h-L]+2`.
- BF/SS share physical representation, coalescence, output and extension code.
  Only when no gap fits: reuse the free physical tail and dig the minimum
  number of 20 m sections. Trench length never shrinks. No forced dig, special
  small-item routing, right-edge placement or hidden reservations.

No algorithm selection, parameter fitting or threshold sweep on these inputs.
Tiny independent correctness tests precede final freeze. Any defect discovered
after final evaluation is disclosed; a repair cannot reuse this as an untouched
holdout. Both implementation tasks must avoid Open15 and previous test data.

## Data and stop roles

12 independently specified procedural mechanisms, 4 seeds/base streams each,
5 literal prefixes at 20/40/60/80/100 percent = 240 evaluated inputs. First major
shift is at 25 percent, drain/reversal at 65--75 percent; roles distinguish
pre-shift, post-shift, intermediate, post-drain/reversal and full termination.
Ten meso/long families have full lengths 12000/32000/80000/200000; two micro
families 80/160/240/400. Mechanisms and all parameters are fixed in dataset/
before fresh seeds are drawn. No rejection/resampling based on solver scores.
Do not force end occupancy near peak. Preserve low-occupancy and F=0 inputs.
The generator has no solver access. Common-prefix continuation is a sampled
mechanism, not a paired-branches causal experiment: only one branch per seed.

Freeze sources, build flags/binaries, generator, design and protocol before
generation. Seeds use fresh entropy after freeze; record seeds, hashes, phase
boundaries, stop roles, length, final/peak live volume and parameters. Root
checks legal operations, literal prefix identity, dimensions and manifests.

## Evaluation and interpretation

All three solvers use the existing official native checker, 2 workers total,
CPU <5 s and RSS <256 MiB per input. Main metric remains final F/T. The main
mean gives equal weight to families, seeds within family, and stops within
seed. Report all families and stop roles separately, paired wins/losses/ties,
worst regressions, extra trench over the peak-volume bound, and CPU/RSS.
For F=0 keep F/T=0; separately report trench inefficiency rather than deleting
the observation. H0=20*ceil(peak_live/20) is an optimistic volume bound, not an
achievable causal optimum.

Prefixes are correlated. Pair algorithms on identical inputs; cluster summaries
at the 48 base streams, with stratified bootstrap within the 12 families.
Intervals describe seed variation in these fixed constructed mechanisms, not
all hidden-test distributions. Length has one seed per family-length cell;
length-specific conclusions remain descriptive. Fresh seed alone is not proof
of a novel mechanism or of generalization to competition hidden tests.

Reserve 720 final evaluations, 12 deterministic repeats (first and last long
family at full length, first and last micro family at full length, all using
replicate 3), and at most 48 tiny official preflight evaluations: cap 800.
Verify full answer-prefix consistency for all 48 base streams and all solvers.
Any failed correctness/resource check prevents reporting its score as valid.
Keep source, input and binary hashes, commands, individual records and reports.
No automatic candidate promotion. Final findings are diagnostic, not a tuning
signal for another variant in this task.

## Stopping

Before work and at most every 30 seconds during evaluator batches, read Codex
usage without model calls. Preserve at least 65% in every available window;
null windows are unavailable, not zero. Unreliable quota or a value below 65%
stops local jobs and model work, with partial results retained. No paid API,
limit resets, unattended loops or automatic restart. Track owned processes by
PID and creation time; verify no owned workers remain at completion.
