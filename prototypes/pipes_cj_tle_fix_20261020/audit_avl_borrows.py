#!/usr/bin/env python3
"""Independent lightweight branch/bounds audit, not a Cangjie solver test."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import random
import prepare_avl_borrows as prep

HERE = Path(__file__).resolve().parent
RNG = random.Random(202610207391)
COUNTS = dict(trees=0, searches=0, neighbors=0, put_searches=0, pointer_reads=0)


@lru_cache(None)
def shapes(n):
    if n == 0:
        return (None,)
    return tuple((a, b) for k in range(n)
                 for a in shapes(k) for b in shapes(n - 1 - k))


def random_shape(n):
    if not n:
        return None
    left = RNG.randrange(n)
    return random_shape(left), random_shape(n - 1 - left)


def cmp(a, b):
    return (a > b) - (a < b)


class Tree:
    def __init__(self, shape):
        def size(s):
            return 0 if s is None else 1 + size(s[0]) + size(s[1])
        n = size(shape)
        # Include unused/recycled slots and nontrivial stable node identifiers.
        ids = list(range(1, 2 * n + 5))
        RNG.shuffle(ids)
        self.left = [0] * (2 * n + 5)
        self.right = self.left.copy()
        self.parent = self.left.copy()
        self.keys = [(0, 0, 0)] * len(self.left)
        self.live = []
        key_index = 0
        def build(s, parent):
            nonlocal key_index
            if s is None:
                return 0
            node = ids.pop()
            self.live.append(node)
            self.parent[node] = parent
            self.left[node] = build(s[0], node)
            # Extreme values exercise signed lexicographic comparison and all
            # three components. No floating-point arithmetic is involved.
            key_index += 1
            a, b = divmod(key_index, 9)
            self.keys[node] = (a - 2, b // 3 - 1, b % 3 - 1)
            self.right[node] = build(s[1], node)
            return node
        self.root = build(shape, 0)
        self.flat = [c for key in self.keys for c in key]

    def read(self, data, index):
        assert 0 <= index < len(data), (index, len(data))
        COUNTS['pointer_reads'] += 1
        return data[index]

    def direct_order(self, node, wanted):
        offset = node * 3
        first = self.read(self.flat, offset)
        order = 0
        if wanted[0] != first:
            order = -1 if wanted[0] < first else 1
        else:
            second = self.read(self.flat, offset + 1)
            if wanted[1] != second:
                order = -1 if wanted[1] < second else 1
            else:
                third = self.read(self.flat, offset + 2)
                if wanted[2] != third:
                    order = -1 if wanted[2] < third else 1
        assert order == cmp(wanted, self.keys[node])
        return order

    def old_search(self, wanted, kind):
        node, answer, p, order = self.root, 0, 0, 0
        while node:
            order = cmp(wanted, self.keys[node])
            if kind in ('find', 'put'):
                if order == 0:
                    return (node, p, order) if kind == 'put' else node
                p = node
                node = self.left[node] if order < 0 else self.right[node]
            elif order <= 0 if kind == 'lower' else order < 0:
                answer, node = node, self.left[node]
            else:
                node = self.right[node]
        return (node, p, order) if kind == 'put' else (node if kind == 'find' else answer)

    def direct_search(self, wanted, kind):
        node, answer, p, order = self.root, 0, 0, 0
        assert 0 <= node < len(self.keys)
        while node:
            order = self.direct_order(node, wanted)
            if kind in ('find', 'put'):
                if order == 0:
                    break
                p = node
                node = self.read(self.left if order < 0 else self.right, node)
            elif order <= 0 if kind == 'lower' else order < 0:
                answer, node = node, self.read(self.left, node)
            else:
                node = self.read(self.right, node)
        result = node if kind in ('find', 'put') else answer
        assert 0 <= result < len(self.keys)
        return (node, p, order) if kind == 'put' else result

    def old_edge(self, edge):
        node = self.root
        while node and edge[node]:
            node = edge[node]
        return node

    def direct_edge(self, edge):
        node = self.root
        assert 0 <= node < len(self.keys)
        while node:
            child = self.read(edge, node)
            if child == 0:
                break
            node = child
        assert 0 <= node < len(self.keys)
        return node

    def old_neighbor(self, node, nxt):
        if node == 0:
            return 0 if nxt else self.old_edge(self.right)
        cur = node
        down, extreme = (self.right, self.left) if nxt else (self.left, self.right)
        if down[cur]:
            cur = down[cur]
            while extreme[cur]:
                cur = extreme[cur]
            return cur
        p = self.parent[cur]
        while p and cur == down[p]:
            cur, p = p, self.parent[p]
        return p

    def direct_neighbor(self, node, nxt):
        if node == 0:
            return 0 if nxt else self.direct_edge(self.right)
        assert 0 <= node < len(self.keys)
        down, extreme = (self.right, self.left) if nxt else (self.left, self.right)
        cur = node
        child = self.read(down, cur)
        if child:
            cur = child
            while True:
                following = self.read(extreme, cur)
                if not following:
                    break
                cur = following
            answer = cur
        else:
            p = self.read(self.parent, cur)
            while p and cur == self.read(down, p):
                cur = p
                p = self.read(self.parent, cur)
            answer = p
        assert 0 <= answer < len(self.keys)
        return answer


def run():
    # All ordered binary shapes through 7 nodes, plus randomized larger trees.
    cases = [s for n in range(8) for s in shapes(n)]
    cases += [random_shape(RNG.randrange(8, 129)) for _ in range(128)]
    for shape in cases:
        tree = Tree(shape)
        COUNTS['trees'] += 1
        for edge in (tree.left, tree.right):
            assert tree.old_edge(edge) == tree.direct_edge(edge)
        # Also cover unused but in-bounds node slots (zeroed erased nodes).
        for node in range(len(tree.keys)):
            for nxt in (False, True):
                assert tree.old_neighbor(node, nxt) == tree.direct_neighbor(node, nxt)
                COUNTS['neighbors'] += 1
        queries = [tree.keys[node] for node in tree.live]
        queries += [(a, b, c) for a in (-2**63, -1, 0, 1, 2**63-1)
                    for b in (-2**63, 0, 2**63-1) for c in (-2**63, 0, 2**63-1)]
        for wanted in queries:
            for kind in ('find', 'lower', 'upper', 'put'):
                assert tree.old_search(wanted, kind) == tree.direct_search(wanted, kind)
                COUNTS['put_searches' if kind == 'put' else 'searches'] += 1
        for invalid in (-1, len(tree.keys), len(tree.keys)+1):
            for nxt in (False, True):
                try:
                    tree.direct_neighbor(invalid, nxt)
                except AssertionError:
                    pass
                else:
                    raise AssertionError('Missing invalid entry guard')

    original = prep.BASE.read_text()
    output = (prep.OUT / 'solution.cj').read_text()
    # Reversing exactly the declared replacements and two borrower additions
    # must recover the base byte-for-byte. This protects all writes, clone,
    # recycle, reserve, DP, policy, FP arithmetic and non-Map code.
    restored = output
    for class_name in ('OrderedMap<V>', 'IntOrderedMap'):
        a = original.index('public class ' + class_name + ' {')
        b = original.index('\npublic class ', a + 1)
        old = original[a:b]
        a = restored.index('public class ' + class_name + ' {')
        b = restored.index('\npublic class ', a + 1)
        new = restored[a:b]
        for name in ('first', 'last', 'next', 'prev', 'find', 'lower', 'upper', 'put'):
            sig = 'public func ' + name + '('
            lo, hi = prep.method_span(old, sig)
            nl, nh = prep.method_span(new, sig)
            replacement = new[nl:nh]
            assert '.write(' not in replacement
            assert replacement.count('blackBox(this)') == 1
            assert replacement.rfind('.read(') < replacement.index('blackBox(this)')
            before_fence = replacement.split('blackBox(this)', 1)[0]
            assert before_fence.count('{') - before_fence.count('}') == 1
            if name == 'put':
                assert replacement.index('blackBox(this)') < replacement.index('values[node] = v')
                assert replacement.index('blackBox(this)') < replacement.index('newNode(k, v, p)')
                old_tail = old[lo:hi].split('        let added = newNode', 1)[1]
                assert replacement.split('        let added = newNode', 1)[1] == old_tail
            new = new[:nl] + old[lo:hi] + new[nh:]
        restored = restored[:a] + new + restored[b:]
    borrower = '''

    // Package-internal, transient read-only borrows; callers retain this owner
    // and finish the borrow before add/reserve can replace the allocation.
    func borrowData(): CPointer<Int64> { data }'''
    assert restored.count(borrower) == 2
    restored = restored.replace(borrower, '')
    assert restored == original
    result = {
        'schema': 'avl-read-borrows-independent-audit-v1',
        'base_sha256': hashlib.sha256(original.encode()).hexdigest(),
        'output_sha256': hashlib.sha256(output.encode()).hexdigest(),
        'audit_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'counts': COUNTS, 'mismatches': 0,
        'scope': 'Both Map classes: first,last,next,prev,find,lower,upper; put search only.',
        'unchanged': 'Reversal proves all other bytes unchanged. put insertion tail is byte-identical. No new pointer writes.',
        'bounds': 'Entry checked against allocated key slots (includes sentinel and vacant slots), not live count. Every translated pointer read checked in Python. Internal link bounds and acyclicity rely on existing tree invariants; corrupt-link exception behavior is not promised.',
        'lifetime': 'No owner fields change or storage grows in read-only methods. put pointer locals end before values write/newNode/rebalance. All16methods call the public documented optimizer barrier blackBox(this) after their last pointer read. This retains a strong Map use beyond the borrow and its private owning fields remain reachable. Internal links must satisfy the pre-existing tree invariants. No raw managed Array pinning occurs.',
        'documented_barrier_implemented': {
            'api': 'import std.runtime.blackBox; public func blackBox<T>(input:T):T',
            'availability': 'Official1.0.5 declaration is public @Frozen @Intrinsic, gated only to cjnative backend; no OS guard.',
            'official_contract': 'The1.0.5 runtime API says the input enters an optimization black box and cannot be subject to dead-code elimination and similar optimizations.',
            'official_version': '1.0.5',
            'official_runtime_commit': 'c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9',
            'application': 'A blackBox(this) use after pointer reads is the documented anti-DCE alternative to a redundant keys.size guard or global strong keeper. Since a live Map reaches all its private vector fields, no separate field keeper is needed. This is a reasoned application of the public optimizer contract; the docs do not separately name GC reachabilityFence semantics. Inserted exactly once after the last pointer read in each of16methods, before any put values write/newNode/rebalance.',
            'source': 'https://github.com/cangjielanguage/cangjie_runtime/blob/c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9/std/doc/libs/std/runtime/runtime_package_api/runtime_package_funcs.md#func-blackboxtt',
            'declaration': 'https://github.com/cangjielanguage/cangjie_runtime/blob/c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9/std/libs/std/runtime/runtime_memoryInfo.cj#L25-L28'
        },
        'official_sources': [
            'https://github.com/cangjielanguage/cangjie_docs/blob/f8f8cd75a336e23785a4c57bd6091b2adf1e0302/docs/dev-guide/source_zh_cn/class_and_interface/class.md#class-终结器',
            'https://github.com/cangjielanguage/cangjie_runtime/blob/c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9/std/libs/std/core/c_pointer_resource.cj',
            'https://github.com/cangjielanguage/cangjie_runtime/blob/c6aa169ce8c6aaeb65cb1262bddb3700aebe8cb9/std/libs/std/core/libc.cj'],
        'limits': 'Python is a branch/bounds model, not Cangjie code execution. No compilation, solver, profile, target Windows execution or GC stress run.',
        'cangjie_compiled': False, 'solver_executed': False,
    }
    (HERE / 'audit/avl-borrows-fenced.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    run()
