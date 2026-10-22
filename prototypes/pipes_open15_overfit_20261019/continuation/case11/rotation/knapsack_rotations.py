"""Try the bounded-survivor knapsack planner on the four rotated case11 pins."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
from condition_rotations import INPUT15, PREFIX, OUT, read_input, read_positions, replay, sha
from runtime import ROOT, e


def main():
    _, _, _, lengths15, *_ = read_input(INPUT15)
    exe = ROOT / "conditioned_knapsack"
    if not exe.is_file():
        raise FileNotFoundError(exe)
    all_results = []
    for variant_name in (
        "mode2-H20811-direct.txt", "mode2-H20811-reflected.txt",
        "mode2-H20820-direct.txt", "mode2-H20820-reflected.txt",
    ):
        d = OUT / variant_name.removesuffix(".txt")
        pins = d / "pins.txt"
        best = None
        for mode in range(2000, 2008):
            dest = d / f"case15-conditioned_knapsack-{mode}.txt"
            log = f"case15-conditioned_knapsack-{mode}.log"
            rc = e.invoke([str(exe), str(INPUT15), str(pins), str(PREFIX), str(dest), str(mode)], d, log, 120)
            if rc != 0:
                raise RuntimeError(f"knapsack failed variant={variant_name} mode={mode} rc={rc}")
            matches = re.findall(r"(?m)^\s*(\d+)\s*$", (d / log).read_text())
            if not matches:
                raise ValueError(f"cannot parse T from {log}")
            declared = int(matches[-1])
            report = replay(INPUT15, read_positions(dest, len(lengths15)-1))
            if report["trench_score"] != declared:
                raise ValueError(f"score mismatch for {dest}: {declared} != {report['trench_score']}")
            row = {"T": declared, "method": "conditioned_knapsack", "mode": mode,
                   "positions": str(dest), "sha256": sha(dest), "replay": report}
            if best is None or (row["T"], mode) < (best["T"], best["mode"]):
                best = row
            print(json.dumps({"variant": variant_name, "mode": mode, "T": declared}), flush=True)

        prior_path = d / "result.json"
        prior = json.loads(prior_path.read_text())
        prior["knapsack_best15"] = best
        if best["T"] < prior["pair"]["15"]["T"]:
            prior["pair"]["15"] = best
            prior["pair"]["score"] = 20361 / prior["pair"]["11"]["T"] + 10 * 418757 / best["T"]
        e.save(prior_path, prior)
        all_results.append({"variant": variant_name, "best15": best,
                            "T11": prior["pair"]["11"]["T"],
                            "T15_pair": prior["pair"]["15"]["T"],
                            "score": prior["pair"]["score"]})

    report_path = OUT / "report.json"
    report = json.loads(report_path.read_text())
    report["conditioned_knapsack_modes_2000_2007"] = all_results
    e.save(report_path, report)
    winner = max(all_results, key=lambda x: x["score"])
    winner_record = next(x for x in all_results if x["variant"] == winner["variant"])
    best_source = Path(winner_record["best15"]["positions"])
    (OUT / "best-pair-case15.txt").write_bytes(best_source.read_bytes())
    e.save(OUT / "best-pair.json", winner_record)
    print(json.dumps({"best_pairs": all_results, "winner": winner_record}, indent=2))


if __name__ == "__main__":
    main()
