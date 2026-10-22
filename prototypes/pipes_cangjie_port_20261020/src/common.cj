package pipes

import std.collection.*

func iMin(a: Int64, b: Int64): Int64 { if (a < b) { a } else { b } }
func iMax(a: Int64, b: Int64): Int64 { if (a > b) { a } else { b } }
func fMin(a: Float64, b: Float64): Float64 { if (a < b) { a } else { b } }
func fMax(a: Float64, b: Float64): Float64 { if (a > b) { a } else { b } }

// The live domains are nonnegative and fit Int64, including release epochs.
public struct Key {
    public let a: Int64
    public let b: Int64
    public let c: Int64
    public init(a: Int64) { this.a = a; this.b = 0; this.c = 0 }
    public init(a: Int64, b: Int64) { this.a = a; this.b = b; this.c = 0 }
    public init(a: Int64, b: Int64, c: Int64) { this.a = a; this.b = b; this.c = c }
}

func compareKey(a: Key, b: Key): Int64 {
    if (a.a != b.a) { return if (a.a < b.a) { -1 } else { 1 } }
    if (a.b != b.b) { return if (a.b < b.b) { -1 } else { 1 } }
    if (a.c != b.c) { return if (a.c < b.c) { -1 } else { 1 } }
    return 0
}

// AVL tree with stable node IDs. Erasing a node transplants its successor;
// it never swaps another live node's key or payload into the erased node ID.
// Arrays and recycled node slots avoid one managed allocation per tree node.
public class OrderedMap<V> {
    private let zero: V
    private var root: Int64 = 0
    private var count: Int64 = 0
    private var left = ArrayList<Int64>()
    private var right = ArrayList<Int64>()
    private var parent = ArrayList<Int64>()
    private var heights = ArrayList<Int64>()
    private var keys = ArrayList<Key>()
    private var values = ArrayList<V>()
    private var vacant = ArrayList<Int64>()

    public init(defaultValue: V) {
        zero = defaultValue
        left.add(0); right.add(0); parent.add(0); heights.add(0)
        keys.add(Key(0)); values.add(defaultValue)
    }
    public prop size: Int64 { get() { count } }
    public func isEmpty(): Bool { count == 0 }
    public func key(node: Int64): Key { keys[node] }
    public func value(node: Int64): V { values[node] }
    public func setValue(node: Int64, value: V): Unit { values[node] = value }

    public func first(): Int64 {
        var node = root
        while (node != 0 && left[node] != 0) { node = left[node] }
        return node
    }
    public func last(): Int64 {
        var node = root
        while (node != 0 && right[node] != 0) { node = right[node] }
        return node
    }
    public func next(node: Int64): Int64 {
        if (node == 0) { return 0 }
        var cur = node
        if (right[cur] != 0) {
            cur = right[cur]
            while (left[cur] != 0) { cur = left[cur] }
            return cur
        }
        var p = parent[cur]
        while (p != 0 && cur == right[p]) { cur = p; p = parent[cur] }
        return p
    }
    public func prev(node: Int64): Int64 {
        if (node == 0) { return last() }
        var cur = node
        if (left[cur] != 0) {
            cur = left[cur]
            while (right[cur] != 0) { cur = right[cur] }
            return cur
        }
        var p = parent[cur]
        while (p != 0 && cur == left[p]) { cur = p; p = parent[cur] }
        return p
    }
    public func find(wanted: Key): Int64 {
        var node = root
        while (node != 0) {
            let order = compareKey(wanted, keys[node])
            if (order == 0) { return node }
            node = if (order < 0) { left[node] } else { right[node] }
        }
        return 0
    }
    public func lower(wanted: Key): Int64 {
        var node = root
        var answer: Int64 = 0
        while (node != 0) {
            if (compareKey(keys[node], wanted) >= 0) {
                answer = node; node = left[node]
            } else { node = right[node] }
        }
        return answer
    }
    public func upper(wanted: Key): Int64 {
        var node = root
        var answer: Int64 = 0
        while (node != 0) {
            if (compareKey(keys[node], wanted) > 0) {
                answer = node; node = left[node]
            } else { node = right[node] }
        }
        return answer
    }
    private func fixHeight(node: Int64): Unit {
        heights[node] = 1 + iMax(heights[left[node]], heights[right[node]])
    }
    private func replaceAtParent(oldNode: Int64, newNode: Int64): Unit {
        let p = parent[oldNode]
        if (p == 0) { root = newNode }
        else if (left[p] == oldNode) { left[p] = newNode }
        else { right[p] = newNode }
        if (newNode != 0) { parent[newNode] = p }
    }
    private func rotateLeft(node: Int64): Int64 {
        let top = right[node]
        let middle = left[top]
        replaceAtParent(node, top)
        left[top] = node; parent[node] = top
        right[node] = middle
        if (middle != 0) { parent[middle] = node }
        fixHeight(node); fixHeight(top)
        return top
    }
    private func rotateRight(node: Int64): Int64 {
        let top = left[node]
        let middle = right[top]
        replaceAtParent(node, top)
        right[top] = node; parent[node] = top
        left[node] = middle
        if (middle != 0) { parent[middle] = node }
        fixHeight(node); fixHeight(top)
        return top
    }
    private func rebalance(start: Int64): Unit {
        var node = start
        while (node != 0) {
            fixHeight(node)
            let balance = heights[left[node]] - heights[right[node]]
            if (balance > 1) {
                let child = left[node]
                if (heights[left[child]] < heights[right[child]]) { rotateLeft(child) }
                node = rotateRight(node)
            } else if (balance < -1) {
                let child = right[node]
                if (heights[right[child]] < heights[left[child]]) { rotateRight(child) }
                node = rotateLeft(node)
            }
            node = parent[node]
        }
    }
    private func newNode(k: Key, v: V, p: Int64): Int64 {
        var node: Int64
        if (vacant.size > 0) {
            node = vacant.remove(at: vacant.size - 1)
            left[node] = 0; right[node] = 0; parent[node] = p
            heights[node] = 1; keys[node] = k; values[node] = v
        } else {
            node = keys.size
            left.add(0); right.add(0); parent.add(p); heights.add(1)
            keys.add(k); values.add(v)
        }
        count++
        return node
    }
    public func put(k: Key, v: V): Int64 {
        var node = root
        var p: Int64 = 0
        var order: Int64 = 0
        while (node != 0) {
            order = compareKey(k, keys[node])
            if (order == 0) { values[node] = v; return node }
            p = node
            node = if (order < 0) { left[node] } else { right[node] }
        }
        let added = newNode(k, v, p)
        if (p == 0) { root = added }
        else if (order < 0) { left[p] = added }
        else { right[p] = added }
        rebalance(p)
        return added
    }
    public func eraseKey(k: Key): Unit {
        let node = find(k)
        if (node != 0) { eraseNode(node) }
    }
    public func eraseNode(node: Int64): Unit {
        if (node == 0) { return }
        var repair: Int64
        if (left[node] == 0 || right[node] == 0) {
            repair = parent[node]
            let child = if (left[node] != 0) { left[node] } else { right[node] }
            replaceAtParent(node, child)
        } else {
            var successor = right[node]
            while (left[successor] != 0) { successor = left[successor] }
            if (parent[successor] != node) {
                repair = parent[successor]
                replaceAtParent(successor, right[successor])
                right[successor] = right[node]
                parent[right[successor]] = successor
            } else { repair = successor }
            replaceAtParent(node, successor)
            left[successor] = left[node]
            parent[left[successor]] = successor
            heights[successor] = heights[node]
        }
        left[node] = 0; right[node] = 0; parent[node] = 0; heights[node] = 0
        values[node] = zero
        vacant.add(node); count--
        rebalance(repair)
    }
    public func clone(): OrderedMap<V> {
        let result = OrderedMap<V>(zero)
        result.root = root; result.count = count
        result.left = left.clone(); result.right = right.clone()
        result.parent = parent.clone(); result.heights = heights.clone()
        result.keys = keys.clone(); result.values = values.clone()
        result.vacant = vacant.clone()
        return result
    }
    public func clear(): Unit {
        while (root != 0) { eraseNode(root) }
    }
}

public class Ring<T> {
    private let zero: T
    private var data: Array<T>
    private var head: Int64 = 0
    private var count: Int64 = 0
    public init(defaultValue: T) {
        zero = defaultValue
        data = Array<T>(16, { _ => defaultValue })
    }
    public prop size: Int64 { get() { count } }
    public func get(index: Int64): T { data[(head + index) % data.size] }
    public func back(): T { get(count - 1) }
    public func pushBack(value: T): Unit {
        if (count == data.size) {
            let expanded = Array<T>(data.size * 2, { _ => zero })
            for (i in 0..count) { expanded[i] = get(i) }
            data = expanded; head = 0
        }
        data[(head + count) % data.size] = value
        count++
    }
    public func popFront(): Unit {
        data[head] = zero
        head = (head + 1) % data.size
        count--
    }
    public func popBack(): Unit {
        count--; data[(head + count) % data.size] = zero
    }
    public func clone(): Ring<T> {
        let result = Ring<T>(zero)
        for (i in 0..count) { result.pushBack(get(i)) }
        return result
    }
}
