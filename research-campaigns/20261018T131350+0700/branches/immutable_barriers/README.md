# Immutable survivor barrier lower bound

`verify_bound.py` independently replays the first 100,000 commands and saved
baseline replies from the completed local Open15 evaluation, then uses EOF PID
labels from that same trace. It does not run the solver or checker. Provenance
is pinned through the evaluation manifest: baseline source, compiled binary,
input, summary, and output paths/hashes are checked before the arithmetic.

At the prefix, trench length is 241,380 m and 60,380 pipes are live. At EOF,
60,510 pipes survive; 51,606 of them were already live at the prefix and their
positions therefore cannot move. Excluding the tail after the last such
survivor, the gaps shorter than 8 m sum to 14,962 m. Only 1 m of new final-pipe
volume is in pipes shorter than 8 m, so at least 14,961 m of these gaps remains
empty. The final live-pipe volume is 418,757 m. Thus

```text
T >= 418757 + 14961 = 433718 m
T is a multiple of 20 m, so T >= 433720 m.
```

The saved baseline uses 438,640 m, leaving at most 4,920 m of savings after
this exact prefix if its surviving EOF pipes remain fixed. The corresponding
whole-table ceiling is 30.18258324945119 for that fixed prefix, using the
existing scores on the other cases.

This is a hindsight bound: it uses future EOF survivor labels and is conditional
on the baseline's first-100,000-operation placement. It is not an unconditional
offline optimum, an online guarantee, a hidden-test estimate, or evidence that a
policy can realize the ceiling. Full independently replayed fields are in
`independent_replay.json`.
