#!/usr/bin/env python3
"""Build the isolated speed-v4 runtime with the frozen release-v5 tables."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTINUATION = HERE.parent
TABLE_SOURCE = CONTINUATION / "release-v5" / "solution.cpp"
RUNTIME_SOURCE = HERE / "solver_runtime.cpp"
OUTPUT_SOURCE = HERE / "solution.cpp"
OUTPUT_BINARY = HERE / "solver"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    frozen = TABLE_SOURCE.read_text()
    match = re.search(r"static const char\* encoded\[\]=\{.*?\n\};", frozen, re.S)
    if match is None:
        raise SystemExit("could not locate the frozen encoded table in release-v5")
    template = RUNTIME_SOURCE.read_text()
    if template.count("// GENERATED_TABLES") != 1:
        raise SystemExit("runtime template must contain one GENERATED_TABLES marker")
    source = template.replace("// GENERATED_TABLES", match.group(0), 1)
    OUTPUT_SOURCE.write_text(source)
    subprocess.run(
        ["/usr/bin/clang++", "-O2", "-std=c++17", "-Wall", "-Wextra",
         str(OUTPUT_SOURCE), "-o", str(OUTPUT_BINARY)],
        check=True,
    )
    (HERE / "build.json").write_text(json.dumps({
        "source_sha256": sha(OUTPUT_SOURCE),
        "binary_sha256": sha(OUTPUT_BINARY),
        "compiler": "/usr/bin/clang++",
        "flags": ["-O2", "-std=c++17", "-Wall", "-Wextra"],
        "table_source_sha256": sha(TABLE_SOURCE),
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
