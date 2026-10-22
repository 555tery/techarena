#!/usr/bin/env python3
"""Preserve the submitted source and add observation-only GC probes."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "pipes_current_hybrid_cj_20261020"
original = (BASE / "release/solution.cj").read_bytes()
assert hashlib.sha256(original).hexdigest() == "fd5fe184cb85bf47c18085a3ef12ceb36ae20168398dd00d8983f16165b8fc9a"
(HERE / "baseline").mkdir(exist_ok=True)
(HERE / "baseline/solution.cj").write_bytes(original)
source = original.decode()
source = source.replace("    let hybrid = CautiousHybrid()\n", "    let hybrid = CautiousHybrid()\n    var diagnosticStep: Int64 = 0\n")
old = "            if (getAllocatedHeapSize() > 96 * 1024 * 1024) { gc(heavy: true) }"
assert source.count(old) == 1
source = source.replace(old, """            diagnosticStep++
            let heap = getAllocatedHeapSize()
            if (diagnosticStep == 1717 || diagnosticStep == 1718 || diagnosticStep == 1719 ||
                diagnosticStep == 15869 || diagnosticStep == 15870 || diagnosticStep == 15871 ||
                diagnosticStep == 10581 || diagnosticStep == 10582 || diagnosticStep == 10583) {
                getStdErr().writeln("probe step=${diagnosticStep} heap=${heap}")
            }
            if (heap > 96 * 1024 * 1024) {
                getStdErr().writeln("gc-start step=${diagnosticStep} heap=${heap}")
                gc(heavy: true)
                getStdErr().writeln("gc-done step=${diagnosticStep} heap=${getAllocatedHeapSize()}")
            }""")
(HERE / "diagnostic").mkdir(exist_ok=True)
(HERE / "diagnostic/solution.cj").write_text(source)
(HERE / "diagnostic-source.json").write_text(json.dumps({
    "baseline_sha256": hashlib.sha256(original).hexdigest(),
    "diagnostic_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "changes": "Only stderr probes after each completed command; same GC threshold and decision policy.",
}, indent=2) + "\n")
