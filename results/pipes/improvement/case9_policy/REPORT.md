# Case 9: causal alternating-deletion policy

## Scope and decision

**Promotion update (2026-10-16):** after the independent audit and final-path official reruns, this exact source (SHA-256 `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`) was copied byte-identically to `results/pipes/final/solution.cpp`. The previous corrected-MC + scoped-run and cohort-owner final sources were preserved as `solution_corrected_mc_scoped_run.cpp` and `solution_cohort_owner.cpp`. The final build and current open/holdout metrics are recorded in `results/pipes/final/README.md` and `manifest.json`.

This report records the candidate as an isolated experiment at the time of the original comparison. It did not modify `src/pipes.cpp`.

The frozen comparison baseline is the exact corrected MC plus scoped-run source `cohort_owner_mc_corrected_scoped_run.cpp`, SHA-256 `e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41` (the current `e95ed98e…` candidate). It was rebuilt locally and independently rerun with the same open and holdout inputs as the experimental candidate. The input hashes are recorded in [`manifest.json`](manifest.json), and per-case input/output hashes are in [`per_case_comparison.csv`](per_case_comparison.csv).

The new causal policy improves the 15-case open score from **29.781127111082** to **29.785293754007 / 32.1**, a reproducible **+0.004166642925**. It changes trench length only on open case 9: **62,960 → 62,440 m** (520 m saved). All other open-case trench lengths match, though case 5's raw placement transcript differs while its trench and score remain the same.

On the 12-case synthetic holdout-v2, both sources score **5.135264324280 / 12** and every case has byte-identical judge output. This is neutral holdout evidence, not evidence that the gain generalizes to other alternating-delete streams. The best-known open gain remains small relative to case 9's remaining gap to its live-volume bound.

## Policy

The solver watches deletion commands. After eight consecutive deletions of pipes with the same length and PID increments of exactly +2, it records the parity of the last removed PID. For the subsequent placement phase, it places that observed PID parity at the low edge of a selected gap and the other parity at the high edge. A later deletion whose length or PID step breaks the pattern clears the mode. This state uses only observed history and the current command; it has no test identifier, future command, file, environment, or score access.

The mechanism attempts to convert a known alternating-removal cohort into spatially grouped survivor/deletion classes, so deletions can create larger merged gaps for following pipes. It is causal, but it extrapolates one observed deletion phase to the next placement phase; the holdout does not contain a confirming gain.

## Results

| Dataset | Baseline | Candidate | Delta | Cases |
|---|---:|---:|---:|---:|
| Official open | 29.781127111082 / 32.1 | 29.785293754007 / 32.1 | +0.004166642925 | 15/15 both |
| Synthetic holdout-v2 | 5.135264324280 / 12 | 5.135264324280 / 12 | 0 | 12/12 both |
| 200,000-command stress | — | 0.746875 | — | pass |

Case 9 has **47,500 m** as its live-volume lower bound, final occupied volume **31,500 m**, and candidate trench **62,440 m**. Its maximum possible KPI using that lower bound is `31,500/47,500 = 0.663157895`; the candidate KPI is `0.504484305`. The 520 m gain raises the case KPI by **0.004166643**, so most of the headroom remains.

## Resources and build

Both baseline and candidate compile with Apple Clang 17.0.0 using `-O2 -std=c++17 -pipe -Wall -Wextra -Wconversion -Wshadow -Werror`.

The independent candidate rerun used at most **1.959576 s CPU / 9.468750 MiB RSS** across open15 and **0.391043 s / 4.203125 MiB** across holdout-v2. The 200,000-command stress run used **0.841126 s / 7.718750 MiB**, below 5 s / 256 MiB.

## Rejected bootstrap ablation

A separate exploratory version also parity-striped repeated short-length runs before observing any deletion pattern. It scored **29.7675605511 / 32.1**, below the frozen baseline/candidate comparison target of 29.7852937540. It regressed open cases 5, 7, and 11 despite improving case 9, so it was rejected; no holdout or stress run was performed. Its source/hash remain in the directory for traceability and it is not included in this candidate.

## Files

- Candidate source: [`alternating_delete_parity_edges.cpp`](alternating_delete_parity_edges.cpp), SHA-256 `57338ca2dd0d81e2c553edefb5c2c40fdb1b3aec88873709a21da6574c85560f`.
- Frozen baseline source: [`../beam_diagnosis/source/cohort_owner_mc_corrected_scoped_run.cpp`](../beam_diagnosis/source/cohort_owner_mc_corrected_scoped_run.cpp), SHA-256 `e95ed98e038aad6f46ccf62f4f167a45b2f1cc695772484d53001936c178df41`.
- Per-case KPI, trench, input hash, and judge transcript hashes: [`per_case_comparison.csv`](per_case_comparison.csv).
- Exact input/output/source/binary and summary hashes: [`manifest.json`](manifest.json).
- Independent official harness outputs: `repro-e95-open/`, `repro-e95-holdout-v2/`, `repro-current-open/`, `repro-current-holdout-v2/`.
- 200,000-command stress output: `stress-200k/`.
- The bootstrap ablation is preserved as `bootstrap_short_parity_stripe.cpp` and `bootstrap-open-15/`; it is not a candidate.

## Независимый аудит исходника

Отдельный аудитор подтвердил SHA исходника и строгую сборку Apple Clang 17.0.0 с `-O2 -std=c++20 -pipe -Wall -Wextra -Werror -pedantic`. Проверка исходника не выявила чтения файлов, `score.txt`, `argv`, environment, test ID, будущих команд, часов или внешнего RNG; live detector и его rollout-модель согласованы по состоянию и выбору края. Отдельный replay case 9 подтвердил score `0.504484304932735`, траншею `62,440 м`, CPU `0.068971 s`, RSS `3.015625 MiB`.

Ограничение модели: Monte Carlo сохраняет удаления как квантованный `rank-permille` и затем восстанавливает объект по rank в counterfactual active list. Это может дать другой PID, чем в live истории, и изменить последующее срабатывание детектора. Следовательно, rollout forecast с новым правилом может быть неточен. Подробный аудит и хеш дополнительного бинарника — в [`audit/source_audit.md`](audit/source_audit.md). Аудитор также отметил inherited malformed-input edge: `-command` overflow для `INT64_MIN`; официальные входы используют допустимые PID, так что это вне contest protocol.


## Synthetic trigger/reset check

After freezing the main comparison, I ran a narrow test of detector activation and reset with Monte Carlo disabled, so the trench comparison isolates the live causal rule. Odd-parity stride-2 deletions activated at PID 15 and reset on the length change; baseline and candidate both used 340 m. Even parity activated at PID 16; the candidate used 340 m versus baseline 360 m. In the interrupted control, PID 8 broke the first stride and only five later transitions followed; the detector stayed off and both used 180 m. The small synthetic suite shows the reset works and one parity arrangement can help, while the odd arrangement is neutral. This does not demonstrate a general gain. Exact per-case records and hashes are in [`audit/synthetic/RESULTS.md`](audit/synthetic/RESULTS.md), [`audit/synthetic/per_case_comparison.csv`](audit/synthetic/per_case_comparison.csv), and [`audit/synthetic/manifest.json`](audit/synthetic/manifest.json).
