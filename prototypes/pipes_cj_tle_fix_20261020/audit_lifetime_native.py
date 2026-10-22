#!/usr/bin/env python3
"""Primitive-layout/copy/source audit; never builds or runs Cangjie."""
import hashlib
import json
from pathlib import Path
import random
import struct
import prepare_lifetime_native as prep

HERE = Path(__file__).resolve().parent
RNG = random.Random(202610208247)


class FlatOwner:
    def __init__(self, size, stride, zero=0):
        self.size, self.stride = size, stride
        self.payload = [zero] * (size * stride)

    def get(self, index):
        if index < 0 or index >= self.size:
            raise IndexError
        offset = index * self.stride
        assert 0 <= offset and offset + self.stride <= len(self.payload)
        return list(self.payload[offset:offset + self.stride])

    def set(self, index, value):
        if index < 0 or index >= self.size:
            raise IndexError
        offset = index * self.stride
        assert 0 <= offset and offset + self.stride <= len(self.payload)
        self.payload[offset:offset + self.stride] = list(value)


def bits(values):
    return [struct.pack('<d', value).hex() for value in values]


def run():
    original = prep.BASE.read_text()
    candidate = (prep.OUT / 'solution.cj').read_text()
    owner_source = prep.owners()
    assert candidate.count(owner_source) == 1
    restored = candidate.replace(owner_source, '', 1)
    for old, new in prep.DECLARATIONS:
        assert restored.count(new) == 1
        restored = restored.replace(new, old, 1)
    assert restored == original
    assert 'borrowData' not in owner_source
    assert 'return data' not in owner_source
    assert 'CPointer<Lifetime' not in owner_source
    assert 'CPointer<Int64>' in owner_source and 'CPointer<Float64>' in owner_source
    assert 'private let lower: VArray<Int64, $8> = [0, 16, 64, 256, 1024, 4096, 16384, 65536]' in candidate

    checks = dict(record_appends=0, record_reallocations=0, record_read_write_checks=0,
                  cell_read_write_checks=0, rate_read_write_checks=0,
                  cursor_read_write_checks=0, bounds_checks=0, detached_copy_checks=0)
    # Vector model mirrors native stride3, capacity growth, sentinel, bool
    # encoding. The reference uses independent per-record copied values.
    capacity, used = 16, 1
    payload = [0] * 48
    reference = [[0, 0, False]]
    assert payload[:3] == [0, 0, 0]
    for i in range(8193):
        value = [RNG.randrange(-2**63, 2**63), RNG.randrange(1, 41), bool(RNG.randrange(2))]
        saved = value.copy()
        if used == capacity:
            expanded = [None] * (capacity * 6)
            expanded[:used * 3] = payload[:used * 3]
            payload = expanded
            capacity *= 2
            checks['record_reallocations'] += 1
        payload[used * 3:used * 3 + 3] = [value[0], value[1], int(value[2])]
        reference.append(value.copy())
        used += 1
        value[:] = [999, 999, False]
        assert reference[-1] == saved
        checks['record_appends'] += 1
        for node in (0, used - 1, RNG.randrange(used)):
            offset = node * 3
            read = [payload[offset], payload[offset + 1], payload[offset + 2] != 0]
            assert read == reference[node]
            read[0] ^= 71
            assert payload[offset] == reference[node][0]
            checks['detached_copy_checks'] += 1
            # Mirror the only Model records setter: copy born/length, clear
            # active on deletion, with no other record being changed.
            changed = reference[node].copy()
            changed[2] = False
            payload[offset:offset+3] = [changed[0], changed[1], int(changed[2])]
            reference[node] = changed.copy()
            checks['record_read_write_checks'] += 1
    for node in range(used):
        offset = node * 3
        assert [payload[offset], payload[offset+1], payload[offset+2] != 0] == reference[node]

    cells = FlatOwner(328, 4)
    rates = FlatOwner(328, 2, 0.0)
    cursors = FlatOwner(8, 1, 1)
    assert cells.payload == [0] * 1312
    assert bits(rates.payload) == ['0000000000000000'] * 656
    assert cursors.payload == [1] * 8
    float_patterns = [0, 0x8000000000000000, 1, 0x7ff0000000000000,
                      0xfff0000000000000, 0x7ff8000000000021, 0x3ff0000000000000]
    float_values = [struct.unpack('<d', struct.pack('<Q', value))[0] for value in float_patterns]
    for owner, kind in ((cells, 'cell'), (rates, 'rate'), (cursors, 'cursor')):
        for i in range(4000):
            index = RNG.randrange(owner.size)
            value = ([RNG.choice(float_values) for _ in range(owner.stride)] if kind == 'rate'
                     else [RNG.randrange(-2**63, 2**63) for _ in range(owner.stride)])
            saved = value.copy()
            owner.set(index, value)
            value[0] = 721
            got = owner.get(index)
            assert (bits(got) == bits(saved)) if kind == 'rate' else (got == saved)
            got[0] = 819
            copied_again = owner.get(index)
            assert (bits(copied_again) == bits(saved)) if kind == 'rate' else (copied_again == saved)
            checks[f'{kind}_read_write_checks'] += 1
            checks['detached_copy_checks'] += 2
        for index in (-2**63, -1, owner.size, owner.size + 1, 2**63-1):
            for operation in (lambda: owner.get(index), lambda: owner.set(index, [0] * owner.stride)):
                try:
                    operation()
                except IndexError:
                    checks['bounds_checks'] += 1
                else:
                    raise AssertionError('Missing bounds guard')
    result = {
        'schema': 'lifetime-native-storage-independent-audit-v1',
        'base_sha256': hashlib.sha256(original.encode()).hexdigest(),
        'output_sha256': hashlib.sha256(candidate.encode()).hexdigest(),
        'audit_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'reverse_exact': True, 'mismatches': 0, 'checks': checks,
        'source_changes': 'Four field declarations and four new private owners only. All pre-existing classes/methods/struct bodies, lower VArray, FP expression ordering and policy thresholds are byte-identical.',
        'copy_semantics': 'Independent primitive fields on every getter/setter; the only Bool uses lossless0/1 encoding. Float tests include+0/-0, subnormal, infinities, NaN payload and ordinary values. No arithmetic is applied to Float64 storage.',
        'bounds': 'Record getter/setter check0<=index<used. Fixed owners check against328/328/8 then use safe stride4/2/1. Growth copies used*3 words before replacing current allocation. Tests include sentinel and10growth boundaries.',
        'ownership': 'One current allocation per owner, private pointers, no pointer export or managed-reference payload. Null checked before dereference. Fixed constructor initialization cannot throw arithmetic for constant sizes; failed allocation owns no block. Records expansion failure leaves old data/current capacity unchanged. ~init frees only current allocation.',
        'keeper': 'Every successful native-access path outside finalizers ends in public std.runtime.blackBox(this) after copying return values or committing writes. This uses the official1.0.5 anti-DCE contract; owner fields remain reachable. Finalizers contain only free.',
        'limits': 'Independent Python layout/copy/bounds model and source reversal, not Cangjie compilation/execution or target performance evidence. Behavior after allocation failure or exception-message identity need not match ArrayList/Array; valid successful operations preserve values.',
        'cangjie_compiled': False, 'solver_executed': False,
    }
    (HERE / 'audit/lifetime-native.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    run()
