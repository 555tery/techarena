#!/usr/bin/env python3
"""Short IEEE64 elimination-only comparison; does not execute Cangjie/DP tables."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import random
import struct

HERE = Path(__file__).resolve().parent


def bits(x):
    return struct.pack('>d', x).hex()


def div(numerator, denominator):
    try:
        return numerator / denominator
    except ZeroDivisionError:
        if numerator == 0.0 or math.isnan(numerator):
            return float('nan')
        return math.copysign(float('inf'), numerator) * math.copysign(1.0, denominator)


def eliminate(rewards, rates, expiry, optimized):
    active = 0
    minimum = float('inf')
    numerator = 0.0
    denominator = expiry
    trace = []
    for request in range(1, 41):
        rate = rates[request]
        if rate == 0.0:
            continue
        reward = rewards[request]
        if optimized and reward < minimum:
            minimum = reward
        numerator += rate * reward
        denominator += rate
        active |= 1 << request
    estimate = div(numerator, denominator)
    trace.append(('initial', bits(numerator), bits(denominator), bits(estimate), active))
    removed_order = []
    passes = 0
    while not optimized or estimate > minimum:
        passes += 1
        assert passes <= 42
        if optimized:
            minimum = float('inf')
        removed = False
        for request in range(1, 41):
            bit = 1 << request
            if active & bit:
                rr = rewards[request]
                if rr < estimate:
                    request_rate = rates[request]
                    numerator -= request_rate * rr
                    denominator -= request_rate
                    active &= ~bit
                    removed = True
                    removed_order.append(request)
                    trace.append(('remove', request, bits(numerator), bits(denominator), active))
                elif optimized and rr < minimum:
                    minimum = rr
        if not removed:
            break
        estimate = div(numerator, denominator)
        trace.append(('estimate', bits(estimate)))
    return ((bits(numerator), bits(denominator), bits(estimate), active), removed_order, trace, passes)


def main():
    rng = random.Random(20261020)
    counts = Counter()
    skipped = 0
    for case in range(10000):
        category = case % 5
        rewards = [0.0] * 41
        rates = [0.0] * 41
        for i in range(1, 41):
            if category == 0:
                rewards[i] = float(i) + rng.random() * 512.0
                rates[i] = rng.randrange(0, 200001) / float(rng.randrange(1, 200002))
            elif category == 1:
                rewards[i] = rng.choice([1.0, 2.0, 40.0, 512.0, 0.0, -0.0])
                rates[i] = rng.choice([0.0, -0.0, 0.5, 1.0, 2.0, 1000.0])
            elif category == 2:
                rewards[i] = rng.uniform(0.5, 1.5) * (10.0 ** rng.randrange(-300, 301))
                rates[i] = 0.0 if rng.random() < .2 else 10.0 ** rng.randrange(-300, 301)
            elif category == 3:
                rewards[i] = math.nextafter(float(rng.randrange(0, 513)), rng.choice([-math.inf, math.inf]))
                rates[i] = rng.choice([0.0, 1.0, 2.0 ** -52, 2.0 ** 52, 1e-300, 1e300])
            else:
                # Beyond the policy domain: cancellation, infinities and NaNs.
                rewards[i] = rng.choice([float('nan'), math.inf, -math.inf,
                                         -1e300, -1e-300, -0.0, 0.0, 1e-300, 1e300])
                rates[i] = rng.choice([0.0, -0.0, -1.0, 1.0, 1e-300, 1e300])
        expiry = (rng.choice([0.0, .5, 1.0, 400000.0]) if category < 2 else
                  rng.choice([0.0, 1e-300, 1e-100, 1.0, 1e100, 1e300]))
        old = eliminate(rewards, rates, expiry, False)
        new = eliminate(rewards, rates, expiry, True)
        assert old[:3] == new[:3], (case, category, old, new)
        skipped += old[3] - new[3]
        counts[category] += 1
    # Explicit empty masks, no-op equal rewards, +Inf and signed-zero cases.
    fixtures = [([0.0] * 41, [0.0] * 41, 0.0),
                ([1.0] * 41, [1.0] * 41, 0.0),
                ([math.inf] * 41, [1.0] * 41, 1.0),
                ([float('nan')] * 41, [1.0] * 41, 1.0),
                ([-0.0] * 41, [1.0] * 41, -0.0)]
    for rewards, rates, expiry in fixtures:
        old = eliminate(rewards, rates, expiry, False)
        new = eliminate(rewards, rates, expiry, True)
        assert old[:3] == new[:3]

    parent = HERE.parent
    original = (parent / 'candidate-primal-int/solution.cj').read_text()
    minimum = (parent / 'candidate-min-bound-example/solution.cj').read_text()
    bounded = (parent / 'candidate-bounded-example/solution.cj').read_text()
    # Reverse exactly the added minimum bookkeeping and loop guard.
    lines = minimum.splitlines(True)
    keep = []
    skip_min_assignment = False
    for line in lines:
        stripped = line.strip()
        if stripped == 'var minActiveReward = Float64.Inf':
            continue
        if stripped == 'if (requestReward < minActiveReward) { minActiveReward = requestReward }':
            continue
        if stripped == 'minActiveReward = Float64.Inf':
            continue
        if stripped == '} else if (rr < minActiveReward) {':
            skip_min_assignment = True
            continue
        if skip_min_assignment and stripped == 'minActiveReward = rr':
            skip_min_assignment = False
            continue
        keep.append(line.replace('while (estimate > minActiveReward) {', 'while (true) {'))
    assert ''.join(keep) == original
    for method in ('rebuildPrimalGapValues', 'rebuildCausalGapValues'):
        marker = f'    @OverflowWrapping\n    public func {method}(maxGap: Int64): Unit {{'
        assert bounded.count(marker) == 1
        assert 'if (maxGap < 0 || maxGap > kPrimalGapValueCap)' in bounded[bounded.index(marker):bounded.index(marker) + 340]
    assert bounded.replace('    @OverflowWrapping\n    public func rebuildPrimalGapValues', '    public func rebuildPrimalGapValues').replace('    @OverflowWrapping\n    public func rebuildCausalGapValues', '    public func rebuildCausalGapValues') == original
    sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
    report = {
        'status': 'pass',
        'scope': 'Short independent Python IEEE64 elimination-only audit plus source normalization; no Cangjie compile/solver/full DP tables.',
        'sha256': {'baseline': sha(original), 'min_bound_example': sha(minimum), 'bounded_example': sha(bounded),
                   'prepare_dp_min_bound.py': sha((parent / 'prepare_dp_min_bound.py').read_text()),
                   'prepare_bounded_dp.py': sha((parent / 'prepare_bounded_dp.py').read_text()),
                   'test': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        'differential': {'randomized_sets': 10000, 'rewards_per_set': 40, 'seed': 20261020,
                         'categories': dict(counts), 'explicit_edge_fixtures': len(fixtures),
                         'compared': ['final numerator Float64 bits', 'final denominator Float64 bits',
                                      'final estimate Float64 bits', 'remaining active bits',
                                      'exact removed-request order', 'every intermediate removal FP state and estimate bits'],
                         'omitted_empty_passes': skipped, 'mismatches': 0},
        'min_bound_proof': [
            'minimum starts+Inf and ignores NaN rewards because comparisons are false. It equals the least ordered active reward; active NaNs never satisfy rr<estimate and need not constrain minimum.',
            'estimate>minimum holds exactly when at least one active reward can satisfy original rr<estimate. If false, the original pass performs no FP arithmetic, changes no bits and exits.',
            'After every executed pass, minimum is accumulated only from retained active rewards. All removed requests, increasing order, multiplications/subtractions and recomputed estimates are identical.',
            'NaN estimate suppresses removal in both versions. Empty/all+Inf/allNaN active sets keep minimum+Inf and have no removable request. Signed-zero comparison equality preserves strict thresholds.',
            'Reverse removal of bookkeeping restores the entire baseline source byte-for-byte, confirming both methods and no accidental edits elsewhere.',
        ],
        'bounded_dp_review': {
            'scope': 'Exactly two added annotations, and reverse deletion restores baseline byte-for-byte. Both unchanged explicit maxGap guards remain at function entry.',
            'integer_domains': ['maxGap0..512; g/gap0..512; model0/1; offset0/513; causal indexes0..1025.',
                                'lastRequest descends40..0; firstRequest advances at most41. Request loops are empty when start>top; otherwise1..40. Gap-request is nonnegative wherever accessed.',
                                'active mask uses1<<request,request<=40: positive bits below2^41. Bitwise complement/and cannot overflow.',
                                'fitting sums disjoint, nonnegative free-gap bucket counts, conservatively<=200001 for<=200000 commands.',
                                'primalModelStep/primalStep and active counts are bounded by input events; per-Allocator model rebuild counter is bounded by ordinary placement-triggered calls, far below Int64 limit.',
                                'No narrowing integer conversion is introduced. FP expressions, explicit bounds checks and called-method definitions remain unchanged.'],
            'official_documentation': 'https://raw.githubusercontent.com/cangjielanguage/cangjie_docs/f8f8cd75a336e23785a4c57bd6091b2adf1e0302/docs/dev-guide/source_zh_cn/reflect_and_annotation/anno.md',
            'documentation_use': 'Annotation is function-scoped and changes integer arithmetic/conversion overflow policy. Since audited mathematical intermediates fit Int64, wrapping never activates on valid states.',
            'preparer_caveat': 'Not idempotent: applying prepare_bounded_dp to an already annotated source adds duplicate annotations. Apply once or add an explicit existing-annotation guard.',
        },
        'findings': [],
        'limitations': ['Python uses binary64 operation results and an explicit IEEE division helper for zero denominators; it does not validate Cangjie code generation or Windows runtime behavior.',
                        'No performance claim follows from removing empty passes; parent measures actual runtime and whole-transcript parity.'],
    }
    (HERE / 'dp-min-bound-equivalence.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': 'pass', 'randomized_sets': 10000, 'fixtures': len(fixtures), 'omitted_empty_passes': skipped}))


if __name__ == '__main__':
    main()
