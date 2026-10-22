#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
src=(HERE/'candidate-sparse/solution.cj').read_text();base=hashlib.sha256(src.encode()).hexdigest()
bridge=r'''
// Normal C ABI calls may block; no FastNative annotation is used.
@When[os == "Windows"]
foreign func _read(fd: Int32, p: CPointer<UInt8>, n: UInt32): Int32
@When[os == "Windows"]
foreign func _write(fd: Int32, p: CPointer<UInt8>, n: UInt32): Int32
@When[os == "Windows"]
foreign func _setmode(fd: Int32, mode: Int32): Int32
@When[os == "Windows"]
foreign func _errno(): CPointer<Int32>
@When[os != "Windows"]
foreign func read(fd: Int32, p: CPointer<UInt8>, n: UIntNative): IntNative
@When[os != "Windows"]
foreign func write(fd: Int32, p: CPointer<UInt8>, n: UIntNative): IntNative
@When[os == "macOS"]
foreign func __error(): CPointer<Int32>
@When[os == "Linux"]
foreign func __errno_location(): CPointer<Int32>

@When[os == "Windows"]
func protocolRead(p: CPointer<UInt8>, count: Int64): Int64 {
    return Int64(unsafe { _read(0, p, UInt32(count)) })
}
@When[os != "Windows"]
func protocolRead(p: CPointer<UInt8>, count: Int64): Int64 {
    return Int64(unsafe { read(0, p, UIntNative(count)) })
}
@When[os == "Windows"]
func protocolWrite(p: CPointer<UInt8>, count: Int64): Int64 {
    return Int64(unsafe { _write(1, p, UInt32(count)) })
}
@When[os != "Windows"]
func protocolWrite(p: CPointer<UInt8>, count: Int64): Int64 {
    return Int64(unsafe { write(1, p, UIntNative(count)) })
}
@When[os == "Windows"]
func protocolErrno(): Int32 { return unsafe { _errno().read() } }
@When[os == "macOS"]
func protocolErrno(): Int32 { return unsafe { __error().read() } }
@When[os == "Linux"]
func protocolErrno(): Int32 { return unsafe { __errno_location().read() } }
@When[os == "Windows"]
func protocolBinary(fd: Int32): Unit {
    if (unsafe { _setmode(fd, 0x8000) } == -1) { throw Exception("binary protocol mode") }
}
@When[os != "Windows"]
func protocolBinary(fd: Int32): Unit {}

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
    private func nextByte(): Int64 {
        if (position == count) {
            while (true) {
                count = protocolRead(data, 4096)
                if (count >= 0) { break }
                let error = protocolErrno()
                if (error != 4) { throw Exception("protocol read") }
            }
            position = 0
            if (count == 0) { return -1 }
        }
        let result = Int64(unsafe { data.read(position) })
        position++
        blackBox(this)
        return result
    }
    public func nextCommand(): Option<Int64> {
        var c = nextByte()
        while (c >= 0 && c <= 32) { c = nextByte() }
        if (c < 0) { return None }
        var sign: Int64 = 1
        if (c == 45) { sign = -1; c = nextByte() }
        else if (c == 43) { c = nextByte() }
        if (c < 48 || c > 57) { throw Exception("protocol integer") }
        var command: Int64 = 0
        while (c >= 48 && c <= 57) {
            command = command * 10 + c - 48
            c = nextByte()
        }
        if (c > 32) { throw Exception("protocol separator") }
        return Some(command * sign)
    }
}

'''
marker='// Source: main.cj';assert src.count(marker)==1;src=src.replace(marker,bridge+marker)
a=src.index('main(): Int64 {');b=src.index('\nfunc replayTable0()',a)
src=src[:a]+'''main(): Int64 {
    setGCThreshold(64 * 1024)
    let hybrid = CautiousHybrid()
    let input = ProtocolInput()
    while (let Some(command) <- input.nextCommand()) {
        if (command == 0) { hybrid.finish(); return 0 }
        hybrid.process(command)
        if (getAllocatedHeapSize() > 96 * 1024 * 1024) { gc(heavy: true) }
    }
    return 0
}
'''+src[b:]
out=HERE/'candidate-input';out.mkdir(exist_ok=True);(out/'solution.cj').write_text(src)
(out/'source.json').write_text(json.dumps(dict(base_sha256=base,source_sha256=hashlib.sha256(src.encode()).hexdigest(),changes=['Short-read-safe byte protocol parser using standard C read/_read. Never fills the whole buffer before returning the received command.','Whitespace signed integer syntax and zero/EOF termination retained for valid task protocol.','Windows binary mode set before first input; normal blocking foreign calls.','Output code unchanged.']),indent=2)+'\n')
old='''    private let bytes = Array<Byte>(64, repeat: 0)
    private var used: Int64 = 0'''
new='''    private let bytes: CPointer<UInt8>
    private var used: Int64 = 0
    public init() {
        bytes = LibC.malloc<UInt8>(count: 64)
        if (bytes.isNull()) { throw IllegalMemoryException("protocol output buffer") }
        protocolBinary(1)
        blackBox(this)
    }
    ~init() { unsafe { LibC.free(bytes) } }'''
assert src.count(old)==1;src=src.replace(old,new)
a=src.index('class OutputBuffer {');b=src.index('\nlet protocolOutput',a);part=src[a:b]
part=part.replace('bytes[used] = 45','unsafe { bytes.write(used, 45) }')
part=part.replace('bytes[used] = UInt8(n % 10 + 48)','unsafe { bytes.write(used, UInt8(n % 10 + 48)) }')
part=part.replace('let temp = bytes[l]; bytes[l] = bytes[r]; bytes[r] = temp','let temp = unsafe { bytes.read(l) }; unsafe { bytes.write(l, bytes.read(r)); bytes.write(r, temp) }')
part=part.replace('bytes[used] = 32','unsafe { bytes.write(used, 32) }')
old='''        bytes[used] = 10; used++
        getStdOut().write(bytes[..used])
        getStdOut().flush()'''
new='''        unsafe { bytes.write(used, 10) }; used++
        var sent: Int64 = 0
        while (sent < used) {
            let written = protocolWrite(unsafe { bytes + sent }, used - sent)
            if (written < 0) {
                let error = protocolErrno()
                if (error == 4) { continue }
                throw Exception("protocol write")
            }
            if (written == 0) { throw Exception("protocol short write") }
            sent += written
        }
        blackBox(this)'''
assert part.count(old)==1;part=part.replace(old,new)
assert 'bytes[' not in part
src=src[:a]+part+src[b:]
out=HERE/'candidate-io';out.mkdir(exist_ok=True);(out/'solution.cj').write_text(src)
(out/'source.json').write_text(json.dumps(dict(base_sha256=hashlib.sha256((HERE/'candidate-input/solution.cj').read_bytes()).hexdigest(),source_sha256=hashlib.sha256(src.encode()).hexdigest(),changes=['Native 64-byte output owner, exactly same decimal/newline formatting.','Send every reply immediately via normal blocking write/_write; retry partial remainder and EINTR. No response batching.','Windows binary mode retains LF bytes; strongly hold owner until write completes.']),indent=2)+'\n')
print('prepared candidate-input, candidate-io')
