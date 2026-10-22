#!/usr/bin/env python3
"""A complete legal counterexample already in the frozen archive."""
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ID = "80069ba227b45472edac2fe865fb9df9b15364869ed6634c203a7654e7d208b2"

def main():
    freeze = json.loads((HERE / "freeze.json").read_text())
    c = next(c for c in freeze["cases"] if c["id"] == ID)
    rows = {r["method"]: r for line in (HERE / "records.jsonl").read_text().splitlines()
            if (r := json.loads(line))["id"] == ID}
    tokens = (HERE / c["input"]).read_text().split()
    commands = list(map(int, tokens[2:2 + int(tokens[1])]))
    assert len(commands) == 16
    out = {"id": ID, "input": c["input"], "origin": c["origin"], "commands": commands,
           "frozen_input_sha256": c["input_sha256"],
           "scope": "Existing archival stream, not an independently generated new test."}
    for method in ("online_cj", "hybrid_cj"):
        r = rows[method]
        assert r["status"] == "ok" and r["within_limits"]
        replies = [list(map(int, line.split())) for line in gzip.open(r["judge_output_file"], "rt")]
        assert len(replies) == len(commands)
        out[method] = {"F": r["occupied_length_m"], "T": r["trench_length_m"], "KPI": r["kpi"],
                       "replies": replies, "response_sha256": r["response_sha256"],
                       "diagnostic": r["candidate_stderr"]}
    assert out["online_cj"]["T"] == 40 and out["hybrid_cj"]["T"] == 60
    assert out["online_cj"]["replies"][1:3] == [[0, 18], [0, 14]]
    assert out["hybrid_cj"]["replies"][1:3] == [[0, 2], [0, 16]]
    assert commands[-3:] == [-2, -3, 6]
    out["explanation"] = (
        "At command 2, guarded replay places length-2 PID 2 at x=2; pure online uses x=18. "
        "Replay ends before command 3. PID 3 has length 4 at x=16 in hybrid, x=14 online. "
        "Later deleting PIDs 2 and 3 frees separate intervals [2,4) and [16,20) for hybrid, "
        "but adjacent [18,20) and [14,18) for online. The final length 6 fits [14,20) online; "
        "hybrid grows from 40 to 60. Both are legal. Online attains the volume bound 38/40=0.95."
    )
    (HERE / "counterexample.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({m: out[m]["KPI"] for m in ("online_cj", "hybrid_cj")}))

if __name__ == "__main__":
    main()
