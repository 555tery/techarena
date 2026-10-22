# Exact handoff repair

`build.py` derives `solution.cpp` from the previous fast hybrid without writing
any frozen or primary candidate. `build.json` contains hashes and all exact
replacement pairs; reversing them recovers the original source byte for byte.

Before each replay command, `livePositionDifferences==0 && physical.T==shadow.T`
tests exact physical equality. Both states consumed the same prefix, hence PID
counts, lengths and active flags agree. A replay placement increments the count
when its address differs from the shadow address. A replay deletion decrements
it if the deleted PID's addresses differed; the shadow's old start is captured
before removal. Thus deleting all differing live PIDs permits later
resynchronization. The bookkeeping is O(1) per command and needs no state scan.

On replay rejection with equality **before** the current command, the already
advanced shadow is moved into `online`. Its stored current placement answer or
the saved removal coordinate is written once, then `emit=true` enables normal
future responses. No command is executed twice. With unequal geometry the old
physical/history import is used. No gap-count equality, public test ID, address
special case, model reset, or altered allocator decision is introduced.

## Checks

`check.py` reads only the previous calibration64 + final128 (now DEV192) and
Open15. Both old hybrid and repair passed full bulk occupancy checks on all207
inputs. This is not an official interactive or resource measurement.

| Set | Wins / ties / losses vs old hybrid | Mean delta KPI |
|---|---|---:|
| calibration64 |0 /64 /0|0|
| final128 |2 /125 /1|+0.0000031051|
| Open15 |0 /15 /0|0|

Only three final trench lengths change: final105 14740→14680,
final120 28840→28820, **final090 8620→8680**. The repair preserves online state;
it is not a guarantee of improving the former import policy, whose MC reset
incidentally helped final090. Open15 weighted score is unchanged. Some other
answer sequences change while ending with the same trench.

Three small production-table cases cover placement handoff, deletion handoff,
and unequal-layout import. A fourth test uses a **separate diagnostic binary
with a tiny replacement replay table**, to cover late resynchronization:
commands4,4,-2 accept positions0,4, then delete the differing PID2; command6
rejects replay and correctly adopts the now-equal shadow. The candidate table
is untouched. All four cases passed occupancy checks; log counters confirm the
expected branch, including one late resynchronization. `crafted.json` contains
the exact commands and results.

Detailed results: `comparison.json`, compact `summary.json`. No new evaluation
inputs, platform actions, primary candidate edits, or official runs occurred.
Windows/MSVC and fresh interactive CPU/RSS remain for the coordinator.
