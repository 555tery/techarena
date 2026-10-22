"""Bounded exact CSP trial on the inherited 76-movable peak relaxation."""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from runtime import ROOT, REPO, e
sys.path.insert(0, str(HERE.parent))
from rotation.condition_rotations import INPUT11, read_input, read_positions, replay, sha

H = 20759
SRC = ROOT / "peak-relax" / "partial.txt"
CSP = ROOT / "joint-csp" / "repair_ac"


def main():
    partial = HERE / "peak-relax-76-partial.txt"
    shutil.copyfile(SRC, partial)
    _, _, _, lengths, *_ = read_input(INPUT11)
    raw = list(map(int, partial.read_text().split()))
    count = sum(x < 0 for x in raw)
    if len(raw) != len(lengths) - 1 or count != 76 or raw[0] != 0:
        raise ValueError(f"unexpected relaxation: pipes={len(raw)}, movable={count}, pid1={raw[0]}")
    output = HERE / "csp20759-peakrelax.txt"
    log = HERE / "csp20759-peakrelax.log"
    status = None
    error = None
    try:
        status = e.invoke([str(CSP), str(INPUT11), str(partial), str(output), str(H), "70", "11192026"], HERE, log.name, 85)
    except TimeoutError as exc:
        error = f"e.invoke timeout: {exc}"
    record = {"input_sha256": sha(INPUT11), "partial_sha256": sha(partial),
              "movable_count": count, "target_extent": H, "csp_sha256": sha(CSP),
              "status": status, "error": error}
    if output.exists():
        positions = read_positions(output, len(lengths)-1)
        result = replay(INPUT11, positions)
        record.update({"output_sha256": sha(output), "replay": result, "pid1": positions[1]})
        if result["extent"] > H or positions[1] != 0:
            raise ValueError("CSP output violates target or PID1 pin")
    if log.exists():
        record["log_tail"] = log.read_text()[-6000:]
    (HERE / "csp20759-peakrelax-report.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
