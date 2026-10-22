# Public-only left-move repair search

Source SHA-256: `a843822451c2a7c5e07330daa33268fc77bccfbc08fd196bfaf98a673ae24cfe`.
Search used 75.325 CPU seconds; 15 monotone left move(s) were accepted.

Open11 op2 T/BF: 240/20 = 12 before; 20/20 = 1 after.
Open8 op402 T/BF: 3260/540 = 6.03704 before; 3260/540 = 6.03704 after.

All 15 Open ceilings remain exact: **True**. Independent byte-occupancy and all-pairs shared-prefix audits passed.

## Accepted moves

| Block | Length | Old x | New x | Source risk witness |
|---:|---:|---:|---:|---|
| 21532 | 2 | 229 | 3 | Open11 op2: 240/20 (12) |
| 5284 | 20 | 272 | 50 | Open8 op7: 300/80 (3.75) |
| 5321 | 6 | 799 | 44 | Open8 op67: 820/260 (3.15385) |
| 5343 | 7 | 799 | 70 | Open8 op109: 820/260 (3.15385) |
| 5288 | 5 | 416 | 77 | Open8 op11: 440/140 (3.14286) |
| 5287 | 5 | 341 | 82 | Open8 op10: 360/120 (3) |
| 5407 | 9 | 838 | 87 | Open8 op233: 860/300 (2.86667) |
| 5418 | 10 | 838 | 87 | Open8 op255: 860/300 (2.86667) |
| 5443 | 11 | 879 | 87 | Open8 op303: 900/320 (2.8125) |
| 29991 | 10 | 2724 | 44 | Open13 op2003: 2740/1000 (2.74) |
| 29999 | 10 | 2734 | 54 | Open13 op2017: 2760/1020 (2.70588) |
| 5468 | 12 | 879 | 87 | Open8 op352: 900/340 (2.64706) |
| 5293 | 5 | 562 | 44 | Open8 op17: 580/220 (2.63636) |
| 5291 | 14 | 480 | 87 | Open8 op14: 500/200 (2.5) |
| 29553 | 15 | 1821 | 44 | Open13 op1154: 1840/740 (2.48649) |

## Scope

The helper reads only the 15 public inputs, the G5420 cache32 table source, `joint.json`, and the existing causal Best-Fit probe. It does not modify a solver or inspect fresh/holdout streams. Each proposed block position is shared across every public occurrence of that block. A left shift cannot raise any public prefix endpoint; exact lower-bound ceilings plus independent occupancy validation establish that the Open15 score is unchanged for this candidate.

This coordinate-wise search does not solve coordinated moves when every position left of a target is blocked by current co-live blocks. Such cases require a bounded multi-block repair set.

Artifacts: `changes.json`, `provenance.json`, and `report.json`.
