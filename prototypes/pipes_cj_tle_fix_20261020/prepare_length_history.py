#!/usr/bin/env python3
"""Prepare exact cached last-three-run queries; no Cangjie compile/solver run."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'candidate-key-search/solution.cj'
OUT = HERE / 'candidate-length-history'
BASE_SHA256 = '86fece6427f0a240b37cc6520ce3662b4cebf0839a8b4d95f7cfd3ff76e345db'
original = BASE.read_text()
assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA256
source = original

HISTORY = '''// The ring stores the exact current window. Scalar counters retain the
// full last three pushed runs; runCount clips them to the current suffix size.
public class LengthHistory {
    private let zero: Int64
    private var data: IntRing
    private var length0: Int64 = 0
    private var length1: Int64 = 0
    private var length2: Int64 = 0
    private var count0: Int64 = 0
    private var count1: Int64 = 0
    private var count2: Int64 = 0

    public init(defaultValue: Int64) { zero = defaultValue; data = IntRing(defaultValue) }
    public prop size: Int64 { get() { data.size } }
    public func get(index: Int64): Int64 { data.get(index) }
    public func back(): Int64 { data.back() }

    public func runLength(index: Int64): Int64 {
        if (index == 0) { return length0 }
        if (index == 1) { return length1 }
        if (index == 2) { return length2 }
        throw IndexOutOfBoundsException("Length run index")
    }

    public func runCount(index: Int64): Int64 {
        let newest = iMin(count0, data.size)
        if (index == 0) { return newest }
        let second = iMin(count1, data.size - newest)
        if (index == 1) { return second }
        if (index == 2) { return iMin(count2, data.size - newest - second) }
        throw IndexOutOfBoundsException("Length run index")
    }

    public func pushBack(value: Int64): Unit {
        // Mutate the ring first, so a failed ring expansion cannot alter cache.
        data.pushBack(value)
        if (data.size == 1) {
            length0 = value; count0 = 1
            length1 = 0; count1 = 0; length2 = 0; count2 = 0
        } else if (value == length0) { count0++ }
        else {
            length2 = length1; count2 = count1
            length1 = length0; count1 = count0
            length0 = value; count0 = 1
        }
    }

    public func popFront(): Unit {
        data.popFront()
        // Otherwise clipping by current size handles all front deletions.
        if (data.size == 0) {
            length0 = 0; length1 = 0; length2 = 0
            count0 = 0; count1 = 0; count2 = 0
        }
    }

    // No current recentLengths callsite uses popBack. Keep exact API semantics
    // with a rare fallback scan, because removing a newest run can expose run4.
    public func popBack(): Unit {
        data.popBack()
        length0 = 0; length1 = 0; length2 = 0
        count0 = 0; count1 = 0; count2 = 0
        var index = data.size - 1
        for (run in 0..3) {
            if (index < 0) { break }
            let value = data.get(index)
            var count: Int64 = 0
            while (index >= 0 && data.get(index) == value) { count++; index-- }
            if (run == 0) { length0 = value; count0 = count }
            else if (run == 1) { length1 = value; count1 = count }
            else { length2 = value; count2 = count }
        }
    }

    public func clone(): LengthHistory {
        let result = LengthHistory(zero)
        result.data = data.clone()
        result.length0 = length0; result.length1 = length1; result.length2 = length2
        result.count0 = count0; result.count1 = count1; result.count2 = count2
        return result
    }
}

'''

assert source.count('// Source: models.cj\n') == 1
source = source.replace('// Source: models.cj\n', HISTORY + '// Source: models.cj\n')
assert source.count('public var recentLengths = IntRing(0)') == 2
source = source.replace('public var recentLengths = IntRing(0)', 'public var recentLengths = LengthHistory(0)')
assert source.count('history: IntRing, currentLength: Int64') == 2
source = source.replace('history: IntRing, currentLength: Int64', 'history: LengthHistory, currentLength: Int64')


def method_blocks(name):
    result = []
    start = 0
    marker = '    public func ' + name + '('
    while True:
        start = source.find(marker, start)
        if start < 0: return result
        stop = source.index('\n    }', start) + 6
        result.append((start, stop, source[start:stop]))
        start = stop


for start, stop, body in reversed(method_blocks('hasSteadySizeTrend')):
    prefix = body[:body.index('        var distinctLengths')]
    new = prefix + '''        if (recentLengths.runCount(2) == 0) { return false }
        let newest = recentLengths.runLength(0)
        let previous = recentLengths.runLength(1)
        let beforePrevious = recentLengths.runLength(2)
        return newest - previous == previous - beforePrevious
    }'''
    source = source[:start] + new + source[stop:]

for start, stop, body in reversed(method_blocks('hasSmoothSizeTrendWith')):
    prefix = body[:body.index('        var priorRunLengths')]
    new = prefix + '''        let firstPrior: Int64 = if (currentRunAlreadyInHistory) { 1 } else { 0 }
        if (recentLengths.runCount(firstPrior + 1) == 0) { return false }
        let previous = recentLengths.runLength(firstPrior)
        let beforePrevious = recentLengths.runLength(firstPrior + 1)
        return currentLength - previous == previous - beforePrevious
    }'''
    source = source[:start] + new + source[stop:]

start, stop, body = method_blocks('hasLongAdditiveSizeTrend')[0]
prefix = body[:body.index('        let sizes =')]
new = prefix + '''        let firstPrior: Int64 = if (recentLengths.size > 0 && recentLengths.back() == currentLength) { 1 } else { 0 }
        if (recentLengths.runCount(firstPrior) < 46) { return false }
        if (recentLengths.runCount(firstPrior + 1) < 46) { return false }
        let previous = recentLengths.runLength(firstPrior)
        let beforePrevious = recentLengths.runLength(firstPrior + 1)
        return currentLength == previous + 1 && previous == beforePrevious + 1
    }'''
source = source[:start] + new + source[stop:]

start = source.index('public func predictNextGeometricSize(')
stop = source.index('\n}', start) + 2
body = source[start:stop]
prefix = body[:body.index('    var index =')]
tail = body[body.index('    if (!(beforePrevious < previous'):]
new = prefix + '''    if (history.runCount(2) == 0 || history.runLength(0) != currentLength ||
        history.runCount(0) < kSameLengthRightRun || history.runCount(1) < kSameLengthRightRun ||
        history.runCount(2) < kSameLengthRightRun) { return 0 }
    let previous = history.runLength(1)
    let beforePrevious = history.runLength(2)
''' + tail
source = source[:start] + new + source[stop:]

# No other IntRing client, import replay loop or deep-copy assignment changes.
assert 'recentLengths.popBack' not in original
assert source.count('recentLengths.clone()') == original.count('recentLengths.clone()') == 2
assert source.count('recentLengths.pushBack(length)') == original.count('recentLengths.pushBack(length)') == 2
assert source[source.index('func replayTable0():'):] == original[original.index('func replayTable0():'):]
for marker in ['public class IntRing', 'public class Ring<T>', 'public class OrderedMap<V>', 'public class IntOrderedMap']:
    def section(s):
        st = s.index(marker); en = s.index('\n}\n',st)+3; return s[st:en]
    assert section(source) == section(original)

OUT.mkdir(exist_ok=True)
(OUT / 'solution.cj').write_text(source)
(OUT / 'changes.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),source.splitlines(True),
                                                           fromfile='candidate-key-search/solution.cj',
                                                           tofile='candidate-length-history/solution.cj')))
(OUT / 'source.json').write_text(json.dumps({
    'baseline_sha256': hashlib.sha256(original.encode()).hexdigest(),
    'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
    'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'scope': 'Only recentLengths storage and four run-scanning predicates; related helper signature uses LengthHistory.',
    'proof': 'Last three complete pushed runs clipped by the current suffix size equal last three actual window runs. popBack rescans because it may expose an older run.',
    'clones_imports': 'Clone deep-copies IntRing and all six cache scalars. Both deep-copy/import assignments remain unchanged; imports call existing recordLength.',
    'pop_back_current_callsites': 0,
    'compile_executed': False, 'solver_executed': False,
},indent=2)+'\n')
print(OUT / 'solution.cj')
print(hashlib.sha256(source.encode()).hexdigest())
