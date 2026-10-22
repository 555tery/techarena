package pipes

import std.collection.*

// Independent sorted-vector oracle; deliberately does not use compareKey.
class Oracle {
    let keys = ArrayList<Key>()
    let values = ArrayList<Int64>()
    let ids = ArrayList<Int64>()
    func lower(key: Key): Int64 {
        var i: Int64 = 0
        while (i < keys.size && oracleCompare(keys[i], key) < 0) { i++ }
        return i
    }
    func upper(key: Key): Int64 {
        var i: Int64 = 0
        while (i < keys.size && oracleCompare(keys[i], key) <= 0) { i++ }
        return i
    }
    func put(key: Key, value: Int64, id: Int64): Unit {
        let pos = lower(key)
        if (pos < keys.size && oracleCompare(keys[pos], key) == 0) {
            require(ids[pos] == id, "put changed existing node ID")
            values[pos] = value
            return
        }
        // Append and shift instead of sharing any map/search implementation.
        keys.add(key); values.add(value); ids.add(id)
        var i = keys.size - 1
        while (i > pos) { keys[i] = keys[i - 1]; values[i] = values[i - 1]; ids[i] = ids[i - 1]; i-- }
        keys[pos] = key; values[pos] = value; ids[pos] = id
    }
    func erase(pos: Int64): Unit {
        keys.remove(at: pos); values.remove(at: pos); ids.remove(at: pos)
    }
}

func oracleCompare(a: Key, b: Key): Int64 {
    if (a.a < b.a) { return -1 }
    if (a.a > b.a) { return 1 }
    if (a.b < b.b) { return -1 }
    if (a.b > b.b) { return 1 }
    if (a.c < b.c) { return -1 }
    if (a.c > b.c) { return 1 }
    return 0
}

func require(condition: Bool, message: String): Unit {
    if (!condition) { throw Exception(message) }
}

func checkQueries(tree: OrderedMap<Int64>, oracle: Oracle, key: Key): Unit {
    let lower = oracle.lower(key)
    let upper = oracle.upper(key)
    let expectedLower = if (lower == oracle.keys.size) { 0 } else { oracle.ids[lower] }
    let expectedUpper = if (upper == oracle.keys.size) { 0 } else { oracle.ids[upper] }
    let expectedFind = if (lower < oracle.keys.size && oracleCompare(oracle.keys[lower], key) == 0) { oracle.ids[lower] } else { 0 }
    require(tree.lower(key) == expectedLower, "lower disagrees with sorted oracle")
    require(tree.upper(key) == expectedUpper, "upper disagrees with sorted oracle")
    require(tree.find(key) == expectedFind, "find disagrees with sorted oracle")
}

func checkTree(tree: OrderedMap<Int64>, oracle: Oracle): Unit {
    require(tree.size == oracle.keys.size, "size disagrees with oracle")
    require(tree.isEmpty() == (oracle.keys.size == 0), "isEmpty disagrees with oracle")
    require(tree.prev(0) == tree.last(), "prev(end) is not last")
    require(tree.next(0) == 0, "next(end) is not end")
    var node = tree.first()
    var i: Int64 = 0
    while (node != 0) {
        require(i < oracle.keys.size, "ascending traversal cycle or extra node")
        require(node == oracle.ids[i], "surviving node changed its ID")
        require(oracleCompare(tree.key(node), oracle.keys[i]) == 0, "ascending key order differs")
        require(tree.value(node) == oracle.values[i], "ascending payload differs")
        require(tree.find(oracle.keys[i]) == node, "find lost a traversed node")
        let successor = tree.next(node)
        if (successor != 0) { require(tree.prev(successor) == node, "next/prev linkage differs") }
        node = successor
        i++
    }
    require(i == oracle.keys.size, "ascending traversal missed nodes")
    node = tree.last()
    i = oracle.keys.size - 1
    while (node != 0) {
        require(i >= 0, "descending traversal cycle or extra node")
        require(node == oracle.ids[i], "descending node ID differs")
        require(oracleCompare(tree.key(node), oracle.keys[i]) == 0, "descending key order differs")
        require(tree.value(node) == oracle.values[i], "descending payload differs")
        node = tree.prev(node)
        i--
    }
    require(i == -1, "descending traversal missed nodes")
    checkQueries(tree, oracle, Key(Int64.Min, Int64.Min, Int64.Min))
    checkQueries(tree, oracle, Key(Int64.Max, Int64.Max, Int64.Max))
}

func targeted(): Unit {
    let tree = OrderedMap<Int64>(0)
    let oracle = Oracle()
    // This inserts both immediate and deeper successors, including a deeper
    // successor with its own right child. Every surviving ID is checked.
    for (x in [40, 20, 60, 10, 30, 50, 70, 45, 55, 47]) {
        let key = Key(x)
        oracle.put(key, x * 11, tree.put(key, x * 11))
    }
    checkTree(tree, oracle)
    let successorId = tree.find(Key(45))
    let erasedId = tree.find(Key(40))
    tree.eraseNode(erasedId)
    oracle.erase(oracle.lower(Key(40)))
    require(tree.find(Key(45)) == successorId, "two-child erase changed deeper successor ID")
    checkTree(tree, oracle)
    let reused = tree.put(Key(41), 451)
    require(reused == erasedId, "deleted node slot was not reused")
    oracle.put(Key(41), 451, reused)
    checkTree(tree, oracle)

    let immediate = OrderedMap<Int64>(0)
    let immediateOracle = Oracle()
    for (x in [2, 1, 3]) { immediateOracle.put(Key(x), x, immediate.put(Key(x), x)) }
    let immediateSuccessor = immediate.find(Key(3))
    immediate.eraseKey(Key(2))
    immediateOracle.erase(immediateOracle.lower(Key(2)))
    require(immediate.find(Key(3)) == immediateSuccessor, "two-child erase changed immediate successor ID")
    checkTree(immediate, immediateOracle)
    immediate.eraseKey(Key(1)); immediateOracle.erase(0)
    immediate.eraseKey(Key(3)); immediateOracle.erase(0)
    checkTree(immediate, immediateOracle)
    immediate.eraseNode(0)
    immediate.eraseKey(Key(999))
    checkTree(immediate, immediateOracle)
}

func checkClone(tree: OrderedMap<Int64>, oracle: Oracle, step: Int64): Unit {
    let copy = tree.clone()
    checkTree(copy, oracle)
    if (oracle.keys.size > 0) {
        let firstKey = oracle.keys[0]
        let firstId = oracle.ids[0]
        let originalValue = oracle.values[0]
        tree.setValue(firstId, originalValue + 1)
        require(copy.value(firstId) == originalValue, "clone payload changed with source mutation")
        tree.setValue(firstId, originalValue)
        copy.eraseNode(firstId)
        require(tree.find(firstKey) == firstId, "clone erase changed original structure")
        require(tree.value(firstId) == originalValue, "clone erase changed original payload")
    }
    let specialKey = Key(9999, step, 1)
    copy.put(specialKey, step)
    require(tree.find(specialKey) == 0, "clone insertion leaked into source")
    copy.clear()
    require(copy.size == 0 && copy.first() == 0 && copy.last() == 0, "clone clear failed")
    checkTree(tree, oracle)
}

class Random {
    var state: Int64 = 0x735a2d19
    func next(): Int64 {
        state = (state ^ (state << 13)) & 0xffffffff
        state = (state ^ (state >> 17)) & 0xffffffff
        state = (state ^ (state << 5)) & 0xffffffff
        return state
    }
}

main(): Int64 {
    targeted()
    let tree = OrderedMap<Int64>(0)
    let oracle = Oracle()
    let random = Random()
    var inserts: Int64 = 0
    var deletes: Int64 = 0
    var updates: Int64 = 0
    for (step in 0..20000) {
        let key = Key(random.next() % 33, random.next() % 5, random.next() % 3)
        let operation = random.next() % 10
        let pos = oracle.lower(key)
        let exists = pos < oracle.keys.size && oracleCompare(oracle.keys[pos], key) == 0
        if (operation < 4) {
            let value = random.next()
            let id = tree.put(key, value)
            oracle.put(key, value, id)
            inserts++
        } else if (operation < 7) {
            if (operation == 4 && exists) { tree.eraseNode(oracle.ids[pos]) }
            else { tree.eraseKey(key) }
            if (exists) { oracle.erase(pos) }
            deletes++
        } else if (operation == 7 && exists) {
            let value = random.next()
            tree.setValue(oracle.ids[pos], value)
            oracle.values[pos] = value
            updates++
        }
        checkQueries(tree, oracle, key)
        checkQueries(tree, oracle, Key(random.next() % 35, random.next() % 7, random.next() % 5))
        checkTree(tree, oracle)
        if (step % 500 == 0) { checkClone(tree, oracle, step) }
    }
    println("PASS 20000 randomized operations; puts=${inserts}, erases=${deletes}, setValue=${updates}; targeted successor IDs, node reuse, clone independence, bounds, ascending/descending order")
    return 0
}
