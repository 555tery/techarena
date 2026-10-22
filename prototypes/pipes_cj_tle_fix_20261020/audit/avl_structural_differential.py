#!/usr/bin/env python3
"""Exact stable-node AVL translation; compare full and height-stable repair."""
from collections import Counter
from itertools import permutations
from pathlib import Path
import hashlib
import json
import random

HERE = Path(__file__).resolve().parent
COUNTS = Counter()


class Tree:
    def __init__(self, early):
        self.early = early
        self.root = self.count = 0
        self.left = [0]
        self.right = [0]
        self.parent = [0]
        self.heights = [0]
        self.keys = [0]
        self.values = [0]
        self.vacant = []
        self.context = None

    def fix(self, node):
        self.heights[node] = 1 + max(self.heights[self.left[node]], self.heights[self.right[node]])

    def replace(self, old, new):
        p = self.parent[old]
        if not p:
            self.root = new
        elif self.left[p] == old:
            self.left[p] = new
        else:
            self.right[p] = new
        if new:
            self.parent[new] = p

    def rotate_left(self, node):
        top = self.right[node]
        middle = self.left[top]
        self.replace(node, top)
        self.left[top] = node
        self.parent[node] = top
        self.right[node] = middle
        if middle:
            self.parent[middle] = node
        self.fix(node)
        self.fix(top)
        return top

    def rotate_right(self, node):
        top = self.left[node]
        middle = self.right[top]
        self.replace(node, top)
        self.right[top] = node
        self.parent[node] = top
        self.left[node] = middle
        if middle:
            self.parent[middle] = node
        self.fix(node)
        self.fix(top)
        return top

    def rebalance(self, node):
        visited_successor = False
        while node:
            if self.context and node == self.context[1]:
                visited_successor = True
            old_height = self.heights[node]
            self.fix(node)
            balance = self.heights[self.left[node]] - self.heights[self.right[node]]
            if balance > 1:
                child = self.left[node]
                if self.heights[self.left[child]] < self.heights[self.right[child]]:
                    self.rotate_left(child)
                node = self.rotate_right(node)
            elif balance < -1:
                child = self.right[node]
                if self.heights[self.right[child]] < self.heights[self.left[child]]:
                    self.rotate_right(child)
                node = self.rotate_left(node)
            if self.early and self.heights[node] == old_height:
                COUNTS['early_stops'] += 1
                if self.context and self.context[0] == 'deep_successor' and not visited_successor:
                    COUNTS['stops_below_transplanted_successor'] += 1
                break
            node = self.parent[node]

    def new(self, key, value, p):
        if self.vacant:
            node = self.vacant.pop()
            self.left[node] = self.right[node] = 0
            self.parent[node] = p
            self.heights[node] = 1
            self.keys[node] = key
            self.values[node] = value
        else:
            node = len(self.keys)
            self.left.append(0)
            self.right.append(0)
            self.parent.append(p)
            self.heights.append(1)
            self.keys.append(key)
            self.values.append(value)
        self.count += 1
        return node

    def put(self, key, value):
        self.context = None
        node, p, order = self.root, 0, 0
        while node:
            order = (key > self.keys[node]) - (key < self.keys[node])
            if not order:
                self.values[node] = value
                return node
            p = node
            node = self.left[node] if order < 0 else self.right[node]
        added = self.new(key, value, p)
        if not p:
            self.root = added
        elif order < 0:
            self.left[p] = added
        else:
            self.right[p] = added
        self.rebalance(p)
        return added

    def find(self, key):
        node = self.root
        while node:
            if key == self.keys[node]:
                return node
            node = self.left[node] if key < self.keys[node] else self.right[node]
        return 0

    def erase(self, node):
        self.context = None
        if not node:
            return
        if not self.left[node] or not self.right[node]:
            repair = self.parent[node]
            child = self.left[node] or self.right[node]
            self.replace(node, child)
            if self.early:
                COUNTS['at_most_one_child'] += 1
        else:
            successor = self.right[node]
            while self.left[successor]:
                successor = self.left[successor]
            if self.parent[successor] != node:
                self.context = ('deep_successor', successor)
                repair = self.parent[successor]
                self.replace(successor, self.right[successor])
                self.right[successor] = self.right[node]
                self.parent[self.right[successor]] = successor
            else:
                self.context = ('immediate_successor', successor)
                repair = successor
            self.replace(node, successor)
            self.left[successor] = self.left[node]
            self.parent[self.left[successor]] = successor
            self.heights[successor] = self.heights[node]
            if self.early:
                COUNTS[self.context[0]] += 1
        self.left[node] = self.right[node] = self.parent[node] = self.heights[node] = 0
        self.values[node] = 0
        self.vacant.append(node)
        self.count -= 1
        self.rebalance(repair)

    def structural_state(self):
        return (self.root, self.count, self.left, self.right, self.parent,
                self.heights, self.keys, self.values, self.vacant)

    def validate(self):
        seen = set()

        def visit(node, parent, low, high):
            if not node:
                return 0
            assert node not in seen
            seen.add(node)
            assert self.parent[node] == parent
            assert (low is None or low < self.keys[node]) and (high is None or self.keys[node] < high)
            left = visit(self.left[node], node, low, self.keys[node])
            right = visit(self.right[node], node, self.keys[node], high)
            assert abs(left - right) <= 1
            assert self.heights[node] == 1 + max(left, right)
            return self.heights[node]

        visit(self.root, 0, None, None)
        assert len(seen) == self.count
        assert not seen.intersection(self.vacant)
        assert len(seen) + len(self.vacant) == len(self.keys) - 1


def equal(a, b):
    COUNTS['paired_mutations_checked'] += 1
    assert a.structural_state() == b.structural_state()
    b.validate()


def perform(a, b, op, key=0, value=0):
    if op == 'put':
        assert a.put(key, value) == b.put(key, value)
    elif op == 'erase':
        assert a.find(key) == b.find(key)
        a.erase(a.find(key))
        b.erase(b.find(key))
    elif op == 'root':
        a.erase(a.root)
        b.erase(b.root)
    equal(a, b)


def main():
    workloads = 0
    # Every insertion order followed by every complete deletion order through5.
    for n in range(1, 6):
        for insertion in permutations(range(n)):
            for deletion in permutations(range(n)):
                a, b = Tree(False), Tree(True)
                for key in insertion:
                    perform(a, b, 'put', key, key + 1)
                for key in deletion:
                    perform(a, b, 'erase', key)
                workloads += 1
    exhaustive_full_delete = workloads
    # All insertion orders for6 and every single first deletion, including roots.
    for insertion in permutations(range(6)):
        for deletion in range(6):
            a, b = Tree(False), Tree(True)
            for key in insertion:
                perform(a, b, 'put', key, key + 1)
            perform(a, b, 'erase', deletion)
            workloads += 1
    # Mixed deletes, overwrites, free-slot reuse and root deletion/clear behavior.
    for seed in range(32):
        rng = random.Random(20261020 + seed)
        a, b = Tree(False), Tree(True)
        for step in range(2000):
            roll = rng.randrange(100)
            key = rng.randrange(128)
            if roll < 54:
                perform(a, b, 'put', key, step + 1)
            elif roll < 97:
                perform(a, b, 'erase', key)
            else:
                perform(a, b, 'root')
        while a.root:
            perform(a, b, 'root')
        workloads += 1
    assert COUNTS['deep_successor'] and COUNTS['immediate_successor']
    assert COUNTS['stops_below_transplanted_successor']
    parent = HERE.parent
    report = {
        'status': 'pass',
        'scope': 'Source proof and standalone structural Python differential test; no Cangjie compile/solver/platform action.',
        'generator_sha256': hashlib.sha256((parent / 'prepare_avl.py').read_bytes()).hexdigest(),
        'test_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_review': 'Generator adds oldHeight before fixHeight and compares it only after all rotations; both generic and concrete copies are matched exactly twice. No other replacement is made.',
        'proof': [
            'Before insertion/deletion, stored heights are correct. At each visited node, oldHeight represents the previous height of this subtree. After balancing, node denotes the new subtree root; comparing its updated height to oldHeight is therefore the correct propagation test.',
            'If the height is unchanged, the parent sees the same child height as before the mutation. Its opposite child is unchanged. The parent was AVL, so baseline would perform no rotation and rewrite the same height. Induction applies to every skipped ancestor, proving exact tree geometry, not only key ordering.',
            'For immediate-successor deletion, repair starts at the transplanted successor. heights[successor]=heights[deleted] gives the previous height of the replaced subtree. New left/right heights are recalculated and balanced before the equality test.',
            'For deep-successor deletion, repair begins at the old successor parent; its ancestry after transplantation reaches the successor. All nodes below successor retain their correct pre-deletion stored heights. The successor stores the old deleted-subtree height, which is exactly the oldHeight needed when repair reaches it.',
            'If repair stops below the transplanted successor, the height of that branch is unchanged at every higher level. Thus successor has the same left/right child heights as the old deleted root; its copied height is already correct and its balance is unchanged. Baseline would neither rotate nor alter height there.',
            'Rotations keep the same tie rules and stable IDs. Consequently root ID, links, parent arrays, live/inactive keys/payloads, stored heights, vacant-slot stack and future reused IDs remain identical to baseline. In-order iterators, lower/upper/find and allocator tie choices are preserved.',
        ],
        'structural_test': {
            'full_insertion_and_deletion_permutation_workloads_n1_to5': exhaustive_full_delete,
            'all_insertions_n6_each_first_deletion_workloads': 4320,
            'randomized_seeds': 32,
            'randomized_mutations_per_seed_before_final_clear': 2000,
            'randomized_key_domain': [0, 127],
            'workloads_total': workloads,
            'checks': dict(COUNTS),
            'compared_after_every_mutation': ['root', 'count', 'left', 'right', 'parent', 'heights', 'keys including vacant slots', 'values including reset slots', 'vacant free-slot stack', 'returned insertion node ID'],
            'independently_validated': ['strict BST ordering', 'exact heights', 'AVL balance', 'parent consistency', 'no cycles', 'live/free partition'],
        },
        'findings': [],
        'caveats': ['Finite differential testing supplements the propagation proof; actual Cangjie transcript parity and resource measurements remain separate parent checks.'],
    }
    (HERE / 'avl-early-stop.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': 'pass', 'workloads': workloads, 'checks': dict(COUNTS)}))


if __name__ == '__main__':
    main()
