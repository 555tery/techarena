package pipes

import std.env.*

// Keep every protocol response in one byte buffer and flush immediately.
class OutputBuffer {
    private let bytes = Array<Byte>(64, repeat: 0)
    private var used: Int64 = 0
    private func number(value: Int64): Unit {
        var n = value
        if (n < 0) { bytes[used] = 45; used++; n = -n }
        let first = used
        while (true) {
            bytes[used] = UInt8(n % 10 + 48); used++; n /= 10
            if (n == 0) { break }
        }
        var l = first
        var r = used - 1
        while (l < r) {
            let temp = bytes[l]; bytes[l] = bytes[r]; bytes[r] = temp
            l++; r--
        }
    }
    private func send(): Unit {
        bytes[used] = 10; used++
        getStdOut().write(bytes[..used])
        getStdOut().flush()
    }
    public func placement(digs: Int64, start: Int64): Unit {
        used = 0; number(digs)
        bytes[used] = 32; used++
        number(start); send()
    }
    public func removal(start: Int64): Unit { used = 0; number(start); send() }
}

let protocolOutput = OutputBuffer()
func answer(digs: Int64, start: Int64): Unit { protocolOutput.placement(digs, start) }
func answerRemoval(start: Int64): Unit { protocolOutput.removal(start) }

main(): Int64 {
    let allocator = Allocator()
    // ConsoleReader.read(buffer) fills the requested buffer and can deadlock
    // in this protocol. readln returns after the current complete command.
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
            if (command == 0) {
                getStdErr().writeln("recency_different_selections=${allocator.recencyDifferentSelections}")
                getStdErr().writeln("primal_dp_scored_decisions=${allocator.primalScoredDecisions} changed_selections=${allocator.primalChangedSelections} first_activation_event=${allocator.primalFirstActivationEvent} cap_fallbacks=${allocator.primalCapFallbacks} model_rebuilds=${allocator.primalModelRebuilds}")
                return 0
            }
            if (command > 0) { allocator.place(command) }
            else { allocator.remove(-command) }
        }
    }
    return 0
}
