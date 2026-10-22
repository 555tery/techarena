"""Run the original official interactor via the unchanged project harness."""
import concurrent.futures
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))
import pipes_harness as harness


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((HERE / "manifest.json").read_text())
    old = REPO / "prototypes/pipes_prefix_shock_20261019"
    v4 = REPO / "prototypes/pipes_open15_adversary_20261019/snapshots/release-v4"
    build4 = json.loads((v4 / "build.json").read_text())
    assert sha(v4 / "solver") == build4["binary_sha256"]
    strategies = {
        "release-v5": [str(HERE / "target/solver")],
        "release-v4": [str(v4 / "solver")],
        "bestfit": [str(old / "allocator-probe"), "bestfit", str(old / "tape.txt")],
        "trial22": [str(old / "trial22")],
    }
    binary_hashes = {s: sha(Path(argv[0])) for s, argv in strategies.items()}
    assert binary_hashes["release-v5"] == manifest["target"]["binary_sha256"]
    assert sha(HERE / "target/solution.cpp") == manifest["target"]["source_sha256"]
    reused = {}
    for strategy in ["release-v5", "bestfit"]:
        path = HERE / "evaluations/quiet-minimal" / strategy / "summary.json"
        data = json.loads(path.read_text())
        for record in data["records"]:
            reused[strategy, record["test_sha256"]] = record
    def execute(strategy, row):
        key = (strategy, row["test_sha256"])
        destination = HERE / "evaluations/final" / strategy / row["name"]
        if key in reused:
            result = dict(reused[key])
            result["reused_verified_current_task_record"] = True
        elif (destination / "record.json").exists():
            result = json.loads((destination / "record.json").read_text())
            assert result["binary_sha256"] == binary_hashes[strategy]
            assert result["test_sha256"] == row["test_sha256"]
        else:
            result = harness.run_case(strategies[strategy], REPO / "tools/interactor", REPO / row["file"],
                                      destination, 5.0, 180.0)
        result.update({"strategy": strategy, "suite_case": row["name"], "binary_sha256": binary_hashes[strategy],
                       "cpu_limit_s": 5.0, "memory_limit_mb": 256.0,
                       "solver_cpu_limit_exceeded": result["solver_cpu_total_s"] is None or result["solver_cpu_total_s"] >= 5,
                       "solver_memory_limit_exceeded": result["solver_peak_rss_mb"] is None or result["solver_peak_rss_mb"] >= 256})
        assert result["test_sha256"] == sha(REPO / row["file"])
        assert result["status"] == "ok", result
        assert not result["solver_cpu_limit_exceeded"] and not result["solver_memory_limit_exceeded"]
        assert result["judge_commands_seen_including_final_zero"] == row["operation_count"] + 1
        if strategy == "release-v5":
            counters = {k: int(v) for k, v in re.findall(r"(replay|fallback|table_conflict|T)=(\d+)", result["candidate_stderr"])}
            assert counters["fallback"] > 0 and counters["table_conflict"] == 0
            assert counters["T"] == result["trench_length_m"]
            result["runtime_counters"] = counters
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "record.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    jobs = [(s, row) for s in strategies for row in manifest["tests"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pending = {pool.submit(execute, s, row): (s, row["name"]) for s, row in jobs}
        results = []
        for future in concurrent.futures.as_completed(pending):
            r = future.result()
            results.append(r)
            print(r["strategy"], r["suite_case"], r["kpi"], flush=True)
    assert len(results) == len(jobs) == 36
    for s, argv in strategies.items():
        assert sha(Path(argv[0])) == binary_hashes[s]
    assert sha(HERE / "target/solution.cpp") == manifest["target"]["source_sha256"]
    summary = {"status": "36_of_36_official_local_checks_ok", "records": results,
               "strategies": strategies, "binary_hashes": binary_hashes,
               "official_interactor_sha256": sha(REPO / "tools/interactor"),
               "official_interactor_source_sha256": sha(REPO / "vendor/pipes_official/interactor.cpp"),
               "harness_sha256": sha(REPO / "tools/pipes_harness.py"),
               "reused_checks": len(reused), "new_checks": len(jobs)-len(reused), "platform_actions": 0}
    (HERE / "official-results.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
