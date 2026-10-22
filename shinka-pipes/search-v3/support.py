"""Read-only dependencies for SEARCH-v3; never compile or evaluate on import."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_dependencies(include_active=False):
    guard = json.loads((ROOT / "source-guard.json").read_text())
    checked = {}
    for name, expected in guard["files"].items():
        if name.endswith("active-run.json") and not include_active:
            continue  # A run pointer is evidence, not an evaluator dependency.
        if digest(PARENT / name) != expected:
            raise ValueError(f"preserved dependency changed: {name}")
        checked[name] = expected
    return checked


def reference():
    verify_dependencies()
    path = PARENT / "evaluator-fast/reference.py"
    spec = importlib.util.spec_from_file_location("_search_v3_reference", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.check_reference()  # 33 pinned support files; no held-out inputs.
    return module


def frozen_v2(name):
    previous = sys.path[:]
    try:
        return reference().load_frozen(name)
    finally:
        # Legacy modules prepend their own root. Keep imports in this namespace.
        sys.path[:] = previous


def native_cache():
    reference()
    previous = sys.path[:]
    try:
        sys.path.insert(0, str(PARENT / "evaluator-native"))
        from cache import native_binary
        return native_binary()  # Called only during a future explicit evaluation.
    finally:
        sys.path[:] = previous
