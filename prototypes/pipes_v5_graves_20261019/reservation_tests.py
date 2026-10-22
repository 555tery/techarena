"""Fresh v5 reservation traps, with high final loading and no deletion suffix."""
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))
from pipes_harness import parse_test
spec = importlib.util.spec_from_file_location("previous_constructor", REPO / "prototypes/pipes_open15_adversary_20261019/construct.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main():
    old = REPO / "prototypes/pipes_prefix_shock_20261019"
    decoded = module.decode(HERE / "target/solution.cpp")
    candidates = []
    for case, (commands, positions) in enumerate(decoded, 1):
        first_delete = next((i for i, c in enumerate(commands) if c < 0), len(commands))
        prefix = commands[:first_delete]
        if not prefix:
            continue
        replies = subprocess.run([str(old / "allocator-probe"), "bestfit", str(old / "tape.txt")],
            input="\n".join(map(str, prefix + [0])) + "\n", text=True,
            capture_output=True, check=True, timeout=20).stdout.splitlines()
        target_trench = bf_trench = volume = 0
        best = []
        max_ratio = 1
        for n, (c, x, reply) in enumerate(zip(prefix, positions, replies), 1):
            volume += c
            target_trench = max(target_trench, (x + c + 19) // 20 * 20)
            bf_trench += 20 * int(reply.split()[0])
            max_ratio = max(max_ratio, target_trench / bf_trench)
            if n == len(commands):
                continue
            # Preserve every prefix pipe and add a single different size,
            # followed by 1 m pipes to fill the causal BF trench completely.
            next_public = commands[n]
            F = max(40, math.ceil(volume / 40) * 40)
            need = F - volume
            if need == 0:
                F += 40
                need = 40
            first = next((L for L in range(min(40, need), 0, -1) if L != next_public), None)
            if first is None:
                continue
            seq = prefix[:n] + [first] + [1] * (need-first)
            if len(seq) > 200000:
                continue
            best.append({"case": case, "prefix": n, "sequence": seq, "F": F,
                         "target_prefix_trench": target_trench, "BF_prefix_trench": bf_trench,
                         "prefix_max_trench_ratio": max_ratio,
                         "predicted_kpi": F/max(F,target_trench)})
        if best:
            best.sort(key=lambda d: (d["predicted_kpi"], len(d["sequence"])))
            candidates.append(best[0])
    candidates.sort(key=lambda d: d["predicted_kpi"])
    directory = HERE / "reservation-inputs"
    directory.mkdir(exist_ok=True)
    rows = []
    for c in candidates:
        if c["predicted_kpi"] >= .2 or len(rows) >= 5:
            continue
        name = f"reserve-open{c['case']:02d}-p{c['prefix']}"
        path = directory / (name + ".in")
        seq = c.pop("sequence")
        path.write_text(f"1\n{len(seq)}\n" + "\n".join(map(str,seq)) + "\n")
        meta = parse_test(path)
        assert meta["kpi_upper_bound_from_live_volume"] == 1
        assert all(cmd > 0 for cmd in seq)
        rows.append({"name": name, "file": str(path.relative_to(REPO)),
                     "mechanism": "Early reservation; every command is an insertion; no depletion and no deletion-triggered fallback.",
                     "classification": "obvious_advance_cost_trap", **c, **meta})
    (HERE / "reservation-manifest.json").write_text(json.dumps({"tests": rows}, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
