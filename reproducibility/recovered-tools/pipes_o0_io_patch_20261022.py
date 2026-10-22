def patch(source):
 start=source.index('class ProtocolInput {');end=source.index('// Only the public tables are offline information.',start)
 source=source[:start]+'''// One native buffer borrow per command; fields are committed once on return.
class ProtocolInput {
    private let data: CPointer<UInt8>
    private var count: Int64 = 0
    private var position: Int64 = 0
    public init() {
        data = LibC.malloc<UInt8>(count: 4096)
        if (data.isNull()) { throw IllegalMemoryException("protocol input buffer") }
        protocolBinary(0)
        blackBox(this)
    }
    ~init() { unsafe { LibC.free(data) } }
    @OverflowWrapping
    public func nextCommand(): Option<Int64> {
        let buffer = data
        var available = count
        var at = position
        var begun = false
        var digits = false
        var sign: Int64 = 1
        var command: Int64 = 0
        while (true) {
            if (at == available) {
                while (true) {
                    available = protocolRead(buffer, 4096)
                    if (available >= 0) { break }
                    if (protocolErrno() != 4) { throw Exception("protocol read") }
                }
                at = 0
                if (available == 0) {
                    position = 0; count = 0
                    blackBox(this)
                    if (begun && !digits) { throw Exception("protocol integer") }
                    return if (digits) { Some(command * sign) } else { None }
                }
            }
            let c = Int64(unsafe { buffer.read(at) })
            at++
            if (!begun) {
                if (c <= 32) { continue }
                begun = true
                if (c == 45) { sign = -1; continue }
                if (c == 43) { continue }
            }
            if (c >= 48 && c <= 57) {
                command = command * 10 + c - 48
                digits = true
                continue
            }
            if (!digits) { throw Exception("protocol integer") }
            if (c > 32) { throw Exception("protocol separator") }
            position = at; count = available
            blackBox(this)
            return Some(command * sign)
        }
        throw Exception("unreachable protocol state")
    }
}

// One response per write. Digit loops use local offsets and one buffer borrow.
class OutputBuffer {
    private let bytes: CPointer<UInt8>
    private var used: Int64 = 0
    public init() {
        bytes = LibC.malloc<UInt8>(count: 64)
        if (bytes.isNull()) { throw IllegalMemoryException("protocol output buffer") }
        protocolBinary(1)
        blackBox(this)
    }
    ~init() { unsafe { LibC.free(bytes) } }
    @OverflowWrapping
    private func number(value: Int64): Unit {
        let buffer = bytes
        var at = used
        var n = value
        if (n < 0) { unsafe { buffer.write(at, 45) }; at++; n = -n }
        let first = at
        while (true) {
            unsafe { buffer.write(at, UInt8(n % 10 + 48)) }; at++; n /= 10
            if (n == 0) { break }
        }
        var l = first
        var r = at - 1
        while (l < r) {
            let temp = unsafe { buffer.read(l) }
            unsafe { buffer.write(l, buffer.read(r)); buffer.write(r, temp) }
            l++; r--
        }
        used = at
        blackBox(this)
    }
    @OverflowWrapping
    private func send(): Unit {
        let buffer = bytes
        let count = used + 1
        unsafe { buffer.write(used, 10) }
        var sent: Int64 = 0
        while (sent < count) {
            let written = protocolWrite(unsafe { buffer + sent }, count - sent)
            if (written < 0) {
                if (protocolErrno() == 4) { continue }
                throw Exception("protocol write")
            }
            if (written == 0) { throw Exception("protocol short write") }
            sent += written
        }
        used = count
        blackBox(this)
    }
    @OverflowWrapping
    public func placement(digs: Int64, start: Int64): Unit {
        used = 0; number(digs)
        unsafe { bytes.write(used, 32) }; used++
        number(start); send()
    }
    @OverflowWrapping
    public func removal(start: Int64): Unit { used = 0; number(start); send() }
}

let protocolOutput = OutputBuffer()
func answer(digs: Int64, start: Int64): Unit { protocolOutput.placement(digs, start) }
func answerRemoval(start: Int64): Unit { protocolOutput.removal(start) }


'''+source[end:]
 return source
