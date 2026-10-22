"""Directly compare the split and packed reply records, without a harness."""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "speed-v20"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_literals(source: str, pattern: str) -> dict[int, bytes]:
    result = {}
    for match in re.finditer(pattern, source, re.S):
        result[int(match.group(1))] = ast.literal_eval("(" + match.group(2) + ")").encode("latin1")
    return result


def parse_stages(source: str, table: str) -> list[tuple[int, int, int, int]]:
    block = re.search(rf"static const Stage {table}\[\]=\{{(.*?)\n\}};", source, re.S)
    assert block
    if table == "stages" and "meta" not in block.group(1):
        return [tuple(map(int, row)) for row in re.findall(
            r"\{reinterpret_cast<const unsigned char\*>\(replies(\d+)\),(\d+)u,(\d+)u,(\d+)u\}",
            block.group(1),
        )]
    return [tuple(map(int, row)) for row in re.findall(
        r"\{meta(\d+),reinterpret_cast<const unsigned char\*>\(replies\d+\),(\d+)u,(\d+)u,(\d+)u\}",
        block.group(1),
    )]


def parse_edges(source: str) -> list[tuple[int, int]]:
    block = re.search(r"static const Edge edges\[\]=\{(.*?)\};", source, re.S)
    assert block
    return [(int(a), int(b)) for a, b in re.findall(r"\{(-?\d+),(\d+)u\}", block.group(1))]


def main() -> None:
    old_source = (BASE / "solution.cpp").read_text()
    new_source = (HERE / "solution.cpp").read_text()
    old = parse_literals(old_source, r"static const char replies(\d+)\[\]=\n(.*?);")
    meta = parse_literals(new_source, r"static const unsigned char meta(\d+)\[\]=\n(.*?);")
    payload = parse_literals(new_source, r"static const char replies(\d+)\[\]=\n(.*?);")
    assert len(old) == len(meta) == len(payload) == 22
    assert parse_stages(old_source, "stages") == parse_stages(new_source, "stages")
    assert parse_edges(old_source) == parse_edges(new_source)

    records = 0
    payload_bytes = 0
    packed_bytes = 0
    for stage in range(22):
        packed = old[stage]
        descriptors = meta[stage]
        data = payload[stage]
        p = q = 0
        for header in descriptors:
            assert p < len(packed) and packed[p] == header
            p += 1
            length = header & 15
            assert length > 0 and p + length <= len(packed)
            assert q + length <= len(data)
            assert packed[p : p + length] == data[q : q + length]
            p += length
            q += length
            records += 1
            payload_bytes += length
        assert p == len(packed)
        assert q == len(data)
        packed_bytes += len(packed)

    summary = {
        "status": "exact_record_decomposition_passed",
        "baseline_source": str(BASE / "solution.cpp"),
        "baseline_sha256": sha(BASE / "solution.cpp"),
        "candidate_source": str(HERE / "solution.cpp"),
        "candidate_sha256": sha(HERE / "solution.cpp"),
        "stages": 22,
        "records_compared": records,
        "payload_bytes_compared": payload_bytes,
        "packed_bytes": packed_bytes,
        "split_table_bytes": payload_bytes + records,
        "table_bytes_identical": packed_bytes == payload_bytes + records,
        "stage_metadata_identical": True,
        "branch_edges_identical": True,
        "full_interactive_harness": "not run by assignment",
    }
    (HERE / "direct-check.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
