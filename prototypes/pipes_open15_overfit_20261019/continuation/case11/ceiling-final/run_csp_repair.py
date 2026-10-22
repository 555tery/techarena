"""Run the existing exact-domain CSP against the 74-pipe peak-hole repair."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from runtime import ROOT, REPO, e
sys.path.insert(0, str(HERE.parent))
from rotation.condition_rotations import INPUT11, read_input, read_positions, replay, sha

OUT = HERE
SOURCE_PARTIAL = ROOT / "peak-repair" / "random" / "partial.txt"
CSP = ROOT / "joint-csp" / "repair_csp"
H = 20759


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    partial = OUT / "peak-hole-partial.txt"
    shutil.copyfile(SOURCE_PARTIAL, partial)
    _, _, _, lengths, *_ = read_input(INPUT11)
    raw = list(map(int, partial.read_text().split()))
    if len(raw) != len(lengths)-1 or sum(x < 0 for x in raw) != 74:
        raise ValueError("unexpected peak-hole repair source shape")
    if raw[0] != 0:
        raise ValueError("PID1 is not pinned at coordinate zero")
    output = OUT / "csp20759.txt"
    log = OUT / "csp20759.log"
    status = None
    error = None
    try:
        status = e.invoke([str(CSP), str(INPUT11), str(partial), str(output), str(H), "110", "112619"], OUT, log.name, 120)
    except TimeoutError as exc:
        error = f"e.invoke timeout: {exc}"
    record = {"input_sha256": sha(INPUT11), "partial_sha256": sha(partial),
              "partial_movable_count": 74, "target_extent": H,
              "csp_source_sha256": sha(CSP), "status": status, "error": error}
    if output.exists():
        positions = read_positions(output, len(lengths)-1)
        report = replay(INPUT11, positions)
        record.update({"output_sha256": sha(output), "replay": report,
                       "pid1": positions[1]})
        if report["extent"] > H or positions[1] != 0:
            raise ValueError("CSP output violates target or PID1 pin")
    if log.exists():
        record["log_tail"] = log.read_text()[-5000:]
    e.save(OUT / "csp20759-report.json", record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
