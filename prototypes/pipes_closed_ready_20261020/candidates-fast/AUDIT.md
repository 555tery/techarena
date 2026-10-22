# Fast I/O derivatives

Built by `../build_fast_io.py` from frozen `../candidates/{online,full,hybrid}`.
The frozen files are never written. Each derivative has `solution.cpp`, `solver`
and `build.json`; aggregate hashes and exact replacement pairs are in
`build.json` here.

The builder reverses every replacement and asserts byte equality with the
complete frozen source. Only input extraction, answer formatting/writing, and
unused stream setup change. Allocation expressions, tables, imports, histories,
guard conditions and policy selection stay unchanged. The added I/O namespace
does not change numeric decisions.

## Protocol and verification

POSIX uses `read`/`write`; Windows uses `ReadFile`/`WriteFile`. Signed decimal
integers are parsed without locale or iostream operations. The parser handles
whitespace, optional signs, EOF after a final digit, negative PIDs and range
overflow. Input uses a 64 KiB byte buffer; only the next command is parsed before
answering. Bulk available bytes can be prefetched, but no later token is parsed
or consulted by the solver.

Each response is formatted on the stack and written immediately, with no output
buffer or deferred flush. Partial writes continue until the entire response is
written. POSIX interrupted reads/writes retry; zero-byte EOF is recognized.
I/O errors terminate the program. Cold diagnostic stderr remains unchanged.

`parity.json`: all **45 Open15 policy/input pairs** have byte-identical stdout
and stderr against their frozen original, plus nine policy/tiny-input pairs
(three edge cases for each policy). This is a direct bulk-stdin equivalence
check, not an official harness run or a speed benchmark.

`interactive-tiny.json`: the same three tiny cases were fed incrementally to
each fast binary on macOS. Every response arrived before sending the next command;
the final token without a delimiter completed correctly when stdin reached EOF.

## Remaining runtime risk

No new allocation policy is introduced. Actual CPU/RSS improvement and the
contest limit margin require the coordinator's fresh official interactive
evaluation. Direct output still requires a system call per response, so system
time need not disappear. Input buffering helps only when bytes are available.

The POSIX backend was compiled and executed on macOS. The conditional Windows
backend has been source-reviewed, but has not been compiled with MSVC or tested
against Windows pipes here. It uses anonymous byte-pipe semantics and emits
literal LF line endings. Kernel-level short writes and EINTR branches are
handled explicitly but were not fault-injected during the parity checks.
