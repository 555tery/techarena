#!/usr/bin/env python3
"""Prepare read-only native AVL walks. Never compiles or executes Cangjie."""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'candidate-exact-fast/solution.cj'
OUT = HERE / 'candidate-avl-borrows-fenced'
BASE_SHA256 = '4e7efbcfd0b3d7f1d2cd2ca6f8764afa4bdee46566294116272d27e778cbf2b9'


def method_span(text, signature):
    start = text.index('    ' + signature)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return start, end


def comparison(wanted, assign='let order', indent=16):
    # Exact lexicographic sign: wanted versus stored. No subtraction/overflow.
    p = ' ' * indent
    return '\n'.join(p + line for line in f'''let offset = node * 3
let first = keyData.read(offset)
var keyOrder: Int64 = 0
if ({wanted}.a != first) {{ keyOrder = if ({wanted}.a < first) {{ -1 }} else {{ 1 }} }}
else {{
    let second = keyData.read(offset + 1)
    if ({wanted}.b != second) {{ keyOrder = if ({wanted}.b < second) {{ -1 }} else {{ 1 }} }}
    else {{
        let third = keyData.read(offset + 2)
        if ({wanted}.c != third) {{ keyOrder = if ({wanted}.c < third) {{ -1 }} else {{ 1 }} }}
    }}
}}
{assign} = keyOrder'''.splitlines())


def guard(name, slots='nodeSlots'):
    return f'        if ({name} < 0 || {name} >= {slots}) {{ throw IndexOutOfBoundsException("AVL node index") }}'


def finish(name):
    # Access to this owner occurs after every pointer read, keeping the Map and
    # its private vectors reachable throughout the unsafe block.
    return f'''        // Public1.0.5 optimizer black box retains the strong owner use.
        blackBox(this)
{guard(name, 'this.keys.size')}
        return {name}'''


def edge_method(name, edge):
    return f'''    public func {name}(): Int64 {{
        var node = root
        let nodeSlots = keys.size
{guard('node')}
        unsafe {{
            let edgeData = {edge}.borrowData()
            while (node != 0) {{
                let child = edgeData.read(node)
                if (child == 0) {{ break }}
                node = child
            }}
        }}
{finish('node')}
    }}'''


def neighbor_method(name):
    nxt = name == 'next'
    down, extreme, upward = ('right', 'left', 'right') if nxt else ('left', 'right', 'left')
    zero = '0' if nxt else 'last()'
    return f'''    public func {name}(node: Int64): Int64 {{
        if (node == 0) {{ return {zero} }}
        let nodeSlots = keys.size
{guard('node')}
        var answer: Int64 = 0
        unsafe {{
            let leftData = left.borrowData()
            let rightData = right.borrowData()
            let parentData = parent.borrowData()
            var cur = node
            let child = {down}Data.read(cur)
            if (child != 0) {{
                cur = child
                while (true) {{
                    let following = {extreme}Data.read(cur)
                    if (following == 0) {{ break }}
                    cur = following
                }}
                answer = cur
            }} else {{
                var p = parentData.read(cur)
                while (p != 0 && cur == {upward}Data.read(p)) {{ cur = p; p = parentData.read(cur) }}
                answer = p
            }}
        }}
{finish('answer')}
    }}'''


def search_method(name):
    prefix = f'''    public func {name}(wanted: Key): Int64 {{
        var node = root
        let nodeSlots = keys.size
{guard('node')}
'''
    if name != 'find':
        prefix += '        var answer: Int64 = 0\n'
    prefix += '''        unsafe {
            let leftData = left.borrowData()
            let rightData = right.borrowData()
            let keyData = keys.borrowData()
            while (node != 0) {
'''
    prefix += comparison('wanted') + '\n'
    if name == 'find':
        prefix += '''                if (order == 0) { break }
                node = if (order < 0) { leftData.read(node) } else { rightData.read(node) }
'''
    else:
        op = '<=' if name == 'lower' else '<'
        prefix += f'''                if (order {op} 0) {{
                    answer = node; node = leftData.read(node)
                }} else {{ node = rightData.read(node) }}
'''
    return prefix + f'''            }}
        }}
{finish('node' if name == 'find' else 'answer')}
    }}'''


def put_method(value_type):
    return f'''    public func put(k: Key, v: {value_type}): Int64 {{
        var node = root
        var p: Int64 = 0
        var order: Int64 = 0
        let nodeSlots = keys.size
{guard('node')}
        // This scope ends before values writes, newNode, append, or rebalance.
        unsafe {{
            let leftData = left.borrowData()
            let rightData = right.borrowData()
            let keyData = keys.borrowData()
            while (node != 0) {{
{comparison('k', 'order')}
                if (order == 0) {{ break }}
                p = node
                node = if (order < 0) {{ leftData.read(node) }} else {{ rightData.read(node) }}
            }}
        }}
        blackBox(this)
        if (node != 0) {{ values[node] = v; return node }}
        let added = newNode(k, v, p)
        if (p == 0) {{ root = added }}
        else if (order < 0) {{ left[p] = added }}
        else {{ right[p] = added }}
        rebalance(p)
        return added
    }}'''


def main():
    original = BASE.read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA256, 'Base changed'
    source = original
    changed = []
    for class_name in ('FastIntVector', 'FastKeyVector'):
        start = source.index('public class ' + class_name + ' {')
        end = source.index('\npublic class ', start + 1)
        block = source[start:end]
        marker = '    public prop size: Int64 { get() { used } }'
        assert block.count(marker) == 1
        block = block.replace(marker, marker + '''

    // Package-internal, transient read-only borrows; callers retain this owner
    // and finish the borrow before add/reserve can replace the allocation.
    func borrowData(): CPointer<Int64> { data }''')
        source = source[:start] + block + source[end:]
    replacements = {
        'first': edge_method('first', 'left'),
        'last': edge_method('last', 'right'),
        'next': neighbor_method('next'),
        'prev': neighbor_method('prev'),
        **{name: search_method(name) for name in ('find', 'lower', 'upper')},
    }
    for class_name, value_type in [('OrderedMap<V>', 'V'), ('IntOrderedMap', 'Int64')]:
        start = source.index('public class ' + class_name + ' {')
        end = source.index('\npublic class ', start + 1)
        block = source[start:end]
        for name, replacement in {**replacements, 'put': put_method(value_type)}.items():
            signature = 'public func ' + name + '('
            lo, hi = method_span(block, signature)
            old = block[lo:hi]
            changed.append({'class': class_name, 'method': name,
                            'old_sha256': hashlib.sha256(old.encode()).hexdigest(),
                            'new_sha256': hashlib.sha256(replacement.encode()).hexdigest()})
            block = block[:lo] + replacement + block[hi:]
        source = source[:start] + block + source[end:]
    OUT.mkdir(exist_ok=True)
    (OUT / 'solution.cj').write_text(source)
    (OUT / 'changes.diff').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), source.splitlines(True),
        fromfile='candidate-exact-fast/solution.cj', tofile='candidate-avl-borrows-fenced/solution.cj')))
    manifest = {'base': str(BASE.relative_to(HERE)), 'base_sha256': BASE_SHA256,
                'output_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'changed_methods': changed, 'cangjie_compiled': False, 'solver_executed': False,
                'owner_fence': {
                    'api': 'std.runtime.blackBox<T>(input:T):T',
                    'placement': 'blackBox(this) after the last pointer read in each modified method, before any put mutation/reallocation.',
                    'official_version': '1.0.5',
                    'official_runtime_commit': 'c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9',
                    'contract': 'Input enters an optimizer black box and cannot be subject to dead-code elimination and similar optimizations.',
                    'sources': [
                        'https://github.com/cangjielanguage/cangjie_runtime/blob/c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9/std/doc/libs/std/runtime/runtime_package_api/runtime_package_funcs.md#func-blackboxtt',
                        'https://github.com/cangjielanguage/cangjie_runtime/blob/c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9/std/libs/std/runtime/runtime_memoryInfo.cj#L25-L28'],
                    'inference': 'The post-read strong Map use keeps its private owning vectors reachable throughout borrow; no vector field is changed or grown in that interval.',
                    'availability': 'Public @Frozen @Intrinsic; only cjnative backend guard, no Windows/macOS OS guard.',
                    'limits': 'Documented anti-DCE mechanism, not an API separately named GC keepAlive. No assembly inspection or Cangjie execution in this task.'}}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(OUT / 'solution.cj'), 'sha256': manifest['output_sha256']}))


if __name__ == '__main__':
    main()
