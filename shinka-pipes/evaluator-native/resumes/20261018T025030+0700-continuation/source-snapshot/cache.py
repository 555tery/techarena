"""Content-addressed cache of the fixed native checker, never evaluation results."""

from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

from build_native import BASE, ROOT, build, check_reference, digest


@lru_cache(maxsize=1)
def toolchain():
    compiler = shutil.which("g++")
    if not compiler:
        raise ValueError("g++ unavailable")
    data = {"compiler": compiler, "version": subprocess.run([compiler, "--version"], capture_output=True,
             text=True, timeout=30, check=True).stdout, "compiler_sha256": digest(Path(compiler).resolve()),
            "platform": platform.platform(), "machine": platform.machine(),
            "environment_sha256": hashlib.sha256(json.dumps(dict(os.environ), sort_keys=True).encode()).hexdigest()}
    if platform.system() == "Darwin":
        clang = subprocess.run(["xcrun", "--find", "clang++"], capture_output=True, text=True, timeout=30, check=True).stdout.strip()
        data["actual_clang_sha256"] = digest(Path(clang).resolve())
        data["sdk"] = subprocess.run(["xcrun", "--show-sdk-build-version"], capture_output=True,
                                     text=True, timeout=30, check=True).stdout.strip()
    return data


def native_binary():
    check_reference()
    key_data = {"adapter_sha256": digest(ROOT / "native_runner.cpp"),
                "builder_sha256": digest(ROOT / "build_native.py"),
                "cache_version_sha256": digest(ROOT / "cache.py"),
                "official_sha256": digest(BASE / "task/vendor/interactor.cpp"),
                "testlib_sha256": digest(BASE / "task/vendor/testlib.h"),
                "toolchain": toolchain(), "flags": ["-O2", "-std=c++17", "-pipe", "-pthread"]}
    key = hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    cache = ROOT / "cache"
    cache.mkdir(exist_ok=True)
    target = cache / key
    if not target.exists():
        with tempfile.TemporaryDirectory(prefix="native-build-", dir=cache) as temporary:
            directory = Path(temporary) / "artifact"
            binary = build(directory)
            (directory / "cache-key.json").write_text(json.dumps(key_data, indent=2) + "\n")
            try:
                directory.rename(target)
            except FileExistsError:
                pass
    metadata = json.loads((target / "build.json").read_text())
    if (json.loads((target / "cache-key.json").read_text()) != key_data
            or digest(target / "native_runner") != metadata["binary_sha256"]
            or digest(target / "official_checker.cpp") != metadata["transformed_source_sha256"]):
        raise ValueError("native build cache checksum mismatch; refusing to use binary")
    return target / "native_runner", key
