"""Explicit future-run supervisor. Import/--check never starts an experiment."""

import argparse
import fcntl
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from research import atomic_json
from support import ROOT, PARENT, digest


def prepared_run(run):
    from research_runner import checked_run, check_upstream
    from evaluator import verify_snapshot
    verify_snapshot()
    check_upstream()
    run, manifest = checked_run(run)
    policy = json.loads((ROOT / "night-policy.json").read_text())
    if (manifest.get("night_protocol") != policy["version"]
            or manifest.get("night_policy_sha256") != digest(ROOT / "night-policy.json")
            or manifest["target_generations"] != policy["target_generations"]
            or manifest.get("model") != policy["model"]
            or manifest.get("reasoning_effort") != "xhigh"
            or manifest.get("launch_authorized") is not True):
        raise ValueError("a separately authorized night run with a pinned policy/model/budget is required")
    task = run / "task"
    for name in ("shinka.yaml", "evaluate.py", "AGENTS.md"):
        if digest(task / name) != digest(ROOT / "task" / name):
            raise ValueError("future task differs from the prepared support: " + name)
    if digest(task / "initial.cpp") != manifest.get("source_sha256"):
        raise ValueError("future run needs an explicitly selected, pinned initial program")
    return run, manifest, policy


class ProcessTree:
    """Track only this worker's descendants, including separate child sessions."""

    def __init__(self, pid):
        import psutil
        self.psutil = psutil
        self.root = psutil.Process(pid)
        self.known = {pid: self.root.create_time()}
        self.errors = set()

    def capture(self):
        for pid, created in list(self.known.items()):
            try:
                process = self.psutil.Process(pid)
                if process.create_time() == created:
                    for child in process.children(recursive=True):
                        self.known[child.pid] = child.create_time()
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.AccessDenied:
                self.errors.add(f"cannot inspect owned process {pid}")

    def send(self, sig):
        self.capture()
        for pid, created in reversed(list(self.known.items())):
            try:
                process = self.psutil.Process(pid)
                if process.create_time() == created:
                    process.send_signal(sig)
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.AccessDenied:
                self.errors.add(f"cannot signal owned process {pid}")

    def confirm_cleanup(self):
        processes = []
        for pid, created in self.known.items():
            try:
                process = self.psutil.Process(pid)
                if process.create_time() == created:
                    processes.append(process)
            except self.psutil.NoSuchProcess:
                pass
            except self.psutil.AccessDenied:
                self.errors.add(f"cannot confirm exit of owned process {pid}")
        _, alive = self.psutil.wait_procs(processes, timeout=2)
        return not alive and not self.errors


def supervise(run):
    run, manifest, policy = prepared_run(run)
    lock = (run / ".night-manager.lock").open("a+")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise RuntimeError("this run already has a night supervisor")
    try:
        # A crash/resume must not restart the overnight clock.
        clock_path = run / "night-clock.json"
        if clock_path.exists():
            clock = json.loads(clock_path.read_text())
        else:
            started = time.time()
            clock = {"started_at": started,
                     "soft_deadline": None if policy["soft_deadline_seconds"] is None else started + policy["soft_deadline_seconds"],
                     "hard_deadline": None if policy["hard_deadline_seconds"] is None else started + policy["hard_deadline_seconds"]}
            atomic_json(clock_path, clock)
        remaining = None if clock["hard_deadline"] is None else clock["hard_deadline"] - time.time()
        if remaining is not None and remaining <= 0:
            raise RuntimeError("the original overnight deadline has already expired")
        old = run / "night-supervisor.json"
        if old.exists():
            state = json.loads(old.read_text())
            import psutil
            try:
                process = psutil.Process(state["worker_pid"])
                if process.create_time() == state.get("worker_created_at") and process.is_running():
                    raise RuntimeError("a previous worker is still alive; do not resume concurrently")
            except (psutil.NoSuchProcess, KeyError):
                pass
            if state.get("status") == "running" or state.get("cleanup_confirmed") is not True:
                raise RuntimeError("previous supervisor ended without confirmed cleanup; reconcile before resume")
            for pid, created in state.get("processes", {}).items():
                try:
                    process = psutil.Process(int(pid))
                    if process.create_time() == created and process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                        raise RuntimeError("a previous owned helper is still alive; reconcile before resume")
                except psutil.NoSuchProcess:
                    pass
        # All descendants inherit the worker environment and process provenance.
        sys.path.insert(0, str(PARENT))
        from local_runtime import subscription_environment
        env = subscription_environment()
        usage_enabled = policy.get("usage_guard", {}).get("enabled", False)
        if usage_enabled:
            from usage_guard import gate
            gate(run, min_remaining_percent=65, max_age_seconds=60)
        env["PIPES_SEARCH_V31_SUPERVISOR"] = str(os.getpid())
        for name in ("soft_deadline", "hard_deadline"):
            key = "PIPES_SEARCH_V31_" + name.upper()
            if clock[name] is None:
                env.pop(key, None)
            else:
                env[key] = str(clock[name])
        log = (run / "night-manager.log").open("a")
        child = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()),
                                  "--worker", str(run)], cwd=str(ROOT), env=env,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        tree = ProcessTree(child.pid)
        state = {"worker_pid": child.pid, "worker_created_at": tree.known[child.pid],
                 "supervisor_pid": os.getpid(), "status": "running", "cleanup_confirmed": False,
                 "processes": dict(tree.known), **clock}
        atomic_json(old, state)
        deadline = None if remaining is None else time.monotonic() + remaining
        terminated = False
        termination_reason = None
        kill_at = None
        next_usage_check = time.monotonic() + 60
        try:
            while child.poll() is None:
                tree.capture()
                if state["processes"] != tree.known:
                    state["processes"] = dict(tree.known)
                    atomic_json(old, state)
                left = None if deadline is None else min(deadline - time.monotonic(), clock["hard_deadline"] - time.time())
                if usage_enabled and not terminated and time.monotonic() >= next_usage_check:
                    try:
                        gate(run, min_remaining_percent=65, max_age_seconds=0)
                    except Exception as exc:
                        termination_reason = "usage_guard: " + str(exc)
                    next_usage_check = time.monotonic() + 60
                request_path = run / "night-stop-request.json"
                if request_path.exists() and not terminated:
                    request = json.loads(request_path.read_text())
                    if request.get("immediate") or request.get("protocol") == "codex-quota-guard-v1" or str(request.get("reason", "")).startswith(("usage_", "quota")):
                        termination_reason = str(request.get("reason", "requested_stop"))
                if termination_reason is not None and not terminated:
                    tree.send(signal.SIGTERM)
                    terminated = True
                    kill_at = time.monotonic() + 5
                if kill_at is not None and time.monotonic() >= kill_at:
                    tree.send(signal.SIGKILL)
                    break
                if left is not None and left <= 5 and not terminated:
                    atomic_json(run / "night-stop-request.json", {"reason": "hard_deadline"})
                    tree.send(signal.SIGTERM)
                    terminated = True
                    termination_reason = "hard_deadline"
                if left is not None and left <= 0:
                    tree.send(signal.SIGKILL)
                    break
                time.sleep(1.0 if left is None else min(1.0, max(.01, left)))
            child.wait(timeout=5)
        finally:
            # Also reap headless/evaluator children which started their own session.
            tree.send(signal.SIGKILL)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            cleaned = tree.confirm_cleanup()
            log.close()
            state.update(status=(("stopped_hard_deadline" if termination_reason == "hard_deadline" else "stopped_requested") if terminated else "worker_finished") if cleaned else "cleanup_unconfirmed",
                         worker_exit_code=child.poll(), finished_at=time.time(), cleanup_confirmed=cleaned,
                         processes=dict(tree.known), cleanup_errors=sorted(tree.errors), stop_reason=termination_reason)
            atomic_json(old, state)
            manifest_path = run / "run-manifest.json"
            if manifest_path.exists():
                final_manifest = json.loads(manifest_path.read_text())
                runtime_path = run / "night-runtime-state.json"
                runtime = json.loads(runtime_path.read_text()) if runtime_path.exists() else {}
                from monitor import evaluated_summary
                completed = evaluated_summary(run)["completed"]
                final_manifest.update(status="completed" if completed >= policy.get("target_generations", 800) else "stopped",
                                      finished_at=time.time(), cleanup_confirmed=cleaned,
                                      stop_reason=termination_reason or runtime.get("stop_reason") or "worker_exit",
                                      worker_exit_code=child.poll())
                atomic_json(manifest_path, final_manifest)
                active_path = ROOT / "active-run.json"
                if active_path.exists():
                    active = json.loads(active_path.read_text())
                    if active.get("run_dir") == str(run):
                        active.update(status=final_manifest["status"], finished_at=final_manifest["finished_at"],
                                      stop_reason=final_manifest["stop_reason"], cleanup_confirmed=cleaned)
                        atomic_json(active_path, active)
        return child.returncode
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


def worker(run):
    run, manifest, _ = prepared_run(run)
    if os.environ.get("PIPES_SEARCH_V31_SUPERVISOR") != str(os.getppid()):
        raise RuntimeError("night worker must be launched by its local supervisor")
    from research_runner import run_with_research
    cli = importlib.import_module("shinka.cli.run")
    result, stopped = run_with_research(cli, task=run / "task", run=run,
                                       generations=manifest["target_generations"])
    atomic_json(run / "night-outcome.json", {"cli_result": result, "stop": stopped})
    return result or 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--execute-authorized-run", type=Path)
    mode.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check:
        from evaluator import verify_snapshot
        from research_runner import check_upstream
        verify_snapshot()
        check_upstream()
        print("Night support verified; no process, model call or evaluation started.")
        return 0
    return worker(args.worker) if args.worker else supervise(args.execute_authorized_run)


if __name__ == "__main__":
    raise SystemExit(main())
