#!/usr/bin/env python3
"""Restore published test inputs and verify their original SHA-256."""
import gzip, hashlib, json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
out = Path(sys.argv[1] if len(sys.argv) > 1 else "unpacked-tests")
out.mkdir(parents=True, exist_ok=True)
count = 0
for line in (root / "tests/cases.jsonl").open():
    item = json.loads(line)
    compressed = (root / "tests" / item["input_gzip"]).read_bytes()
    if hashlib.sha256(compressed).hexdigest() != item["gzip_sha256"]:
        raise ValueError("Compressed input hash mismatch")
    data = gzip.decompress(compressed)
    if hashlib.sha256(data).hexdigest() != item["test_sha256"]:
        raise ValueError("Original input hash mismatch")
    target = out / (item["test_sha256"] + ".in")
    if target.exists() and target.read_bytes() != data:
        raise FileExistsError(target)
    target.write_bytes(data)
    count += 1
print(f"Restored and checked {count} inputs")
