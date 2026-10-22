#!/usr/bin/env python3
"""Copy the frozen current core verbatim and transcode unchanged replay tables."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ONLINE = ROOT / "prototypes/pipes_cangjie_port_20261020/release/solution.cj"
CPP = HERE / "cpp/solution.cpp"

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

assert sha(ONLINE) == "cc2fcdf7d930bad6c75a0656c105c28399c66d5184c937740c69764a1e9e681f"
assert sha(CPP) == "1587e43be50aaf4b3bb134ac750b2507bd795f112e9081d94eadc01251360a26"
text = ONLINE.read_text()
core = text[:text.index("\nmain(): Int64 {")] + "\n"
(HERE / "cj/core.cj").write_text(core)
cpp = CPP.read_text()
tables = re.findall(r"static const char\* const encoded(\d+)\[\]=\{\s*(.*?)\n\};", cpp, re.S)
if not tables:
    tables = re.findall(r"static const char\* encoded(\d+)\[\]=\{\s*(.*?)\n\};", cpp, re.S)
assert len(tables) == 15, [(n, len(x)) for n, x in tables]
output = ["package pipes\n\nimport std.collection.*\n"]
encoded_hashes = []
for number, body in tables:
    chunks = re.findall(r'"([A-Za-z0-9+/=]+)"', body)
    assert chunks
    encoded_hashes.append(hashlib.sha256("".join(chunks).encode()).hexdigest())
    output.append(f"\nfunc replayTable{number}(): ReplayTable {{\n    let decoder = ReplayDecoder()\n")
    # Longer source literals reduce compiler call-count without changing bytes.
    joined = "".join(chunks)
    for start in range(0, len(joined), 4096):
        output.append(f'    decoder.feed("{joined[start:start+4096]}")\n')
    output.append("    return decoder.finish()\n}\n")
output.append("\nfunc loadReplayTables(): ArrayList<ReplayTable> {\n    let tables = ArrayList<ReplayTable>()\n")
for number, _ in tables:
    output.append(f"    tables.add(replayTable{number}())\n")
output.append("    return tables\n}\n")
(HERE / "cj/tables.cj").write_text("".join(output))
parts = [HERE / "cj" / f for f in ("core.cj", "hybrid.cj", "tables.cj")]
release = HERE / "release"
release.mkdir(exist_ok=True)
assembled = core
for p in parts[1:]:
    s = p.read_text()
    assembled += "\n" + s[s.index("\n\n", s.index("import std.")):].lstrip()
# Imports in hybrid match the current core; tables uses the same collection import.
assert assembled.count("package pipes") == 1
assert assembled.count("main(): Int64") == 1
(release / "solution.cj").write_text(assembled)
manifest = {
    "online_cj_sha256": sha(ONLINE),
    "reference_cpp_sha256": sha(CPP),
    "online_core_prefix_sha256": hashlib.sha256(core.encode()).hexdigest(),
    "online_core_unchanged": assembled.startswith(core),
    "encoded_table_sha256s": encoded_hashes,
    "parts_sha256": {str(p.relative_to(HERE)): sha(p) for p in parts},
    "solution_sha256": sha(release / "solution.cj"),
}
(HERE / "cj_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"source_sha256": manifest["solution_sha256"], "bytes": len(assembled)}, indent=2))
