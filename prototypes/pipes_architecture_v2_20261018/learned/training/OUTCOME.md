# Training outcome and frozen status

Exactly408 complete simulator episodes executed:24 BF controls and384 full own-policy trajectories. The first process attempt stopped in file loading before any episode because it expected interactive command format rather than fixture weight,n,commands; its log and pre-repair source hashes remain in `failed_loader*`. Only the input parser was repaired. The second process completed the predeclared recipe; observed process wall time1.057s.

Actor activation over own-policy training episodes:530,336 placements;132,752 eligible actor decisions;99,727 changed actions (18.80% of placements,75.12% of decisions);26,079 interior and25,459 tail choices. Thus this was not a no-op. All408 episode records passed state/action legality checks.

Each generation's best population member remained below its six-input BF control average. Generation8 best paired delta was−0.00007373184436 F/T; rotating inputs prevent interpreting generation-to-generation numbers as a held-out learning curve. No training-result improvement claim is made. Generation4 and8 CEM means are frozen for the coordinator's independent dev selection.

Tiny32-command fixtures verify independent interval legality, zero actor/control action identity, embedded-header/native-weight action parity, and shared-prefix causality.256 independent Python/C++ scorer rows agree to2.22e−16. Runtime/RSS at200,000 commands and official protocol legality are for the coordinator's checker, not established by compilation or these tiny tests.

No dev, final or official inputs/transcripts were read by this implementation agent; no official candidate evaluations were executed here. No checkpoint or threshold adjustment after dev is authorized by this recipe.
