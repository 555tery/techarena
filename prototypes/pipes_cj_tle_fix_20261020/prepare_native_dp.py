#!/usr/bin/env python3
"""Prepare Cangjie DP-only numeric malloc storage; no compile or solver run.

All allocation/free and pointer access use public std.core1.0.5 APIs. The
placement algorithm remains entirely Cangjie; no raw Array pins are used.
"""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'candidate-counts/solution.cj'
OUT = HERE / 'candidate-native-dp'
BASE_SHA256 = '85fa2c3efef59dc00a4fe59b5c346374e39549bf6a0eea0817acd1c67a7eebdf'
original = BASE.read_text()
assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA256
source = original
edits = []


def replace(old, new, count=1):
    global source
    assert source.count(old) == count, (old[:100], source.count(old), count)
    source = source.replace(old, new)
    edits.append({'old': old, 'new': new, 'occurrences': count})


BUFFER = '''// Fixed-capacity owner of stdlib malloc memory. No managed references
// are stored in its payload; Cangjie GC never relocates this C-heap memory.
// Local aliases borrow this class instance. Ownership is never copied.
public class FastFloatBuffer {
    private let data: CPointer<Float64>
    public let size: Int64

    public init(capacity: Int64) {
        if (capacity <= 0) { throw IllegalArgumentException("Invalid numeric buffer capacity") }
        this.size = capacity
        this.data = LibC.malloc<Float64>(count: capacity)
        if (data.isNull()) { throw IllegalMemoryException("Numeric buffer allocation failed") }
        unsafe {
            for (i in 0..capacity) { data.write(i, 0.0) }
        }
    }

    // Official1.0.5 finalizer syntax. No instance method calls, allocation,
    // synchronization or potentially throwing arithmetic in this body.
    ~init() {
        unsafe { LibC.free(data) }
    }

    public operator func [](index: Int64): Float64 {
        if (index < 0 || index >= size) { throw IndexOutOfBoundsException("Numeric buffer index") }
        return unsafe { data.read(index) }
    }

    public operator func [](index: Int64, value!: Float64): Unit {
        if (index < 0 || index >= size) { throw IndexOutOfBoundsException("Numeric buffer index") }
        unsafe { data.write(index, value) }
    }

    public func fill(value: Float64): Unit {
        unsafe {
            for (i in 0..size) { data.write(i, value) }
        }
    }

    public func copyFrom(other: FastFloatBuffer): Unit {
        if (other.size != size) { throw IllegalArgumentException("Numeric buffer copy size") }
        unsafe {
            for (i in 0..size) { data.write(i, other.data.read(i)) }
        }
    }
}

'''

# Private let owning fields prevent accidental replacement/alias assignment.
# Every Allocator constructs exactly these six independent buffers once.
replace('// Source: allocator.cj\n', BUFFER + '// Source: allocator.cj\n')
replace('    public var primalGapValue = VArray<Float64, $513>(repeat: 0.0)',
        '    private let primalGapValue = FastFloatBuffer(513)')
replace('    public var causalRequestRate = VArray<Float64, $41>(repeat: 0.0)',
        '    private let causalRequestRate = FastFloatBuffer(41)')
replace('    public var causalGapValue = VArray<Float64, $1026>(repeat: 0.0)',
        '    private let causalGapValue = FastFloatBuffer(1026)\n'
        '    private let dpRateScratch = FastFloatBuffer(41)\n'
        '    private let dpRewardScratch = FastFloatBuffer(41)\n'
        '    private let dpValueScratch = FastFloatBuffer(513)')


def rewrite_method(name, transform):
    global source
    start = source.index(f'    public func {name}(')
    stop = source.index('\n    }', start) + len('\n    }')
    old = source[start:stop]
    new = transform(old)
    assert new != old
    source = source[:start] + new + source[stop:]


def primal(body):
    assert body.count('var rate = VArray<Float64, $41>(repeat: 0.0)') == 1
    assert body.count('var reward = VArray<Float64, $41>(repeat: 0.0)') == 1
    assert body.count('var value = VArray<Float64, $513>(repeat: 0.0)') == 1
    body = body.replace('        var rate = VArray<Float64, $41>(repeat: 0.0)',
                        '        let rate = dpRateScratch\n'
                        '        rate.fill(0.0)')
    body = body.replace('        var value = VArray<Float64, $513>(repeat: 0.0)',
                        '        let value = dpValueScratch\n'
                        '        value.fill(0.0)')
    body = body.replace('            var reward = VArray<Float64, $41>(repeat: 0.0)',
                        '            let reward = dpRewardScratch\n'
                        '            reward.fill(0.0)')
    body = body.replace('        primalGapValue = value', '        primalGapValue.copyFrom(value)')
    body = body.replace('        causalRequestRate = rate', '        causalRequestRate.copyFrom(rate)')
    return body


def causal(body):
    assert body.count('var value = VArray<Float64, $513>(repeat: 0.0)') == 1
    assert body.count('var reward = VArray<Float64, $41>(repeat: 0.0)') == 1
    assert body.count('        var gapValues = causalGapValue') == 1
    assert body.count('        causalGapValue = gapValues') == 1
    body = body.replace('        var gapValues = causalGapValue',
                        '        let gapValues = causalGapValue\n'
                        '        gapValues.fill(0.0)')
    body = body.replace('            var value = VArray<Float64, $513>(repeat: 0.0)',
                        '            let value = dpValueScratch\n'
                        '            value.fill(0.0)')
    body = body.replace('                var reward = VArray<Float64, $41>(repeat: 0.0)',
                        '                let reward = dpRewardScratch\n'
                        '                reward.fill(0.0)')
    # gapValues is a local non-owning alias of its one persistent buffer.
    # Each row still writes all513 entries, including its zero tail.
    body = body.replace('        causalGapValue = gapValues\n', '')
    return body


rewrite_method('rebuildPrimalGapValues', primal)
rewrite_method('rebuildCausalGapValues', causal)

# Scope checks; constructors/fill/copyFrom change storage only. No FP expression
# or comparison in the numerical recurrence is rewritten by this preparer.
assert source.count('= FastFloatBuffer(') == 6
assert source.count('LibC.malloc<Float64>') == 1
assert source.count('LibC.free(data)') == 1
assert source.count('dpRateScratch') == 2
assert source.count('dpRewardScratch') == 3
assert source.count('dpValueScratch') == 3
assert source[source.index('func replayTable0():'):] == original[original.index('func replayTable0():'):]
assert source.count('acquireArrayRawData') == original.count('acquireArrayRawData')
for marker in ['public class OrderedMap<', 'public class IntOrderedMap', 'public class Ring<', 'public class IntRing']:
    def section(text):
        start = text.index(marker)
        stop = text.index('\n}\n', start) + 3
        return text[start:stop]
    assert section(source) == section(original)

OUT.mkdir(exist_ok=True)
target = OUT / 'solution.cj'
target.write_text(source)
rt = 'https://github.com/cangjielanguage/cangjie_runtime/blob/c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9/'
docs = 'https://github.com/cangjielanguage/cangjie_docs/blob/f8f8cd75a336e23785a4c57bd6091b2adf1e0302/'
metadata = {
    'baseline': str(BASE.relative_to(HERE)),
    'baseline_sha256': hashlib.sha256(original.encode()).hexdigest(),
    'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
    'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'changes': edits,
    'allocations_per_allocator': {'persistent': [513, 41, 1026], 'scratch': [41, 41, 513],
                                  'count': 6, 'payload_bytes': 17400, 'rebuild_allocations': 0},
    'ownership': [
        'Each of six private let fields owns a distinct FastFloatBuffer class instance and its one malloc allocation.',
        'The CPointer is private and never returned; no buffer clone exists and no owning field is assigned another buffer.',
        'Local bindings are non-owning class aliases keeping their owner reachable while operating.',
        'Primal commit copies payload into persistent primalGapValue and causalRequestRate; scratch is never aliased as a persistent table.',
        'Causal rows are written directly to the one persistent causalGapValue; no callback observes intermediate state.',
        'Same scratch buffers are reused sequentially; these DP methods are neither concurrent nor reentrant in the existing solver.',
        'Each FastFloatBuffer finalizer releases its allocation via stdlib LibC.free once. Finalizer timing is unspecified and is never used for synchronization.',
        'If allocation fails constructor throws before any owned non-null allocation; zero initialization has no expected throwing path for these fixed positive capacities.',
    ],
    'official_105_sources': {'malloc_free': rt+'std/libs/std/core/libc.cj#L37-L51',
                            'pointer_read_write': rt+'std/libs/std/core/c_pointer_resource.cj#L48-L65',
                            'operator_syntax': rt+'std/libs/std/core/array.cj#L108-L131',
                            'finalizer': docs+'docs/dev-guide/source_zh_cn/class_and_interface/class.md#class-终结器'},
    'fp_policy': 'All recurrence FP expressions, operation order, iteration order and thresholds preserved. Added fill/copy operations only write identical Float64 values; they perform no FP arithmetic.',
    'caveats': ['Not compiled or executed, as requested.',
                'Bounds checks and Cangjie method/intrinsic overhead remain; performance is unmeasured.',
                'Native payload memory is outside managed heap accounting;17400bytes per Allocator until its six owners finalize.',
                'Finalizers may run on arbitrary threads at unspecified times, so only stdlib free occurs there.',
                'Changing unreachable finalizer timing is a resource behavior change, not a placement-policy change.'],
    'compile_executed': False, 'solver_executed': False,
}
(OUT / 'source.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
(OUT / 'changes.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), source.splitlines(True),
                                                           fromfile='candidate-counts/solution.cj',
                                                           tofile='candidate-native-dp/solution.cj')))
print(target)
print(metadata['source_sha256'])
