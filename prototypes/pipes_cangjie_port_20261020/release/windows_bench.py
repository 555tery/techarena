"""Paired native-Windows benchmark; Python standard library only.

Example (from this directory):
  py -3 windows_bench.py --cpp solution-cpp.exe --cj solution-cj.exe --tests tests --out windows-results.json
  py -3 windows_bench.py --cpp solution-cpp.exe --cj solution-cj.exe --tests tests --out windows-results.json --resume
  py -3 windows_bench.py --tests tests --select "*heavy*.in" --repeat 3 --out windows-heavy.json

This is an independent direct-protocol checker, not the official interactor.
CPU means whole-process user+kernel time, including runtime termination. Never
divide it by CPU count. The 5 s / 256 MiB limits are reported, not enforced.
Wall time includes driver/pipe delays and is only a watchdog. Memory counters
are queried after the last reply, before final zero, and again after exit; if
post-exit peaks are unavailable, a below-limit observation is NOT a full-life
memory pass. The controller's occupancy array is outside the measured process.

No GC/heap environment knobs are set. Inherited CJ/MRT runtime overrides other
than cjProcessorNum are refused; cjProcessorNum=1 is set for both children.
Affinity is applied before the suspended primary thread is resumed. On systems
with processor groups the mask applies to the process's current/default group;
this runner does not implement cross-group CPU selection or child-process sums.
Windows execution has not been verified on the development Mac.

Exit codes: 0 = parity/physics and strict CPU <5 s / both memory peaks <256 MiB
confirmed; 1 = protocol/parity failure; 2 = a resource limit failed;
3 = resource coverage unconfirmed; 130 = interrupted. Protocol failures take
precedence over resource failures, which take precedence over unknown coverage.
The default 240 s wall watchdog is not the CPU limit.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import queue
import struct
import subprocess
import sys
import tempfile
import threading
import time

SCHEMA = "pipes-cangjie-windows-bench-v1"
MIB = 1024 * 1024


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(MIB), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def parse_test(path):
    tokens = path.read_text(encoding="ascii").split()
    if len(tokens) < 2:
        raise ValueError("missing weight/command count")
    weight, n = float(tokens[0]), int(tokens[1])
    commands = list(map(int, tokens[2:]))
    if len(commands) == n + 1 and commands[-1] == 0:
        commands.pop()
    if not 0 < n <= 200000 or len(commands) != n:
        raise ValueError("invalid command count")
    if not 0 <= weight < float("inf"):
        raise ValueError("invalid nonnegative weight")
    active = [False]
    for command in commands:
        if command > 0:
            if command > 40:
                raise ValueError("placement length outside 1..40")
            active.append(True)
        elif command < 0:
            pid = -command
            if pid >= len(active) or not active[pid]:
                raise ValueError("input removes an inactive/unknown PID")
            active[pid] = False
        else:
            raise ValueError("zero occurs inside command stream")
    return weight, commands


def save_json(path, data):
    """Same-directory atomic replacement; initial existing files need --resume."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


class WindowsAPI:
    def __init__(self):
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.psapi = ctypes.WinDLL("psapi", use_last_error=True)
        DWORD, HANDLE, BOOL = wintypes.DWORD, wintypes.HANDLE, wintypes.BOOL
        SIZE_T, LPVOID = ctypes.c_size_t, ctypes.c_void_p

        class Security(ctypes.Structure):
            _fields_ = [("nLength", DWORD), ("lpSecurityDescriptor", LPVOID), ("bInheritHandle", BOOL)]

        class Startup(ctypes.Structure):
            _fields_ = [("cb", DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR)] + [
                (name, DWORD) for name in ("dwX", "dwY", "dwXSize", "dwYSize", "dwXCountChars", "dwYCountChars", "dwFillAttribute", "dwFlags")
            ] + [("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD), ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
                 ("hStdInput", HANDLE), ("hStdOutput", HANDLE), ("hStdError", HANDLE)]

        class StartupEx(ctypes.Structure):
            _fields_ = [("StartupInfo", Startup), ("lpAttributeList", LPVOID)]

        class ProcessInfo(ctypes.Structure):
            _fields_ = [("hProcess", HANDLE), ("hThread", HANDLE), ("dwProcessId", DWORD), ("dwThreadId", DWORD)]

        class FileTime(ctypes.Structure):
            _fields_ = [("low", DWORD), ("high", DWORD)]

        class Memory(ctypes.Structure):
            _fields_ = [("cb", DWORD), ("PageFaultCount", DWORD)] + [(name, SIZE_T) for name in (
                "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]

        self.Security, self.StartupEx, self.ProcessInfo = Security, StartupEx, ProcessInfo
        self.FileTime, self.Memory = FileTime, Memory
        signatures = {
            "CreatePipe": ([ctypes.POINTER(HANDLE), ctypes.POINTER(HANDLE), ctypes.POINTER(Security), DWORD], BOOL),
            "SetHandleInformation": ([HANDLE, DWORD, DWORD], BOOL),
            "CloseHandle": ([HANDLE], BOOL),
            "InitializeProcThreadAttributeList": ([LPVOID, DWORD, DWORD, ctypes.POINTER(SIZE_T)], BOOL),
            "UpdateProcThreadAttribute": ([LPVOID, DWORD, SIZE_T, LPVOID, SIZE_T, LPVOID, LPVOID], BOOL),
            "DeleteProcThreadAttributeList": ([LPVOID], None),
            "CreateProcessW": ([wintypes.LPCWSTR, wintypes.LPWSTR, LPVOID, LPVOID, BOOL, DWORD, LPVOID,
                                wintypes.LPCWSTR, ctypes.POINTER(StartupEx), ctypes.POINTER(ProcessInfo)], BOOL),
            "GetProcessAffinityMask": ([HANDLE, ctypes.POINTER(SIZE_T), ctypes.POINTER(SIZE_T)], BOOL),
            "SetProcessAffinityMask": ([HANDLE, SIZE_T], BOOL),
            "ResumeThread": ([HANDLE], DWORD),
            "WaitForSingleObject": ([HANDLE, DWORD], DWORD),
            "GetExitCodeProcess": ([HANDLE, ctypes.POINTER(DWORD)], BOOL),
            "TerminateProcess": ([HANDLE, wintypes.UINT], BOOL),
            "GetProcessTimes": ([HANDLE] + [ctypes.POINTER(FileTime)] * 4, BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = arguments, result
        self.psapi.GetProcessMemoryInfo.argtypes = [HANDLE, ctypes.POINTER(Memory), DWORD]
        self.psapi.GetProcessMemoryInfo.restype = BOOL

    @staticmethod
    def checked(result):
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())

    def cpu(self, handle):
        try:
            creation, exit_time, kernel, user = [self.FileTime() for _ in range(4)]
            self.checked(self.kernel.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)))
            ticks = lambda value: (value.high << 32) | value.low
            user_ticks, kernel_ticks = ticks(user), ticks(kernel)
            return {"available": True, "user_100ns": user_ticks, "kernel_100ns": kernel_ticks,
                    "user_s": user_ticks / 10000000, "kernel_s": kernel_ticks / 10000000,
                    "user_plus_kernel_s": (user_ticks + kernel_ticks) / 10000000,
                    "creation_filetime_100ns": ticks(creation), "exit_filetime_100ns": ticks(exit_time)}
        except OSError as error:
            return {"available": False, "error": str(error), "winerror": error.winerror}

    def memory(self, handle):
        try:
            memory = self.Memory()
            memory.cb = ctypes.sizeof(memory)
            self.checked(self.psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb))
            return {"available": True, "peak_working_set_bytes": memory.PeakWorkingSetSize,
                    "working_set_bytes": memory.WorkingSetSize, "peak_private_commit_bytes": memory.PeakPagefileUsage,
                    "private_commit_bytes": memory.PrivateUsage, "page_faults": memory.PageFaultCount,
                    "private_peak_api_field": "PROCESS_MEMORY_COUNTERS_EX.PeakPagefileUsage"}
        except OSError as error:
            return {"available": False, "error": str(error), "winerror": error.winerror}


class NativeProcess:
    """Keeps the process handle open for post-exit CPU/memory queries."""
    def __init__(self, api, executable, environment, cpu_index):
        import msvcrt  # Windows only; importing this module on Mac remains safe.

        self.api = api
        self.handle = None
        self.stdin = self.stdout = self.stderr = None
        self.metadata = {}
        owned_handles = []
        thread_handle = None
        attributes_initialized = False
        startup = api.StartupEx()
        attribute_storage = None
        try:
            security = api.Security(ctypes.sizeof(api.Security), None, True)
            def pipe():
                read, write = wintypes.HANDLE(), wintypes.HANDLE()
                api.checked(api.kernel.CreatePipe(ctypes.byref(read), ctypes.byref(write), ctypes.byref(security), 0))
                owned_handles.extend([read.value, write.value])
                return read.value, write.value
            child_in, parent_in = pipe()
            parent_out, child_out = pipe()
            parent_err, child_err = pipe()
            for handle in (parent_in, parent_out, parent_err):
                api.checked(api.kernel.SetHandleInformation(handle, 1, 0))
            required = ctypes.c_size_t()
            api.kernel.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(required))
            if not required.value:
                raise ctypes.WinError(ctypes.get_last_error())
            attribute_storage = ctypes.create_string_buffer(required.value)
            startup.lpAttributeList = ctypes.cast(attribute_storage, ctypes.c_void_p)
            api.checked(api.kernel.InitializeProcThreadAttributeList(startup.lpAttributeList, 1, 0, ctypes.byref(required)))
            attributes_initialized = True
            inherited = (wintypes.HANDLE * 3)(child_in, child_out, child_err)
            api.checked(api.kernel.UpdateProcThreadAttribute(startup.lpAttributeList, 0, 0x00020002,
                        ctypes.cast(inherited, ctypes.c_void_p), ctypes.sizeof(inherited), None, None))
            startup.StartupInfo.cb = ctypes.sizeof(startup)
            startup.StartupInfo.dwFlags = 0x00000100  # STARTF_USESTDHANDLES
            startup.StartupInfo.hStdInput, startup.StartupInfo.hStdOutput, startup.StartupInfo.hStdError = child_in, child_out, child_err
            process_info = api.ProcessInfo()
            command = ctypes.create_unicode_buffer(subprocess.list2cmdline([str(executable)]))
            environment_block = ctypes.create_unicode_buffer("\0".join(f"{key}={value}" for key, value in
                sorted(environment.items(), key=lambda item: item[0].upper())) + "\0\0")
            flags = 0x00000004 | 0x00000400 | 0x00080000 | 0x08000000  # suspended, unicode env, extended startup, no console
            api.checked(api.kernel.CreateProcessW(str(executable), command, None, None, True, flags,
                        ctypes.cast(environment_block, ctypes.c_void_p), None, ctypes.byref(startup), ctypes.byref(process_info)))
            self.handle, thread_handle = process_info.hProcess, process_info.hThread
            allowed, system = ctypes.c_size_t(), ctypes.c_size_t()
            api.checked(api.kernel.GetProcessAffinityMask(self.handle, ctypes.byref(allowed), ctypes.byref(system)))
            if not allowed.value:
                raise RuntimeError("GetProcessAffinityMask returned an empty/unsupported processor-group mask")
            if cpu_index is not None and cpu_index >= ctypes.sizeof(ctypes.c_size_t) * 8:
                raise ValueError("requested --cpu exceeds the native affinity-mask width")
            mask = allowed.value & -allowed.value if cpu_index is None else 1 << cpu_index
            if not mask & allowed.value:
                raise ValueError("requested --cpu is outside this process's allowed affinity mask")
            api.checked(api.kernel.SetProcessAffinityMask(self.handle, mask))
            actual = ctypes.c_size_t()
            api.checked(api.kernel.GetProcessAffinityMask(self.handle, ctypes.byref(actual), ctypes.byref(system)))
            if actual.value != mask:
                raise RuntimeError("one-CPU affinity could not be verified before ResumeThread")
            self.metadata = {"pid": process_info.dwProcessId, "allowed_affinity_mask_before": hex(allowed.value),
                             "system_affinity_mask": hex(system.value), "affinity_mask": hex(mask),
                             "logical_cpu_in_current_group": mask.bit_length() - 1,
                             "affinity_applied_before_resume": True, "creation_flags": hex(flags),
                             "inherited_handles": "only stdin/stdout/stderr via PROC_THREAD_ATTRIBUTE_HANDLE_LIST"}
            # Transfer parent handles to CRT files before resuming the child.
            for name, handle, mode, os_flag in (("stdin", parent_in, "wb", os.O_WRONLY),
                    ("stdout", parent_out, "rb", os.O_RDONLY), ("stderr", parent_err, "rb", os.O_RDONLY)):
                fd = msvcrt.open_osfhandle(handle, os_flag | os.O_BINARY)
                owned_handles.remove(handle)
                try:
                    setattr(self, name, os.fdopen(fd, mode, buffering=0))
                except BaseException:
                    os.close(fd)
                    raise
            for handle in (child_in, child_out, child_err):
                api.kernel.CloseHandle(handle)
                owned_handles.remove(handle)
            previous_suspend_count = api.kernel.ResumeThread(thread_handle)
            if previous_suspend_count == 0xffffffff:
                raise ctypes.WinError(ctypes.get_last_error())
            if previous_suspend_count != 1:
                raise RuntimeError(f"unexpected primary-thread suspend count: {previous_suspend_count}")
        except BaseException:
            if self.handle:
                api.kernel.TerminateProcess(self.handle, 0xEE)
                api.kernel.WaitForSingleObject(self.handle, 5000)
            self.close()
            raise
        finally:
            if thread_handle:
                api.kernel.CloseHandle(thread_handle)
            if attributes_initialized:
                api.kernel.DeleteProcThreadAttributeList(startup.lpAttributeList)
            for handle in owned_handles:
                api.kernel.CloseHandle(handle)

    def wait(self, timeout):
        result = self.api.kernel.WaitForSingleObject(self.handle, max(0, min(int(timeout * 1000), 0xfffffffe)))
        if result == 0x102:
            raise TimeoutError("process did not exit within wall watchdog")
        if result != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        code = wintypes.DWORD()
        self.api.checked(self.api.kernel.GetExitCodeProcess(self.handle, ctypes.byref(code)))
        return code.value

    def close(self):
        for stream in (self.stdin, self.stdout, self.stderr):
            if stream is not None:
                stream.close()
        if self.handle:
            self.api.kernel.CloseHandle(self.handle)
            self.handle = None


class PipeReader:
    def __init__(self, stream, expected_lines):
        self.stream, self.expected_lines = stream, expected_lines
        self.lines = queue.Queue()
        self.hash = hashlib.sha256()
        self.bytes = self.line_count = 0
        self.error = None
        self.complete = False
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        try:
            while True:
                line = self.stream.readline(4097)
                if not line:
                    break
                self.hash.update(line)
                self.bytes += len(line)
                self.line_count += 1
                if len(line) > 4096:
                    self.error = "stdout line exceeded 4096 bytes"
                if self.line_count <= self.expected_lines + 16:
                    self.lines.put(line)
                else:
                    self.error = "extra stdout beyond protocol response count"
            self.complete = True
        except BaseException as error:
            self.error = repr(error)
        finally:
            self.lines.put(None)


class StderrReader:
    def __init__(self, stream):
        self.stream, self.data, self.bytes = stream, bytearray(), 0
        self.error = None
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        try:
            for chunk in iter(lambda: self.stream.read(4096), b""):
                self.bytes += len(chunk)
                self.data.extend(chunk[:max(0, 65536 - len(self.data))])
        except BaseException as error:
            self.error = repr(error)


def measure(api, executable, path, identity, environment, args):
    started = time.monotonic()
    record = {"status": "error", "started_utc": utc_now(), "processed_commands": 0}
    process = output = errors = None
    successful_exit = False
    try:
        if sha256(executable) != identity["binary_sha256"] or sha256(path) != identity["input_sha256"]:
            raise RuntimeError("binary/input hash changed since experiment inventory")
        weight, commands = parse_test(path)
        record["weight"], record["command_count"] = weight, len(commands)
        process = NativeProcess(api, executable, environment, args.cpu)
        record.update(process.metadata)
        output, errors = PipeReader(process.stdout, len(commands)), StderrReader(process.stderr)
        trench = live = peak = 0
        cells, pipes = bytearray(), [None]
        for index, command in enumerate(commands, 1):
            remaining = args.wall_timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError("wall watchdog during protocol; not a CPU-limit result")
            process.stdin.write((str(command) + "\n").encode("ascii"))
            process.stdin.flush()
            line = output.lines.get(timeout=remaining)
            if line is None:
                raise RuntimeError(f"stdout EOF before response {index}")
            if output.error:
                raise RuntimeError(output.error)
            if len(line) > 4096:
                raise ValueError("oversized response line")
            values = [int(token) for token in line.decode("ascii").split()]
            if command > 0:
                if len(values) != 2:
                    raise ValueError(f"placement {index} needs exactly two integers")
                digs, x = values
                if digs < 0 or x < 0:
                    raise ValueError(f"negative placement/dig at {index}")
                trench += 20 * digs
                if not x + command <= trench <= 100000000:
                    raise ValueError(f"placement {index} outside excavated trench/cap")
                cells.extend(b"\0" * (trench - len(cells)))
                if any(cells[x:x + command]):
                    raise ValueError(f"physical overlap at placement {index}")
                cells[x:x + command] = b"\1" * command
                pipes.append((x, command))
                live += command
                peak = max(peak, live)
            else:
                pid = -command
                if not 0 < pid < len(pipes) or pipes[pid] is None:
                    raise ValueError(f"invalid removal PID at {index}")
                x, length = pipes[pid]
                if values != [x] or not all(cells[x:x + length]):
                    raise ValueError(f"wrong removal coordinate/occupancy at {index}")
                cells[x:x + length] = b"\0" * length
                pipes[pid] = None
                live -= length
            record["processed_commands"] = index
        record["physics"] = {"valid": True, "T": trench, "F": live, "KPI": live / trench if trench else 0.0,
                             "weighted_score": weight * live / trench if trench else 0.0,
                             "peak_live_length": peak, "volume_lower_bound": 20 * ((peak + 19) // 20)}
        # The final reply arrived; zero has not been sent. This is not a
        # runtime barrier: the solver may still finish processing that command.
        record["cpu_before_zero"] = api.cpu(process.handle)
        record["memory_before_zero"] = api.memory(process.handle)
        process.stdin.write(b"0\n")
        process.stdin.flush()
        process.stdin.close()
        remaining = args.wall_timeout - (time.monotonic() - started)
        record["exit_code"] = process.wait(min(args.exit_timeout, max(0, remaining)))
        successful_exit = True
        record["cpu_after_exit"] = api.cpu(process.handle)
        record["memory_after_exit"] = api.memory(process.handle)
        output.thread.join(timeout=5)
        errors.thread.join(timeout=5)
        if record["exit_code"] != 0:
            raise RuntimeError(f"solver exit code {record['exit_code']}")
        if not output.complete or output.error or output.line_count != len(commands):
            raise RuntimeError(f"stdout incomplete/extra: lines={output.line_count}, expected={len(commands)}, error={output.error}")
        if sha256(executable) != identity["binary_sha256"] or sha256(path) != identity["input_sha256"]:
            raise RuntimeError("binary/input hash changed during measurement")
        record["status"] = "ok"
    except (Exception, KeyboardInterrupt) as error:
        record["error"] = {"type": type(error).__name__, "message": str(error)}
        if isinstance(error, KeyboardInterrupt):
            record["interrupted"] = True
    finally:
        if process is not None:
            if not successful_exit:
                record["cpu_at_error"] = api.cpu(process.handle)
                record["memory_at_error"] = api.memory(process.handle)
                # Retain metrics after terminating only the child we launched.
                api.kernel.TerminateProcess(process.handle, 0xEE)
                try:
                    record["exit_code"] = process.wait(5)
                    record["cpu_after_forced_exit"] = api.cpu(process.handle)
                    record["memory_after_forced_exit"] = api.memory(process.handle)
                    record["forced_termination"] = True
                except Exception as error:
                    record["cleanup_error"] = str(error)
            for reader in (output, errors):
                if reader is not None:
                    reader.thread.join(timeout=5)
            process.close()
        if output is not None:
            record["stdout_sha256"] = output.hash.hexdigest()
            record["stdout_bytes"], record["stdout_lines"] = output.bytes, output.line_count
            record["stdout_hash_complete"] = output.complete and not output.thread.is_alive()
        if errors is not None:
            record["stderr"] = bytes(errors.data).decode("utf-8", "replace")
            record["stderr_bytes"], record["stderr_capture_truncated"] = errors.bytes, errors.bytes > len(errors.data)
            record["stderr_reader_error"] = errors.error
        record["wall_s_including_controller"] = time.monotonic() - started
        record["finished_utc"] = utc_now()
    final_cpu = record.get("cpu_after_exit", {})
    if final_cpu.get("available") and successful_exit:
        record["CPU_user_plus_kernel_s"] = final_cpu["user_plus_kernel_s"]
        record["CPU_within_5s"] = final_cpu["user_plus_kernel_s"] < 5.0
        record["CPU_includes_runtime_exit"] = True
    else:
        record["CPU_user_plus_kernel_s"] = None
        record["CPU_within_5s"] = None
        record["CPU_includes_runtime_exit"] = False
    before, after = record.get("memory_before_zero", {}), record.get("memory_after_exit", {})
    for field in ("peak_working_set_bytes", "peak_private_commit_bytes"):
        samples = [sample[field] for sample in (before, after, record.get("memory_at_error", {}), record.get("memory_after_forced_exit", {})) if sample.get("available")]
        observed = max(samples) if samples else None
        full = bool(successful_exit and after.get("available") and after[field] > 0 and
                    (not before.get("available") or after[field] >= before[field]))
        label = field.removesuffix("_bytes")
        record[label + "_MiB_observed"] = observed / MIB if observed is not None else None
        record[label + "_full_lifetime_counter_available"] = full
        record[label + "_256MiB_assessment"] = ("fail" if observed is not None and observed >= 256 * MIB
                                                else "pass" if full else "unconfirmed")
    memory_assessments = [record[field + "_256MiB_assessment"] for field in ("peak_working_set", "peak_private_commit")]
    record["resource_limit_assessment"] = (
        "fail" if record["CPU_within_5s"] is False or "fail" in memory_assessments
        else "pass" if record["CPU_within_5s"] is True and memory_assessments == ["pass", "pass"]
        else "unconfirmed")
    return record


def latest_records(data):
    return {(record["test"], record["repeat"], record["language"]): record for record in data["records"]}


def update_pairs(data):
    latest = latest_records(data)
    pairs = []
    for test in data["configuration"]["tests"]:
        for repeat in range(1, data["configuration"]["repeat"] + 1):
            cpp, cj = (latest.get((test["id"], repeat, language)) for language in ("cpp", "cj"))
            pair = {"test": test["id"], "repeat": repeat, "status": "incomplete"}
            if cpp and cj and cpp["status"] != "running" and cj["status"] != "running":
                if cpp["status"] == cj["status"] == "ok":
                    pair["stdout_sha256_equal"] = cpp["stdout_sha256"] == cj["stdout_sha256"] and cpp["stdout_bytes"] == cj["stdout_bytes"]
                    pair["physics_and_KPI_equal"] = cpp["physics"] == cj["physics"]
                    pair["status"] = "pass" if pair["stdout_sha256_equal"] and pair["physics_and_KPI_equal"] else "mismatch"
                    assessments = [cpp["resource_limit_assessment"], cj["resource_limit_assessment"]]
                    pair["resource_limit_assessment"] = "fail" if "fail" in assessments else "pass" if assessments == ["pass", "pass"] else "unconfirmed"
                else:
                    pair["status"] = "error"
            pairs.append(pair)
    data["pairs"] = pairs
    data["summary"] = {status: sum(pair["status"] == status for pair in pairs) for status in ("pass", "mismatch", "error", "incomplete")}
    data["summary"]["pair_pass_means"] = "byte-identical answers and valid independent physics/KPI; resource limits assessed separately"
    data["resource_summary_latest_attempts"] = {
        language: {status: sum(record.get("resource_limit_assessment") == status for key, record in latest.items() if key[2] == language)
                   for status in ("pass", "fail", "unconfirmed")}
        for language in ("cpp", "cj")}
    data["updated_utc"] = utc_now()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cpp", type=Path, default=Path("solution-cpp.exe"))
    parser.add_argument("--cj", type=Path, default=Path("solution-cj.exe"))
    parser.add_argument("--tests", type=Path, default=Path("tests"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--select", action="append", help="relative test glob, repeatable; e.g. '*heavy*.in'")
    parser.add_argument("--wall-timeout", type=float, default=240.0)
    parser.add_argument("--exit-timeout", type=float, default=30.0)
    parser.add_argument("--cpu", type=int, help="logical CPU bit in current group; default lowest allowed")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-errors", action="store_true", help="append new attempts for failed records when resuming")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Native Windows required; Mac timings are neither run nor reported.")
    if (args.repeat < 1 or not math.isfinite(args.wall_timeout) or not math.isfinite(args.exit_timeout)
            or args.wall_timeout <= 0 or args.exit_timeout <= 0 or args.cpu is not None and args.cpu < 0):
        parser.error("repeat/timeouts must be positive and cpu nonnegative")
    if args.retry_errors and not args.resume:
        parser.error("--retry-errors requires --resume")
    if args.out.exists() != args.resume:
        parser.error("existing output requires --resume; --resume requires existing output")
    executables = {"cpp": args.cpp.resolve(), "cj": args.cj.resolve()}
    for path in executables.values():
        if not path.is_file():
            parser.error(f"missing executable: {path}")
    root = args.tests.resolve()
    paths = sorted(root.rglob("*.in")) if root.is_dir() else [root]
    paths = [(path.relative_to(root).as_posix() if root.is_dir() else path.name, path) for path in paths]
    paths = [(name, path) for name, path in paths if not args.select or any(fnmatch.fnmatchcase(name, pattern) for pattern in args.select)]
    if not paths or any(not path.is_file() for _, path in paths):
        parser.error("no selected .in tests")
    environment = dict(os.environ)
    inherited_runtime = {key: value for key, value in environment.items() if key.lower().startswith(("cj", "mrt_"))}
    forbidden = [key for key in inherited_runtime if key.lower() != "cjprocessornum"]
    if forbidden:
        parser.error("unset inherited runtime overrides before benchmark: " + ", ".join(sorted(forbidden)))
    for key in list(environment):
        if key.lower() == "cjprocessornum":
            del environment[key]
    environment["cjProcessorNum"] = "1"
    runtime_paths = set(executables["cj"].parent.glob("*.dll"))
    if environment.get("CANGJIE_HOME"):
        runtime_paths.update((Path(environment["CANGJIE_HOME"]) / "runtime" / "lib").rglob("*.dll"))
    configuration = {"repeat": args.repeat, "wall_timeout_s": args.wall_timeout, "exit_timeout_s": args.exit_timeout,
                     "requested_cpu": args.cpu, "script_sha256": sha256(Path(__file__).resolve()),
                     "executables": {language: {"path": str(path), "sha256": sha256(path)} for language, path in executables.items()},
                     "tests": [{"id": name, "path": str(path), "sha256": sha256(path)} for name, path in paths],
                     "runtime_environment_set": {"cjProcessorNum": "1"}, "inherited_runtime_environment": inherited_runtime,
                     "runtime_dll_sha256": {str(path.resolve()): sha256(path) for path in sorted(runtime_paths) if path.is_file()},
                     "runtime_dll_inventory_scope": "CJ executable directory and CANGJIE_HOME/runtime/lib; system/other PATH dependencies not exhaustively resolved",
                     "source_sha256": {str(path): sha256(path) for path in (Path(__file__).with_name("solution.cj"), Path(__file__).with_name("solution.cpp")) if path.is_file()},
                     "launch_PATH": environment.get("PATH", environment.get("Path", "")), "CANGJIE_HOME": environment.get("CANGJIE_HOME")}
    if args.resume:
        data = json.loads(args.out.read_text(encoding="utf-8"))
        if data.get("schema") != SCHEMA or data.get("configuration") != configuration:
            parser.error("resume refused: schema/configuration/binary/input/source/script hashes differ; choose a fresh --out")
    else:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                cpu_model = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError as error:
            cpu_model = f"unavailable: {error}"
        data = {"schema": SCHEMA, "created_utc": utc_now(), "configuration": configuration, "records": [],
                "host": {"platform": platform.platform(), "CPU_model": cpu_model, "logical_CPU_count": os.cpu_count(),
                         "python": sys.version, "python_pointer_bits": struct.calcsize("P") * 8},
                "measurement": "whole process user+kernel, affinity before resume, independent direct protocol; not official interactor",
                "limitations": ["Windows runner not executed on development Mac", "process-tree CPU not accumulated",
                                "default/current processor group only", "wall is controller-inclusive watchdog, not solver CPU",
                                "memory passes require available nonzero post-exit peak counters; otherwise unconfirmed",
                                "5s/256MiB assessed without hard resource caps; official memory accounting may differ",
                                "SDK version on contest server remains unknown"]}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        update_pairs(data)
        save_json(args.out, data)
    api = WindowsAPI()
    for test_index, (test_id, path) in enumerate(paths):
        for repeat in range(1, args.repeat + 1):
            # Alternate launch order to avoid always warming the same runtime second.
            order = ("cpp", "cj") if (test_index + repeat) % 2 else ("cj", "cpp")
            for language in order:
                previous = latest_records(data).get((test_id, repeat, language))
                if previous and (previous["status"] == "ok" or previous["status"] == "error" and not args.retry_errors):
                    continue
                identity = {"binary_sha256": configuration["executables"][language]["sha256"],
                            "input_sha256": next(test["sha256"] for test in configuration["tests"] if test["id"] == test_id)}
                entry = {"test": test_id, "repeat": repeat, "language": language,
                         "attempt": 1 + sum(record["test"] == test_id and record["repeat"] == repeat and record["language"] == language for record in data["records"]),
                         "status": "running", **identity}
                data["records"].append(entry)
                update_pairs(data)
                save_json(args.out, data)
                entry.update(measure(api, executables[language], path, identity, environment, args))
                update_pairs(data)
                save_json(args.out, data)
                print(test_id, repeat, language, entry["status"], "CPU=", entry.get("CPU_user_plus_kernel_s"), "error=", entry.get("error"), flush=True)
                if entry.get("interrupted"):
                    return 130
    update_pairs(data)
    save_json(args.out, data)
    print(json.dumps(data["summary"], ensure_ascii=False), flush=True)
    print(json.dumps(data["resource_summary_latest_attempts"], ensure_ascii=False), flush=True)
    if data["summary"]["pass"] != len(data["pairs"]):
        return 1
    resource_statuses = [record.get("resource_limit_assessment", "unconfirmed") for record in latest_records(data).values()]
    if "fail" in resource_statuses:
        return 2
    if any(status != "pass" for status in resource_statuses):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
