#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
src=(HERE/'baseline/solution.cj').read_text()
assert hashlib.sha256(src.encode()).hexdigest()=='308d230d99b4bfd52838b9f0ff1086c8838c2ff3e05ea296903c78f1947b14cc'
def replace(old,new,n=1):
 global src
 assert src.count(old)==n,(old[:130],src.count(old),n)
 src=src.replace(old,new)
replace('    public var gapFreedAt = IntOrderedMap(0)','    private let gapRelease = FastIntVector()')
replace('    public var gapCohort = IntOrderedMap(0)','    private let gapOwner = FastIntVector()')
replace('    public init() { pipes.add(Pipe()) }','    public init() { pipes.add(Pipe()); gapOwner.add(0); gapRelease.add(0) }')
# Only live stable freeByStart IDs are used for these two attributes.
replace('gapCohort.value(gapCohort.find(Key(freeByStart.key(tail).a)))','gapOwner[tail]')
replace('gapCohort.value(gapCohort.find(Key(gapStart)))','gapOwner[it]',3)
replace('gapCohort.value(gapCohort.find(Key(start)))','gapOwner[it]',4)
replace('gapFreedAt.value(gapFreedAt.find(Key(start)))','gapRelease[it]',2)
replace('        gapFreedAt.eraseKey(Key(start))\n','')
replace('        gapCohort.eraseKey(Key(start))\n','')
replace('gapCohort.value(gapCohort.find(Key(previousStart)))','gapOwner[previous]')
replace('gapFreedAt.value(gapFreedAt.find(Key(previousStart)))','gapRelease[previous]')
replace('gapCohort.value(gapCohort.find(Key(itStart)))','gapOwner[it]')
replace('gapFreedAt.value(gapFreedAt.find(Key(itStart)))','gapRelease[it]')
replace('        freeByStart.put(Key(mergedStart), mergedEnd)','''        let added = freeByStart.put(Key(mergedStart), mergedEnd)
        while (gapOwner.size <= added) { gapOwner.add(0); gapRelease.add(0) }
        gapOwner[added] = mergedCohort
        gapRelease[added] = mergedFreedAt''')
replace('        gapFreedAt.put(Key(mergedStart), mergedFreedAt)\n','')
replace('        gapCohort.put(Key(mergedStart), mergedCohort)\n','')
replace('''        if (it != freeByStart.first()) {
            let previous = freeByStart.prev(it)
            if (freeByStart.value(previous) >= mergedStart) {''','''        let previous = freeByStart.prev(it)
        if (previous != 0) {
            if (freeByStart.value(previous) >= mergedStart) {''')
replace('''                eraseGap(previous)
                it = freeByStart.lower(Key(mergedStart))''','''                eraseGap(previous)
                // it is the preserved stable ID of the immediate successor.''')
# Compute upper bound once in the high-side group branch, at its original point.
replace('''            if (confidentRecentAddress) { candidate = gaps.prev(gaps.upper(Key(gaps.key(candidate).a, Int64.Max))) }
            let gapLength = gaps.key(candidate).a''','''            var nextGroup: Int64 = 0
            if (confidentRecentAddress) {
                nextGroup = gaps.upper(Key(gaps.key(candidate).a, Int64.Max))
                candidate = gaps.prev(nextGroup)
            }
            let gapLength = gaps.key(candidate).a''')
replace('''            candidate = gaps.upper(Key(gapLength, Int64.Max))
        }
        let historySize''','''            candidate = if (confidentRecentAddress) { nextGroup } else { gaps.upper(Key(gapLength, Int64.Max)) }
        }
        let historySize''')
start=src.index('public class Allocator {')
a,b=src[:start],src[start:]
old='''        if (recentLengths.size < kSameLengthRightRun) { return false }
        for (seen in 0..kSameLengthRightRun) { if (recentLengths.get(recentLengths.size - 1 - seen) != length) { return false } }
        return true'''
assert b.count(old)==1
b=b.replace(old,'''        return recentLengths.size >= kSameLengthRightRun &&
            recentLengths.runLength(0) == length && recentLengths.runCount(0) >= kSameLengthRightRun''')
# Reuse exactly the same predicate result without mutating length history.
old='''else { length <= kRightEdgeMaxPipeLength || hasSameLengthRecentRun(length) }'''
assert b.count(old)==1
b=b.replace(old,'''else { length <= kRightEdgeMaxPipeLength || sameSizeRun }''')
src=a+b
replace('    public var primalRecentDeletes: Int64 = 0','    public var primalRecentDeletes: Int64 = 0\n    private var primalRecentDemandTotal: Int64 = 0')
replace('''        if (old > 0) {
            primalRecentRequests[old]--''','''        if (old > 0) {
            primalRecentDemandTotal--
            primalRecentRequests[old]--''')
replace('''            primalRecentRequests[event]++
        } else if (event < 0)''','''            primalRecentRequests[event]++
            primalRecentDemandTotal++
        } else if (event < 0)''')
replace('''        for (length in 1..primalRecentRequests.size) { if (primalRecentRequests[length] > 0) { return true } }
        return false''','''        return primalRecentDemandTotal > 0''')
assert 'gapFreedAt' not in src and 'gapCohort' not in src
out=HERE/'candidate-metadata';out.mkdir(exist_ok=True);(out/'solution.cj').write_text(src)
(out/'source.json').write_text(json.dumps(dict(base_sha256=hashlib.sha256((HERE/'baseline/solution.cj').read_bytes()).hexdigest(),source_sha256=hashlib.sha256(src.encode()).hexdigest(),changes=['Two auxiliary attribute AVL maps replaced by stable freeByStart node ID side vectors; reused ID metadata overwritten on every put.','Eliminate first() and duplicate lower() in predecessor gap merge; stable successor ID retained.','Reuse identical group upper lookup.','Use exact cached last run and reuse sameSizeRun without history changes.','Maintain exact positive primal event count.']),indent=2)+'\n')
print(out)
