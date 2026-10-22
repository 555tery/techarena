"""Fail-closed guard for local Codex subscription quota.

The only Codex app-server method used here is the read-only
``account/rateLimits/read`` request. This module never starts a thread or turn,
uses an API-key fallback, or consumes a reset credit.
"""

from __future__ import annotations

import fcntl
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import time
from typing import Callable


PROTOCOL = "codex-quota-guard-v1"
USAGE_METHOD = "account/rateLimits/read"
DEFAULT_MIN_REMAINING_PERCENT = 65.0
DEFAULT_MAX_AGE_SECONDS = 60.0
MAX_RPC_SECONDS = 20.0
MAX_GATE_SECONDS = 20.0
CODEX_BIN = Path(
    "/Applications/ChatGPT.app/Contents/Resources/codex-cli/"
    "CodexCLI.app/Contents/MacOS/codex"
)


class UsageGuardError(RuntimeError):
    """The quota could not be read or validated safely."""


class UsageStopped(UsageGuardError):
    """A persisted stop request or the quota threshold blocks further calls."""


def _finite_number(value, name, *, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UsageGuardError(f"invalid {name} in Codex quota response")
    value = float(value)
    if not math.isfinite(value):
        raise UsageGuardError(f"invalid {name} in Codex quota response")
    if minimum is not None and value < minimum:
        raise UsageGuardError(f"invalid {name} in Codex quota response")
    if maximum is not None and value > maximum:
        raise UsageGuardError(f"invalid {name} in Codex quota response")
    return value


def _optional_number(value, name, *, minimum=None):
    if value is None:
        return None
    return _finite_number(value, name, minimum=minimum)


def _rate_limit_buckets(response):
    if not isinstance(response, dict):
        raise UsageGuardError("Codex quota response has an invalid structure")
    if "rateLimitsByLimitId" in response:
        buckets = response["rateLimitsByLimitId"]
        if not isinstance(buckets, dict):
            raise UsageGuardError("Codex quota buckets have an invalid structure")
        if not buckets:
            raise UsageGuardError("Codex returned no rate-limit buckets")
        return buckets
    legacy = response.get("rateLimits")
    if not isinstance(legacy, dict):
        raise UsageGuardError("Codex returned no rate-limit buckets")
    bucket_id = legacy.get("limitId", "codex")
    if not isinstance(bucket_id, str) or not bucket_id:
        raise UsageGuardError("Codex quota bucket has an invalid identifier")
    return {bucket_id: legacy}


def _normalize_usage(response, captured_at):
    """Return a small, account-safe snapshot; null windows remain unavailable."""
    captured_at = _finite_number(captured_at, "capture time", minimum=0)
    buckets = _rate_limit_buckets(response)
    normalized = []
    remaining_values = []

    for map_id, bucket in buckets.items():
        if not isinstance(map_id, str) or not map_id or len(map_id) > 120:
            raise UsageGuardError("Codex quota bucket has an invalid identifier")
        if not isinstance(bucket, dict):
            raise UsageGuardError("Codex quota bucket has an invalid structure")
        bucket_id = bucket.get("limitId", map_id)
        if not isinstance(bucket_id, str) or not bucket_id or len(bucket_id) > 120:
            raise UsageGuardError("Codex quota bucket has an invalid identifier")
        bucket_name = bucket.get("limitName")
        if bucket_name is not None and (not isinstance(bucket_name, str) or len(bucket_name) > 160):
            raise UsageGuardError("Codex quota bucket has an invalid name")

        windows = []
        for window_name in ("primary", "secondary"):
            # A null window means the service reports no window for this bucket.
            raw_window = bucket.get(window_name)
            if raw_window is None:
                continue
            if not isinstance(raw_window, dict):
                raise UsageGuardError("Codex quota window has an invalid structure")
            used = _finite_number(raw_window.get("usedPercent"), "used percentage",
                                  minimum=0, maximum=100)
            duration = _optional_number(raw_window.get("windowDurationMins"),
                                        "window duration", minimum=0)
            reset = _optional_number(raw_window.get("resetsAt"), "reset time", minimum=0)
            remaining = 100.0 - used
            windows.append({
                "name": window_name,
                "used_percent": used,
                "remaining_percent": remaining,
                "window_duration_mins": duration,
                "resets_at": reset,
            })
            remaining_values.append(remaining)

        if windows:
            normalized.append({"limit_id": bucket_id, "limit_name": bucket_name,
                               "windows": windows})

    if not remaining_values:
        raise UsageGuardError("Codex returned no available quota windows")
    return {
        "protocol": PROTOCOL,
        "source": USAGE_METHOD,
        "captured_at": captured_at,
        "min_remaining_percent": min(remaining_values),
        "buckets": normalized,
    }


def _subscription_env():
    # Reuse the project's API-key stripping and provider check. It reads only
    # Codex's non-secret config settings; credential files are left to the CLI.
    parent = Path(__file__).resolve().parents[1]
    import sys

    parent_text = str(parent)
    if parent_text not in sys.path:
        sys.path.insert(0, parent_text)
    from local_runtime import subscription_environment

    env = subscription_environment()
    for name in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"):
        env.pop(name, None)
    return env


def _app_server_rate_limits_read(timeout_seconds=MAX_RPC_SECONDS):
    """Issue one read-only app-server RPC, bounded to at most twenty seconds."""
    timeout_seconds = _finite_number(timeout_seconds, "RPC timeout", minimum=0.01,
                                     maximum=MAX_RPC_SECONDS)
    binary = CODEX_BIN
    if not binary.is_file():
        raise UsageGuardError("local Codex app-server executable is unavailable")
    try:
        env = _subscription_env()
        process = subprocess.Popen(
            [str(binary), "app-server"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env,
            bufsize=0,
        )
    except Exception as error:
        raise UsageGuardError("could not start the local Codex app-server") from error

    selector = selectors.DefaultSelector()
    try:
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout_seconds
        pending = bytearray()

        def send(message):
            wire = json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
            process.stdin.write(wire)
            process.stdin.flush()

        def receive(request_id):
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise UsageGuardError("Codex quota read timed out")
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    raise UsageGuardError("Codex app-server closed before returning quota")
                pending.extend(chunk)
                while b"\n" in pending:
                    line, _, rest = pending.partition(b"\n")
                    pending[:] = rest
                    if not line.strip():
                        continue
                    try:
                        message = json.loads(line)
                    except (UnicodeDecodeError, json.JSONDecodeError) as error:
                        raise UsageGuardError("Codex app-server returned invalid JSON") from error
                    if not isinstance(message, dict):
                        raise UsageGuardError("Codex app-server returned an invalid message")
                    if message.get("id") == request_id:
                        return message

        send({"method": "initialize", "id": 1, "params": {
            "clientInfo": {"name": "shinka_quota_guard", "title": "Shinka quota guard",
                           "version": "1.0.0"},
        }})
        initialized = receive(1)
        if "error" in initialized or not isinstance(initialized.get("result"), dict):
            raise UsageGuardError("Codex app-server initialization failed")
        send({"method": "initialized", "params": {}})
        send({"method": USAGE_METHOD, "id": 2})
        message = receive(2)
        if "error" in message:
            raise UsageGuardError("Codex app-server rejected the quota read")
        result = message.get("result")
        if not isinstance(result, dict):
            raise UsageGuardError("Codex app-server returned no quota result")
        return result
    except UsageGuardError:
        raise
    except Exception as error:
        raise UsageGuardError("local Codex quota RPC failed") from error
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)


def read_usage(*, rpc: Callable[[str], dict] | None = None,
               now: Callable[[], float] = time.time,
               timeout_seconds: float = MAX_RPC_SECONDS) -> dict:
    """Read and sanitize current subscription limits.

    ``rpc`` is an injection point for deterministic tests and must return the
    result object of ``account/rateLimits/read``. Production uses the local
    Codex app-server and never calls a model.
    """
    try:
        response = rpc(USAGE_METHOD) if rpc is not None else _app_server_rate_limits_read(timeout_seconds)
    except UsageGuardError:
        raise
    except Exception as error:
        raise UsageGuardError("Codex quota service could not be read") from error
    return _normalize_usage(response, now())


def _atomic_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".tmp-{os.getpid()}-{time.monotonic_ns()}")
    try:
        with temp.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get("protocol") != PROTOCOL:
        raise UsageGuardError("cached Codex quota snapshot has an invalid protocol")
    captured_at = _finite_number(snapshot.get("captured_at"), "cached capture time", minimum=0)
    buckets = snapshot.get("buckets")
    if not isinstance(buckets, list):
        raise UsageGuardError("cached Codex quota snapshot has invalid buckets")
    remaining_values = []
    for bucket in buckets:
        if not isinstance(bucket, dict) or not isinstance(bucket.get("limit_id"), str):
            raise UsageGuardError("cached Codex quota snapshot has an invalid bucket")
        windows = bucket.get("windows")
        if not isinstance(windows, list):
            raise UsageGuardError("cached Codex quota snapshot has invalid windows")
        for window in windows:
            if not isinstance(window, dict) or window.get("name") not in ("primary", "secondary"):
                raise UsageGuardError("cached Codex quota snapshot has an invalid window")
            used = _finite_number(window.get("used_percent"), "cached used percentage",
                                  minimum=0, maximum=100)
            remaining = _finite_number(window.get("remaining_percent"),
                                       "cached remaining percentage", minimum=0, maximum=100)
            if not math.isclose(remaining, 100.0 - used, rel_tol=0, abs_tol=1e-9):
                raise UsageGuardError("cached Codex quota snapshot is inconsistent")
            remaining_values.append(remaining)
    if not remaining_values:
        raise UsageGuardError("cached Codex quota snapshot has no available windows")
    minimum = _finite_number(snapshot.get("min_remaining_percent"),
                             "cached minimum remaining percentage", minimum=0, maximum=100)
    if not math.isclose(minimum, min(remaining_values), rel_tol=0, abs_tol=1e-9):
        raise UsageGuardError("cached Codex quota snapshot has an inconsistent minimum")
    if snapshot.get("source") != USAGE_METHOD:
        raise UsageGuardError("cached Codex quota snapshot has an invalid source")
    return {**snapshot, "captured_at": captured_at,
            "min_remaining_percent": minimum}


def _existing_stop(stop_path):
    try:
        data = json.loads(stop_path.read_text(encoding="utf-8"))
        reason = data.get("reason") if isinstance(data, dict) else None
    except Exception:
        reason = None
    return reason if isinstance(reason, str) and reason else "existing_stop_request"


def _write_stop(stop_path, *, reason, now, snapshot=None, error_type=None):
    payload = {"protocol": PROTOCOL, "reason": reason, "requested_at": float(now())}
    if snapshot is not None:
        payload["quota"] = {"captured_at": snapshot["captured_at"],
                            "min_remaining_percent": snapshot["min_remaining_percent"]}
    if error_type is not None:
        payload["error_type"] = str(error_type)[:120]
    _atomic_json(stop_path, payload)


def _acquire_lock(lock_file, deadline, monotonic):
    stream = lock_file.open("a+")
    while True:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return stream
        except BlockingIOError:
            remaining = deadline - monotonic()
            if remaining <= 0:
                stream.close()
                return None
            time.sleep(min(0.05, remaining))


def gate(run, min_remaining_percent=DEFAULT_MIN_REMAINING_PERCENT,
         max_age_seconds=DEFAULT_MAX_AGE_SECONDS, *,
         now: Callable[[], float] = time.time,
         rpc: Callable[[str], dict] | None = None,
         monotonic: Callable[[], float] = time.monotonic) -> dict:
    """Allow a request only with a fresh quota snapshot at or above threshold.

    Parallel bridge processes serialize through a per-run ``flock`` and share
    ``quota-usage.json``. A read/structure/lock failure writes a durable stop
    request; callers must treat :class:`UsageStopped` as terminal for the run.
    """
    threshold = _finite_number(min_remaining_percent, "minimum remaining percentage",
                               minimum=0, maximum=100)
    max_age = _finite_number(max_age_seconds, "maximum snapshot age", minimum=0,
                             maximum=86400)
    run = Path(run)
    if not run.is_dir():
        raise UsageGuardError("run directory is unavailable for quota checks")

    quota_path = run / "quota-usage.json"
    stop_path = run / "night-stop-request.json"
    lock_path = run / ".usage-guard.lock"
    deadline = monotonic() + MAX_GATE_SECONDS
    lock = _acquire_lock(lock_path, deadline, monotonic)
    if lock is None:
        _write_stop(stop_path, reason="quota_lock_timeout", now=now)
        raise UsageStopped("quota check lock timed out; new model requests are stopped")

    try:
        if stop_path.exists():
            raise UsageStopped(f"run has a stop request: {_existing_stop(stop_path)}")

        snapshot = None
        if quota_path.exists():
            try:
                cached = _validate_snapshot(json.loads(quota_path.read_text(encoding="utf-8")))
                age = now() - cached["captured_at"]
                if 0 <= age <= max_age:
                    snapshot = cached
            except UsageGuardError:
                _write_stop(stop_path, reason="invalid_cached_quota", now=now)
                raise UsageStopped("cached Codex quota data is invalid; new model requests are stopped")
            except Exception as error:
                _write_stop(stop_path, reason="invalid_cached_quota", now=now,
                            error_type=type(error).__name__)
                raise UsageStopped("cached Codex quota data could not be read; new model requests are stopped") from error

        if snapshot is None:
            remaining_time = deadline - monotonic()
            if remaining_time <= 0:
                _write_stop(stop_path, reason="quota_read_timeout", now=now)
                raise UsageStopped("quota read deadline expired; new model requests are stopped")
            try:
                snapshot = read_usage(rpc=rpc, now=now,
                                      timeout_seconds=min(MAX_RPC_SECONDS, remaining_time))
            except Exception as error:
                _write_stop(stop_path, reason="quota_read_failed", now=now,
                            error_type=type(error).__name__)
                raise UsageStopped("Codex quota could not be verified; new model requests are stopped") from error
            # A lock waiter may have requested stop while this RPC was in progress.
            if stop_path.exists():
                raise UsageStopped(f"run has a stop request: {_existing_stop(stop_path)}")
            _atomic_json(quota_path, snapshot)

        if snapshot["min_remaining_percent"] < threshold:
            _write_stop(stop_path, reason="quota_below_threshold", now=now,
                        snapshot=snapshot)
            raise UsageStopped(
                f"Codex quota remaining is below {threshold:g}%; new model requests are stopped"
            )
        # Recheck at the point where the bridge is about to issue its request.
        if stop_path.exists():
            raise UsageStopped(f"run has a stop request: {_existing_stop(stop_path)}")
        return snapshot
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()

