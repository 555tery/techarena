# Sealed fresh evaluation set

This directory contains fixed-seed public-prefix continuations for a one-time paired evaluation. The generator reads only `data/pipes/open/`; it does not read candidates, solver outputs, or prior fresh sets. Use only after freezing a single candidate. These are fresh seeds of known mechanisms, not samples from the hidden distribution.

The `.in` files use the local harness format: weight `1`, declared operation count, then commands. The generator checks PID validity and positive final live volume without running any solver.
