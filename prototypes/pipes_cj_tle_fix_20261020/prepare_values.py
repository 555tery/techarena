#!/usr/bin/env python3
"""Prepare a storage-only VArray candidate; never compile or run the solver.

Official 1.0.5 VArray documentation:
https://github.com/cangjielanguage/cangjie_docs/blob/f8f8cd75a336e23785a4c57bd6091b2adf1e0302/docs/dev-guide/source_zh_cn/basic_data_type/array.md
"""
import difflib
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'candidate-v1/solution.cj'
OUT = HERE / 'candidate-values'
BASE_SHA256 = '83e2e6852e51955e6ec05eee5cf87800c6e7e528f662336d550518cd556e10ab'
original = BASE.read_text()
assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA256
source = original
edits = []


def replace(old, new, count=1):
    global source
    actual = source.count(old)
    assert actual == count, (old[:100], actual, count)
    source = source.replace(old, new)
    edits.append({'old': old, 'new': new, 'occurrences': count})


# Pin the numeric capacities rather than trying to use a runtime expression as
# VArray's literal length. Preserve the original policy constant itself.
assert 'public let kPrimalGapValueCap: Int64 = 512' in source

replace('private let lower: Array<Int64> = [0, 16, 64, 256, 1024, 4096, 16384, 65536]',
        'private let lower: VArray<Int64, $8> = [0, 16, 64, 256, 1024, 4096, 16384, 65536]')
replace('private var cells = Array<Array<LifetimeCell>>(41, { _ => Array<LifetimeCell>(8, repeat: LifetimeCell()) })',
        'private var cells = VArray<LifetimeCell, $328>(repeat: LifetimeCell())')
replace('private var rates = Array<Array<LifetimeEstimate>>(41, { _ => Array<LifetimeEstimate>(8, repeat: LifetimeEstimate()) })',
        'private var rates = VArray<LifetimeEstimate, $328>(repeat: LifetimeEstimate())')
replace('private var nextCrossing = Array<Int64>(8, repeat: 1)',
        'private var nextCrossing = VArray<Int64, $8>(repeat: 1)')

# Flatten only this class. LifetimeCell and LifetimeEstimate contain primitive
# numeric fields, so VArray's backend restriction on reference members is met.
start = source.index('public class CensoredLifetimeModel {')
stop = source.index('// Source: allocator.cj', start)
before = source[start:stop]
after = before
index_edits = {}
for name, expected in [('cells', 10), ('rates', 2)]:
    pattern = rf'\b{name}\[([^\[\]]+)\]\[([^\[\]]+)\]'
    after, count = re.subn(pattern, lambda m: f'{name}[({m[1]}) * 8 + ({m[2]})]', after)
    assert count == expected, (name, count, expected)
    index_edits[name] = count
source = source[:start] + after + source[stop:]

for name, element, old_size, literal_size, zero in [
    ('primalGapCounts', 'Int64', 'kPrimalGapValueCap + 2', 514, '0'),
    ('primalEventHistory', 'Int64', '256', 256, '0'),
    ('primalRecentRequests', 'Int64', '41', 41, '0'),
    ('primalGapValue', 'Float64', 'kPrimalGapValueCap + 1', 513, '0.0'),
    ('causalRequestRate', 'Float64', '41', 41, '0.0'),
]:
    replace(f'public var {name} = Array<{element}>({old_size}, repeat: {zero})',
            f'public var {name} = VArray<{element}, ${literal_size}>(repeat: {zero})')

replace('public var causalGapValue = Array<Array<Float64>>(2, {_ => Array<Float64>(kPrimalGapValueCap + 1, repeat: 0.0)})',
        'public var causalGapValue = VArray<Float64, $1026>(repeat: 0.0)')
replace('        let rate = Array<Float64>(41, repeat: 0.0)',
        '        var rate = VArray<Float64, $41>(repeat: 0.0)')
replace('        primalGapValue = Array<Float64>(kPrimalGapValueCap + 1, repeat: 0.0)',
        '        primalGapValue = VArray<Float64, $513>(repeat: 0.0)')
replace('            let reward = Array<Float64>(41, repeat: 0.0)',
        '            var reward = VArray<Float64, $41>(repeat: 0.0)', count=2)
replace('            let value = Array<Float64>(kPrimalGapValueCap + 1, repeat: 0.0)',
        '            var value = VArray<Float64, $513>(repeat: 0.0)')

# Original row assignment transfers a fresh, independently allocated row.
# Copy every element, including the zero tail above maxGap. This prevents stale
# values when a later rebuild has a smaller maxGap. No FP arithmetic is added.
replace('            causalGapValue[model] = value',
        '            for (cell in 0..513) { causalGapValue[model * 513 + cell] = value[cell] }')
replace('causalGapValue[0][gap]', 'causalGapValue[gap]')
replace('causalGapValue[1][gap]', 'causalGapValue[513 + gap]')

# Aliasing audit:
# * Lifetime cells already use struct-copy/read, modify local, write back.
# * rates are only read into local structs and assigned per element.
# * rate is not mutated after causalRequestRate = rate; changing the former
#   reference assignment to a value copy preserves all observable reads.
# * DP value is not mutated after its row is committed. No outside references
#   to these private/local tables escape; none of these fields uses clone().
# * No other Array, maps, rings, replay tables or the 200001-entry Fenwick array
#   changes. Floating-point expressions, loop order and thresholds stay intact.
assert 'Array<Int64>(200001, repeat: 0)' in source
assert source[source.index('func replayTable0():'): ] == original[original.index('func replayTable0():'): ]
assert not re.search(r'VArray<[^\n]+\$200001', source)
assert 'causalRequestRate = rate' in source

OUT.mkdir(exist_ok=True)
target = OUT / 'solution.cj'
target.write_text(source)
metadata = {
    'baseline': str(BASE.relative_to(HERE)),
    'baseline_sha256': BASE_SHA256,
    'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
    'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'official_105_varray_documentation': 'https://github.com/cangjielanguage/cangjie_docs/blob/f8f8cd75a336e23785a4c57bd6091b2adf1e0302/docs/dev-guide/source_zh_cn/basic_data_type/array.md',
    'changes': edits,
    'flat_lifetime_index_changes': index_edits,
    'aliasing_review': [
        'LifetimeCell and LifetimeEstimate contain only numeric fields; existing local-copy/writeback remains.',
        'causalRequestRate = rate becomes a value copy; no later mutation of local rate exists.',
        'causalGapValue commits all 513 entries of each local value row, including the zero tail.',
        'No clone calls involve converted fields; other clone calls are untouched.',
    ],
    'policy': 'Storage-only changes; same floating-point arithmetic order, comparison thresholds and policy loops.',
    'caveats': [
        'Not compiled and not executed, as requested.',
        'VArray copying may cost time at -O0; acceleration is a hypothesis pending parent measurements.',
        'Largest VArray has1026 Float64 elements; no large200001 array conversion.',
        'Flattened row commit adds513 non-FP element copies per model, replacing reference assignment.',
    ],
    'compile_executed': False,
    'solver_executed': False,
}
(OUT / 'source.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
(OUT / 'changes.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), source.splitlines(True),
                                                           fromfile='candidate-v1/solution.cj',
                                                           tofile='candidate-values/solution.cj')))
print(target)
print(metadata['source_sha256'])
