# Generational regions: hypothesis and screen plan

## Hypothesis

Allocations born in the same bounded PID window may share deletion timing. If a same-window free span can satisfy a request, prefer that span before the baseline's global best-fit choice. This can keep holes formed by one birth wave reusable by later members of that wave and can make a set of co-born pipes release adjacent space. The rule is opportunistic: when the current birth window has no fitting span, preserve the baseline's global choice and tail-growth behavior exactly.

The window is based only on the online insertion ordinal/PID. No test ID, trace fingerprint, future command, predicted shift index, or offline age label is used. Pipe lengths remain exact integers. Existing immobility and immediate coalescing remain unchanged. Existing size-parity routing remains the inner policy: region-local choice first seeks its preferred parity cohort, then its shared gaps; if no such region-local fit exists, ordinary baseline global best-fit runs.

This differs from the existing size-parity cohort and `cohortSlab`: those route a detected size/deletion pattern or reserve one predicted same-size run. This design routes every ordinary placement by bounded birth-time windows and never predicts a future size or deletion pattern. It also differs from buddy, harmonic classes, and fixed size arenas: it creates no power-of-two or length-class partition and leaves all free space eligible to the old global fallback.

## Complexity

Keep a size/start ordered index per region and per existing size-cohort bucket. A region lookup uses lower_bound and the baseline's gap score; insert, split, merge, and erase update the indexes in O(log G), where G is the number of free spans. No per-placement scan of all gaps is needed. Region metadata is one integer per pipe and per free span.

## Risks and falsifiers

- Deletion timing may not correlate strongly enough with fixed PID windows.
- Global fallback may mix birth groups quickly, leaving too few region-owned fitting spans to matter.
- A small window may churn and a large window may rarely contain reusable spans before it closes.
- The baseline's other routing, including `cohortSlab`, may bypass or dominate the new rule.
- Open15 case 15 can improve while total weighted score regresses; only the full Open15 score decides whether a screen candidate merits further attention.

Falsify the case-15 mechanism if window-size variants do not lower case-15 trench length versus 438,640 m, or if apparent improvement comes from violating placement validity/runtime/resource constraints. Screen three windows (512, 2,048, 8,192 insertions) on Open15 test 15 only. Run the full Open15 suite only for a correct case-15 improvement.
