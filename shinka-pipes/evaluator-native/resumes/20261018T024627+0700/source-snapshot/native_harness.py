#!/usr/bin/env python3
"""Reuse report/aggregation code, with the official checker driving the solver."""

from __future__ import annotations

import json
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "evaluator-fast"))
from reference import check_reference, load_frozen


def run_case(base, solver_argv, native, test_path, case_dir, response_timeout, wall_timeout):
    case_dir.mkdir(parents=True, exist_ok=True)
    meta = base.parse_test(test_path)
    names = {"judge_output_file": "judge_output.txt", "interactor_report_file": "interactor_report.txt",
             "candidate_stderr_file": "solver_stderr.txt", "interactor_stderr_file": "interactor_stderr.txt"}
    paths = {key: case_dir / value for key, value in names.items()}
    (case_dir / "unused_answer.txt").write_text("")
    started = time.monotonic()
    process = None
    native_usage = None
    native_report = {}
    authentic_pid = None
    control_read, control_write = os.pipe()
    try:
        with paths["interactor_stderr_file"].open("wb") as log:
            process = subprocess.Popen([
                str(native), str(Path(test_path).resolve()), "judge_output.txt", "unused_answer.txt",
                "interactor_report.txt", str(response_timeout), str(wall_timeout), "--", *solver_argv,
            ], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=log, cwd=case_dir,
                env={**os.environ, "PIPES_NATIVE_CONTROL_FD": str(control_write)},
                pass_fds=(control_write,), start_new_session=True)
            os.close(control_write)
            control_write = -1
            native_usage = base.reap_with_stats(process, wall_timeout + 0.5)
        control = bytearray()
        while chunk := os.read(control_read, 65536):
            control.extend(chunk)
            if len(control) > 65536:
                raise ValueError("native control report too large")
        lines = bytes(control).splitlines()
        if lines:
            authentic_pid = int(lines[0])
        if len(lines) == 2:
            native_report = json.loads(lines[1])
            if native_report["solver_pid"] != authentic_pid:
                raise ValueError("native child identity mismatch")
        (case_dir / "native_report.json").write_text(json.dumps(native_report, indent=2) + "\n")
    finally:
        if process is not None and process.returncode is None:
            base.terminate_and_reap(process)
        if authentic_pid is None:
            # On cancellation the already-written control PID still identifies
            # the child, without trusting files writable by the candidate.
            os.set_blocking(control_read, False)
            try:
                pending = os.read(control_read, 65536)
                if pending:
                    authentic_pid = int(pending.splitlines()[0])
            except (BlockingIOError, ValueError):
                pass
        if authentic_pid and authentic_pid > 1:
            try:
                os.killpg(authentic_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        os.close(control_read)
        if control_write >= 0:
            os.close(control_write)
    stderr = paths["interactor_stderr_file"].read_text(errors="replace")
    candidate_stderr = paths["candidate_stderr_file"].read_text(errors="replace") if paths["candidate_stderr_file"].exists() else ""
    match = base.SCORE_RE.search(stderr)
    occupied, trench, kpi, weight, score = None, None, None, None, None
    if match:
        occupied, trench = int(match[1]), int(match[2])
        kpi = occupied / trench if trench else 0.0
        weight, score = float(match[4]), float(match[5])
    if native_report.get("error"):
        status, detail = native_report["error_kind"], native_report["error"]
    elif not native_report or not native_report.get("saw_zero"):
        status, detail = "protocol_error", stderr.strip() or "native checker ended before final 0"
    elif process.returncode != 0 or native_report.get("official_returncode") != 0:
        status, detail = "invalid", stderr.strip() or "official checker returned nonzero"
    elif native_report.get("solver_returncode") != 0:
        status, detail = "solver_error", "solver exited with status %s" % native_report.get("solver_returncode")
    elif not native_report.get("has_usage"):
        status, detail = "invalid", "fresh solver resource measurement unavailable"
    elif kpi is None or score is None:
        status, detail = "missing_score", "official interactor did not produce a parseable score"
    else:
        status, detail = "ok", ""
    if time.monotonic() - started > wall_timeout:
        status, detail = "timeout", "overall wall timeout exceeded"
    if status != "ok":
        occupied, trench, kpi, score = None, None, 0.0, 0.0
    solver_usage = None
    if native_report.get("has_usage"):
        solver_usage = SimpleNamespace(ru_utime=native_report["cpu_user_s"],
                                       ru_stime=native_report["cpu_system_s"], ru_maxrss=native_report["maxrss_raw"])
    if "self_cpu_user_s" in native_report:
        # wait4(native_driver) can include the solver that the driver reaped.
        # Do not count that child twice in diagnostic interactor CPU/RSS.
        native_usage = SimpleNamespace(ru_utime=native_report["self_cpu_user_s"],
                                       ru_stime=native_report["self_cpu_system_s"],
                                       ru_maxrss=native_report["self_maxrss_raw"])
    record = dict(meta)
    record.update({
        "case": Path(test_path).stem, "test_file": str(Path(test_path).resolve()),
        "status": status, "detail": detail,
        "judge_commands_seen_including_final_zero": native_report.get("commands", 0),
        "occupied_length_m": occupied, "trench_length_m": trench, "kpi": kpi, "weighted_score": score,
        "official_weight": weight if weight is not None else meta["weight"],
        "fraction_of_bound": kpi / meta["kpi_upper_bound_from_live_volume"] if kpi is not None and meta["kpi_upper_bound_from_live_volume"] > 0 else None,
        "lower_bound_to_actual_trench_ratio": meta["minimum_trench_lower_bound_m"] / trench if trench else None,
        "wall_orchestration_s": time.monotonic() - started,
        "candidate_stderr": candidate_stderr[-4000:], "interactor_stderr": stderr[-4000:],
        **{key: str(value) for key, value in paths.items()},
        **{"solver_" + key: value for key, value in base.usage_fields(solver_usage).items()},
        **{"interactor_" + key: value for key, value in base.usage_fields(native_usage).items()},
    })
    return record


def skipped_record(base, test_path):
    meta = base.parse_test(test_path)
    record = dict(meta, case=Path(test_path).stem, test_file=str(Path(test_path).resolve()),
                  status="skipped", detail="not executed after a proven correctness/resource failure",
                  judge_commands_seen_including_final_zero=0, occupied_length_m=None,
                  trench_length_m=None, kpi=None, weighted_score=0.0, official_weight=meta["weight"],
                  fraction_of_bound=None, lower_bound_to_actual_trench_ratio=None,
                  wall_orchestration_s=0.0, candidate_stderr="", interactor_stderr="")
    record.update({prefix + key: None for prefix in ("solver_", "interactor_")
                   for key in ("cpu_user_s", "cpu_system_s", "cpu_total_s", "peak_rss_mb")})
    return record


def failed(record, cpu_limit=5, memory_limit=256):
    cpu, rss = record["solver_cpu_total_s"], record["solver_peak_rss_mb"]
    return record["status"] != "ok" or cpu is None or rss is None or cpu >= cpu_limit or rss >= memory_limit


def build_harness():
    base = load_frozen("task/tools/pipes_harness.py")
    rejected = False

    def evaluate_or_skip(solver_argv, native, test_path, case_dir, response_timeout, wall_timeout):
        nonlocal rejected
        if rejected:
            return skipped_record(base, test_path)
        record = run_case(base, solver_argv, native, test_path, case_dir, response_timeout, wall_timeout)
        if failed(record):
            rejected = True
        return record

    base.run_case = evaluate_or_skip
    return base


def main():
    check_reference()
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--workers", type=int, default=1, choices=range(1, 9))
    selection, remaining = parser.parse_known_args()
    sys.argv[1:] = remaining
    if selection.workers == 1:
        return build_harness().main()
    args_parser = argparse.ArgumentParser(add_help=False)
    for name in ("solver", "interactor", "tests", "out"):
        args_parser.add_argument("--" + name, required=True)
    args_parser.add_argument("--response-timeout", type=float, default=5)
    args_parser.add_argument("--wall-timeout", type=float, default=180)
    args_parser.add_argument("--cpu-limit", type=float, default=5)
    args_parser.add_argument("--memory-limit-mb", type=float, default=256)
    args, _ = args_parser.parse_known_args()
    path = Path(args.tests)
    files = sorted(path.glob("*.in"), key=lambda p: (0, int(p.stem)) if p.stem.isdigit() else (1, p.name)) if path.is_dir() else [path]
    if not files:
        raise ValueError("no input files")
    solver = shlex.split(args.solver)
    if not solver:
        raise ValueError("--solver parsed to an empty command")
    if Path(solver[0]).exists():
        solver[0] = str(Path(solver[0]).resolve())
    base = load_frozen("task/tools/pipes_harness.py")
    records, next_index, rejected = {}, 0, False
    with ThreadPoolExecutor(max_workers=selection.workers) as pool:
        pending = {}

        def submit():
            nonlocal next_index
            index = next_index
            next_index += 1
            file = files[index]
            job = pool.submit(run_case, base, solver, Path(args.interactor).resolve(), file,
                              Path(args.out) / "runs" / file.stem, args.response_timeout, args.wall_timeout)
            pending[job] = index

        while next_index < min(len(files), selection.workers):
            submit()
        while pending:
            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for job in completed:
                index = pending.pop(job)
                records[index] = job.result()
                rejected = rejected or failed(records[index], args.cpu_limit, args.memory_limit_mb)
            while not rejected and next_index < len(files) and len(pending) < selection.workers:
                submit()
    for index in range(next_index, len(files)):
        records[index] = skipped_record(base, files[index])
    by_path = {str(file.resolve()): records[index] for index, file in enumerate(files)}
    # The original main emits results in its original canonical order, regardless
    # of completion order. Family means retain precisely the same float order.
    base.run_case = lambda solver, native, test, *unused: by_path[str(Path(test).resolve())]
    result = base.main()
    summary_path = Path(args.out) / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["native_workers"] = selection.workers
    summary["native_cpu_measurement_note"] = "solver via POSIX wait4; checker/transport self via getrusage(RUSAGE_SELF), excludes solver"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
