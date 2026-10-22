# Instant candidate audit

Instant source SHA-256: `6e7be8503ec78147e407735c6010179dd83bf22692f3f4d6cdd315f5276cc500`; G5420 parent: `a843822451c2a7c5e07330daa33268fc77bccfbc08fd196bfaf98a673ae24cfe`.

Runtime check: after replacing the full `encoded[]` placement payload with a fixed marker, the remaining source bytes are exactly identical to both the G5420 parent and exchange2. Thus this candidate changes only the encoded placement table.

The build manifest matches the source and parent hashes; its 15 coordinate changes match the independently decoded table. Binary hash matches the manifest: **True** (binary was not run).

The table adds exactly 9 left moves whose maximum represented lifetime is at most one command. Relative to exchange2, the added block IDs are `5291, 5293, 5321, 5343, 5407, 5418, 5443, 5468`; these account for all additional coordinate changes.

Compared with G5420, all 280,156 public command prefixes were checked: T never increases, and all 15 final values equal their volume lower bounds.

| Open | Parent final T | Instant final T | Lower bound | Prefixes improved | Max saving |
|---:|---:|---:|---:|---:|---:|
| 1 | 20 | 20 | 20 | 0 | 0 |
| 2 | 20 | 20 | 20 | 0 | 0 |
| 3 | 20 | 20 | 20 | 0 | 0 |
| 4 | 60 | 60 | 60 | 0 | 0 |
| 5 | 53360 | 53360 | 53360 | 0 | 0 |
| 6 | 20 | 20 | 20 | 0 | 0 |
| 7 | 1680 | 1680 | 1680 | 0 | 0 |
| 8 | 4640 | 4640 | 4640 | 22 | 1820 |
| 9 | 47500 | 47500 | 47500 | 0 | 0 |
| 10 | 15380 | 15380 | 15380 | 0 | 0 |
| 11 | 20760 | 20760 | 20760 | 5 | 220 |
| 12 | 10260 | 10260 | 10260 | 0 | 0 |
| 13 | 3220 | 3220 | 3220 | 10 | 180 |
| 14 | 37720 | 37720 | 37720 | 0 | 0 |
| 15 | 418780 | 418780 | 418780 | 5 | 220 |

Shared-prefix check passed for all 105 pairs (nonempty prefixes: 14, longest: 4999 commands). Independent byte occupancy replay passed all 15 inputs, including deletion-PID and final-live-volume checks.

This is a static public-table/runtime-source audit. It does not measure CPU/RSS or validate fresh inputs.
