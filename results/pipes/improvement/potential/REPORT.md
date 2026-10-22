# Experiment 2: free-space potential

## Protocol and result

All five binaries (the T46 control, three bounded potential variants, and one literal uncapped variant) passed the official interactive harness on all 15 open inputs. The T46 control re-ran at 29.447164543483/32.1, matching the supplied baseline. All builds used `-Wall -Wextra -Wconversion -Wshadow -pedantic -Werror`. The same test hashes and weights were asserted across all reports. Candidate selection used only the official open results.

| Variant | Score / 32.1 | Delta vs T46 | OK | Max solver CPU | Max RSS |
|---|---:|---:|---:|---:|---:|
| T46 baseline | 29.447164543483 | +0.000000000000 | 15/15 | 1.007602 s | 5.828 MiB |
| V loss all gaps, cap 40, W 2048 | 28.846401673218 | -0.600762870265 | 15/15 | 0.894304 s | 5.953 MiB |
| V loss all gaps, cap 80, W 2048 | 28.839083512575 | -0.608081030908 | 15/15 | 1.012242 s | 5.938 MiB |
| V loss internal-first, cap 80, W 2048 | 28.349156266597 | -1.098008276886 | 15/15 | 1.350278 s | 5.953 MiB |
| Literal unbounded V loss, W 2048 | 28.845139569517 | -0.602024973966 | 15/15 | 0.888413 s | 5.875 MiB |

## Per-case results

The complete case table contains weighted score, KPI, trench length, solver CPU and solver RSS for every variant, plus per-case score/trench deltas against T46 and the shared input SHA-256: [per_case_comparison.csv](per_case_comparison.csv). Raw official harness outputs are in [runs](runs/), while build/run commands and binary/source/input hashes are in [manifest.json](manifest.json).

## Potential definition and scope

For each fitting gap of length `G` and current request `q`, the candidate minimizes the estimated one-step loss `V(G)-V(G-q)`, with `V(G)=Σ_L p(L) floor(G/L)`. `p(L)` is the empirical distribution of lengths among the most recent 2048 placements; the table is stored unnormalized because dividing all candidate losses by the same history size does not change their ordering. The potential table is updated on placement; deletion does not change the request distribution.

Because an uncapped `V(G)` produces residue-dependent losses even for very large gaps, the tested implementations cap the useful span at `C=40` or `C=80` (`V_C(G)=V(min(G,C))`). Thus the variants test a bounded one-step capacity proxy, not the uncapped formula. Ties go to the smaller gap, then the lower start address.

The tail-aware variant treats the expandable tail separately: if any internal gap fits, it chooses among internal gaps by potential loss; otherwise it ranks the tail by that loss. If it places in the tail, it uses the left edge so the remainder remains expandable. The all-gap variants include tail gaps in the same potential ranking and keep T46 endpoint placement.

## Interpretation

None of the three variants improved the open score. The bounded potential is a weighted average of homogeneous-length capacities. It is not the expected number of mixed-size future requests that can actually be packed, and it does not estimate how many 20 m trench sections those requests will force. The tail has an additional option value because it can expand in 20 m increments, which ordinary `V(G)` does not encode. Making that distinction explicitly performed worse here. The evidence supports a null result for this experiment as tested; it does not rule out better calibrated or multi-step cost models.

Per-case score and trench outcomes are the primary comparison; resource values remain comfortably below the 5 s / 256 MiB limits. No broad parameter sweep was run. A single literal uncapped follow-up, requested separately, is documented below.

## Reproduction

See exact commands in `manifest.json`. The baseline source is a byte-for-byte copy of `src/pipes.cpp`; canonical source was not modified.

## Secondary fixed-set diagnostic

At the coordinator’s request, the best open-set potential variant (cap=40) and T46 were also run on `data/pipes/synthetic/final-holdout-v2`. This is secondary only: prior runs of this fixed set already exist in `results/pipes/final-holdout-v2`, so it is not independent evidence and did not affect the candidate or parameter choice. Both passed 12/12. T46 scored **5.135100030340/12**; cap=40 scored **5.121299188924/12** (delta **-0.013800841416**). Max solver CPU was 0.415370 s for T46 and 0.424334 s for cap=40; max RSS was 2.359 and 2.391 MiB. Per-case score, trench and resources are in [holdout_per_case_comparison.csv](holdout_per_case_comparison.csv); raw outputs are under `runs/*_holdout/`.

## Literal uncapped follow-up

The single follow-up uses the literal `V(G)=Σ_L p(L) floor(G/L)` with no cap and the T46 endpoint rule and tie-break. `p(L)` is the normalized frequency among the last at most 2048 positive placements. The solver compares the exact integer numerator `N·(V(G)-V(G-q)) = Σ_L f(L)[floor(G/L)-floor((G-q)/L)]`; omitting division by common `N` changes no ranking. It scans fitting gap sizes in T46 order and stops only when it reaches the provable lower bound `Σ_L f(L) floor(q/L)`, so this early stop preserves the exact optimum and the size/address tie-break.

For the conservative domain `N≤2048`, `G≤100,000,000`, `q≤40`, `N·V(G)≤204,800,000,000` and `N·ΔV≤81,920`, both safely fit signed 64-bit integers. An independent formula audit checked 30,240 gap/request/distribution combinations, including the maximum trench boundary, and confirmed integer equality and the lower bound; see [literal_preflight.json](literal_preflight.json). The candidate compiled with strict warnings and passed 15/15 official open tests. It scored **28.8451395695/32.1**, **−0.602024973966** versus T46. Maximum solver CPU was 0.888413 s and RSS 5.875 MiB. Per-case score, trench, CPU, RSS and hashes are in [per_case_comparison.csv](per_case_comparison.csv); source/binary hashes and exact commands are in [manifest.json](manifest.json).

Because its open score is below T46, it was not run on the synthetic holdout, per the selection gate. No test-ID or command-position branch was used; the candidate depends only on current gaps and the empirical length history.
