"""Run the three frozen policies on Windows, one pinned process at a time.

No installation and no submission. Requires existing Python, Cangjie runtime
and locally built executables. Uses windows_bench.py's independent checker and
GetProcessTimes/peak-memory implementation. Mac measurements are not accepted.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import platform
import sys
import windows_bench as wb

HERE = Path(__file__).resolve().parent
NAMES = ("online_cj", "hybrid_cpp", "hybrid_cj")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=HERE / "windows-results.json")
    p.add_argument("--cpu", type=int, help="Logical CPU index; default first allowed CPU")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--wall-timeout", type=float, default=240.)
    p.add_argument("--exit-timeout", type=float, default=30.)
    args = p.parse_args()
    if sys.platform != "win32":
        p.error("Native Windows is required; nothing has been run.")
    if not math.isfinite(args.wall_timeout) or not math.isfinite(args.exit_timeout) or args.wall_timeout <= 0 or args.exit_timeout <= 0 or args.cpu is not None and args.cpu < 0:
        p.error("Timeouts must be positive; CPU index must be nonnegative.")
    manifest = json.loads((HERE / "tests_manifest.json").read_text())
    expected = json.loads((HERE / "expected_results.json").read_text())
    executables = {m: HERE / (m.replace("_", "-") + ".exe") for m in NAMES}
    if any(not x.is_file() for x in executables.values()):
        p.error("Build all three executables with build_windows.bat first.")
    env = dict(os.environ)
    forbidden = [k for k in env if k.lower().startswith(("cj", "mrt_")) and k.lower() != "cjprocessornum"]
    if forbidden:
        p.error("Unset inherited runtime overrides: " + ", ".join(forbidden))
    env = {k: v for k, v in env.items() if k.lower() != "cjprocessornum"}
    env["cjProcessorNum"] = "1"
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
        cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    host = {"platform": platform.platform(), "cpu": cpu, "python": sys.version,
            "node": platform.node(), "logical_cpu_count": os.cpu_count()}
    runtime_paths = set(HERE.glob("*.dll"))
    if env.get("CANGJIE_HOME"):
        runtime_paths.update((Path(env["CANGJIE_HOME"]) / "runtime/lib").rglob("*.dll"))
    configuration = {
        "schema": "current-hybrid-three-policy-windows-v1",
        "tests_manifest_sha256": wb.sha256(HERE / "tests_manifest.json"),
        "expected_results_sha256": wb.sha256(HERE / "expected_results.json"),
        "runner_sha256": wb.sha256(Path(__file__)),
        "measurement_helper_sha256": wb.sha256(HERE / "windows_bench.py"),
        "binary_sha256": {m: wb.sha256(x) for m, x in executables.items()},
        "source_sha256": {name: wb.sha256(HERE / name) for name in ("online.cj", "hybrid.cj", "hybrid.cpp")},
        "requested_cpu": args.cpu, "wall_timeout_s": args.wall_timeout,
        "exit_timeout_s": args.exit_timeout, "cjProcessorNum": "1",
        "CANGJIE_HOME": env.get("CANGJIE_HOME"),
        "launch_PATH": env.get("PATH", env.get("Path", "")),
        "runtime_dll_sha256": {str(path.resolve()): wb.sha256(path) for path in sorted(runtime_paths)},
        "runtime_inventory_scope": "executable directory and SDK runtime/lib; other PATH/system dependencies not exhaustively resolved",
        "host": host,
    }
    if args.resume:
        data = json.loads(args.out.read_text())
        if data["configuration"] != configuration:
            p.error("Resume refused: configuration, binary or input hashes changed.")
    else:
        if args.out.exists():
            p.error("Existing output requires --resume.")
        data = {
            "configuration": configuration,
            "host": host,
            "measurement": "whole process user+kernel including runtime exit, affinity before resume; serial",
            "checker": "independent direct protocol, not the official interactor",
            "records": [], "complete": False,
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    wb.save_json(args.out, data)
    index = {(r["id"], r["method"]): r for r in data["records"]}
    if len(index) != len(data["records"]):
        p.error("Duplicate test/method records; output is not a valid resume checkpoint.")
    api = wb.WindowsAPI()
    for number, case in enumerate(manifest["cases"]):
        path = HERE / case["path"]
        assert wb.sha256(path) == case["input_sha256"]
        order = NAMES[number % 3:] + NAMES[:number % 3]
        for method in order:
            if (case["id"], method) in index:
                continue
            identity = {"binary_sha256": configuration["binary_sha256"][method],
                        "input_sha256": case["input_sha256"]}
            row = wb.measure(api, executables[method], path, identity, env, args)
            row.update(id=case["id"], method=method, cohort=case["cohort"],
                       public_number=case["public_number"], **identity)
            ref = expected[case["id"]][method]
            row["matches_mac_response_bytes"] = row.get("stdout_sha256") == ref["response_sha256"]
            row["matches_mac_trench"] = row.get("physics", {}).get("T") == ref["T"]
            valid = row["status"] == "ok"
            row["contest_adjusted_kpi"] = (
                row["physics"]["KPI"] if valid and row["resource_limit_assessment"] == "pass" else 0.
            )
            data["records"].append(row)
            index[case["id"], method] = row
            wb.save_json(args.out, data)
            print(case["id"][:12], method, row["status"], row.get("CPU_user_plus_kernel_s"),
                  row["resource_limit_assessment"], flush=True)
            if row.get("interrupted"):
                return 130
    data["complete"] = len(index) == len(manifest["cases"]) * 3
    data["hybrid_response_mismatch_ids"] = [
        c["id"] for c in manifest["cases"]
        if index[c["id"], "hybrid_cpp"].get("stdout_sha256") != index[c["id"], "hybrid_cj"].get("stdout_sha256")
    ]
    data["mac_reference_mismatches"] = [
        {"id": r["id"], "method": r["method"]} for r in data["records"]
        if not r["matches_mac_response_bytes"] or not r["matches_mac_trench"]
    ]
    data["resource_summary"] = {
        m: {s: sum(r["resource_limit_assessment"] == s for r in data["records"] if r["method"] == m)
            for s in ("pass", "fail", "unconfirmed")}
        for m in NAMES
    }
    data["open15_adjusted"] = {
        m: sum(index[c["id"], m]["contest_adjusted_kpi"] * c["weight"]
               for c in manifest["cases"] if c["public_number"] is not None)
        for m in NAMES
    }
    wb.save_json(args.out, data)
    if data["hybrid_response_mismatch_ids"] or data["mac_reference_mismatches"] or any(r["status"] != "ok" for r in data["records"]):
        return 1
    if any(r["resource_limit_assessment"] == "fail" for r in data["records"]):
        return 2
    if any(r["resource_limit_assessment"] == "unconfirmed" for r in data["records"]):
        return 3
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
