#!/usr/bin/env python3
"""Direct persistent Cangjie numeric DP; prepares source only, never runs it."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'candidate-native-dp/solution.cj'
OUT = HERE / 'candidate-native-direct'
BASE_SHA256 = '6cbb4810a69dd70a1fd59f312dbd6f1502bf991bbf4d02a02f2b796d5dbf8f24'
original = BASE.read_text()
assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA256
source = original


def replace(old, new, count=1):
    global source
    assert source.count(old) == count, (old[:100], source.count(old), count)
    source = source.replace(old, new)


replace('    private let dpRateScratch = FastFloatBuffer(41)\n', '')
replace('    private let dpValueScratch = FastFloatBuffer(513)\n', '')


def rewrite_method(name, transform):
    global source
    start = source.index(f'    public func {name}(')
    stop = source.index('\n    }', start) + len('\n    }')
    old = source[start:stop]
    new = transform(old)
    assert new != old
    source = source[:start] + new + source[stop:]


def eliminate(body, rate_name):
    # A reward slot is read only if its active bit is set. Each bit is set only
    # after this gap's positive-rate branch wrote that slot. Once removed, it
    # is never inspected again. Stale inactive slots therefore need no reset.
    old = ('                    if ((active & bit) != 0 && reward[request] < estimate) {\n'
           f'                        numerator -= {rate_name}[request] * reward[request]\n'
           f'                        denominator -= {rate_name}[request]\n'
           '                        active = active & (!bit)\n'
           '                        removed = true\n'
           '                    }')
    new = ('                    if ((active & bit) != 0) {\n'
           '                        let rr = reward[request]\n'
           '                        if (rr < estimate) {\n'
           f'                            let requestRate = {rate_name}[request]\n'
           '                            numerator -= requestRate * rr\n'
           '                            denominator -= requestRate\n'
           '                            active = active & (!bit)\n'
           '                            removed = true\n'
           '                        }\n'
           '                    }')
    # Causal DP is indented four spaces deeper than primal DP.
    if body.count(old) == 0:
        old = '\n'.join('    ' + line for line in old.split('\n'))
        new = '\n'.join('    ' + line for line in new.split('\n'))
    assert body.count(old) == 1
    return body.replace(old, new)


def primal(body):
    assert body.count('let rate = dpRateScratch') == 1
    assert body.count('let value = dpValueScratch') == 1
    assert body.count('reward.fill(0.0)') == 1
    body = body.replace('let rate = dpRateScratch', 'let rate = causalRequestRate')
    body = body.replace('let value = dpValueScratch', 'let value = primalGapValue')
    body = body.replace('            reward.fill(0.0)\n', '')
    old = ('                reward[request] = Float64(request) + value[g - request]\n'
           '                numerator += requestRate * reward[request]')
    new = ('                let requestReward = Float64(request) + value[g - request]\n'
           '                reward[request] = requestReward\n'
           '                numerator += requestRate * requestReward')
    assert body.count(old) == 1
    body = body.replace(old, new)
    body = eliminate(body, 'rate')
    body = body.replace('        primalGapValue.copyFrom(value)\n', '')
    body = body.replace('        causalRequestRate.copyFrom(rate)\n', '')
    return body


def causal(body):
    old = ('        for (model in 0..2) {\n'
           '            let value = dpValueScratch\n'
           '            value.fill(0.0)')
    new = ('        for (model in 0..2) {\n'
           '            let offset: Int64 = model * 513')
    assert body.count(old) == 1
    body = body.replace(old, new)
    body = body.replace('                reward.fill(0.0)\n', '')
    old = ('                    reward[request] = Float64(request) + value[gap - request]\n'
           '                    numerator += requestRate * reward[request]')
    new = ('                    let requestReward = Float64(request) + gapValues[offset + gap - request]\n'
           '                    reward[request] = requestReward\n'
           '                    numerator += requestRate * requestReward')
    assert body.count(old) == 1
    body = body.replace(old, new)
    body = eliminate(body, 'requestRates')
    body = body.replace('                value[gap] = fMin(fMax(estimate, 0.0), Float64(gap))',
                        '                gapValues[offset + gap] = fMin(fMax(estimate, 0.0), Float64(gap))')
    old = '            for (cell in 0..513) { gapValues[model * 513 + cell] = value[cell] }\n'
    assert body.count(old) == 1
    body = body.replace(old, '')
    return body


rewrite_method('rebuildPrimalGapValues', primal)
rewrite_method('rebuildCausalGapValues', causal)

assert 'dpRateScratch' not in source and 'dpValueScratch' not in source
assert 'reward.fill(0.0)' not in source
assert source.count('= FastFloatBuffer(') == 4
assert source.count('copyFrom(') == 1  # helper declaration only; no DP commits.
assert source.count('let requestReward = Float64(request) +') == 2
assert source.count('let rr = reward[request]') == 2
assert source.count('numerator -= requestRate * rr') == 2
assert 'rate.fill(0.0)' in source and 'value.fill(0.0)' in source and 'gapValues.fill(0.0)' in source
assert source[source.index('func replayTable0():'):] == original[original.index('func replayTable0():'):]

# Numeric-expression audit: the recurrence keeps each FP operation exactly as
# before. Caching replaces repeated immutable reads only, and offset arithmetic
# affects integer addressing alone. Scalar helper definitions are unchanged.
for helper in ['func fMin(', 'func fMax(']:
    old = next(line for line in original.splitlines() if line.startswith(helper))
    new = next(line for line in source.splitlines() if line.startswith(helper))
    assert old == new

OUT.mkdir(exist_ok=True)
target = OUT / 'solution.cj'
target.write_text(source)
metadata = {
    'baseline': str(BASE.relative_to(HERE)), 'baseline_sha256': BASE_SHA256,
    'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
    'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'changes': [
        'Primal recurrence writes directly into persistent primalGapValue and rates directly into causalRequestRate.',
        'Causal recurrence writes directly into persistent causalGapValue at model*513 offset.',
        'Both whole-table zero fills remain, preserving index0 and all tails above maxGap.',
        'Rate/value scratch owning fields and their two malloc allocations are removed.',
        'Reward scratch41 persists without per-gap fill; active bits guard all subsequent reward reads.',
        'requestReward, rr and requestRate scalar caches remove repeated immutable buffer reads.',
    ],
    'allocations_per_allocator': {'persistent': [513,41,1026], 'scratch':[41],
                                  'count':4, 'payload_bytes':12968, 'rebuild_allocations':0},
    'equivalence_review': [
        'Every reward active bit is set only after a nonzero-rate branch writes its reward entry for this gap.',
        'Elimination reads reward only inside its active-bit branch. Removed/zero-rate entries are never read.',
        'Caching does not change multiplication/subtraction/addition order or stored Float64 values.',
        'Primal tables are unobservable during recurrence: only scalar helpers execute before lifetimeModel.fit.',
        'The two causal rows are disjoint; whole1026-entry zero fill precedes both rows.',
        'All pointer ownership, finalizer, null checking and bounds checks from native-dp are unchanged.',
    ],
    'memset_audit': {
        'version':'1.0.5',
        'source':'https://github.com/cangjielanguage/cangjie_runtime/blob/c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9/std/libs/std/core/libc.cj',
        'finding':'No public LibC.memset API exists in the checked1.0.5 source. Public APIs are malloc/free/mallocCString plus sizeOf/alignOf functions.',
        'applied':False,
        'abi_caveat':'A separately declared foreign memset would require independent Windows CRT/linkage/calling-ABI verification and was not introduced.',
    },
    'compile_executed':False, 'solver_executed':False,
    'performance_status':'Experimental; no performance claim until parent compiles and measures.',
}
(OUT / 'source.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
(OUT / 'changes.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),source.splitlines(True),
                                                           fromfile='candidate-native-dp/solution.cj',
                                                           tofile='candidate-native-direct/solution.cj')))
print(target)
print(metadata['source_sha256'])
