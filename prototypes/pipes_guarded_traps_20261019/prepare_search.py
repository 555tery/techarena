"""Export selected frozen-plan/BF prefix states for a bounded diagnostic."""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OLD = REPO / "prototypes/pipes_open15_overfit_20261019"
PROBE = REPO / "prototypes/pipes_prefix_shock_20261019/allocator-probe"
TAPE = REPO / "prototypes/pipes_prefix_shock_20261019/tape.txt"


def main():
    joint = json.loads((OLD / "joint.json").read_text())
    places = list(map(int, (OLD / "best-positions.txt").read_text().split()))
    snapshots = []
    data = []
    for case in joint["cases"]:
        commands = case["commands"]
        output = subprocess.run([str(PROBE), "bestfit", str(TAPE)],
            input="\n".join(map(str, commands + [0])) + "\n", text=True,
            capture_output=True, check=True, timeout=20).stdout.splitlines()
        assert len(output) == len(commands)
        points = {16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192,
                  16384, 32768, 65536, 100000, 131072, len(commands)-1}
        pid = 0
        active = {}
        good_trench = bad_trench = 0
        for index, (command, bid, response) in enumerate(zip(commands, case["block_ids"], output), 1):
            if command > 0:
                digs, pos = map(int, response.split())
                good_trench += 20 * digs
                bad_pos = places[bid]
                bad_trench = max(bad_trench, (bad_pos + command + 19) // 20 * 20)
                pid += 1
                active[pid] = (pid, command, pos, bad_pos)
            else:
                del active[-command]
            if index in points and index < len(commands) and index + len(active) + good_trench // 40 < 195000:
                snapshots.append((case["case"], index, good_trench, bad_trench, len(active)))
                data.append(str(len(snapshots)-1) + " " + " ".join(map(str, snapshots[-1])) + "\n")
                data.extend(" ".join(map(str, row)) + "\n" for row in active.values())
    (HERE / "states.txt").write_text(str(len(snapshots)) + "\n" + "".join(data))
    (HERE / "snapshots.json").write_text(json.dumps(snapshots) + "\n")
    print("exported", len(snapshots), "states")


if __name__ == "__main__":
    main()
