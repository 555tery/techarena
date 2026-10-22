#!/usr/bin/env python3
"""Storage-only lifetime candidate; no Cangjie build or solver execution."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'candidate-avl-inline/solution.cj'
OUT = HERE / 'candidate-lifetime-native'
BASE_SHA256 = 'b582fcb4c111f2e469bb2fee4cd928b26cf0c7c5aef2078ac4b343236df1110f'
DECLARATIONS = [
    ('private var records = ArrayList<LifetimeRecord>([LifetimeRecord()])',
     'private var records = NativeLifetimeRecords()'),
    ('private var cells = Array<LifetimeCell>(328, repeat: LifetimeCell())',
     'private var cells = NativeLifetimeCells()'),
    ('private var rates = Array<LifetimeEstimate>(328, repeat: LifetimeEstimate())',
     'private var rates = NativeLifetimeRates()'),
    ('private var nextCrossing = VArray<Int64, $8>(repeat: 1)',
     'private var nextCrossing = NativeLifetimeCrossings()'),
]


def fixed_owner(name, element, primitive, count, fields, initial):
    stride = len(fields)
    loads = '\n'.join(f'            result.{field} = data.read(offset + {i})'
                      for i, field in enumerate(fields))
    stores = '\n'.join(f'            data.write(offset + {i}, value.{field})'
                       for i, field in enumerate(fields))
    if element == 'Int64':
        read_body = '''        let result = unsafe { data.read(index) }
        blackBox(this)
        return result'''
        write_body = '''        unsafe { data.write(index, value) }
        let ownerFence = blackBox(this)'''
    else:
        read_body = f'''        let offset = index * {stride}
        var result = {element}()
        unsafe {{
{loads}
        }}
        blackBox(this)
        return result'''
        write_body = f'''        let offset = index * {stride}
        unsafe {{
{stores}
        }}
        let ownerFence = blackBox(this)'''
    return f'''private class {name} {{
    private let data: CPointer<{primitive}>
    public let size: Int64 = {count}

    public init() {{
        data = LibC.malloc<{primitive}>(count: {count * stride})
        if (data.isNull()) {{ throw IllegalMemoryException("Lifetime buffer allocation failed") }}
        unsafe {{ for (i in 0..{count * stride}) {{ data.write(i, {initial}) }} }}
        let ownerFence = blackBox(this)
    }}

    ~init() {{ unsafe {{ LibC.free(data) }} }}

    public operator func [](index: Int64): {element} {{
        if (index < 0 || index >= size) {{ throw IndexOutOfBoundsException("Lifetime buffer index") }}
{read_body}
    }}

    public operator func [](index: Int64, value!: {element}): Unit {{
        if (index < 0 || index >= size) {{ throw IndexOutOfBoundsException("Lifetime buffer index") }}
{write_body}
    }}
}}
'''


RECORD_OWNER = '''private class NativeLifetimeRecords {
    private var data: CPointer<Int64>
    private var capacity: Int64 = 16
    private var used: Int64 = 1

    public init() {
        data = LibC.malloc<Int64>(count: 48)
        if (data.isNull()) { throw IllegalMemoryException("Lifetime record allocation failed") }
        // Slot zero is the same default sentinel record as the ArrayList base.
        unsafe { for (i in 0..48) { data.write(i, 0) } }
        let ownerFence = blackBox(this)
    }

    ~init() { unsafe { LibC.free(data) } }

    public prop size: Int64 { get() { used } }

    public operator func [](index: Int64): LifetimeRecord {
        if (index < 0 || index >= used) { throw IndexOutOfBoundsException("Lifetime record index") }
        let offset = index * 3
        let result = unsafe { LifetimeRecord(data.read(offset), data.read(offset + 1), data.read(offset + 2) != 0) }
        blackBox(this)
        return result
    }

    public operator func [](index: Int64, value!: LifetimeRecord): Unit {
        if (index < 0 || index >= used) { throw IndexOutOfBoundsException("Lifetime record index") }
        let offset = index * 3
        unsafe {
            data.write(offset, value.born)
            data.write(offset + 1, value.length)
            data.write(offset + 2, if (value.active) { 1 } else { 0 })
        }
        let ownerFence = blackBox(this)
    }

    private func reserveForAdd(): Unit {
        if (used < capacity) { return }
        if (capacity > Int64.Max / 6) { throw IllegalMemoryException("Lifetime record capacity overflow") }
        let expandedCapacity = capacity * 2
        let expanded = LibC.malloc<Int64>(count: expandedCapacity * 3)
        if (expanded.isNull()) { throw IllegalMemoryException("Lifetime record expansion failed") }
        unsafe { for (i in 0..(used * 3)) { expanded.write(i, data.read(i)) } }
        let previous = data
        data = expanded
        capacity = expandedCapacity
        unsafe { LibC.free(previous) }
        let ownerFence = blackBox(this)
    }

    public func add(value: LifetimeRecord): Unit {
        reserveForAdd()
        let offset = used * 3
        unsafe {
            data.write(offset, value.born)
            data.write(offset + 1, value.length)
            data.write(offset + 2, if (value.active) { 1 } else { 0 })
        }
        used++
        let ownerFence = blackBox(this)
    }
}
'''


def owners():
    return ('// Concrete lifetime storage. Primitive native payloads have one owner;\n'
            '// accessors copy structs and never export pointers or managed references.\n'
            + RECORD_OWNER + '\n'
            + fixed_owner('NativeLifetimeCells', 'LifetimeCell', 'Int64', 328,
                          ['completedExposure', 'birthSum', 'active', 'deaths'], '0') + '\n'
            + fixed_owner('NativeLifetimeRates', 'LifetimeEstimate', 'Float64', 328,
                          ['mean', 'error'], '0.0') + '\n'
            + fixed_owner('NativeLifetimeCrossings', 'Int64', 'Int64', 8, ['value'], '1')
            + '\n')


def main():
    original = BASE.read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA256, 'Base changed'
    source = original
    for before, after in DECLARATIONS:
        assert source.count(before) == 1
        source = source.replace(before, after)
    marker = 'public class CensoredLifetimeModel {'
    assert source.count(marker) == 1
    owner_source = owners()
    source = source.replace(marker, owner_source + marker)
    restored = source.replace(owner_source, '', 1)
    for before, after in DECLARATIONS:
        restored = restored.replace(after, before, 1)
    assert restored == original, 'Changes must reverse exactly'
    OUT.mkdir(exist_ok=True)
    (OUT / 'solution.cj').write_text(source)
    (OUT / 'changes.diff').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), source.splitlines(True),
        fromfile='candidate-avl-inline/solution.cj', tofile='candidate-lifetime-native/solution.cj')))
    meta = {
        'schema': 'cangjie-lifetime-native-storage-v1',
        'base': str(BASE.relative_to(HERE)), 'base_sha256': BASE_SHA256,
        'output_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope': 'Only four lifetime field declarations and four new private concrete owners; every pre-existing method and struct body unchanged.',
        'storage': {'records': 'one growable Int64 allocation, triple born,length,active0/1; sentinel zero; capacity16 then doubling',
                    'cells': 'one fixed1312Int64 allocation, stride4 completedExposure,birthSum,active,deaths; zero initialized',
                    'rates': 'one fixed656Float64 allocation, stride2 mean,error; +0.0 initialized',
                    'nextCrossing': 'one fixed8Int64 allocation initialized to1; dedicated owner avoids modifying the shared FastIntBuffer'},
        'copy_semantics': 'Getters construct independent existing structs; setters copy all primitive fields. No pointer export, aliases or clones added.',
        'ownership': 'Each successfully constructed owner frees its current sole allocation once in ~init. Records reallocation copies before swapping/freeing old data. No managed references in payload.',
        'fence': 'blackBox(this) after each last native access outside finalizers, with return values copied first; native pointers never escape their owner.',
        'official105': {'commit': 'c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9',
            'malloc_free': 'https://github.com/cangjielanguage/cangjie_runtime/blob/c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9/std/libs/std/core/libc.cj',
            'pointer': 'https://github.com/cangjielanguage/cangjie_runtime/blob/c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9/std/libs/std/core/c_pointer_resource.cj',
            'blackBox': 'https://github.com/cangjielanguage/cangjie_runtime/blob/c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9/std/doc/libs/std/runtime/runtime_package_api/runtime_package_funcs.md#func-blackboxtt',
            'finalizer': 'https://github.com/cangjielanguage/cangjie_docs/blob/f8f8cd75a336e23785a4c57bd6091b2adf1e0302/docs/dev-guide/source_zh_cn/class_and_interface/class.md#class-终结器'},
        'reverse_exact': True, 'cangjie_compiled': False, 'solver_executed': False,
    }
    (OUT / 'manifest.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps({'output': str(OUT / 'solution.cj'), 'sha256': meta['output_sha256']}))


if __name__ == '__main__':
    main()
