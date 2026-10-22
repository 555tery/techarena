#!/usr/bin/env python3
"""Bounded independent Python equivalence audit; never runs Cangjie code."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import random

HERE = Path(__file__).resolve().parent
OUT = HERE / 'candidate-length-history'
WINDOW = 2048


class CacheModel:
    def __init__(self):
        self.data = []
        self.lengths = [0, 0, 0]
        self.counts = [0, 0, 0]

    def push(self, value):
        self.data.append(value)
        if len(self.data) == 1:
            self.lengths = [value, 0, 0]
            self.counts = [1, 0, 0]
        elif value == self.lengths[0]:
            self.counts[0] += 1
        else:
            self.lengths = [value, self.lengths[0], self.lengths[1]]
            self.counts = [1, self.counts[0], self.counts[1]]

    def front(self):
        self.data.pop(0)
        if not self.data:
            self.lengths = [0, 0, 0]
            self.counts = [0, 0, 0]

    def back(self):
        self.data.pop()
        self.lengths = [0, 0, 0]
        self.counts = [0, 0, 0]
        i = len(self.data) - 1
        for run in range(3):
            if i < 0:
                break
            size = self.data[i]
            self.lengths[run] = size
            while i >= 0 and self.data[i] == size:
                self.counts[run] += 1
                i -= 1

    def run_count(self, run):
        newest = min(self.counts[0], len(self.data))
        if run == 0:
            return newest
        second = min(self.counts[1], len(self.data) - newest)
        if run == 1:
            return second
        return min(self.counts[2], len(self.data) - newest - second)

    def clone(self):
        other = CacheModel()
        other.data = self.data.copy()
        other.lengths = self.lengths.copy()
        other.counts = self.counts.copy()
        return other


# Expected side scans actual window elements and deliberately does not read
# CacheModel counters, lengths, or optimized endpoint-selection logic.
def scanned_runs(seq):
    result = []
    i = len(seq) - 1
    while i >= 0 and len(result) < 3:
        size = seq[i]
        count = 0
        while i >= 0 and seq[i] == size:
            count += 1
            i -= 1
        result.append((size, count))
    return result


def old_steady(seq, freq):
    if len(seq) < 128 or len(freq) < 3:
        return False
    distinct = []
    previous = -1
    i = len(seq) - 1
    while i >= 0:
        size = seq[i]
        i -= 1
        if size == previous:
            continue
        distinct.append(size)
        previous = size
        if len(distinct) == 3:
            break
    if len(distinct) < 3:
        return False
    return distinct[0] - distinct[1] == distinct[1] - distinct[2]


def old_smooth(seq, current, freq):
    if not seq:
        return False
    available = len(freq) + (current not in freq)
    if available < 3:
        return False
    already = seq[-1] == current
    prior = []
    first = True
    last = -1
    i = len(seq) - 1
    while i >= 0:
        size = seq[i]
        i -= 1
        if first:
            first = False
            last = size
            if not already:
                prior.append(size)
            continue
        if size == last:
            continue
        last = size
        prior.append(size)
        if len(prior) == 2:
            break
    if len(prior) < 2:
        return False
    return current - prior[0] == prior[0] - prior[1]


def old_long(seq, current, observed):
    if current < 3 or current >= 40 or observed < 46:
        return False
    sizes = [current, 0, 0]
    counts = [observed, 0, 0]
    i = len(seq) - 1
    while i >= 0 and seq[i] == current:
        i -= 1
    for run in range(1, 3):
        if i < 0:
            return False
        size = seq[i]
        sizes[run] = size
        while i >= 0 and seq[i] == size:
            counts[run] += 1
            i -= 1
        if counts[run] < 46:
            return False
    return sizes[0] == sizes[1] + 1 and sizes[1] == sizes[2] + 1


def geometric_tail(current, previous, before):
    if not before < previous < current:
        return 0
    observed = current * before
    expected = previous * previous
    error = observed - expected if observed > expected else expected - observed
    if 2 * error > before:
        return 0
    predicted = (current * previous + before // 2) // before
    return predicted if current < predicted <= 40 else 0


def old_geo(seq, current):
    if not seq or seq[-1] != current:
        return 0
    runs = scanned_runs(seq)
    if len(runs) < 3 or runs[0][0] != current or any(count < 46 for _, count in runs):
        return 0
    return geometric_tail(current, runs[1][0], runs[2][0])


snapshots = predicate_checks = cache_checks = clone_forks = pop_back_checks = 0


def check(model, label, predicates=True):
    global snapshots, predicate_checks, cache_checks
    expected = scanned_runs(model.data)
    actual = [(model.lengths[r], model.run_count(r)) for r in range(3) if model.run_count(r) > 0]
    assert actual == expected, (label, expected, actual)
    cache_checks += 1
    if not predicates:
        return
    snapshots += 1
    seq = model.data
    freq = Counter(seq)
    newest, previous, before = model.lengths
    steady = len(seq) >= 128 and len(freq) >= 3 and model.run_count(2) != 0 and newest - previous == previous - before
    assert steady == old_steady(seq, freq), ('steady', label)
    predicate_checks += 1
    for current in range(1, 41):
        first = 1 if seq and seq[-1] == current else 0
        smooth = bool(seq) and len(freq) + (current not in freq) >= 3 and model.run_count(first + 1) != 0 and current - model.lengths[first] == model.lengths[first] - model.lengths[first + 1]
        assert smooth == old_smooth(seq, current, freq), ('smooth', label, current)
        geo = 0
        if seq and seq[-1] == current and model.run_count(2) != 0 and newest == current and all(model.run_count(r) >= 46 for r in range(3)):
            geo = geometric_tail(current, previous, before)
        assert geo == old_geo(seq, current), ('geo', label, current)
        predicate_checks += 2
        for observed in [45, 46, 200000]:
            long = current >= 3 and current < 40 and observed >= 46 and model.run_count(first) >= 46 and model.run_count(first + 1) >= 46 and current == model.lengths[first] + 1 and model.lengths[first] == model.lengths[first + 1] + 1
            assert long == old_long(seq, current, observed), ('long', label, current, observed)
            predicate_checks += 1


def build(runs, cap=WINDOW):
    model = CacheModel()
    for value, count in runs:
        for _ in range(count):
            model.push(value)
            if cap is not None and len(model.data) > cap:
                model.front()
    return model


check(CacheModel(), 'empty')
boundaries = [0, 1, 2, 44, 45, 46, 47, 63, 64, 127, 128, 129, 2047, 2048, 2049, 4096, 10000]
models = []
for n in boundaries:
    for runs in [[(1,n)], [(1,46),(2,46),(3,n)], [(3,46),(6,46),(12,n)], [(2,n),(4,47),(8,46)], [(1,46),(2,n),(1,46)]]:
        model = build(runs)
        check(model, f'boundary{runs}')
        models.append(model)
for count in [45,46,47,1000,2047,2048,2049]:
    model = build([(40,2048),(1,128),(2,count),(3,46)])
    check(model, f'front-clipped-{count}')
    models.append(model)

# Uncapped mode probes wrapper API semantics separately from the2048 window.
for n in [2047,2048,2049,4096,10000]:
    model = build([(1,n),(2,46),(3,46)], cap=None)
    check(model, f'uncapped-{n}')

model = build([(1,199800),(2,46),(3,46)])
check(model, 'near200000-with-clipped-third-run')
models.append(model)

rng = random.Random(20261020816429)
model = CacheModel()
for t in range(18000):
    value = 1 + (t // 701) % 40 if t < 9000 else rng.randint(1,40)
    model.push(value)
    if len(model.data) > WINDOW:
        model.front()
    if t in [0,44,45,46,126,127,128,2046,2047,2048] or t % 173 == 0:
        check(model, f'mixed-{t}')
        models.append(model.clone())
for cycle in [2,3,40]:
    model = CacheModel()
    for t in range(5000):
        model.push(1+t%cycle)
        if len(model.data) > WINDOW: model.front()
        if t in [45,46,127,128,2047,2048,2049,4999]: check(model,f'alternating-{cycle}-{t}')

# Clone forks: independent mutations, ring import-by-push equivalence and the
# currently unused popBack fallback exposing fourth/fifth older runs.
for index, original in enumerate(models[::5]):
    clone_forks += 1
    saved = original.data.copy()
    child = original.clone()
    imported = CacheModel()
    for value in original.data: imported.push(value)
    check(imported, f'import-{index}')
    for t in range(99):
        if t % 7 == 0 and child.data:
            child.back()
            pop_back_checks += 1
        elif t % 11 == 0 and child.data:
            child.front()
        else:
            child.push(1+(t//13+index)%40)
            if len(child.data)>WINDOW: child.front()
        check(child, f'clone-{index}-{t}', predicates=t%19==0)
    assert original.data == saved, ('clone alias',index)
    check(original, f'original-after-clone-{index}')
model = build([(1,31),(2,33),(3,35),(4,37),(5,39)])
while model.data:
    model.back()
    pop_back_checks += 1
    check(model,'popback-reveal-old-runs',predicates=len(model.data)%17==0)
model.push(7);check(model,'reuse-after-empty')

result = {'verdict':'PASS independent Python model equivalence',
          'source_sha256':hashlib.sha256((OUT/'solution.cj').read_bytes()).hexdigest(),
          'audit_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'cache_checks':cache_checks,'predicate_checks':predicate_checks,'predicate_snapshots':snapshots,
          'clone_forks':clone_forks,'pop_back_checks':pop_back_checks,'mismatches':0,
          'boundaries':boundaries,'master_seed':20261020816429,
          'scope':'Pure Python scanned-window reference versus independent cache model; original detector thresholds/guards translated literally. Includes2048 truncation, long runs, missing current run, alternating runs, clone forks, import-by-push, empty/reuse and popBack exposing older runs.',
          'limitation':'Not a Cangjie execution or proof of compiler correctness; parent must compile and check transcript/resource parity.',
          'compile_executed':False,'solver_executed':False}
(OUT/'python-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
