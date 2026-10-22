#!/usr/bin/env python3
"""Run an interactive Pipes solver against the official source interactor."""

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import queue
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path


SCORE_RE = re.compile(
    r"Score\s*=\s*(\d+)/(\d+)\s*\*\s*weight\s*=\s*([0-9.eE+-]+)\s*x\s*"
    r"([0-9.eE+-]+)\s*=\s*([0-9.eE+-]+)"
)
INT_RE = re.compile(rb"^[+-]?\d+$")
MAX_RESPONSE_LINE = 4096


def parse_test(path):
    data = Path(path).read_text(encoding="ascii").split()
    if len(data) < 2:
        raise ValueError("test file needs weight, operation count, and commands")
    weight = float(data[0])
    n = int(data[1])
    if n < 0 or n > 200000:
        raise ValueError("operation count must be in [0, 200000]")
    raw_commands = [int(x) for x in data[2:]]
    # The participant archive includes an optional trailing 0 even though the
    # interactor reads only the declared n commands and emits its own terminator.
    if len(raw_commands) == n + 1 and raw_commands[-1] == 0:
        raw_commands.pop()
    if len(raw_commands) != n:
        raise ValueError("declared operation count does not match command count")
    commands = raw_commands
    if any(x == 0 or abs(x) > 40 and x > 0 for x in commands):
        raise ValueError("commands must be positive pipe lengths 1..40 or negative PIDs")
    pid_lengths = [0]
    alive = [False]
    live_total = 0
    peak_live = 0
    for command in commands:
        if command > 0:
            if command > 40:
                raise ValueError("pipe length exceeds 40")
            pid_lengths.append(command)
            alive.append(True)
            live_total += command
            peak_live = max(peak_live, live_total)
        else:
            pid = -command
            if pid <= 0 or pid >= len(pid_lengths) or not alive[pid]:
                raise ValueError("invalid delete command: PID is absent or already removed")
            alive[pid] = False
            live_total -= pid_lengths[pid]
    final_occupied = live_total
    lower_bound = ((peak_live + 19) // 20) * 20
    if final_occupied == 0 or lower_bound == 0:
        upper_kpi = 0.0
    else:
        upper_kpi = min(1.0, final_occupied / lower_bound)
    return {
        "weight": weight,
        "test_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "operation_count": n,
        "placement_count": len(pid_lengths) - 1,
        "peak_live_pipe_length_m": peak_live,
        "minimum_trench_lower_bound_m": lower_bound,
        "final_occupied_length_m": final_occupied,
        "kpi_upper_bound_from_live_volume": upper_kpi,
    }


def start_line_reader(stream, out_queue, label):
    def run():
        try:
            while True:
                line = stream.readline(MAX_RESPONSE_LINE + 1)
                if not line:
                    break
                out_queue.put(line)
                if len(line) > MAX_RESPONSE_LINE and not line.endswith(b"\n"):
                    # The caller will reject this chunk. Continue draining to avoid blocking.
                    continue
        except Exception as exc:
            out_queue.put(("reader_error", label + ": " + repr(exc)))
        finally:
            out_queue.put(None)

    thread = threading.Thread(target=run, name="pipes-reader-" + label, daemon=True)
    thread.start()
    return thread


def start_stderr_reader(stream):
    chunks = []

    def run():
        while True:
            chunk = stream.read(65536)
            if not chunk:
                return
            chunks.append(chunk)

    thread = threading.Thread(target=run, name="pipes-stderr", daemon=True)
    thread.start()
    return thread, chunks


def wait_line(out_queue, process, deadline):
    while time.monotonic() < deadline:
        try:
            item = out_queue.get(timeout=min(0.02, max(0.001, deadline - time.monotonic())))
        except queue.Empty:
            if process.returncode is None:
                try:
                    pid, status, usage = os.wait4(process.pid, os.WNOHANG)
                except ChildProcessError:
                    pid = 0
                    status = None
                    usage = None
                if pid:
                    process.returncode = os.waitstatus_to_exitcode(status)
                    process._pipes_wait4_usage = usage
            if process.returncode is not None:
                # Let the reader thread enqueue any bytes that were buffered before EOF.
                try:
                    return out_queue.get(timeout=0.05)
                except queue.Empty:
                    continue
            continue
        return item
    return "__TIMEOUT__"


def reap_with_stats(process, timeout):
    deadline = time.monotonic() + timeout
    while process.returncode is None and time.monotonic() < deadline:
        try:
            pid, status, usage = os.wait4(process.pid, os.WNOHANG)
        except ChildProcessError:
            break
        if pid:
            process.returncode = os.waitstatus_to_exitcode(status)
            process._pipes_wait4_usage = usage
            break
        time.sleep(0.005)
    if process.returncode is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            process.kill()
        try:
            pid, status, usage = os.wait4(process.pid, 0)
            if pid:
                process.returncode = os.waitstatus_to_exitcode(status)
                process._pipes_wait4_usage = usage
        except ChildProcessError:
            pass
    return getattr(process, "_pipes_wait4_usage", None)


def usage_fields(usage):
    if usage is None:
        return {"cpu_user_s": None, "cpu_system_s": None, "cpu_total_s": None, "peak_rss_mb": None}
    peak = float(usage.ru_maxrss)
    # ru_maxrss is bytes on macOS and KiB on Linux/BSD.
    if sys.platform == "darwin":
        peak_mb = peak / (1024.0 * 1024.0)
    else:
        peak_mb = peak / 1024.0
    user = float(usage.ru_utime)
    system = float(usage.ru_stime)
    return {
        "cpu_user_s": user,
        "cpu_system_s": system,
        "cpu_total_s": user + system,
        "peak_rss_mb": peak_mb,
    }


def terminate_and_reap(process):
    if process is None or process.returncode is not None:
        return getattr(process, "_pipes_wait4_usage", None) if process else None
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()
    return reap_with_stats(process, 1.0)


def read_response(out_queue, process, expected_count, deadline):
    result = []
    while len(result) < expected_count:
        item = wait_line(out_queue, process, deadline)
        if item == "__TIMEOUT__":
            raise TimeoutError("solver did not flush a complete response before deadline")
        if item is None:
            raise RuntimeError("solver closed stdout before replying")
        if isinstance(item, tuple) and item and item[0] == "reader_error":
            raise RuntimeError(item[1])
        if len(item) > MAX_RESPONSE_LINE or not item.endswith(b"\n"):
            raise RuntimeError("response line is too long or missing a newline")
        tokens = item.split()
        if not tokens:
            raise RuntimeError("empty response line")
        if len(tokens) != expected_count:
            raise RuntimeError(
                "expected %d integer token(s) on one response line, got %d"
                % (expected_count, len(tokens))
            )
        for token in tokens:
            if not INT_RE.match(token):
                raise RuntimeError("response contains a non-integer token")
            result.append(int(token))
        if len(result) > expected_count:
            raise RuntimeError("response contains extra tokens")
    return result


def get_item(out_queue, process, deadline):
    item = wait_line(out_queue, process, deadline)
    if item == "__TIMEOUT__":
        return "__TIMEOUT__"
    return item


def run_case(solver_argv, interactor, test_path, case_dir, response_timeout, wall_timeout):
    case_dir.mkdir(parents=True, exist_ok=True)
    meta = parse_test(test_path)
    judge_output = case_dir / "judge_output.txt"
    unused_answer = case_dir / "unused_answer.txt"
    report_path = case_dir / "interactor_report.txt"
    candidate_stderr_path = case_dir / "solver_stderr.txt"
    judge_stderr_path = case_dir / "interactor_stderr.txt"
    score_path = case_dir / "score.txt"
    for path in (judge_output, unused_answer, report_path, candidate_stderr_path, judge_stderr_path, score_path):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    unused_answer.write_text("", encoding="ascii")

    judge = None
    solver = None
    solver_q = queue.Queue()
    judge_q = queue.Queue()
    started = time.monotonic()
    status = "unknown"
    detail = ""
    candidate_stderr = []
    judge_stderr = []
    candidate_stderr_thread = None
    judge_stderr_thread = None
    solution_usage = None
    judge_usage = None
    command_count = 0
    try:
        solver = subprocess.Popen(
            solver_argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(case_dir),
            bufsize=0,
            start_new_session=True,
        )
        solver_reader = start_line_reader(solver.stdout, solver_q, "solver")
        candidate_stderr_thread, candidate_stderr = start_stderr_reader(solver.stderr)
        judge = subprocess.Popen(
            [str(interactor), str(Path(test_path).resolve()), judge_output.name, unused_answer.name, report_path.name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(case_dir),
            bufsize=0,
            start_new_session=True,
        )
        judge_reader = start_line_reader(judge.stdout, judge_q, "interactor")
        judge_stderr_thread, judge_stderr = start_stderr_reader(judge.stderr)
        total_deadline = started + wall_timeout
        saw_terminator = False
        while True:
            if time.monotonic() >= total_deadline:
                raise TimeoutError("overall wall timeout exceeded")
            judge_line = wait_line(judge_q, judge, min(total_deadline, time.monotonic() + response_timeout))
            if judge_line == "__TIMEOUT__":
                raise TimeoutError("interactor did not issue a command before deadline")
            if judge_line is None:
                if judge.returncode is None:
                    raise RuntimeError("interactor closed its command stream unexpectedly")
                raise RuntimeError("interactor exited before issuing terminator 0")
            if isinstance(judge_line, tuple) and judge_line[0] == "reader_error":
                raise RuntimeError(judge_line[1])
            if not judge_line.endswith(b"\n") or len(judge_line) > MAX_RESPONSE_LINE:
                raise RuntimeError("malformed command line from interactor")
            parts = judge_line.split()
            if len(parts) != 1 or not INT_RE.match(parts[0]):
                raise RuntimeError("interactor command is not one integer")
            command = int(parts[0])
            solver.stdin.write(judge_line)
            solver.stdin.flush()
            command_count += 1
            if command == 0:
                saw_terminator = True
                solver.stdin.close()
                # The specification requires immediate termination and no response to zero.
                post_deadline = min(total_deadline, time.monotonic() + 2.0)
                while solver.returncode is None and time.monotonic() < post_deadline:
                    try:
                        pid, status_word, usage = os.wait4(solver.pid, os.WNOHANG)
                    except ChildProcessError:
                        pid = 0
                    if pid:
                        solver.returncode = os.waitstatus_to_exitcode(status_word)
                        solver._pipes_wait4_usage = usage
                        break
                    time.sleep(0.005)
                if solver.returncode is None:
                    raise TimeoutError("solver did not terminate shortly after receiving 0")
                solution_usage = getattr(solver, "_pipes_wait4_usage", None)
                # Allow the stdout reader to drain and reject any byte after the final 0.
                while True:
                    extra = get_item(solver_q, solver, time.monotonic() + 0.2)
                    if extra == "__TIMEOUT__":
                        break
                    if extra is None:
                        break
                    if isinstance(extra, tuple):
                        raise RuntimeError(extra[1])
                    if extra:
                        raise RuntimeError("solver wrote to stdout after receiving final 0")
                break
            expected = 2 if command > 0 else 1
            response = read_response(solver_q, solver, expected, min(total_deadline, time.monotonic() + response_timeout))
            judge.stdin.write((" ".join(map(str, response)) + "\n").encode("ascii"))
            judge.stdin.flush()

        judge_usage = reap_with_stats(judge, max(0.1, total_deadline - time.monotonic()))
        solution_usage = solution_usage or getattr(solver, "_pipes_wait4_usage", None)
        if candidate_stderr_thread is not None:
            candidate_stderr_thread.join(timeout=1.0)
        if judge_stderr_thread is not None:
            judge_stderr_thread.join(timeout=1.0)
        judge.returncode = judge.returncode if judge.returncode is not None else -999
        solver.returncode = solver.returncode if solver.returncode is not None else -999
        score = None
        if score_path.exists():
            try:
                score = float(score_path.read_text(encoding="ascii").split()[0])
            except Exception:
                score = None
        stderr_text = b"".join(judge_stderr).decode("utf-8", errors="replace")
        candidate_stderr_text = b"".join(candidate_stderr).decode("utf-8", errors="replace")
        candidate_stderr_path.write_text(candidate_stderr_text, encoding="utf-8")
        judge_stderr_path.write_text(stderr_text, encoding="utf-8")
        score_match = SCORE_RE.search(stderr_text)
        if score_match:
            occupied = int(score_match.group(1))
            trench = int(score_match.group(2))
            kpi = occupied / trench if trench else 0.0
            judge_weight = float(score_match.group(4))
            score = float(score_match.group(5))
        else:
            occupied = None
            trench = None
            kpi = None
            judge_weight = None
        if not saw_terminator:
            status = "protocol_error"
            detail = "final 0 was not observed"
        elif judge.returncode != 0:
            status = "invalid"
            detail = stderr_text.strip() or "official interactor returned nonzero status"
        elif solver.returncode != 0:
            status = "solver_error"
            detail = "solver exited with status %s" % solver.returncode
        elif score is None or kpi is None:
            status = "missing_score"
            detail = "official interactor did not produce a parseable score"
        else:
            status = "ok"
            detail = ""
        elapsed = time.monotonic() - started
        rec = dict(meta)
        rec.update({
            "case": Path(test_path).stem,
            "test_file": str(Path(test_path).resolve()),
            "status": status,
            "detail": detail,
            "judge_commands_seen_including_final_zero": command_count,
            "occupied_length_m": occupied,
            "trench_length_m": trench,
            "kpi": kpi,
            "weighted_score": score,
            "official_weight": judge_weight if judge_weight is not None else meta["weight"],
            "kpi_upper_bound_from_live_volume": meta["kpi_upper_bound_from_live_volume"],
            "fraction_of_bound": (kpi / meta["kpi_upper_bound_from_live_volume"]
                                  if kpi is not None and meta["kpi_upper_bound_from_live_volume"] > 0 else None),
            "wall_orchestration_s": elapsed,
        })
        rec["lower_bound_to_actual_trench_ratio"] = (
            meta["minimum_trench_lower_bound_m"] / trench
            if trench is not None and trench > 0 else None
        )
        rec.update({"solver_" + k: v for k, v in usage_fields(solution_usage).items()})
        rec.update({"interactor_" + k: v for k, v in usage_fields(judge_usage).items()})
        rec["candidate_stderr"] = candidate_stderr_text[-4000:]
        rec["interactor_stderr"] = stderr_text[-4000:]
        rec["judge_output_file"] = str(judge_output)
        rec["interactor_report_file"] = str(report_path)
        rec["candidate_stderr_file"] = str(candidate_stderr_path)
        rec["interactor_stderr_file"] = str(judge_stderr_path)
        return rec
    except Exception as exc:
        status = "timeout" if isinstance(exc, TimeoutError) else "protocol_error"
        detail = str(exc)
        if solver is not None:
            solution_usage = terminate_and_reap(solver)
        if judge is not None:
            judge_usage = terminate_and_reap(judge)
        if candidate_stderr_thread is not None:
            candidate_stderr_thread.join(timeout=1.0)
        if judge_stderr_thread is not None:
            judge_stderr_thread.join(timeout=1.0)
        candidate_stderr_text = b"".join(candidate_stderr).decode("utf-8", errors="replace")
        judge_stderr_text = b"".join(judge_stderr).decode("utf-8", errors="replace")
        candidate_stderr_path.write_text(candidate_stderr_text, encoding="utf-8")
        judge_stderr_path.write_text(judge_stderr_text, encoding="utf-8")
        elapsed = time.monotonic() - started
        rec = dict(meta)
        rec.update({
            "case": Path(test_path).stem,
            "test_file": str(Path(test_path).resolve()),
            "status": status,
            "detail": detail,
            "judge_commands_seen_including_final_zero": command_count,
            "occupied_length_m": None,
            "trench_length_m": None,
            "kpi": 0.0,
            "weighted_score": 0.0,
            "official_weight": meta["weight"],
            "kpi_upper_bound_from_live_volume": meta["kpi_upper_bound_from_live_volume"],
            "fraction_of_bound": 0.0 if meta["kpi_upper_bound_from_live_volume"] > 0 else None,
            "lower_bound_to_actual_trench_ratio": None,
            "wall_orchestration_s": elapsed,
        })
        rec.update({"solver_" + k: v for k, v in usage_fields(solution_usage).items()})
        rec.update({"interactor_" + k: v for k, v in usage_fields(judge_usage).items()})
        rec["candidate_stderr"] = candidate_stderr_text[-4000:]
        rec["interactor_stderr"] = judge_stderr_text[-4000:]
        rec["judge_output_file"] = str(judge_output)
        rec["interactor_report_file"] = str(report_path)
        rec["candidate_stderr_file"] = str(candidate_stderr_path)
        rec["interactor_stderr_file"] = str(judge_stderr_path)
        return rec
    finally:
        for proc in (solver, judge):
            if proc is not None:
                if proc.returncode is None:
                    terminate_and_reap(proc)
                for stream_name in ("stdin", "stdout", "stderr"):
                    stream = getattr(proc, stream_name, None)
                    if stream is not None:
                        try:
                            stream.close()
                        except Exception:
                            pass


def write_csv(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = []
    for rec in records:
        for key in rec:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver", required=True, help="solver command; quoted and split with shell-like rules")
    parser.add_argument("--name", default="solver", help="strategy label for the report")
    parser.add_argument("--interactor", default="tools/interactor", help="locally compiled official interactor")
    parser.add_argument("--tests", required=True, help="one .in file or directory of .in files")
    parser.add_argument("--out", required=True, help="directory for JSON/CSV report and per-run files")
    parser.add_argument("--response-timeout", type=float, default=5.0, help="seconds allowed per interactive response")
    parser.add_argument("--wall-timeout", type=float, default=120.0, help="seconds allowed for a full test including orchestration")
    parser.add_argument("--cpu-limit", type=float, default=5.0, help="official solver CPU limit in seconds; report violations")
    parser.add_argument("--memory-limit-mb", type=float, default=256.0, help="official solver RSS limit in MiB; report violations")
    args = parser.parse_args()

    tests_path = Path(args.tests)
    test_files = sorted(
        tests_path.glob("*.in"),
        key=lambda p: (0, int(p.stem)) if p.stem.isdigit() else (1, p.name),
    ) if tests_path.is_dir() else [tests_path]
    if not test_files:
        parser.error("no .in files found under --tests")
    solver_argv = shlex.split(args.solver)
    if not solver_argv:
        parser.error("--solver parsed to an empty command")
    first = Path(solver_argv[0])
    if first.exists():
        solver_argv[0] = str(first.resolve())
    interactor = Path(args.interactor).resolve()
    if not interactor.exists():
        parser.error("interactor not found; run `make interactor` first")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for test_file in test_files:
        case_dir = out / "runs" / test_file.stem
        record = run_case(
            solver_argv,
            interactor,
            test_file,
            case_dir,
            args.response_timeout,
            args.wall_timeout,
        )
        record["strategy"] = args.name
        record["cpu_limit_s"] = args.cpu_limit
        record["memory_limit_mb"] = args.memory_limit_mb
        record["solver_cpu_limit_exceeded"] = (
            record["solver_cpu_total_s"] is not None and record["solver_cpu_total_s"] >= args.cpu_limit
        )
        record["solver_memory_limit_exceeded"] = (
            record["solver_peak_rss_mb"] is not None and record["solver_peak_rss_mb"] >= args.memory_limit_mb
        )
        records.append(record)
        print("%s  %s  KPI=%s  CPU=%s s  wall=%s s  RSS=%s MiB"
              % (record["case"], record["status"], record["kpi"],
                 record["solver_cpu_total_s"], record["wall_orchestration_s"], record["solver_peak_rss_mb"]))

    weighted = sum(float(r["weighted_score"] or 0.0) for r in records)
    bound_fractions = [r["fraction_of_bound"] for r in records if r["fraction_of_bound"] is not None]
    upper_bounds = [r["kpi_upper_bound_from_live_volume"] for r in records]
    summary = {
        "strategy": args.name,
        "solver_argv": solver_argv,
        "interactor": str(interactor),
        "tests": [str(Path(p).resolve()) for p in test_files],
        "case_count": len(records),
        "ok_count": sum(r["status"] == "ok" for r in records),
        "weighted_score_sum": weighted,
        "weight_sum": sum(float(r["official_weight"]) for r in records),
        "mean_kpi_upper_bound_from_live_volume": (sum(upper_bounds) / len(upper_bounds) if upper_bounds else None),
        "mean_kpi_fraction_of_bound": (sum(bound_fractions) / len(bound_fractions) if bound_fractions else None),
        "worst_relative_regret_vs_bound": (1.0 - min(bound_fractions) if bound_fractions else None),
        "mean_lower_bound_to_actual_trench_ratio": (sum(bound_fractions) / len(bound_fractions) if bound_fractions else None),
        "min_lower_bound_to_actual_trench_ratio": min(bound_fractions) if bound_fractions else None,
        "mean_trench_to_lower_bound_ratio": (
            sum(r["trench_length_m"] / r["minimum_trench_lower_bound_m"]
                for r in records if r["trench_length_m"] is not None and r["minimum_trench_lower_bound_m"] > 0)
            / max(1, sum(r["trench_length_m"] is not None and r["minimum_trench_lower_bound_m"] > 0 for r in records))
        ),
        "is_official_open_test_set": len(records) == 15 and all(Path(p).name == "%d.in" % i for i, p in enumerate(test_files, 1)),
        "cpu_measurement": "solver child only via os.wait4 (user+system CPU); interactor CPU reported separately",
        "wall_measurement": "wall orchestration includes Python harness, solver, and interactor",
        "rss_measurement": "OS ru_maxrss for solver child only; unit converted to MiB (macOS reports bytes)",
        "host_platform": platform.platform(),
        "python_version": sys.version,
        "records": records,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(out / "cases.csv", records)
    print("weighted_score_sum=%.12g (sum over these tests only)" % weighted)
    print("JSON: %s" % (out / "summary.json"))
    print("CSV:  %s" % (out / "cases.csv"))
    if any(r["status"] != "ok" or r["solver_cpu_limit_exceeded"] or r["solver_memory_limit_exceeded"] for r in records):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
