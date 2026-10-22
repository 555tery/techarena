package pipes

import std.collection.*
import std.env.*
import std.runtime.*

// Only the public tables are offline information. A table survives while its
// entire observed command prefix matches, and every placement is guarded.
class ReplayTable {
    public let commands: Array<Int64>
    public let positions: Array<Int64>
    public init(commands: Array<Int64>, positions: Array<Int64>) {
        this.commands = commands
        this.positions = positions
    }
}

// Streaming base64 + unsigned varint decoder. Keep only 32 buffer bits, as in
// the C++ decoder; signed integers use the same zigzag encoding.
class ReplayDecoder {
    private var buffer: Int64 = 0
    private var bits: Int64 = -8
    private var value: Int64 = 0
    private var shift: Int64 = 0
    private var expected: Int64 = -1
    private var index: Int64 = 0
    private var previous: Int64 = 0
    private var needsPosition = false
    private var commands = Array<Int64>(0, repeat: 0)
    private var positions = Array<Int64>(0, repeat: 0)

    private func acceptByte(byte: Int64): Unit {
        value = value | ((byte & 127) << shift)
        if ((byte & 128) != 0) {
            shift += 7
            if (shift > 28) { throw Exception("bad table varint") }
            return
        }
        let decoded = value
        value = 0
        shift = 0
        if (expected < 0) {
            expected = decoded
            commands = Array<Int64>(expected, repeat: 0)
            positions = Array<Int64>(expected, repeat: -1)
            return
        }
        if (index >= expected) { throw Exception("table tail") }
        let signedValue = if ((decoded & 1) != 0) { -(decoded + 1) / 2 } else { decoded / 2 }
        if (needsPosition) {
            previous += signedValue
            positions[index] = previous
            needsPosition = false
            index++
        } else {
            commands[index] = signedValue
            if (signedValue > 0) { needsPosition = true } else { index++ }
        }
    }

    public func feed(text: String): Unit {
        for (i in 0..text.size) {
            let c = Int64(text[i])
            let digit: Int64 = if (c >= 65 && c <= 90) { c - 65 }
                else if (c >= 97 && c <= 122) { c - 97 + 26 }
                else if (c >= 48 && c <= 57) { c - 48 + 52 }
                else if (c == 43) { 62 } else if (c == 47) { 63 } else { -1 }
            if (digit < 0) { continue }
            buffer = ((buffer << 6) | digit) & 4294967295
            bits += 6
            if (bits >= 0) { acceptByte((buffer >> bits) & 255); bits -= 8 }
        }
    }
    public func finish(): ReplayTable {
        if (expected < 0 || index != expected || needsPosition || shift != 0) {
            throw Exception("truncated replay table")
        }
        return ReplayTable(commands, positions)
    }
}

class PhysicalAllocator {
    public var trench: Int64 = 0
    public let gaps = OrderedMap<Int64>(0)
    // Historical coordinates stay available even after the pipe is deleted.
    public let pipes = ArrayList<Key>()
    public init() { pipes.add(Key(0, 0)) }

    public func add(left: Int64, right: Int64): Unit {
        var l = left
        var r = right
        if (l >= r) { return }
        var it = gaps.lower(Key(l))
        if (it != gaps.first()) {
            let p = gaps.prev(it)
            if (gaps.value(p) == l) { l = gaps.key(p).a; gaps.eraseNode(p) }
        }
        it = gaps.lower(Key(l))
        if (it != 0 && gaps.key(it).a == r) { r = gaps.value(it); gaps.eraseNode(it) }
        gaps.put(Key(l), r)
    }

    public func fits(x: Int64, n: Int64): Bool {
        if (x < 0 || x + n > 100000000) { return false }
        if (x >= trench) { return true }
        let upper = gaps.upper(Key(x))
        if (upper == gaps.first()) { return false }
        let it = gaps.prev(upper)
        return gaps.key(it).a <= x && (gaps.value(it) >= x + n || gaps.value(it) == trench)
    }

    public func place(n: Int64, x: Int64): Unit {
        let digs = iMax(0, (x + n - trench + 19) / 20)
        if (digs > 0) { add(trench, trench + 20 * digs); trench += 20 * digs }
        let upper = gaps.upper(Key(x))
        if (upper == gaps.first()) { throw Exception("no replay gap") }
        let it = gaps.prev(upper)
        let l = gaps.key(it).a
        let r = gaps.value(it)
        if (x < l || x + n > r) { throw Exception("replay overlap") }
        gaps.eraseNode(it)
        add(l, x)
        add(x + n, r)
        pipes.add(Key(x, n))
        answer(digs, x)
    }

    public func remove(id: Int64): Unit {
        if (id <= 0 || id >= pipes.size || pipes[id].b <= 0) { throw Exception("bad replay PID") }
        let p = pipes[id]
        add(p.a, p.a + p.b)
        pipes[id] = Key(p.a, 0)
        answerRemoval(p.a)
    }
}

func guardedReplay(actual: PhysicalAllocator, x: Int64, n: Int64, shadowTrench: Int64): Bool {
    if (!actual.fits(x, n)) { return false }
    let digs = iMax(0, (x + n - actual.trench + 19) / 20)
    let newTrench = actual.trench + 20 * digs
    if (newTrench > shadowTrench) { return false }
    var left = actual.trench
    var right = newTrench
    if (x < actual.trench) {
        let upper = actual.gaps.upper(Key(x))
        if (upper == actual.gaps.first()) { return false }
        let it = actual.gaps.prev(upper)
        left = actual.gaps.key(it).a
        right = actual.gaps.value(it)
        if (right == actual.trench) { right = newTrench }
    } else if (!actual.gaps.isEmpty() && actual.gaps.value(actual.gaps.last()) == actual.trench) {
        left = actual.gaps.key(actual.gaps.last()).a
    }
    return x == left || x + n == right
}

// Import accepted commands once, without replaying decisions or moving pipes.
// Gap ownership and reservations of the virtual shadow are not physical state.
func importObserved(out: Allocator, actual: PhysicalAllocator, observed: ArrayList<Int64>): Unit {
    var next: Int64 = 0
    for (command in observed) {
        out.lifetimeModel.advance()
        if (command > 0) {
            next++
            let id = next
            if (out.observedRunLength != command) {
                if (out.observedRunCount > 0) {
                    out.completedPlacementRuns.pushBack(Key(out.observedRunLength, out.observedRunCount))
                    if (out.completedPlacementRuns.size > 8) { out.completedPlacementRuns.popFront() }
                    let total = out.activeRunDeleteParityCount[0] + out.activeRunDeleteParityCount[1]
                    let dominant = iMax(out.activeRunDeleteParityCount[0], out.activeRunDeleteParityCount[1])
                    if (total >= 8 && dominant * 100 >= total * 85) {
                        let parity: Int64 = if (out.activeRunDeleteParityCount[0] > out.activeRunDeleteParityCount[1]) { 0 } else { 1 }
                        out.previousCompletedDeleteRelativeParity = out.lastCompletedDeleteRelativeParity
                        out.lastCompletedDeleteRelativeParity = parity ^ (out.activeRunFirstPid & 1)
                    } else {
                        out.previousCompletedDeleteRelativeParity = -1
                        out.lastCompletedDeleteRelativeParity = -1
                    }
                }
                out.observedRunLength = command
                out.observedRunCount = 0
                out.activeRunFirstPid = id
                out.activeRunDeleteParityCount = Array<Int64>(2, repeat: 0)
            }
            out.observedRunCount++
            if (out.activePipeCount > kMcMaxActivePipes) { out.lifoLaneDisabledForScale = true }
            if (out.hasSmoothSizeTrendWith(command)) { out.runLeftDisabledBySmoothTrend = true }
            let cohort = out.lengthOccurrenceCount[command] % 2
            let x = actual.pipes[id].a
            out.pipes.add(Pipe(x, command, true, cohort))
            out.activeByEnd.put(Key(x + command), id)
            out.fenwickAdd(id, 1)
            out.activePipeCount++
            out.lengthOccurrenceCount[command]++
            out.recordLength(command)
            out.recordObservation(Observation(1, command))
            out.recordPrimalEvent(command)
        } else {
            let id = -command
            var p = out.pipes[id]
            if (!p.active) { throw Exception("import inactive PID") }
            let rank = out.rankFromNewestPermille(id)
            out.lifetimeModel.observeDeletion(id)
            out.activeByEnd.eraseKey(Key(p.start + p.length))
            p.active = false
            out.pipes[id] = p
            out.fenwickAdd(id, -1)
            out.activePipeCount--
            out.releaseEpoch++
            out.recordDeletionPattern(id, p.length)
            out.recordPrimalEvent(-1)
            if (id >= out.activeRunFirstPid) { out.activeRunDeleteParityCount[id & 1]++ }
            out.removedLengthCohort[p.length][p.sizeCohort]++
            let total = out.removedLengthCohort[p.length][0] + out.removedLengthCohort[p.length][1]
            let dominant = iMax(out.removedLengthCohort[p.length][0], out.removedLengthCohort[p.length][1])
            if (total >= 8 && dominant * 100 >= total * 85 && out.hasSteadySizeTrend()) { out.parityCohortMode = true }
            out.recordObservation(Observation(-1, rank))
        }
    }
    out.trenchLength = actual.trench
    var it = actual.gaps.first()
    while (it != 0) {
        out.addFreeGap(actual.gaps.key(it).a, actual.gaps.value(it), -1, out.releaseEpoch)
        it = actual.gaps.next(it)
    }
    out.cohortSlabActive = false
    if (out.pipes.size != actual.pipes.size) { throw Exception("import PID count") }
    for (id in 1..actual.pipes.size) {
        let p = out.pipes[id]
        if (p.start != actual.pipes[id].a || p.active != (actual.pipes[id].b > 0)) {
            throw Exception("import geometry")
        }
    }
    if (out.fenwickPrefix(out.pipes.size - 1) != out.activePipeCount) { throw Exception("import rank index") }
}

class CautiousHybrid {
    private var tables = loadReplayTables()
    private var active = Array<Bool>(15, repeat: true)
    private var physical: Option<PhysicalAllocator> = Some(PhysicalAllocator())
    private var shadow: Option<Allocator> = None
    private var online: Option<Allocator> = None
    private var observed = ArrayList<Int64>()
    private var step: Int64 = 0
    private var replayPlacements: Int64 = 0
    private var fallbackCommands: Int64 = 0
    private var abortStep: Int64 = 0
    private var abortReason = "none"
    public init() {
        let core = Allocator()
        core.emit = false
        shadow = Some(core)
    }

    public func process(command: Int64): Unit {
        if (let Some(core) <- online) {
            if (command > 0) { core.place(command) } else { core.remove(-command) }
            fallbackCommands++
            step++
            return
        }
        var shadowTrench: Int64 = 0
        if (let Some(core) <- shadow) {
            if (command > 0) { core.place(command) } else { core.remove(-command) }
            shadowTrench = core.trenchLength
        }
        if (let Some(actual) <- physical) {
            var address: Int64 = -1
            var agrees = true
            var matched = false
            for (i in 0..tables.size) {
                if (!active[i]) { continue }
                let table = tables[i]
                if (step >= table.commands.size || table.commands[step] != command) {
                    active[i] = false
                    continue
                }
                matched = true
                if (command > 0) {
                    let position = table.positions[step]
                    if (address >= 0 && address != position) { agrees = false }
                    address = position
                }
            }
            let replayOK = matched && agrees &&
                (command < 0 || actual.fits(address, command)) &&
                (command < 0 || guardedReplay(actual, address, command, shadowTrench))
            if (replayOK) {
                if (command > 0) { actual.place(command, address); replayPlacements++ }
                else { actual.remove(-command) }
                observed.add(command)
                step++
                return
            }
            abortStep = step + 1
            abortReason = if (!matched) { "command_mismatch" }
                else if (!agrees) { "table_conflict" }
                else if (command > 0 && !actual.fits(address, command)) { "invalid_replay_geometry" }
                else { "guard" }
            shadow = None
            let core = Allocator()
            importObserved(core, actual, observed)
            online = Some(core)
            physical = None
            tables = ArrayList<ReplayTable>()
            active = Array<Bool>(0, repeat: false)
            observed = ArrayList<Int64>()
            if (command > 0) { core.place(command) } else { core.remove(-command) }
            fallbackCommands++
            step++
            return
        }
        throw Exception("missing hybrid state")
    }

    public func finish(): Unit {
        var trench: Int64 = 0
        if (let Some(core) <- online) { trench = core.trenchLength }
        else if (let Some(actual) <- physical) { trench = actual.trench }
        getStdErr().writeln("replay_placements=${replayPlacements} fallback_commands=${fallbackCommands} abort_reason=${abortReason} abort_step=${abortStep} T=${trench}")
    }
}

main(): Int64 {
    setGCThreshold(64 * 1024)
    let hybrid = CautiousHybrid()
    while (let Some(line) <- getStdIn().readln()) {
        var pos: Int64 = 0
        while (pos < line.size) {
            while (pos < line.size && line[pos] <= 32) { pos++ }
            if (pos == line.size) { break }
            var sign: Int64 = 1
            if (line[pos] == 45) { sign = -1; pos++ }
            else if (line[pos] == 43) { pos++ }
            var command: Int64 = 0
            while (pos < line.size && line[pos] >= 48 && line[pos] <= 57) {
                command = command * 10 + Int64(line[pos]) - 48
                pos++
            }
            command *= sign
            if (command == 0) { hybrid.finish(); return 0 }
            hybrid.process(command)
            if (getAllocatedHeapSize() > 96 * 1024 * 1024) { gc(heavy: true) }
        }
    }
    return 0
}
