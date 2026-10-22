# Joint public-prefix audit

Audited the current joint placement table against the G5420 cache32 parent and the 15 public inputs. No fresh or holdout inputs/outputs were read, and no solver was edited or executed.

Candidate SHA-256: `cd8e72220ac015bc7c2321c11c65a3b556e7b3e8b78907156cc1a732cc086801`; parent SHA-256: `a843822451c2a7c5e07330daa33268fc77bccfbc08fd196bfaf98a673ae24cfe`. The joint build manifest matches both source hashes.

All 280,156 public command prefixes were compared. Candidate T never exceeds the G5420 parent at any prefix; all 15 final T values equal their volume lower bounds.

| Open case | Parent final T | Candidate final T | Lower bound | Prefixes checked | Prefixes improved | Max saving |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 20 | 20 | 20 | 6 | 0 | 0 |
| 2 | 20 | 20 | 20 | 18 | 0 | 0 |
| 3 | 20 | 20 | 20 | 12 | 0 | 0 |
| 4 | 60 | 60 | 60 | 20 | 0 | 0 |
| 5 | 53360 | 53360 | 53360 | 7520 | 0 | 0 |
| 6 | 20 | 20 | 20 | 11 | 0 | 0 |
| 7 | 1680 | 1680 | 1680 | 312 | 0 | 0 |
| 8 | 4640 | 4640 | 4640 | 6565 | 24 | 1820 |
| 9 | 47500 | 47500 | 47500 | 9000 | 0 | 0 |
| 10 | 15380 | 15380 | 15380 | 9997 | 0 | 0 |
| 11 | 20760 | 20760 | 20760 | 9999 | 1981 | 620 |
| 12 | 10260 | 10260 | 10260 | 1501 | 0 | 0 |
| 13 | 3220 | 3220 | 3220 | 9999 | 90 | 220 |
| 14 | 37720 | 37720 | 37720 | 25196 | 0 | 0 |
| 15 | 418780 | 418780 | 418780 | 200000 | 81 | 31220 |

Shared-prefix audit checked all 105 pairs of public cases (14 have a nonempty command prefix, longest 4999 commands). Every allocation in each common prefix has the same coordinate in both tables.

Independent byte-occupancy replay passed all 15 inputs: no live overlap, invalid deletion, out-of-trench allocation, or final-volume mismatch. Candidate final T is exact in every case.

`permute.py` reads `exchange2/solution.cpp` (SHA-256 `71b7031b19a58528e6b867a008d54e3a795b79b9eb2c2911e18eead687298557`), builds 49,836 static spatial components for Open11/Open15, and emits 36,672 changed global block positions. Its per-record packing deadline is bounded by the source prefix cap, Open lower bound, and Best-Fit ratio cap; the global block-ID assertion rejects inconsistent duplicate coordinates. All 36,672 emitted positions appear unchanged in the joint table.

The recorded permuted11 audit reports max T/BF 5.125 on Open11/Open15 with exact final T. This audit independently validates the composed table's occupancy, common prefixes, and no-increase property across all Open15 cases.

The coordinator did not select this broad candidate after regression screens: known81 was reported as 5 wins / 73 ties / 3 losses and prior24 as 2 wins / 20 ties / 2 losses. This audit records public-table safety only; it does not override those selection results.

This is a static public-table audit. It does not establish hidden-test generalization or replace the official harness, target-hardware timing, or any separate frozen evaluation.
