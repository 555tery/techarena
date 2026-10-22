#!/usr/bin/env python3
"""Storage/local-snapshot fix for VArray field copies; no compile or solver run."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'candidate-histograms/solution.cj'
OUT = HERE / 'candidate-values-local'
BASE_SHA256 = '69b968a9e05e139e376cf1591b9c0013f303d1f86e8fed0a98b5068cd21c3777'
original = BASE.read_text()
assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA256
source = original
edits = []


def replace(old, new, count=1):
    global source
    assert source.count(old) == count, (old[:100], source.count(old), count)
    source = source.replace(old, new)
    edits.append({'old': old, 'new': new, 'occurrences': count})


def rewrite_method(name, transform):
    global source
    start = source.index(f'    public func {name}(')
    stop = source.index('\n    }', start) + len('\n    }')
    old = source[start:stop]
    new = transform(old)
    assert new != old
    source = source[:start] + new + source[stop:]


# These structs have only primitive numeric fields. Ordinary flat Arrays retain
# the row-major layout without copying all328 structs at every class-field read.
replace('private var cells = VArray<LifetimeCell, $328>(repeat: LifetimeCell())',
        'private var cells = Array<LifetimeCell>(328, repeat: LifetimeCell())')
replace('private var rates = VArray<LifetimeEstimate, $328>(repeat: LifetimeEstimate())',
        'private var rates = Array<LifetimeEstimate>(328, repeat: LifetimeEstimate())')


def primal(body):
    # All uses of gap counts and request counts in this function are reads.
    assert body.count('primalGapCounts[') == 2
    assert body.count('primalRecentRequests[') == 1
    assert body.count('primalGapValue') == 6
    body = body.replace('        var rate = VArray<Float64, $41>(repeat: 0.0)',
                        '        let gapCounts = primalGapCounts\n'
                        '        let recentRequests = primalRecentRequests\n'
                        '        var rate = VArray<Float64, $41>(repeat: 0.0)')
    body = body.replace('primalGapCounts[', 'gapCounts[')
    body = body.replace('primalRecentRequests[', 'recentRequests[')
    body = body.replace('        primalGapValue = VArray<Float64, $513>(repeat: 0.0)',
                        '        var value = VArray<Float64, $513>(repeat: 0.0)')
    body = body.replace('primalGapValue[', 'value[')
    body = body.replace('        causalRequestRate = rate',
                        '        primalGapValue = value\n'
                        '        causalRequestRate = rate')
    assert body.count('primalGapValue') == 1
    assert body.count('primalGapValue = value') == 1
    assert body.count('primalGapCounts') == 1
    return body


rewrite_method('rebuildPrimalGapValues', primal)


def causal(body):
    assert body.count('causalRequestRate[') == 3
    assert body.count('causalGapValue[') == 1
    body = body.replace('        for (model in 0..2) {',
                        '        let requestRates = causalRequestRate\n'
                        '        var gapValues = causalGapValue\n'
                        '        for (model in 0..2) {')
    body = body.replace('causalRequestRate[', 'requestRates[')
    body = body.replace('causalGapValue[', 'gapValues[')
    body = body.replace('        causalComputedLimit = maxGap',
                        '        causalGapValue = gapValues\n'
                        '        causalComputedLimit = maxGap')
    return body


rewrite_method('rebuildCausalGapValues', causal)

# Both operands read one field; snapshot once rather than copying513 doubles
# twice. fMin/fMax/Float64 arithmetic and left-to-right expression are unchanged.
replace('    public func primalGapLoss(gapLength: Int64, length: Int64): Float64 { return primalGapValue[gapLength] - primalGapValue[gapLength - length] }',
        '    public func primalGapLoss(gapLength: Int64, length: Int64): Float64 {\n'
        '        let value = primalGapValue\n'
        '        return value[gapLength] - value[gapLength - length]\n'
        '    }')

# Static guards for the intended scope; no execution of the Cangjie candidate.
assert source[source.index('func replayTable0():'):] == original[original.index('func replayTable0():'):]
for marker in ['public class OrderedMap<', 'public class IntOrderedMap', 'public class Ring<', 'public class IntRing']:
    def section(text):
        start = text.index(marker)
        stop = text.index('\n}\n', start) + 3
        return text[start:stop]
    assert section(source) == section(original)

OUT.mkdir(exist_ok=True)
target = OUT / 'solution.cj'
target.write_text(source)
metadata = {
    'baseline': str(BASE.relative_to(HERE)),
    'baseline_sha256': hashlib.sha256(original.encode()).hexdigest(),
    'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
    'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'changes': [
        'Flat lifetime cells/rates328 use ordinary Array rather than class-field VArray copies.',
        'Primal DP uses local VArray513 value; commits primalGapValue once before causalRequestRate assignment.',
        'Primal gapCounts514 and recentRequests41 are immutable local snapshots during the rebuild.',
        'Causal DP reads local requestRates41 and writes local gapValues1026; commits field once after both rows.',
        'primalGapLoss reads one local snapshot513 for its two operands.',
    ],
    'aliasing_review': [
        'Primal rebuild neither mutates gapCounts/recentRequests fields nor calls other stateful methods before their final use.',
        'Primal value field is not observed during DP; only scalar helpers run. Commit still precedes lifetimeModel.fit.',
        'Causal rebuild uses scalar helpers only; gapValues is unobservable until the method returns.',
        'Both causal rows still copy all513 elements including the zero tail; snapshots preserve old row values until overwritten.',
        'Lifetime structs still use local struct-copy/mutate/write-back, without reference members.',
        'primalGapLoss has no mutation or callback between its two field reads.',
    ],
    'scope_caveat': 'Single-access causalValueAt snapshots would still copy the full table once per call; unchanged to avoid signature/caller expansion. Other small8/41/256-element fields are unchanged outside the named methods.',
    'policy': 'Same FP expressions, loop order, thresholds, comparisons and DP iteration order; only storage and field commit timing within non-reentrant methods change.',
    'compile_executed': False,
    'solver_executed': False,
    'exact_declaration_edits': edits,
}
(OUT / 'source.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
(OUT / 'changes.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), source.splitlines(True),
                                                           fromfile='candidate-histograms/solution.cj',
                                                           tofile='candidate-values-local/solution.cj')))
print(target)
print(metadata['source_sha256'])
